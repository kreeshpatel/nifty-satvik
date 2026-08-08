"""MEASUREMENT (no trial): the swing book's AFTER-TAX return, which has never been computed.

Every published figure for this book is pre-tax. Study 0001's after-tax CAGR is committed (18.16%
against a 21.73% gross); the Bhanushali book's does not exist, so the two have never been compared
in the same units and the destination book's headline is not comparable to anything.

Why it is not simply "subtract 20%". `nq.runner.research.after_tax_curve` pays the STCG bill **out
of the book each calendar year**, so the tax stops compounding — money paid to the exchequer in 2018
is not available to earn returns from 2019 on. That is strictly worse, and more honest, than netting
the whole bill off the final value, and it is what pre-registration 0001 §5.4 requires.

The gap between the two codebases is shape, not arithmetic. `after_tax_curve` wants
``{"equity_curve": [{"date","equity"}...], "trades": [{"exit_date","pnl"}...]}``. The swing harness
returns ``curve`` as a **pd.Series**, uses **``net_pnl``** (proceeds − cash_out, already net of both
cost legs and STT) rather than ``pnl``, and — a genuine trap — its ``trades`` key is an integer
*count*, not the trade list. The per-trade records only exist in the caller-supplied ``ledger``.

Two books are measured, because they are different configurations and only one of them trades:
  * **base-swing** — `backtest()` at bare defaults. The certified run of record (Sharpe 1.132 /
    CAGR 24.7% / DSR 0.894 at n_trials 114). All grades, no discipline, no scaled exit.
  * **live (config P)** — A-only + LIVE_DISCIPLINE + LIVE_EXIT + LIVE_STALENESS, i.e. what the
    Saturday cron actually runs. Adopted on owner override; it fails its pre-registered 2022-26
    gate at 0.91 against a 1.04 bar and carries a −39.5% drawdown.

STCG at 20% is the right bracket: swing holds are weeks. Caveats inherited from the tax module —
calendar year approximates the fiscal year, no loss carry-forward, and no business-income treatment.

    python pipelines/diagnostics/diag_swing_after_tax.py
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
from nq.runner.research import _after_tax_cagr, after_tax_curve  # noqa: E402
from run_bhanushali_cron import LIVE_DISCIPLINE, LIVE_EXIT, LIVE_STALENESS  # noqa: E402
from run_bhanushali_faithful import EQ0  # noqa: E402
from run_bhanushali_path1 import corrected_universe  # noqa: E402

STCG = 0.20
OUT_JSON = ROOT / "diagnostics" / "research" / "swing_after_tax.json"
OUT_MD = ROOT / "diagnostics" / "research" / "swing_after_tax.md"


def to_bt(m: dict, ledger: list) -> dict:
    """Swing harness output -> the {equity_curve, trades} shape the tax module expects.

    `net_pnl` is renamed to `pnl`, not recomputed: it is already proceeds − cash_out, net of both
    cost legs, which is the correct base for a realised-gain tax. Rows without an exit are dropped —
    an open position has realised nothing and owes nothing.
    """
    curve = m["curve"].sort_index()
    trades = [{**r, "pnl": float(r["net_pnl"])} for r in ledger
              if r.get("exit_date") is not None and r.get("net_pnl") is not None]
    return {"equity_curve": [{"date": str(d)[:10], "equity": float(v)} for d, v in curve.items()],
            "trades": trades}


def summarise(name: str, m: dict, ledger: list) -> dict:
    bt = to_bt(m, ledger)
    ec = bt["equity_curve"]
    yrs = (pd.Timestamp(ec[-1]["date"]) - pd.Timestamp(ec[0]["date"])).days / 365.25
    gross_cagr = ((ec[-1]["equity"] / EQ0) ** (1 / yrs) - 1) * 100
    at_curve = after_tax_curve(bt, stcg=STCG)
    at_cagr = _after_tax_cagr(bt, EQ0, stcg=STCG)

    eq = pd.Series([e["equity"] for e in ec], index=pd.to_datetime([e["date"] for e in ec]))
    at_eq = pd.Series([e["equity"] for e in at_curve], index=eq.index)
    realised = {}
    for t in bt["trades"]:
        y = int(str(t["exit_date"])[:4])
        realised[y] = realised.get(y, 0.0) + t["pnl"]

    return {
        "book": name,
        "n_closed": len(bt["trades"]),
        "years": round(yrs, 3),
        "gross_cagr_pct": round(gross_cagr, 3),
        "after_tax_cagr_pct": round(at_cagr, 3) if at_cagr is not None else None,
        "tax_wedge_pp": round(gross_cagr - at_cagr, 3) if at_cagr is not None else None,
        "gross_final": round(float(eq.iloc[-1]), 2),
        "after_tax_final": round(float(at_eq.iloc[-1]), 2),
        "gross_maxdd_pct": round(float((eq / eq.cummax() - 1).min()) * 100, 2),
        "after_tax_maxdd_pct": round(float((at_eq / at_eq.cummax() - 1).min()) * 100, 2),
        "realised_gain_by_year": {y: round(v, 2) for y, v in sorted(realised.items())},
        "tax_paid_by_year": {y: round(STCG * max(0.0, v), 2) for y, v in sorted(realised.items())},
        "total_tax_paid": round(sum(STCG * max(0.0, v) for v in realised.values()), 2),
    }


def main() -> int:
    print("building weekly panel ...", flush=True)
    ohlcv, mem = corrected_universe(), load_membership()
    P = R94.prep_weekly_rank(ohlcv)
    a = R94.grade_a_entries(P)

    print("running base-swing (certified defaults) ...", flush=True)
    led_base: list = []
    base = R94.backtest(P, mem, ledger=led_base)

    print("running live config P (A-only + LIVE_*) ...", flush=True)
    led_live: list = []
    live = R94.backtest(P, mem, ledger=led_live, start="2017-01-01", eq0=EQ0, a_grade=a,
                        **LIVE_DISCIPLINE, **LIVE_EXIT, **LIVE_STALENESS)

    rows = [summarise("base-swing (certified, all grades)", base, led_base),
            summarise("live config P (A-only, what trades)", live, led_live)]

    out = {
        "_doc": "MEASUREMENT, no trial. STCG paid annually out of the book (tax stops compounding).",
        "stcg_rate": STCG,
        "initial_capital": EQ0,
        "reproduce": "python pipelines/diagnostics/diag_swing_after_tax.py",
        "caveats": ["calendar year approximates the fiscal year",
                    "no loss carry-forward",
                    "no business-income treatment (slab rates with deductible costs)",
                    "net_pnl is already net of brokerage/STT/slippage; STCG is applied on top"],
        "books": rows,
    }
    OUT_JSON.write_text(json.dumps(out, indent=1), encoding="utf-8")

    md = ["# Swing book — after-tax return (MEASUREMENT, no trial)", "",
          f"STCG {STCG:.0%}, paid out of the book each calendar year so the tax stops compounding.",
          f"Initial capital Rs {EQ0:,.0f}. Reproduce: `python pipelines/diagnostics/diag_swing_after_tax.py`",
          "",
          "| book | closed | gross CAGR | **after-tax CAGR** | wedge | gross MaxDD | after-tax MaxDD | total tax |",
          "|---|--:|--:|--:|--:|--:|--:|--:|"]
    for r in rows:
        md.append(f"| {r['book']} | {r['n_closed']} | {r['gross_cagr_pct']:.2f}% | "
                  f"**{r['after_tax_cagr_pct']:.2f}%** | {r['tax_wedge_pp']:.2f}pp | "
                  f"{r['gross_maxdd_pct']:.1f}% | {r['after_tax_maxdd_pct']:.1f}% | "
                  f"Rs {r['total_tax_paid']:,.0f} |")
    OUT_MD.write_text("\n".join(md) + "\n", encoding="utf-8")

    for r in rows:
        print(f"\n  {r['book']}")
        print(f"    closed {r['n_closed']} | gross CAGR {r['gross_cagr_pct']:.2f}% -> "
              f"AFTER-TAX {r['after_tax_cagr_pct']:.2f}%  (wedge {r['tax_wedge_pp']:.2f}pp)")
        print(f"    MaxDD {r['gross_maxdd_pct']:.1f}% -> {r['after_tax_maxdd_pct']:.1f}% | "
              f"total tax Rs {r['total_tax_paid']:,.0f}")
    print(f"\nwrote {OUT_JSON.relative_to(ROOT)} + .md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
