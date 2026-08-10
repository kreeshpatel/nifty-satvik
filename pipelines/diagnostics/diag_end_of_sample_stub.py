"""MEASUREMENT (no trial): how much of the swing headline is an unrealised end-of-sample mark?

A red-team pass on 2026-08-09 flagged that both swing books return roughly +31% in 2026 H1 while the
NIFTY 500 TRI is -3.20%, and that a large share of final equity sits in positions that were never
sold — the backtest force-closes whatever is open on the last bar and books it as an `eos` trade at
the closing mark. A mark is not a fill. It has paid no spread, no impact and no STT, and it can be
taken back by the next week's open.

This matters right now for a specific reason: the next planned step is certifying the live
configuration. Certifying a headline that contains an unrealised stub bakes the stub into the
certification, so it has to be priced first.

Two questions, both answered off ONE continuous run per book — never a re-run from a different start,
which would reset the equity peak (the phantom-0.762 defect this programme has already paid for):

  1. **Composition.** What fraction of final equity is `eos` marks rather than realised P&L?
  2. **End-date sensitivity.** Stop the clock at successively earlier dates and re-read the headline.
     A book whose CAGR swings by several points on where you stop is telling you the last stretch is
     doing disproportionate work.

Truncating the END is not the fresh-capital error: it stops the clock on one curve rather than
restarting it. But every end date has *some* open position marked to market, so the comparison is
between end dates, not against an "unmarked" ideal that does not exist.

    python pipelines/diagnostics/diag_end_of_sample_stub.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import run_bhanushali_weekly_rank as R94  # noqa: E402
from nq.data.membership import load_membership  # noqa: E402
from run_bhanushali_cron import LIVE_DISCIPLINE, LIVE_EXIT, LIVE_STALENESS  # noqa: E402
from run_bhanushali_faithful import EQ0  # noqa: E402
from run_bhanushali_path1 import corrected_universe  # noqa: E402

CUTS = ["2026-06-29", "2025-12-31", "2025-06-30", "2024-12-31"]
OUT = ROOT / "diagnostics" / "research" / "end_of_sample_stub.json"


def headline(curve: pd.Series, upto: str) -> dict:
    """CAGR / Sharpe / MaxDD read off a slice of ONE continuous curve, stopped at `upto`."""
    eq = curve[curve.index <= pd.Timestamp(upto)].sort_index()
    if len(eq) < 60:
        return {}
    yrs = (eq.index[-1] - eq.index[0]).days / 365.25
    r = eq.pct_change().dropna()
    dd = float((eq / eq.cummax() - 1).min()) * 100
    return {"upto": upto, "sessions": int(len(eq)),
            "cagr_pct": round(((eq.iloc[-1] / EQ0) ** (1 / yrs) - 1) * 100, 2),
            "sharpe": round(float(r.mean() / r.std() * (252 ** 0.5)), 3),
            "maxdd_pct": round(dd, 2),
            "final_equity": round(float(eq.iloc[-1]), 2)}


def stub(ledger: list, final_equity: float) -> dict:
    """The end-of-sample forced closes: marks, not fills."""
    eos = [r for r in ledger if r.get("reason") == "eos"]
    pnl = sum(float(r["net_pnl"]) for r in eos if r.get("net_pnl") is not None)
    return {"n_eos_positions": len(eos),
            "eos_net_pnl": round(pnl, 2),
            "eos_pnl_share_of_final_equity_pct": round(pnl / final_equity * 100, 2),
            "eos_exit_dates": sorted({str(r.get("exit_date"))[:10] for r in eos})}


def run_book(name: str, m: dict, ledger: list) -> dict:
    curve = m["curve"].sort_index()
    cuts = [h for h in (headline(curve, c) for c in CUTS) if h]
    full = cuts[0]
    return {"book": name,
            "stub": stub(ledger, full["final_equity"]),
            "by_end_date": cuts,
            "cagr_swing_full_vs_2025_pp": round(cuts[0]["cagr_pct"] - cuts[1]["cagr_pct"], 2)}


def main() -> int:
    print("building weekly panel ...", flush=True)
    ohlcv, mem = corrected_universe(), load_membership()
    P = R94.prep_weekly_rank(ohlcv)
    a = R94.grade_a_entries(P)

    books = []
    lb: list = []
    print("base-swing ...", flush=True)
    books.append(run_book("base-swing (certified)", R94.backtest(P, mem, ledger=lb), lb))
    ll: list = []
    print("live config P ...", flush=True)
    live = R94.backtest(P, mem, ledger=ll, start="2017-01-01", eq0=EQ0, a_grade=a,
                        **LIVE_DISCIPLINE, **LIVE_EXIT, **LIVE_STALENESS)
    books.append(run_book("live config P (what trades)", live, ll))

    out = {"_doc": "MEASUREMENT, no trial. End-date sensitivity and unrealised-mark composition.",
           "reproduce": "python pipelines/diagnostics/diag_end_of_sample_stub.py",
           "note": ("`eos` rows are positions force-closed on the last bar at the closing mark. They "
                    "have paid no spread, no impact and no STT beyond the modelled cost, and no such "
                    "trade was ever executed. Every end date carries some marked-open position; the "
                    "comparison is between end dates, not against an unmarked ideal."),
           "books": books}
    OUT.write_text(json.dumps(out, indent=1), encoding="utf-8")

    for b in books:
        s = b["stub"]
        print(f"\n  {b['book']}")
        print(f"    end-of-sample forced closes: {s['n_eos_positions']} positions, "
              f"net P&L Rs {s['eos_net_pnl']:,.0f} = {s['eos_pnl_share_of_final_equity_pct']:.1f}% "
              f"of final equity")
        print(f"    {'stop the clock at':<20s} {'CAGR':>8s} {'Sharpe':>8s} {'MaxDD':>9s}")
        for h in b["by_end_date"]:
            print(f"    {h['upto']:<20s} {h['cagr_pct']:>7.2f}% {h['sharpe']:>8.3f} {h['maxdd_pct']:>8.1f}%")
        print(f"    CAGR swing, full vs stopping 2025-12-31: {b['cagr_swing_full_vs_2025_pp']:+.2f}pp")
    print(f"\nwrote {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
