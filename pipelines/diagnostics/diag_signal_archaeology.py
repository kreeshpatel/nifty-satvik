"""Why did a name NOT get bought in a given week? Walk the funnel and name the gate.

MEASUREMENT. Zero trials. **Zero screen-ledger rows** — this reads the engine and the committed
capped ledger only, never the banked label dataset `research/substrate/context_windows.parquet`, so
it spends no multiplicity under the standing rule at `diagnostics/research/label_screen_ledger.md`.

## Why this exists

The owner watched HINDALCO signal on the week ending 2026-08-07 at 9.76% extension, *after* an +8.74%
week, when the genuine touch had been the week ending 07-31 (low within 1.28% of the 44-week line).
The natural question — "why didn't it signal a week earlier?" — had no answer short of reading the
engine. That is the wrong price for a question a trader will ask every week.

The book funds roughly **2.6% of activated signals** (168 of 6,359; `MONTECARLO_null.md`), with
19,728 fill attempts abandoned for cash. So "we didn't buy it" has many possible causes and they are
not interchangeable: not in the index, no setup, setup but outranked, ranked but too extended,
ranked and priced but no cash. Each implies a different response, and three of them imply *no*
response at all.

## What it reports

For one `(ticker, signal week)` — the FIRST gate that rejected it, in funnel order:

    universe -> weekly bars -> PIT membership -> setup formed -> Grade A (top-5 CRS) -> price filters -> cash

For a whole week — every signal the funnel produced, its CRS rank, its extension, and which of them
were funded. That is the view that answers "were there better names than the one we bought?"

    python pipelines/diagnostics/diag_signal_archaeology.py --week 2026-07-31
    python pipelines/diagnostics/diag_signal_archaeology.py --week 2026-07-31 --ticker HINDALCO
    python pipelines/diagnostics/diag_signal_archaeology.py --week 2024-03-01 --universe corrected

## Which universe

`--universe live` (default) reads the live cron cache, which is the only one carrying recent weeks.
`--universe corrected` reads the pinned research universe (pin + backfill + aliases) that the 0094
run of record was measured on — it ends 2026-06-29, so it cannot answer a question about August 2026.
They are different universes and produce different books; the choice is printed in every readout.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
from nq.data.membership import load_membership, ticker_in_index_on  # noqa: E402
from nq.data.ohlcv import load_ohlcv_cache  # noqa: E402

import run_bhanushali_weekly_rank as R94  # noqa: E402

OUT = ROOT / "diagnostics" / "research" / "signal_archaeology.json"
CAPPED = ROOT / "research" / "exports" / "bhanushali_weekly_rank_0094_trades.csv"
TOP_N = 5                       # Grade A = top-5 by CRS distance in the setup week (grade_a_entries)

# entry_win tuple layout, from run_bhanushali_weekly_rank.py:332-333. Named here because three
# positional reads of the same tuple in one file is how an off-by-one becomes a wrong answer.
W_EDAYS, W_STOP, W_HIGH, W_CRS, W_SMA, W_ORIGIN = 0, 1, 2, 3, 4, 5


def _iso(ts) -> tuple[int, int]:
    c = pd.Timestamp(ts).isocalendar()
    return int(c.year), int(c.week)


def _load(universe: str) -> dict:
    if universe == "corrected":
        from run_bhanushali_path1 import corrected_universe   # noqa: PLC0415 — heavy import
        return corrected_universe()
    return load_ohlcv_cache()


def _funded_keys() -> set[tuple[str, str]]:
    """(ticker, iso-week) pairs the CAPPED book actually funded — the 0119 join."""
    if not CAPPED.exists():
        return set()
    cap = pd.read_csv(CAPPED)
    if "iw" in cap.columns and "tkr" in cap.columns:
        return set(zip(cap["tkr"].astype(str), cap["iw"].astype(str)))
    col = "entry_date" if "entry_date" in cap.columns else cap.columns[1]
    return {(str(t), "%d-%02d" % _iso(d)) for t, d in zip(cap["tkr"], cap[col])}


def _signals_for_week(P: dict, sig_week: pd.Timestamp) -> list[dict]:
    """Every entry window whose SIGNAL week is `sig_week` (the completed week that decided it).

    The engine keys `entry_win` by the first day of the ENTRY week, which is the week AFTER the
    signal week. Getting this backwards is the single easiest way to answer the wrong question.
    """
    want = _iso(sig_week)
    rows: list[dict] = []
    for t, s in P.items():
        dates = s["dates"]
        for e0, win in s["entry_win"].items():
            entry_day = pd.Timestamp(dates[e0])
            # the signal week is the completed week strictly before the entry week
            sig_fri = entry_day - pd.Timedelta(days=entry_day.weekday() + 3)
            if _iso(sig_fri) != want:
                continue
            sma = float(win[W_SMA])
            hi = float(win[W_HIGH])
            rows.append({
                "ticker": t, "signal_week_end": str(sig_fri.date()),
                "entry_week_start": str(entry_day.date()),
                "crs_dist": round(float(win[W_CRS]), 5),
                "stop": round(float(win[W_STOP]), 2),
                "signal_week_high": round(hi, 2),
                "sma44": round(sma, 2),
                "ext_at_high_pct": (round((hi / sma - 1) * 100, 2) if sma > 0 else None),
                "origin": int(win[W_ORIGIN]),
            })
    rows.sort(key=lambda r: -r["crs_dist"])
    for i, r in enumerate(rows, 1):
        r["crs_rank"] = i
        r["grade"] = "A" if i <= TOP_N else "B"
    return rows


def _verdict(ticker: str, rows: list[dict], P: dict, ohlcv: dict, mem, sig_week: pd.Timestamp,
             funded: set) -> dict:
    """The first gate that rejected `ticker` in funnel order."""
    t = ticker.upper()
    if t not in ohlcv or ohlcv[t] is None or not len(ohlcv[t]):
        return {"ticker": t, "gate": "NOT IN UNIVERSE",
                "detail": "no OHLCV series for this name in the selected universe"}
    if t not in P:
        return {"ticker": t, "gate": "INSUFFICIENT HISTORY",
                "detail": "prep_weekly_rank dropped it — fewer than the daily bars a 44-week SMA needs"}
    # `.date()` is load-bearing: membership periods are datetime.date, and pandas refuses to compare
    # a Timestamp against one rather than coercing.
    if mem is not None and not ticker_in_index_on(t, sig_week.date(), mem):
        return {"ticker": t, "gate": "NOT IN PIT INDEX MEMBERSHIP",
                "detail": f"not an index member on {sig_week.date()}"}

    mine = [r for r in rows if r["ticker"] == t]
    if not mine:
        return {"ticker": t, "gate": "NO SETUP",
                "detail": ("the funnel formed no entry window from this signal week — no qualifying "
                           "touch-and-hold of the rising 44-week line")}

    r = mine[0]
    # Key on the ENTRY week, both sides. The capped ledger records `entry_date`, and the entry week
    # is the one AFTER the signal week — looking it up by signal week misses by exactly one week,
    # which is the same off-by-one this whole tool exists to expose.
    key = (t, "%d-%02d" % _iso(r["entry_week_start"]))
    if key in funded:
        return {"ticker": t, "gate": "FUNDED", "detail": "the book bought it", **r}
    if r["grade"] != "A":
        return {"ticker": t, "gate": "NOT GRADE A", **r,
                "detail": (f"signalled, but ranked {r['crs_rank']} of {len(rows)} by CRS distance "
                           f"that week — only the top {TOP_N} are traded")}
    return {"ticker": t, "gate": "GRADE A, NOT FUNDED", **r,
            "detail": ("it cleared selection. It was then stopped by an entry-price filter "
                       "(ext_cap / band) or by the cash gate — the book funds ~2.6% of activated "
                       "signals. Re-run the capped backtest for this week to separate the two.")}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--week", required=True, help="SIGNAL week end (any date inside it)")
    ap.add_argument("--ticker", default=None, help="one name; omit for the whole week")
    ap.add_argument("--universe", choices=("live", "corrected"), default="live")
    args = ap.parse_args()

    sig_week = pd.Timestamp(args.week)
    ohlcv = _load(args.universe)
    mem = load_membership()
    P = R94.prep_weekly_rank(ohlcv)
    rows = _signals_for_week(P, sig_week)
    funded = _funded_keys()

    # A week beyond the data produces zero signals, which reads identically to "no setup formed"
    # — the exact wrong answer this tool exists to prevent. Say which it is.
    last_bar = max((pd.Timestamp(s["dates"][-1]) for s in P.values()), default=None)
    beyond = last_bar is not None and sig_week.date() > last_bar.date()
    if beyond:
        print(f"!! REQUESTED WEEK IS BEYOND THE DATA. This universe ends {last_bar.date()}; you "
              f"asked about {sig_week.date()}.\n   Zero signals here means NO DATA, not 'no setup "
              f"formed'. The local cache is the research pin; recent weeks live only in the cron's "
              f"cache.\n")

    print(f"universe={args.universe} ({len(ohlcv)} names) | signal week {sig_week.date()} "
          f"(ISO {_iso(sig_week)[0]}-{_iso(sig_week)[1]:02d})")
    print(f"signals produced: {len(rows)} | Grade A = top {TOP_N} by CRS distance\n")

    if rows:
        print(f"  {'#':>3} {'ticker':<14s} {'CRS':>9s} {'ext@high':>9s} {'grade':>6s}  funded")
        for r in rows[:25]:
            key = (r["ticker"], "%d-%02d" % _iso(r["entry_week_start"]))
            f = "YES" if key in funded else "-"
            print(f"  {r['crs_rank']:>3} {r['ticker']:<14s} {r['crs_dist']:>9.4f} "
                  f"{(r['ext_at_high_pct'] if r['ext_at_high_pct'] is not None else float('nan')):>8.2f}% "
                  f"{r['grade']:>6s}  {f}")
        if len(rows) > 25:
            print(f"  ... {len(rows) - 25} more")

    verdicts = []
    if args.ticker:
        v = _verdict(args.ticker, rows, P, ohlcv, mem, sig_week, funded)
        verdicts.append(v)
        print(f"\n{v['ticker']}: {v['gate']}")
        print(f"  {v['detail']}")
        if "crs_rank" in v:
            print(f"  CRS {v['crs_dist']} -> rank {v['crs_rank']} of {len(rows)} | "
                  f"ext at signal-week high {v['ext_at_high_pct']}% | entry week "
                  f"{v['entry_week_start']}")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({
        "_doc": ("MEASUREMENT. Zero trials, zero screen-ledger rows: reads the engine and the "
                 "committed capped ledger, never the banked label dataset."),
        "reproduce": (f"python pipelines/diagnostics/diag_signal_archaeology.py --week {args.week}"
                      + (f" --ticker {args.ticker}" if args.ticker else "")
                      + f" --universe {args.universe}"),
        "universe": args.universe, "n_names": len(ohlcv),
        "signal_week_end": str(sig_week.date()), "top_n_grade_a": TOP_N,
        "n_signals": len(rows), "signals": rows, "verdicts": verdicts,
        "data_last_bar": (str(last_bar.date()) if last_bar is not None else None),
        "week_beyond_data": bool(beyond),
        "capped_ledger_present": CAPPED.exists(),
    }, indent=1, default=str), encoding="utf-8")
    print(f"\nwrote {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
