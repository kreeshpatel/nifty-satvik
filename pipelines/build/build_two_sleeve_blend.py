"""PRODUCER of record for the two-sleeve ERC blend (finding 0115). Committed 2026-07-31.

**Why this file exists.** The 2026Q3 verification audit found that no committed script produced
0115's headline `Sharpe 1.22 / MaxDD -33% / worst year +5.6%`. The sleeve *inputs*
(`research/exports/third_sleeve_returns.csv`) were committed and the sleeve construction was
documented, but the blend arithmetic on top of them was not in the repo, so the number could not be
mechanically replicated. This script closes that gap.

**The vol lookback is named here because 0115 did not name it.** 0115 says only "quarterly
inverse-vol ERC". The audit recovered the lookback by asking which value reproduces the PUBLISHED
triple — not which value maximises anything:

    lookback   Sharpe   MaxDD%   worst yr%      vs published 1.22 / -33 / +5.6
      63d       1.234   -33.13     +5.70
     126d       1.237   -33.04     +5.62        <- best triple match (DD and worst-yr within rounding)
     252d       1.248   -32.57     +5.19
     504d       1.271   -32.49     +5.78
     all-prior  1.261   -32.51     +5.02

`VOL_LOOKBACK_D = 126` is therefore the recovered rule. **A residual of ~+0.017 Sharpe against the
published 1.22 remains unexplained** — most likely a small implementation detail of the original
(minimum-observation rule, weight-normalisation timing, or ddof). It is recorded rather than tuned
away: no parameter here was chosen to close it.

**The published 1.22 / -33% / +5.6% stands as as-measured-then.** This script's output is the
*reproducible* figure and is what the Oct-1 binder should cite.

Reproduce:
    python scripts/build_two_sleeve_blend.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# ---- the rule, fully named. Nothing here is swept. ----
SLEEVES = ("swing", "lowvol")
VOL_LOOKBACK_D = 126        # trailing trading days of realised vol -> inverse-vol weights (recovered)
MIN_OBS = 60                # below this, fall back to equal weight rather than trust a vol estimate
REBALANCE = "Q"             # quarterly, on calendar quarter boundaries
DDOF = 0                    # population std, matching nq.validation.metrics
TRADING_DAYS = 252

SRC = ROOT / "research" / "exports" / "third_sleeve_returns.csv"
OUT_JSON = ROOT / "research" / "exports" / "two_sleeve_blend.json"
OUT_CSV = ROOT / "research" / "exports" / "two_sleeve_blend_returns.csv"

PUBLISHED = {"sharpe": 1.22, "maxdd_pct": -33.0, "worst_year_pct": 5.6, "losing_years": 0}


def sharpe(r: np.ndarray, periods: int = TRADING_DAYS) -> float:
    r = np.asarray(r, float)
    r = r[~np.isnan(r)]
    sd = r.std(ddof=DDOF)
    return float(r.mean() / sd * np.sqrt(periods)) if sd > 0 else float("nan")


def max_drawdown(equity: np.ndarray) -> float:
    e = np.asarray(equity, float)
    return float((e / np.maximum.accumulate(e) - 1.0).min())


def erc_weights(df: pd.DataFrame, cols: tuple[str, ...],
                anchor_offset_weeks: int = 0) -> pd.DataFrame:
    """Quarterly inverse-vol weights from trailing realised vol.

    Weights for a quarter are estimated on data STRICTLY BEFORE that quarter — no in-quarter
    information sets the quarter's own weights.
    """
    shifted = df.index - pd.Timedelta(weeks=anchor_offset_weeks)
    period = pd.Series(shifted, index=df.index).dt.to_period(REBALANCE)
    w = pd.DataFrame(index=df.index, columns=list(cols), dtype=float)
    for per in period.unique():
        mask = (period == per).to_numpy()
        prior = df.loc[(period < per).to_numpy(), list(cols)]
        if len(prior) < MIN_OBS:
            w.loc[mask, list(cols)] = 1.0 / len(cols)
            continue
        vol = prior.tail(VOL_LOOKBACK_D).std(ddof=DDOF).replace(0, np.nan)
        inv = (1.0 / vol).replace([np.inf, -np.inf], np.nan).fillna(0.0)
        w.loc[mask, list(cols)] = ((inv / inv.sum()).to_numpy() if inv.sum() > 0
                                   else 1.0 / len(cols))
    return w


def blend(df: pd.DataFrame, anchor_offset_weeks: int = 0) -> pd.Series:
    w = erc_weights(df, SLEEVES, anchor_offset_weeks)
    return (df[list(SLEEVES)] * w).sum(axis=1)


def perf(r: pd.Series) -> dict:
    r = r.dropna()
    eq = (1 + r).cumprod()
    yrs = max((r.index[-1] - r.index[0]).days / 365.25, 1e-9)
    yearly = {int(y): round(100.0 * float((1 + g).prod() - 1), 2)
              for y, g in r.groupby(r.index.year)}
    return dict(
        sharpe=round(sharpe(r.to_numpy(float)), 3),
        cagr_pct=round(100.0 * (float(eq.iloc[-1]) ** (1 / yrs) - 1), 2),
        maxdd_pct=round(100.0 * max_drawdown(eq.to_numpy(float)), 2),
        ann_vol_pct=round(100.0 * float(r.std(ddof=DDOF)) * np.sqrt(TRADING_DAYS), 2),
        worst_year_pct=min(yearly.values()),
        losing_years=int(sum(1 for v in yearly.values() if v < 0)),
        yearly_pct=yearly, n_days=int(len(r)), span_years=round(yrs, 2))


def main() -> None:
    df = pd.read_csv(SRC, index_col=0, parse_dates=True).sort_index()
    b = blend(df).dropna()
    got = perf(b)

    # Anchor robustness at the RECOVERED lookback (the audit's session-2 sweep used 252d).
    sweep = []
    for off in range(0, 7):
        p = perf(blend(df, off).dropna())
        sweep.append({"anchor_offset_weeks": off, "sharpe": p["sharpe"],
                      "maxdd_pct": p["maxdd_pct"], "worst_year_pct": p["worst_year_pct"],
                      "losing_years": p["losing_years"]})
    sh = [s["sharpe"] for s in sweep]
    dd = [s["maxdd_pct"] for s in sweep]

    res = {
        "_doc": "Two-sleeve ERC blend — PRODUCER OF RECORD (finding 0115; committed by the 2026Q3 audit).",
        "rule": {"sleeves": list(SLEEVES), "rebalance": "quarterly",
                 "weights": "inverse trailing realised vol",
                 "vol_lookback_days": VOL_LOOKBACK_D, "min_obs": MIN_OBS, "ddof": DDOF,
                 "annualization": f"daily returns x sqrt({TRADING_DAYS})"},
        "reproducible": got,
        "published_as_measured_then": PUBLISHED,
        "delta_vs_published": {
            "sharpe": round(got["sharpe"] - PUBLISHED["sharpe"], 3),
            "maxdd_pct": round(got["maxdd_pct"] - PUBLISHED["maxdd_pct"], 2),
            "worst_year_pct": round(got["worst_year_pct"] - PUBLISHED["worst_year_pct"], 2)},
        "note": "the residual Sharpe gap is UNEXPLAINED and was not tuned away; MaxDD and worst-year "
                "agree with the published figures within rounding",
        "anchor_robustness": {"sweep": sweep,
                              "sharpe_range": [min(sh), max(sh)],
                              "sharpe_spread": round(max(sh) - min(sh), 3),
                              "maxdd_range": [min(dd), max(dd)],
                              "maxdd_spread": round(max(dd) - min(dd), 2),
                              "zero_losing_years_at_every_anchor":
                                  bool(all(s["losing_years"] == 0 for s in sweep))},
    }
    OUT_JSON.write_text(json.dumps(res, indent=2, default=str), encoding="utf-8")
    b.rename("blend").to_frame().to_csv(OUT_CSV)

    print(f"two-sleeve ERC blend (lookback {VOL_LOOKBACK_D}d, quarterly, inverse-vol)")
    print(f"  REPRODUCIBLE : Sharpe {got['sharpe']}  CAGR {got['cagr_pct']}%  "
          f"MaxDD {got['maxdd_pct']}%  worst yr {got['worst_year_pct']}%  "
          f"losing yrs {got['losing_years']}")
    print(f"  published    : Sharpe {PUBLISHED['sharpe']}  MaxDD {PUBLISHED['maxdd_pct']}%  "
          f"worst yr {PUBLISHED['worst_year_pct']}%  (as-measured-then)")
    print(f"  delta        : {res['delta_vs_published']}")
    print(f"  anchor sweep : Sharpe {res['anchor_robustness']['sharpe_range']} "
          f"(spread {res['anchor_robustness']['sharpe_spread']}), "
          f"zero losing years at every anchor = "
          f"{res['anchor_robustness']['zero_losing_years_at_every_anchor']}")


if __name__ == "__main__":
    main()
