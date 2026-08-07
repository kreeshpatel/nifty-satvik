"""Verification audit 2026Q3 — session 2, items 1 and 3. VERIFICATION CLASS.

Zero trials, zero new screens, no new hypotheses. Counts frozen at screens 14 · sealed opens 1 ·
n_trials 138. Sealed 2024H2+ not re-opened. Judge log not read.

  ITEM 1  ANNUALIZATION SWEEP — for every book whose Sharpe is load-bearing, recompute under each
          convention and show which one reproduces the published number. The constant alone proves
          nothing; what matters is the constant APPLIED TO THE RIGHT FREQUENCY. A book whose
          published Sharpe matches daily-sqrt252 is consistent; one that only matches a mixed
          convention (daily returns x sqrt52, or weekly returns x sqrt252) is a Tier-A discrepancy.

  ITEM 3  REBALANCE-ANCHOR ROBUSTNESS — the two-sleeve ERC blend (published 1.22 / -33%) re-run with
          the quarterly rebalance anchor shifted by 0..6 weeks. A result that only exists at one
          anchor is a knife-edge, not a property of the sleeves.

  A4      Blend replication: does 1.22 / -33% reproduce at the published anchor at all?

Nothing here imports the original blend code; the ERC is re-implemented from its stated rule
(quarterly inverse-vol on trailing realised vol), so a shared bug cannot survive.

Reproduce:
    python scripts/audit_annualization_anchor_2026Q3.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

OUT = ROOT / "diagnostics" / "research" / "verification_audit_2026Q3"
SLEEVES = ROOT / "research" / "exports" / "third_sleeve_returns.csv"
LOOKBACK_D = 252          # trailing window for the inverse-vol weights (1y, the stated rule)


def sharpe(r, periods: int) -> float:
    r = np.asarray(r, float)
    r = r[~np.isnan(r)]
    sd = r.std(ddof=0)
    return float(r.mean() / sd * np.sqrt(periods)) if sd > 0 else float("nan")


def max_dd(equity) -> float:
    e = np.asarray(equity, float)
    return float((e / np.maximum.accumulate(e) - 1.0).min())


def perf(r: pd.Series) -> dict:
    r = r.dropna()
    eq = (1 + r).cumprod()
    yrs = max((r.index[-1] - r.index[0]).days / 365.25, 1e-9)
    yearly = {int(y): float((1 + g).prod() - 1) for y, g in r.groupby(r.index.year)}
    return dict(sharpe=round(sharpe(r, 252), 3),
                cagr_pct=round(100.0 * (eq.iloc[-1] ** (1 / yrs) - 1), 2),
                maxdd_pct=round(100.0 * max_dd(eq), 2),
                worst_year_pct=round(100.0 * min(yearly.values()), 2),
                losing_years=int(sum(1 for v in yearly.values() if v < 0)))


def erc_blend(df: pd.DataFrame, cols: list[str], anchor_offset_weeks: int) -> pd.Series:
    """Quarterly inverse-vol ERC, re-implemented from the stated rule.

    `anchor_offset_weeks` shifts the rebalance calendar forward by N weeks, so the quarter
    boundaries fall on different dates while the rule itself is unchanged.
    """
    shifted = df.index - pd.Timedelta(weeks=anchor_offset_weeks)
    period = pd.Series(shifted, index=df.index).dt.to_period("Q")
    w = pd.DataFrame(index=df.index, columns=cols, dtype=float)
    for per in period.unique():
        m = (period == per).to_numpy()
        prior = df.loc[~m & (period < per).to_numpy(), cols]
        if len(prior) < 60:                       # not enough history to estimate vol
            w.loc[m, cols] = 1.0 / len(cols)
            continue
        vol = prior.tail(LOOKBACK_D).std(ddof=0).replace(0, np.nan)
        iv = (1.0 / vol).replace([np.inf, -np.inf], np.nan).fillna(0.0)
        w.loc[m, cols] = (iv / iv.sum()).to_numpy() if iv.sum() > 0 else 1.0 / len(cols)
    return (df[cols] * w).sum(axis=1)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    sl = pd.read_csv(SLEEVES, index_col=0, parse_dates=True).sort_index()
    gap = sl.index.to_series().diff().dt.days.dropna().median()

    # ── ITEM 1: which convention reproduces the published number? ──────────────────────────
    published = {"swing": 1.15, "lowvol": 1.06}
    conv = []
    for c, pub in published.items():
        r = sl[c].dropna()
        wk = (1 + r).resample("W-FRI").prod() - 1
        cands = {"daily x sqrt252 (correct for daily)": sharpe(r, 252),
                 "weekly x sqrt52 (correct for weekly)": sharpe(wk, 52),
                 "daily x sqrt52 (MIXED — wrong)": sharpe(r, 52),
                 "weekly x sqrt252 (MIXED — wrong)": sharpe(wk, 252)}
        best = min(cands, key=lambda k: abs(cands[k] - pub))
        conv.append({"book": c, "published": pub,
                     **{k: round(v, 3) for k, v in cands.items()},
                     "reproduced_by": best,
                     "delta_to_published": round(cands[best] - pub, 3),
                     "CONSISTENT": bool("MIXED" not in best and abs(cands[best] - pub) < 0.02)})

    # ── A4 + ITEM 3: blend replication, then the anchor sweep ─────────────────────────────
    pair = ["swing", "lowvol"]
    sweep = []
    for off in range(0, 7):
        b = erc_blend(sl, pair, off)
        p = perf(b)
        sweep.append({"anchor_offset_weeks": off, **p})

    sh_vals = [s["sharpe"] for s in sweep]
    dd_vals = [s["maxdd_pct"] for s in sweep]
    base = sweep[0]
    res = {
        "_doc": "Verification audit 2026Q3 session 2 — items 1 (annualization) and 3 (anchor robustness).",
        "class": "VERIFICATION — 0 trials, 0 screens, no new hypotheses",
        "counts": "screens 14 · sealed opens 1 · n_trials 138 (frozen)",
        "item1_annualization": {
            "series_frequency_median_day_gap": float(gap),
            "series_is_daily": bool(gap <= 3),
            "books": conv,
            "VERDICT": ("CONSISTENT — every load-bearing sleeve Sharpe reproduces under "
                        "daily-returns x sqrt(252); no book matches a mixed convention"
                        if all(b["CONSISTENT"] for b in conv) else
                        "DISCREPANCY — at least one book only reproduces under a mixed convention"),
        },
        "item3_anchor_sweep": {
            "published_blend": {"sharpe": 1.22, "maxdd_pct": -33.0, "worst_year_pct": 5.6,
                                "losing_years": 0},
            "rule_reimplemented": "quarterly inverse-vol on trailing 252d realised vol",
            "at_published_anchor": base,
            "sweep": sweep,
            "sharpe_range": [min(sh_vals), max(sh_vals)],
            "sharpe_spread": round(max(sh_vals) - min(sh_vals), 3),
            "maxdd_range": [min(dd_vals), max(dd_vals)],
            "maxdd_spread": round(max(dd_vals) - min(dd_vals), 2),
            "zero_losing_years_at_every_anchor": bool(all(s["losing_years"] == 0 for s in sweep)),
        },
    }
    (OUT / "session2_annualization_anchor.json").write_text(
        json.dumps(res, indent=2, default=str), encoding="utf-8")

    print("ITEM 1 — annualization")
    for b in conv:
        print(f"  {b['book']:8s} published {b['published']}  reproduced_by: {b['reproduced_by']}"
              f"  delta {b['delta_to_published']:+.3f}  CONSISTENT={b['CONSISTENT']}")
    print(f"  VERDICT: {res['item1_annualization']['VERDICT']}\n")
    print("ITEM 3 — ERC blend anchor sweep (published 1.22 / -33%)")
    for s in sweep:
        print(f"  offset {s['anchor_offset_weeks']}wk: Sharpe {s['sharpe']:.3f}  CAGR {s['cagr_pct']:.2f}%"
              f"  MaxDD {s['maxdd_pct']:.2f}%  worstYr {s['worst_year_pct']:.2f}%  losingYrs {s['losing_years']}")
    print(f"  Sharpe range {res['item3_anchor_sweep']['sharpe_range']} "
          f"(spread {res['item3_anchor_sweep']['sharpe_spread']})")
    print(f"  MaxDD  range {res['item3_anchor_sweep']['maxdd_range']} "
          f"(spread {res['item3_anchor_sweep']['maxdd_spread']})")


if __name__ == "__main__":
    main()
