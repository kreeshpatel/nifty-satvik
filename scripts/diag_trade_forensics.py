#!/usr/bin/env python3
"""Trade forensics on an archived snapshot — MEASUREMENT, zero trials.

Reproduces, from committed inputs plus a dated price pull, the figures quoted to the owner on
2026-09-08/09 about why the swing book's losers lost:

  * stop decomposition — how much of realised R is the stop working as designed vs the fill past it
    (offline; also pinned exactly by `tests/test_brain_attribution.py`);
  * the matched market control — each trade against the median of the tradeable universe over its
    OWN window, as a percentile. Stopped trades vs still-open ones.

Why a market control at all: a loser-only list re-discovers extension every time (program-laws VIII),
and "it fell" is meaningless if everything fell. The question this answers is whether the losers lost
because the market did or because the names did.

What it does not answer: why an entry failed *before* it failed. Five instruments found that invisible
on this funnel (program-laws I). These are outcome descriptions, not features.

Prices come from the vendor at run time, so decimals can move if the vendor revises history; the
summary records the pull date and the universe size used. Outputs go to `diagnostics/`, never
`results/` (cron output) — the suite guard in `tests/conftest.py` would flag the latter.

    python scripts/diag_trade_forensics.py --as-of 2026-09-04 --end 2026-09-09
"""
from __future__ import annotations

import argparse
import glob
import json
import sys
from datetime import date
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from nq.brain import attribution as A  # noqa: E402
from nq.brain import io as brain_io  # noqa: E402

OUT_BASE = ROOT / "diagnostics" / "research" / "trade_forensics"
PRICE_START = "2026-06-15"


def _snapshot(as_of: str) -> tuple[list[A.ClosedTrade], list[dict], Path]:
    snap = ROOT / "results" / "archive" / as_of
    if not (snap / "signals_history_weekly.json").is_file():
        raise SystemExit(f"no archived snapshot at {snap}")
    envelopes = [brain_io.read_json(p) for p in sorted(
        glob.glob(str(ROOT / "results" / "archive" / "2026-*" / "signals_today_weekly.json")))
        if Path(p).parent.name <= as_of]
    trades = A.with_recorded_stops(
        A.closed_trades(brain_io.read_json(snap / "signals_history_weekly.json")),
        A.recorded_stops(envelopes))
    open_cards = [c for c in brain_io.read_json(snap / "signals_today_weekly.json")["signals"]
                  if c.get("status") == "ACTIVE" and c.get("stop")]
    return trades, open_cards, snap


def funded_split(trades: list, as_of: str) -> dict:
    """Split the stopped cohort by whether the ₹10L CAPITAL book ever actually held the name.

    Added 2026-09-26, after finding 0146. The closed-trade history is the UNCAPPED tracker's, so a
    beyond-stop decomposition over it describes a book that holds no money. A funded name appears in
    the capped snapshots strictly inside its [signal_date, close_date) window — half-open, because a
    position is legitimately absent from the snapshot taken at its own close date (0146).
    """
    snaps = {}
    for q in sorted(glob.glob(str(ROOT / "results" / "archive" / "*" / "paper_portfolio_weekly.json"))):
        name = Path(q).parent.name
        if "__rerun" in name or name > as_of:
            continue                      # a rerun repeats its parent's as-of; it is not an observation
        snaps[name] = set(brain_io.read_json(Path(q)).get("positions", {}))

    groups: dict[str, list] = {"funded": [], "never_funded": [], "undetermined": []}
    for tr in trades:
        inside = [k for k in snaps if str(tr.signal_date)[:10] <= k < str(tr.close_date)[:10]]
        if not inside:
            groups["undetermined"].append(tr)
        elif any(tr.ticker in snaps[k] for k in inside):
            groups["funded"].append(tr)
        else:
            groups["never_funded"].append(tr)

    def cell(rows: list) -> dict:
        return {"n": len(rows), "tickers": [r.ticker for r in rows],
                "realised_r": round(sum(r.r_multiple for r in rows), 3),
                "beyond_stop_r": round(sum(r.beyond_stop_r for r in rows), 3)}

    out = {k: cell(v) for k, v in groups.items()}
    out["n_snapshots_used"] = len(snaps)
    out["reading"] = ("beyond-stop slippage on the book that holds money is the `funded` row. The "
                      "`never_funded` row belongs to the uncapped tracker and no rupee was exposed to "
                      "it. Quoting the total without this split describes the wrong book (0146).")
    return out


