"""MEASUREMENT (no trial): per-calendar-year returns, and an actual count of losing years.

The plan of 2026-08-09 accepts a risk profile of "~1.3 losing years per decade". That figure is a
**derivation**, not an observation: it comes from solving Sharpe 1.13 and CAGR 21.73% for sigma
(21.2%) and reading P(year < 0) = Phi(-1.13) = 12.9% off a normal. Daily skew on this family is
-0.639, so the real tail is worse than normal, and the derivation was never checked against the
record.

Nobody can currently state either book's losing-year count. `forward/prereg_swing.md` publishes three
multi-year *slices*; `research/0001-xsec-momentum/result.md` publishes four regime slices. Neither is
a year count. This counts them.

Three books, because they are different questions:
  * **base-swing** — the certified run of record (Sharpe 1.132 / CAGR 24.7%).
  * **live config P** — A-only + LIVE_DISCIPLINE + LIVE_EXIT + LIVE_STALENESS, what the cron runs.
  * **0001** — cross-sectional momentum, for the cross-book comparison that has never existed in
    matched units.

Gross and after-tax are both reported. A year that is positive gross and negative after tax is still
a losing year to the person holding it, and STCG is paid annually out of the book.

Partial years are flagged rather than annualised: 2017 begins 2017-01-02 and 2026 ends 2026-06-30, so
neither is a full calendar year and neither should be counted as one without saying so.

    python pipelines/diagnostics/diag_per_year_returns.py
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
from nq.runner.research import after_tax_curve  # noqa: E402
from nq.universe import build_universe  # noqa: E402
from pipelines.research.run_0001_xsec_momentum import BAND, END, START, add_signals, run  # noqa: E402
from run_bhanushali_cron import LIVE_DISCIPLINE, LIVE_EXIT, LIVE_STALENESS  # noqa: E402
from run_bhanushali_faithful import EQ0  # noqa: E402
from run_bhanushali_path1 import corrected_universe  # noqa: E402

STCG = 0.20
OUT_JSON = ROOT / "diagnostics" / "research" / "per_year_returns.json"
OUT_MD = ROOT / "diagnostics" / "research" / "per_year_returns.md"


def year_table(ec: list[dict], trades: list[dict]) -> dict:
    """Calendar-year returns, gross and after tax, from one continuous equity curve.

    Chained year-end over year-end — never a fresh-capital re-run per year, which would reset the
    compounding base and flatter every year after a bad one.
    """
    eq = pd.Series([float(e["equity"]) for e in ec],
                   index=pd.to_datetime([e["date"] for e in ec])).sort_index()
    at = pd.Series([float(e["equity"]) for e in after_tax_curve({"equity_curve": ec, "trades": trades},
                                                                stcg=STCG)], index=eq.index)
    rows, prev_g, prev_a = [], None, None
    for y, g in eq.groupby(eq.index.year):
        a = at.loc[g.index]
        g0 = prev_g if prev_g is not None else g.iloc[0]
        a0 = prev_a if prev_a is not None else a.iloc[0]
        intra_dd = float((g / g.cummax() - 1).min()) * 100
        rows.append({
            "year": int(y),
            "sessions": int(len(g)),
            "partial": bool(len(g) < 200),
            "gross_pct": round((g.iloc[-1] / g0 - 1) * 100, 2),
            "after_tax_pct": round((a.iloc[-1] / a0 - 1) * 100, 2),
            "intra_year_maxdd_pct": round(intra_dd, 2),
        })
        prev_g, prev_a = g.iloc[-1], a.iloc[-1]
    full = [r for r in rows if not r["partial"]]
    return {
        "years": rows,
        "n_full_years": len(full),
        "losing_years_gross": [r["year"] for r in rows if r["gross_pct"] < 0],
        "losing_years_after_tax": [r["year"] for r in rows if r["after_tax_pct"] < 0],
        "losing_full_years_gross": [r["year"] for r in full if r["gross_pct"] < 0],
        "worst_year_gross_pct": min(r["gross_pct"] for r in rows),
        "worst_intra_year_dd_pct": min(r["intra_year_maxdd_pct"] for r in rows),
    }


def swing_book(name: str, m: dict, ledger: list) -> dict:
    ec = [{"date": str(d)[:10], "equity": float(v)} for d, v in m["curve"].sort_index().items()]
    tr = [{**r, "pnl": float(r["net_pnl"])} for r in ledger
          if r.get("exit_date") is not None and r.get("net_pnl") is not None]
    return {"book": name, **year_table(ec, tr)}


def main() -> int:
    books = []

    print("swing: building weekly panel ...", flush=True)
    ohlcv, mem = corrected_universe(), load_membership()
    P = R94.prep_weekly_rank(ohlcv)
    a = R94.grade_a_entries(P)

    print("swing: base-swing (certified) ...", flush=True)
    lb: list = []
    books.append(swing_book("base-swing (certified)", R94.backtest(P, mem, ledger=lb), lb))

    print("swing: live config P ...", flush=True)
    ll: list = []
    live = R94.backtest(P, mem, ledger=ll, start="2017-01-01", eq0=EQ0, a_grade=a,
                        **LIVE_DISCIPLINE, **LIVE_EXIT, **LIVE_STALENESS)
    books.append(swing_book("live config P (what trades)", live, ll))

    print("0001: building panel ...", flush=True)
    u = build_universe(corrected_universe(), load_membership(), start=START, end=END)
    p = add_signals(u)
    keep = p["ticker"].isin(p.loc[p["size_band"] == BAND, "ticker"].unique())
    band = p[keep].copy()
    import numpy as np
    band["rank"] = np.where(band["eligible"] & (band["size_band"] == BAND) & band["nms"].notna(),
                            band["nms"], np.nan)
    print("0001: running ...", flush=True)
    c = run(band)
    books.append({"book": "0001 cross-sectional momentum",
                  **year_table(c["equity_curve"], c["trades"])})

    out = {"_doc": "MEASUREMENT, no trial. Chained year-end over year-end on ONE continuous curve.",
           "stcg_rate": STCG,
           "reproduce": "python pipelines/diagnostics/diag_per_year_returns.py",
           "note": "2017 and 2026 are PARTIAL years (curve starts 2017-01-02, ends 2026-06-30).",
           "books": books}
    OUT_JSON.write_text(json.dumps(out, indent=1), encoding="utf-8")

    md = ["# Per-calendar-year returns and losing-year counts (MEASUREMENT, no trial)", "",
          "Chained year-end over year-end on one continuous curve. 2017 and 2026 are partial.", ""]
    for b in books:
        md += [f"## {b['book']}", "",
               "| year | sessions | gross % | after-tax % | intra-year MaxDD % |",
               "|---|--:|--:|--:|--:|"]
        for r in b["years"]:
            flag = " *(partial)*" if r["partial"] else ""
            md.append(f"| {r['year']}{flag} | {r['sessions']} | {r['gross_pct']:+.2f} | "
                      f"{r['after_tax_pct']:+.2f} | {r['intra_year_maxdd_pct']:.1f} |")
        md += ["", f"**Losing years (gross):** {b['losing_years_gross'] or 'none'} · "
                   f"**after tax:** {b['losing_years_after_tax'] or 'none'} · "
                   f"worst year {b['worst_year_gross_pct']:+.2f}% · "
                   f"worst intra-year drawdown {b['worst_intra_year_dd_pct']:.1f}%", ""]
    OUT_MD.write_text("\n".join(md) + "\n", encoding="utf-8")

    print()
    for b in books:
        print(f"  {b['book']}")
        print(f"    losing years gross {b['losing_years_gross'] or '[]'} | "
              f"after tax {b['losing_years_after_tax'] or '[]'} | "
              f"worst {b['worst_year_gross_pct']:+.2f}% | "
              f"worst intra-year DD {b['worst_intra_year_dd_pct']:.1f}%")
    print(f"\nwrote {OUT_JSON.relative_to(ROOT)} + .md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
