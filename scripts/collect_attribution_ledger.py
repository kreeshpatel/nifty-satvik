#!/usr/bin/env python3
"""Per-trade ATTRIBUTION LEDGER — one row per trade, what it was made of.

Satvik Brain Phase 1 (Layer 5). MEASUREMENT: no trial, no screen row, nothing adopted.

It joins, for every signal the live book has ever issued, the context recorded AT SIGNAL to the
outcome the book realised, and adds the decomposition that makes a loss readable: the stop width the
R is measured against, the part of the loss the stop was designed to take versus the part filled
beyond it, how far the trade ran each way, and what the index did over the same window.

Sources — all immutable or append-only, nothing re-derived from a mutable working copy:
  * context at signal   <- results/archive/YYYY-MM-DD/signals_today_weekly.json (first appearance)
  * fills / shares      <- results/archive/YYYY-MM-DD/paper_portfolio_weekly.json
  * outcome             <- results/signals_history_weekly.json
  * excursions          <- the OHLCV cache's daily High/Low when it covers the window, else the
                           archived weekly marks. `excursion_basis` says which, because a weekly mark
                           cannot see the intra-week extreme and so UNDERSTATES MAE and MFE. A closed
                           trade the book HELD and still cannot measure is a defect, not a coverage
                           limit (it has committed marks) — see holes().
  * index control       <- the Nifty-50 CSV the book itself uses, which the cron refreshes at runtime;
                           the committed copy ends before inception, so this is a declared hole here

Deterministic: the whole table is rebuilt from the archives every run, so it holds no editable state
and a rerun is a no-op. Rows are labelled `provenance = reconstructed` when they were rebuilt from
snapshots written before this collector existed, and `forward` after it. A reconstructed row is a
record, never forward evidence (`06_habit_ledger_spec.md` §3).

    python scripts/collect_attribution_ledger.py             # rebuild results/attribution_ledger.csv
    python scripts/collect_attribution_ledger.py --validate  # structural coverage only; non-zero on a hole
"""
from __future__ import annotations

import argparse
import glob
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from config import RESULTS_DIR  # noqa: E402
from nq.brain import ledger as L  # noqa: E402

OUT = RESULTS_DIR / "attribution_ledger.csv"
ARCHIVE = RESULTS_DIR / "archive"
HISTORY = RESULTS_DIR / "signals_history_weekly.json"

# The live book's inception. Everything on or after it is in scope; there is nothing before it.
INCEPTION = "2026-07-04"
# Snapshots written before this collector existed are rebuilt and labelled `reconstructed` (owner
# decision 2026-09-25). Rows first seen in a snapshot on or after it accrue as `forward`.
FORWARD_FROM = "2026-09-26"

# Context recorded AT SIGNAL. First non-null wins, so a trail that later moves `stop` cannot rewrite
# what the card said when it was issued.
CONTEXT_FIELDS = ("entry", "stop", "target", "grade", "tier", "crs_rank", "ext_pct_over_sma44",
                  "band_width_pct", "body_ratio", "signal_conviction", "stop_week_low",
                  "buy_zone_low", "buy_zone_high", "record_would_skip_as_extended", "pattern",
                  "bought_date", "corporate_actions")

OUTCOME_FIELDS = ("status", "r_multiple", "return_pct", "exit_reason", "hold_days", "close_date",
                  "close_price")