def convention_divergence(trades: list) -> dict:
    """Two committed decompositions of the same trades disagree, and neither says it is a convention.

    `nq.brain.attribution.ClosedTrade.beyond_stop_r` is `r + 1` unconditionally, so a loss SHALLOWER
    than the stop contributes a POSITIVE amount that nets against genuine overshoot, against a designed
    loss of −1R per trade. `nq.brain.ledger.decompose_r` instead treats a shallower loss as simply a
    shallower designed loss (`beyond_stop_r = 0`), so it counts adverse overshoot only.

    Both are defensible and they answer slightly different questions. The point of reporting them side
    by side is that a reader cannot currently tell which one a quoted figure used.
    """
    rs = [tr.r_multiple for tr in trades]
    net = sum(r + 1.0 for r in rs)
    adverse = sum(min(r + 1.0, 0.0) for r in rs)
    return {
        "attribution_nets_favourable_fills": {
            "designed_r": round(-1.0 * len(rs), 3), "beyond_stop_r": round(net, 3),
            "source": "nq/brain/attribution.py::ClosedTrade.beyond_stop_r"},
        "ledger_counts_adverse_overshoot_only": {
            "designed_r": round(sum(r if r >= -1 else -1.0 for r in rs), 3),
            "beyond_stop_r": round(adverse, 3),
            "source": "nq/brain/ledger.py::decompose_r"},
        "difference_r": round(net - adverse, 3),
        "what_the_difference_is": ("the favourable overshoots — trades that lost LESS than their stop "
                                  "distance. One convention credits them against the overshoot; the "
                                  "other does not treat them as overshoot at all."),
    }


def ledger_crosscheck(trades: list) -> dict:
    """Per-trade agreement with `results/attribution_ledger.csv`, keyed on (ticker, signal_date).

    Keying on ticker alone is wrong and it bit this study: GESHIP carries TWO ledger rows — a closed
    trade and a later open re-entry — so a ticker-keyed lookup finds the blank open row and reports a
    false MISSING.
    """
    path = ROOT / "results" / "attribution_ledger.csv"
    if not path.is_file():
        return {"available": False}
    import csv as _csv
    # Match on ticker among CLOSED rows. Keying on (ticker, signal_date) looks stricter and is in fact
    # WRONG: signal dates are RESTATED between snapshots (results/archive/drift_log.jsonl), so an
    # as-of-dated forensics row and the current ledger disagree about the date for the same trade —
    # GESHIP reads 2026-07-27 here and 2026-07-24 there. Ticker alone was also wrong, because a name
    # can re-enter and carry a second, still-open row. Closed-rows-by-ticker is the stable join, and
    # the date disagreement is REPORTED rather than silently failing the match.
    led: dict[str, list] = {}
    with open(path, newline="", encoding="utf-8") as fh:
        for row in _csv.DictReader(fh):
            if str(row.get("state")) == "closed":
                led.setdefault(row.get("ticker"), []).append(row)
    rows, absent, restated = [], [], []
    for tr in trades:
        cands = led.get(tr.ticker, [])
        if len(cands) != 1 or not cands[0].get("beyond_stop_r"):
            absent.append({"ticker": tr.ticker, "closed_ledger_rows": len(cands)})
            continue
        r = cands[0]
        if str(r.get("signal_date"))[:10] != str(tr.signal_date)[:10]:
            restated.append({"ticker": tr.ticker, "forensics_signal_date": str(tr.signal_date)[:10],
                             "ledger_signal_date": str(r.get("signal_date"))[:10]})
        v = float(r["beyond_stop_r"])
        rows.append({"ticker": tr.ticker, "forensics": round(tr.beyond_stop_r, 4), "ledger": v,
                     "agrees": abs(v - tr.beyond_stop_r) < 0.02,
                     "explained_by_convention": tr.beyond_stop_r > 0 and v == 0.0})
    return {"available": True, "rows": rows, "absent": absent,
            "signal_date_restated": restated,
            "n_agree": sum(1 for r in rows if r["agrees"]),
            "n_convention_only": sum(1 for r in rows if r["explained_by_convention"]),
            "n_unexplained": sum(1 for r in rows if not r["agrees"]
                                 and not r["explained_by_convention"])}


def _closes(tickers: list[str], end: str) -> dict[str, pd.Series]:
    from nq.data.ohlcv import download_ohlcv
    from scripts.run_cpcv import build_universe
    names = sorted(set(build_universe("current")) | set(tickers))
    print(f"fetching {len(names)} names {PRICE_START}..{end} ...", flush=True)
    # Explicit dates, and min_bars=1: this window is short, and the default floor of 50 would drop
    # every name silently (scripts/check_ohlcv_topup_contract.py).
    px = download_ohlcv(names, start=PRICE_START, end=end, min_bars=1)
    return {t: df["Close"] for t, df in px.items() if "Close" in df.columns and len(df) > 5}


