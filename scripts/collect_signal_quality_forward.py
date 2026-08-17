"""Forward per-signal QUALITY collector — the data-gathering half of the signal-quality forward wall
(`forward/prereg_signal_quality.md`, 4-axis family, owner-frozen 2026-08-17).

It joins, for every FRESH signal the book has ever issued, the four quality axes recorded **at signal
time** to that signal's realized outcome, and writes one analyzable table. It is BUILD-ONLY and holds
the same forward seal as the breadth-50 logger: it reports structural coverage (row/field counts)
and **never** the axis→outcome relationship — the per-axis forward-R read is the wall's to compute
later (`nq.runner.research.adjudicate_family`), never this collector's, never during accrual.

Sources (all immutable / append-only — no re-derivation):
  * quality flags at signal  <- results/archive/YYYY-MM-DD/signals_today_weekly.json (first-fresh row)
  * realized outcome         <- results/signals_history_weekly.json (r_multiple / exit_reason)
  * touch_depth (Q2, min ext <- OHLCV via nq.data.weekly.build_weekly_panel, best-effort; null when the
    over the trailing pullback)   ticker's bars don't cover the pre-signal window (deepens over time)

Deterministic: rebuilds the whole table from the archives each run, so it carries no editable state.

    python scripts/collect_signal_quality_forward.py            # rebuild results/signal_quality_forward.csv
    python scripts/collect_signal_quality_forward.py --validate # structural coverage only, no performance
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

from config import RESULTS_DIR  # noqa: E402

# Inception of the pre-registration. Signals FRESH before this are SEED rows (labelled, reported
# separately) so they can never quietly become in-sample. Do not move this date (prereg §2).
INCEPTION = "2026-08-17"
OUT = RESULTS_DIR / "signal_quality_forward.csv"
ARCHIVE = RESULTS_DIR / "archive"
HISTORY = RESULTS_DIR / "signals_history_weekly.json"

# The four frozen axes' recorded fields + the identity/context columns. body_ratio and
# signal_conviction are absent from the oldest snapshot schema -> null, filled from a later FRESH
# snapshot of the same (ticker, signal_date) if one carries them.
FLAG_FIELDS = ("grade", "body_ratio", "signal_conviction", "crs_rank", "ext_pct_over_sma44",
               "band_width_pct", "entry", "stop")


# The mutable book RE-DATES a signal as it recomputes (PTCIL appeared at 2026-08-07 and again at
# 2026-08-10 — the same economic signal). Same ticker within this many days = one episode, collapsed
# to its earliest (first-fresh) date; genuine re-entries months later stay separate.
EPISODE_DAYS = 16


def _first_fresh_flags() -> dict[tuple[str, str], dict]:
    """Walk archived signal snapshots oldest→newest; record each (ticker, signal_date)'s quality flags
    from its FIRST appearance, backfill any still-null flag from later snapshots of the same signal
    (the schema gained body_ratio/conviction mid-stream), then COLLAPSE re-dating episodes so one
    economic signal is one row (keyed by the first-fresh date, flags merged preferring non-null)."""
    rows: dict[tuple[str, str], dict] = {}
    for snap in sorted(glob.glob(str(ARCHIVE / "*" / "signals_today_weekly.json"))):
        try:
            d = json.loads(Path(snap).read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            continue
        for s in d.get("signals", []):
            key = (s.get("ticker"), s.get("signal_date"))
            if not key[0] or not key[1]:
                continue
            rec = rows.setdefault(key, {"ticker": key[0], "signal_date": key[1]})
            for f in FLAG_FIELDS:
                if rec.get(f) is None and s.get(f) is not None:  # first non-null wins
                    rec[f] = s.get(f)

    # Collapse re-dating episodes: per ticker, walk dates ascending; a date within EPISODE_DAYS of the
    # open episode's anchor merges into it (non-null flags fill gaps), otherwise it opens a new episode.
    episodes: dict[tuple[str, str], dict] = {}
    by_ticker: dict[str, list[str]] = {}
    for (t, sd) in rows:
        by_ticker.setdefault(t, []).append(sd)
    for t, dates in by_ticker.items():
        anchor = None
        for sd in sorted(dates):
            if anchor is not None and (pd.Timestamp(sd) - pd.Timestamp(anchor)).days <= EPISODE_DAYS:
                tgt = episodes[(t, anchor)]
                for f in FLAG_FIELDS:                       # backfill the episode from the later re-date
                    if tgt.get(f) is None and rows[(t, sd)].get(f) is not None:
                        tgt[f] = rows[(t, sd)].get(f)
            else:
                anchor = sd
                episodes[(t, anchor)] = dict(rows[(t, sd)])
    return episodes


def _outcomes() -> dict[str, list[tuple[str, dict]]]:
    """Per-ticker (signal_date, outcome) list from the append-only history. Matched to an episode by
    NEAREST date (the history carries the re-dated signal_date, the episode its first-fresh date)."""
    out: dict[str, list[tuple[str, dict]]] = {}
    if not HISTORY.exists():
        return out
    for h in json.loads(HISTORY.read_text(encoding="utf-8")):
        t, sd = h.get("ticker"), h.get("signal_date")
        if t and sd:
            out.setdefault(t, []).append((sd, {k: h.get(k) for k in
                ("status", "r_multiple", "return_pct", "exit_reason", "hold_days", "close_date")}))
    return out


def _match_outcome(outs: dict[str, list[tuple[str, dict]]], ticker: str, sig_date: str) -> dict:
    """The history outcome whose signal_date is nearest the episode anchor, within EPISODE_DAYS."""
    best, best_d = {}, EPISODE_DAYS + 1
    for sd, o in outs.get(ticker, []):
        d = abs((pd.Timestamp(sd) - pd.Timestamp(sig_date)).days)
        if d < best_d:
            best, best_d = o, d
    return best


def _touch_depth(tickers: set[str], sig_dates: dict[str, list[str]]) -> dict[tuple[str, str], float]:
    """Q2 (frozen): the minimum weekly ext over the 8 weeks ENDING at the signal week — the pullback
    low's extension, not the signal-week ext. Best-effort from OHLCV; null when bars don't cover the
    pre-signal window (thin now, deepens as history accrues). Definitive recompute is the wall's."""
    depth: dict[tuple[str, str], float] = {}
    try:
        from nq.data.ohlcv import OHLCV_CACHE, load_ohlcv_cache
        from nq.data.weekly import build_weekly_panel
        oh = load_ohlcv_cache(OHLCV_CACHE)
    except Exception:  # noqa: BLE001
        return depth
    for tkr in tickers:
        df = oh.get(tkr)
        if df is None or "Close" not in getattr(df, "columns", []) or not len(df):
            continue
        try:
            wp = build_weekly_panel({tkr: df}).sort_values("week_end")
            wp["ext"] = (wp["c"] - wp["sma44"]) / wp["sma44"] * 100.0
            wp["week_end"] = pd.to_datetime(wp["week_end"])
        except Exception:  # noqa: BLE001
            continue
        panel_end = wp["week_end"].max()
        for sd in sig_dates.get(tkr, []):
            # FRESHNESS GUARD: only trust the window when the panel actually reaches the signal week.
            # Stale bars (local cache) would otherwise make tail(8) grab weeks long BEFORE the pullback
            # and report a wrong depth — emit null instead (the wall recomputes definitively from OHLCV).
            if (pd.Timestamp(sd) - panel_end).days > 7:
                continue
            win = wp[wp["week_end"] <= pd.Timestamp(sd)].tail(8)
            if len(win):
                depth[(tkr, sd)] = round(float(win["ext"].min()), 2)
    return depth