# Fields this ledger CANNOT fill, each with the reason. Declaring a hole is an admission that
# something is permanently unmeasurable here, so it costs a sentence. It is not a way to be quiet.
DECLARED_HOLES: dict[str, str] = {
    "judge_*": "The 0125 informed-judge verdicts are SEALED until the first review read (>= 2 quarters "
               "from 2026-08-01). nq.brain.io refuses the log; the columns are added when the seal lifts.",
    "owner_action / owner_note": "No source exists yet — owner overrides are not recorded anywhere the "
                                 "cron can read. The decision-memo file records a rubric stamp, not the "
                                 "owner's own call.",
    "management events": "CLOSING (2026-09-29): the engine now emits them and the cron persists "
                         "results/brain/management_events.jsonl; this ledger joins them as n_partial_books, "
                         "n_stop_ratchets, n_trail_updates, fraction_booked and halted. The hole stays listed "
                         "until the first scan has written the stream, and closes only forward. "
                         "Partial bookings and stop ratchets were not archived per event; only the "
                         "position's current state is snapshotted weekly. A child-row stream needs the "
                         "engine to emit them (06_habit_ledger_spec.md §1.3).",
    "cash_at_signal / slots_free": "The envelope carries book-level cash, not the cash and free seats at "
                                   "the moment each card was funded.",
    "nifty_same_window_pct": "No COMMITTED index series covers the live book: the index CSV ends "
                             "2026-07-03 against a first trade on 2026-07-06, and window_pct correctly "
                             "refuses an uncovered window rather than returning a confident 0.0%. The "
                             "weekly cron refreshes the CSV at runtime, so this populates in CI when the "
                             "refresh lands before the collector; it cannot be filled from the repo.",
}


def _snapshots() -> list[tuple[str, dict]]:
    """(as_of, envelope) for every archived weekly snapshot, oldest first."""
    out = []
    for p in sorted(glob.glob(str(ARCHIVE / "*" / "signals_today_weekly.json"))):
        as_of = Path(p).parent.name[:10]
        try:
            out.append((as_of, json.loads(Path(p).read_text(encoding="utf-8"))))
        except Exception:  # noqa: BLE001 — one unreadable snapshot must not lose the rest
            continue
    return out