def assert_completed_session(end: str, today: date | None = None) -> None:
    """Refuse a window that ends today or later: that bar may still be trading.

    Found reproducing this script's own first run. On 2026-09-09 the open-position cohort was pulled
    "to 2026-09-09" while that session's bar was incomplete; the vendor dropped it and every window
    silently ended at the 09-08 close. HEG proves it: its reported −60.37% is 258.60/652.50 − 1, the
    09-08 close, not the final 09-09 close (262.75). The figures were right for 09-08 and labelled as
    09-09. A completed session is the only honest end date.
    """
    today = today or date.today()
    if date.fromisoformat(end) >= today:
        raise SystemExit(f"--end {end} is not a completed session (today is {today.isoformat()}); "
                         f"its bar may be partial or silently dropped. Use the last closed session.")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--as-of", required=True, help="archived snapshot date, e.g. 2026-09-04")
    ap.add_argument("--end", required=True, help="window end for still-open positions, YYYY-MM-DD")
    ap.add_argument("--offline", action="store_true", help="stop decomposition only; no price pull")
    ap.add_argument("--out-date", help="write under this date instead of --as-of, so an earlier "
                                       "run's committed record is not rewritten")
    args = ap.parse_args(argv)
    assert_completed_session(args.end)

    trades, open_cards, snap = _snapshot(args.as_of)
    out = OUT_BASE / (args.out_date or args.as_of)
    out.mkdir(parents=True, exist_ok=True)

    decomp = A.stop_decomposition(trades)
    agreement = A.stop_agreement(trades)
    summary: dict = {"as_of": args.as_of, "snapshot": snap.relative_to(ROOT).as_posix(),
                     "stop_decomposition": decomp,
                     "max_stop_disagreement": max(agreement.values()) if agreement else None,
                     "trades": [{"ticker": t.ticker, "r": t.r_multiple, "exit": t.exit_reason,
                                 "stop_source": t.stop_source, "beyond_stop_r": round(t.beyond_stop_r, 4)}
                                for t in trades],
                     "funded_split": funded_split(trades, args.as_of),
                     "convention_divergence": convention_divergence(trades),
                     "ledger_crosscheck": ledger_crosscheck(trades)}
    print(f"stop decomposition: realised {decomp['realised_r']:+.2f}R = designed {decomp['designed_r']:+.2f}R "
          f"+ beyond-stop {decomp['beyond_stop_r']:+.2f}R  ({decomp['n_filled_beyond_stop']}/{decomp['n']} "
          f"filled past the stop; recorded-vs-implied stop max gap {summary['max_stop_disagreement']:.2%})")

    if not args.offline:
        closes = _closes([t.ticker for t in trades] + [c["ticker"] for c in open_cards], args.end)
        rows = []
        cohorts = [("STOPPED", t.ticker, t.signal_date, t.close_date, t.r_multiple) for t in trades]
        for c in open_cards:
            fill = float(c.get("fill_price") or c["entry"])
            risk = fill - float(c["stop"])
            r_now = (float(c["current_price"]) - fill) / risk if risk else None
            cohorts.append(("OPEN", c["ticker"], c["signal_date"], args.end, r_now))
        for group, tkr, t0, t1, r in cohorts:
            s = closes.get(tkr)
            if s is None:
                continue
            res = A.window_excess(s, closes, t0, t1)
            if res:
                rows.append({"group": group, "ticker": tkr, "start": t0, "end": t1, "r": r, **res})
        df = pd.DataFrame(rows)
        df.to_csv(out / "window_control.csv", index=False)
        cohort = {}
        for g in ("STOPPED", "OPEN"):
            sub = df[df.group == g]
            cohort[g] = {"n": int(len(sub)),
                         "median_excess_pct": round(float(sub.excess.median()) * 100, 2),
                         "median_percentile": round(float(sub.percentile.median()), 1),
                         "n_underperformed_universe": int((sub.excess < 0).sum())}
        summary["market_control"] = cohort
        summary["prices"] = {"pulled_on": date.today().isoformat(), "start": PRICE_START, "end": args.end,
                             "universe_series": len(closes)}
        for g, v in cohort.items():
            print(f"{g:8} n={v['n']:>2}  median excess {v['median_excess_pct']:+.2f}%  "
                  f"median percentile {v['median_percentile']:.1f}  underperformed {v['n_underperformed_universe']}/{v['n']}")

    (out / "summary.json").write_text(json.dumps(summary, indent=2, default=str), encoding="utf-8")
    print(f"wrote {out.relative_to(ROOT).as_posix()}/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