def build() -> pd.DataFrame:
    flags = _first_fresh_flags()
    outs = _outcomes()
    tickers = {k[0] for k in flags}
    sig_dates: dict[str, list[str]] = {}
    for t, sd in flags:
        sig_dates.setdefault(t, []).append(sd)
    depth = _touch_depth(tickers, sig_dates)

    recs = []
    for key, rec in flags.items():
        entry, stop = rec.get("entry"), rec.get("stop")
        r_pct = (round((entry - stop) / entry * 100, 2)
                 if isinstance(entry, (int, float)) and isinstance(stop, (int, float)) and entry else None)
        o = _match_outcome(outs, key[0], key[1])
        recs.append({
            "ticker": key[0], "signal_date": key[1],
            "phase": "seed" if key[1] < INCEPTION else "forward",   # prereg §2 seed vs strictly-forward
            "grade": rec.get("grade"),
            "body_ratio": rec.get("body_ratio"),                    # Q1
            "touch_depth_min_ext": depth.get(key),                  # Q2 (best-effort)
            "signal_conviction": rec.get("signal_conviction"),      # Q3
            "crs_rank": rec.get("crs_rank"),                        # Q4
            "ext_at_signal": rec.get("ext_pct_over_sma44"),
            "band_width_pct": rec.get("band_width_pct"),
            "R_pct": r_pct,
            "status": o.get("status"), "r_multiple": o.get("r_multiple"),
            "return_pct": o.get("return_pct"), "exit_reason": o.get("exit_reason"),
            "hold_days": o.get("hold_days"), "close_date": o.get("close_date"),
        })
    df = pd.DataFrame(recs).sort_values(["signal_date", "ticker"]).reset_index(drop=True)
    return df


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--validate", action="store_true",
                    help="structural coverage only (row/field counts); reports NO axis->outcome relationship")
    args = ap.parse_args(argv)

    df = build()
    n = len(df)
    n_closed = int(df["status"].isin(["HIT_STOP", "HIT_TARGET", "CLOSED", "EXIT"]).sum()) if n else 0
    n_fwd = int((df["phase"] == "forward").sum()) if n else 0
    cov = {c: int(df[c].notna().sum()) for c in
           ("body_ratio", "touch_depth_min_ext", "signal_conviction", "crs_rank", "r_multiple")} if n else {}

    if args.validate:
        # Deliberately prints coverage ONLY — no per-axis forward-R, preserving the forward seal.
        print(f"signal-quality collector VALIDATE: {n} signals ({n_fwd} forward / {n - n_fwd} seed) | "
              f"closed {n_closed}")
        print(f"  field coverage: {cov}")
        print("  (structural only — no axis->outcome relationship reported; the wall computes that)")
        return 0

    OUT.write_text(df.to_csv(index=False), encoding="utf-8")
    print(f"signal-quality forward collector: {n} signals ({n_fwd} forward / {n - n_fwd} seed), "
          f"{n_closed} closed -> {OUT}")
    print(f"  field coverage: {cov}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