def _positions() -> dict[tuple[str, str], dict]:
    """(ticker, entry_date) -> the first archived paper position, for shares and the funded size."""
    out: dict[tuple[str, str], dict] = {}
    for p in sorted(glob.glob(str(ARCHIVE / "*" / "paper_portfolio_weekly.json"))):
        try:
            d = json.loads(Path(p).read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            continue
        for tkr, pos in (d.get("positions") or {}).items():
            key = (tkr, str(pos.get("entry_date") or "")[:10])
            if key[1] and key not in out:
                out[key] = {"shares": pos.get("shares"), "position_size": pos.get("position_size"),
                            "entry_price_filled": pos.get("entry_price")}
    return out


def _outcomes() -> dict[str, list[tuple[str, dict]]]:
    """Per-ticker (signal_date, outcome) from the append-only history."""
    out: dict[str, list[tuple[str, dict]]] = {}
    if not HISTORY.exists():
        return out
    for h in json.loads(HISTORY.read_text(encoding="utf-8")):
        t, sd = h.get("ticker"), h.get("signal_date")
        if t and sd:
            out.setdefault(t, []).append((str(sd)[:10], {k: h.get(k) for k in OUTCOME_FIELDS}))
    return out


def _match_outcome(outs: dict[str, list[tuple[str, dict]]], ticker: str, sig_date: str) -> dict:
    """The outcome whose signal_date is nearest the episode anchor, within one episode window."""
    best, best_d = {}, L.EPISODE_DAYS + 1
    for sd, o in outs.get(ticker, []):
        d = abs((pd.Timestamp(sd) - pd.Timestamp(sig_date)).days)
        if d < best_d:
            best, best_d = o, d
    return best


def _prices() -> dict[str, pd.DataFrame]:
    try:
        from nq.data.ohlcv import OHLCV_CACHE, load_ohlcv_cache
        return dict(load_ohlcv_cache(OHLCV_CACHE))
    except Exception:  # noqa: BLE001 — excursions are best-effort and null when unavailable
        return {}


def _snapshot_marks() -> dict[str, pd.Series]:
    """Per-ticker weekly mark series from the archived snapshots — a COMMITTED price fallback.

    Why this exists (2026-09-27). All four excursion columns were null on every row, and the cause was
    not a swallowed exception: both price sources end before the book's inception. The local OHLCV cache
    stops at 2026-06-29 and the committed index CSV at 2026-07-03, against a first trade on 2026-07-06,
    so the daily-bar window selected zero rows and MAE/MFE stayed None while reading as "best effort".

    These marks are `positions[ticker].current_price`, one print per weekly snapshot. They are a WEAKER
    instrument than daily bars and the rows built from them say so in `excursion_basis`: a weekly mark
    cannot see the intra-week extreme, so MAE and MFE computed this way are **understatements** —
    bounded by the true excursion, never beyond it. That direction is the safe one for a drawdown
    statistic, and it is stated rather than assumed.
    """
    marks: dict[str, dict] = {}
    for q in sorted(glob.glob(str(ROOT / "results" / "archive" / "*" / "paper_portfolio_weekly.json"))):
        name = Path(q).parent.name
        if "__rerun" in name:
            continue                      # a rerun repeats its parent's as-of; it is not a new print
        try:
            pos = json.loads(Path(q).read_text(encoding="utf-8")).get("positions", {})
        except Exception:                 # noqa: BLE001 — a malformed snapshot must not kill the ledger
            continue
        for tkr, v in pos.items():
            px_ = v.get("current_price")
            if px_ is not None:
                marks.setdefault(tkr, {})[pd.Timestamp(name)] = float(px_)
    return {tkr: pd.Series(d).sort_index() for tkr, d in marks.items() if d}


EVENTS = ROOT / "results" / "brain" / "management_events.jsonl"


def _events() -> dict[tuple[str, str], list[dict]] | None:
    """Management events keyed by (ticker, entry date), or None when the stream does not exist yet.

    The engine keys events as `ticker:<fill date>`; this ledger keys trades as `ticker:<signal date>`.
    The join is therefore on (ticker, bought_date), and a trade that finds no events is counted rather
    than silently given zeros — "no events" and "did not join" must not read the same.
    """
    if not EVENTS.is_file():
        return None
    out: dict[tuple[str, str], list[dict]] = {}
    for ln in EVENTS.read_text(encoding="utf-8").splitlines():
        if ln.strip():
            e = json.loads(ln)
            out.setdefault((str(e.get("ticker")), str(e.get("entry_date"))[:10]), []).append(e)
    return out


def _index() -> pd.Series:
    try:
        import run_bhanushali_weekly_crs as CRS
        s = pd.read_csv(CRS.NIFTY50_CSV, parse_dates=["date"]).set_index("date")["nifty50_close"]
        s.index = pd.DatetimeIndex(s.index).normalize()
        return s[~s.index.duplicated(keep="last")].sort_index().astype(float)
    except Exception:  # noqa: BLE001
        return pd.Series(dtype=float)


def build() -> pd.DataFrame:
    snaps = _snapshots()
    seen = L.first_seen(snaps, CONTEXT_FIELDS)
    episodes = L.collapse_episodes(seen, CONTEXT_FIELDS)
    outs, pos, px, idx = _outcomes(), _positions(), _prices(), _index()
    evs = _events()
    marks = _snapshot_marks()

    rows = []
    for (tkr, sig), ctx in sorted(episodes.items()):
        if sig < INCEPTION:
            continue
        o = _match_outcome(outs, tkr, sig)
        entry = ctx.get("entry")
        stop = ctx.get("stop")
        bought = str(ctx.get("bought_date") or "")[:10] or None
        row = {
            "trade_id": f"{tkr}:{sig}", "ticker": tkr, "signal_date": sig, "bought_date": bought,
            "as_of_snapshot": ctx.get("as_of_snapshot"),
            "provenance": "forward" if str(ctx.get("as_of_snapshot") or "") >= FORWARD_FROM else "reconstructed",
            **{f: ctx.get(f) for f in CONTEXT_FIELDS if f not in ("bought_date",)},
            "stop_width_pct_card": L.stop_width_pct(entry, stop),
            **{f: o.get(f) for f in OUTCOME_FIELDS},
            **L.decompose_r(o.get("r_multiple")),
            # Always present, so the schema does not depend on how fresh the price cache happens to be.
            "mae_r": None, "mfe_r": None, "capture_of_mfe": None, "nifty_same_window_pct": None,
            "excursion_basis": None, "mark_prints": 0,
        }
        # The denominator R was measured against, and how far the card's stop is from it. The card and
        # the engine are different sources; where they disagree, the ENGINE basis is the one that makes
        # `r_multiple` mean what it says (red-team, 2026-09-25).
        row["stop_width_pct_engine"] = L.engine_implied_width_pct(o.get("return_pct"), o.get("r_multiple"))
        row["width_gap_pct"] = L.width_gap_pct(row["stop_width_pct_card"], row["stop_width_pct_engine"])
        row["stop_width_pct"] = row["stop_width_pct_engine"] or row["stop_width_pct_card"]
        row["stop_width_basis"] = "engine" if row["stop_width_pct_engine"] else "card"
        # A card that was never bought is not a trade. Three states, so "no outcome" cannot read as a
        # defect for a signal that simply never filled (5 of the 46 rows).
        row["state"] = ("closed" if o.get("exit_reason") else ("open" if bought else "not_entered"))
        row["has_corporate_action"] = bool(ctx.get("corporate_actions"))
        # Management events (the capital book's stream). None = no stream yet, which is different
        # from 0 = the stream exists and this trade had no event.
        if evs is None or not bought:
            row.update(n_partial_books=None, n_stop_ratchets=None, n_trail_updates=None,
                       fraction_booked=None, halted=None)
        else:
            es = evs.get((tkr, bought), [])
            books = [e for e in es if e.get("event_type") == "partial_book"]
            row.update(
                n_partial_books=len(books),
                n_stop_ratchets=sum(e.get("event_type") == "stop_ratchet" for e in es),
                n_trail_updates=sum(e.get("event_type") == "trail_update" for e in es),
                fraction_booked=round(sum(float(e.get("fraction") or 0) for e in books), 6),
                halted=any(e.get("event_type") == "halt" for e in es))
        row["corporate_actions"] = json.dumps(ctx.get("corporate_actions")) if ctx.get("corporate_actions") else None
        p = pos.get((tkr, bought or ""), {})
        row.update({k: p.get(k) for k in ("shares", "position_size", "entry_price_filled")})

        start, end = bought or sig, str(o.get("close_date") or "")[:10] or None
        df = px.get(tkr)
        if df is not None and len(df) and entry and stop and end:
            w = df[(pd.DatetimeIndex(df.index) >= pd.Timestamp(start))
                   & (pd.DatetimeIndex(df.index) <= pd.Timestamp(end))]
            if len(w):
                row.update(L.excursions_r(w["High"], w["Low"], entry=float(entry), stop=float(stop)))
                row["excursion_basis"] = "daily_hl"
        # Fallback: the archived weekly marks, which are committed and therefore always available for a
        # trade the book actually held. Only when the daily bars did not cover the window.
        if row["mae_r"] is None and entry and stop and end:
            m = marks.get(tkr)
            if m is not None and len(m):
                w = m[(m.index >= pd.Timestamp(start)) & (m.index <= pd.Timestamp(end))]
                # the entry and the exit are known realised prices and belong in the path; without the
                # entry a trade that only ever went favourable would report no MAE at all
                path = [float(entry)] + [float(v) for v in w.to_numpy()]
                if o.get("close_price") is not None:
                    path.append(float(o["close_price"]))
                row["mark_prints"] = int(len(w))
                if len(path) > 1:
                    row.update(L.excursions_r(path, path, entry=float(entry), stop=float(stop)))
                    row["excursion_basis"] = "weekly_marks"
        row["capture_of_mfe"] = L.capture_of_mfe(o.get("r_multiple"), row.get("mfe_r"))
        if len(idx) and end:
            row["nifty_same_window_pct"] = L.window_pct(idx, start, end)
        rows.append(row)

    df = pd.DataFrame(rows)
    return df.sort_values(["signal_date", "ticker"]).reset_index(drop=True) if len(df) else df


def holes(df: pd.DataFrame) -> list[str]:
    """Defects only — things that mean a row cannot be read. `--validate` exits non-zero on these.

    A card that never filled is NOT a defect (it has no outcome because it was never a trade), and a
    card-vs-engine width disagreement is handled rather than unresolved: both bases are recorded and the
    engine one is used. Those are notes, not holes — an alarm that is always on is not an alarm.
    """
    out: list[str] = []
    if df is None or not len(df):
        return ["ledger is empty — no archived signal on or after the inception"]
    entered = df[df["state"] != "not_entered"] if "state" in df else df
    closed = df[df["exit_reason"].notna()]
    for col in ("entry", "stop", "stop_width_pct"):
        n = int(df[col].isna().sum())
        if n:
            out.append(f"{n} row(s) missing {col} — a trade whose R denominator is unknown")
    if len(entered):
        n = int(entered["status"].isna().sum())
        if n:
            out.append(f"{n} entered trade(s) with no outcome in the history")
    if len(closed):
        n = int(closed["r_multiple"].isna().sum())
        if n:
            out.append(f"{n} closed trade(s) with no r_multiple")
        # EXCURSIONS ARE NO LONGER ALLOWED TO BE SILENTLY NULL (2026-09-27).
        # Every one of these columns read null on every row for weeks while the run printed
        # "excursions 0/46 (price-cache depth)" as if that were a property of the cache rather than a
        # missing measurement. A closed trade the book actually HELD has committed weekly marks, so a
        # null there is a defect and fails --validate. A closed trade the book never funded has no
        # committed price basis at all (0146: the closed history is the uncapped tracker's), which is a
        # stated condition, not a defect — see notes().
        if "mark_prints" in closed:
            held = closed[closed["mark_prints"].fillna(0) > 0]
            n = int(held["mae_r"].isna().sum()) if len(held) else 0
            if n:
                out.append(f"{n} closed trade(s) the book HELD but with no excursion measurement — "
                           f"weekly marks exist for them, so this is a defect, not a coverage limit")
    return out


def notes(df: pd.DataFrame) -> list[str]:
    """Handled conditions worth stating on every run, which are not defects."""
    out: list[str] = []
    if df is None or not len(df):
        return out
    if "n_partial_books" in df:
        if df["n_partial_books"].isna().all():
            out.append("management events: stream absent (results/brain/management_events.jsonl) — "
                       "the hole stays declared until the first scan that writes it")
        else:
            out.append(f"management events joined: {int(df['n_partial_books'].fillna(0).sum())} partial "
                       f"booking(s) across {int((df['n_partial_books'].fillna(0) > 0).sum())} trade(s)")
    if "state" in df:
        n = int((df["state"] == "not_entered").sum())
        if n:
            out.append(f"{n} card(s) never filled — issued, never bought, so they carry no outcome")
    if "mark_prints" in df and "exit_reason" in df:
        closed = df[df["exit_reason"].notna()]
        unheld = closed[closed["mark_prints"].fillna(0) == 0]
        if len(unheld):
            out.append(f"{len(unheld)} closed trade(s) with no committed price basis for excursions — "
                       f"the capital book never funded them, so no archived mark exists "
                       f"({', '.join(sorted(unheld['ticker'].astype(str)))})")
        by_basis = df["excursion_basis"].value_counts(dropna=True).to_dict() if "excursion_basis" in df else {}
        if by_basis:
            out.append("excursion basis: " + ", ".join(f"{k}={v}" for k, v in sorted(by_basis.items()))
                       + " — weekly marks cannot see the intra-week extreme and UNDERSTATE MAE/MFE")
    wide = df[df["width_gap_pct"].notna() & (df["width_gap_pct"] > 5.0)]
    if len(wide):
        out.append(f"{len(wide)} trade(s) where the card's stop width disagrees with the engine's by >5% "
                   f"({', '.join(sorted(wide['ticker'].astype(str)))}) — R is measured on the engine basis")
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--validate", action="store_true", help="report coverage only; non-zero on an undeclared hole")
    ap.add_argument("--out", default=str(OUT))
    args = ap.parse_args(argv)

    df = build()
    n_closed = int(df["exit_reason"].notna().sum()) if len(df) else 0
    problems, remarks = holes(df), notes(df)
    exc = int(df["mae_r"].notna().sum()) if len(df) else 0
    print(f"attribution ledger: {len(df)} trades ({n_closed} closed) | "
          f"reconstructed {int((df['provenance'] == 'reconstructed').sum()) if len(df) else 0} | "
          f"excursions {exc}/{n_closed} closed | declared holes {len(DECLARED_HOLES)}")
    for r in remarks:
        print(f"  note: {r}")
    for p in problems:
        print(f"  ::warning::{p}")
    if args.validate:
        return 1 if problems else 0
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(args.out, index=False)
    print(f"  -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
