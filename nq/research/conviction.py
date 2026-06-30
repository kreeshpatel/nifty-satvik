"""Stage-C conviction score — an inspectable per-name quality score AMONG the selectable names.

Owner Decision 2: conviction is a score *within the already-selected top-15* — it annotates and
(Stage D) sizes, it never changes which names are selected. Per the promotion bar it must be
explainable in one sentence and carry NO opaque ML.

**The score (4-factor equal-weight z-blend):** on each date, among the rank-gated selectable pool,
z-score four PIT-safe factors and average them:

    conviction = mean[ z(sma200_slope_63),  z(-atr_pct_63),  z(log adv_rupees_20d),  z(roe) ]
                       trend strength        low volatility    liquidity              quality

Higher trend, lower volatility, deeper liquidity, higher ROE → higher conviction. A name missing a
factor (e.g. no ROE) is averaged over the factors it has (not penalised). Normalisation is WITHIN
each date's selectable pool (rank ≥ 1 − gate_quantile) — the set the top-15 are drawn from — so
conviction means "quality relative to the names competing for a slot today."

Skeptical prior (finding 0021): the technical base has ~0 *directional* IC on this universe; its
edge is vol-selection + convexity. So conviction's hope is to rank realised per-trade P&L (which
embeds the target/stop/trailing convexity), not raw direction. KILL is a likely, acceptable result.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from config import load_frozen_cfg

CONVICTION_COL = "conviction"
QUINTILE_COL = "conviction_quintile"


def _zscore(s: pd.Series) -> pd.Series:
    sd = s.std(ddof=0)
    if not np.isfinite(sd) or sd == 0:
        return pd.Series(np.zeros(len(s)), index=s.index)
    return (s - s.mean()) / sd


def add_conviction_score(
    panel: pd.DataFrame, *, date_col: str = "date", rank_col: str = "trend_rank",
    gate_quantile: float | None = None,
) -> pd.DataFrame:
    """Return a copy of ``panel`` with a :data:`CONVICTION_COL` (and :data:`QUINTILE_COL`, 1=low …
    5=high) for every row in each date's selectable pool (``rank_col`` ≥ 1 − gate_quantile);
    rows outside the pool get NaN. ``gate_quantile`` defaults to the frozen cfg's."""
    if gate_quantile is None:
        gate_quantile = float(load_frozen_cfg()["gate_quantile"])
    df = panel.copy()
    df[date_col] = pd.to_datetime(df[date_col])

    in_pool = (df[rank_col] >= (1.0 - gate_quantile)) if rank_col in df.columns else pd.Series(
        True, index=df.index)
    pool = df[in_pool].copy()

    # the four factors, oriented so HIGHER = better conviction
    factors = pd.DataFrame(index=pool.index)
    if "sma200_slope_63" in pool.columns:
        factors["trend"] = pool["sma200_slope_63"].astype(float)
    if "atr_pct_63" in pool.columns:
        factors["lowvol"] = -pool["atr_pct_63"].astype(float)            # lower ATR → higher
    if "adv_rupees_20d" in pool.columns:
        adv = pool["adv_rupees_20d"].astype(float)
        factors["liq"] = np.log(adv.where(adv > 0))                      # log turnover
    if "roe" in pool.columns:
        factors["quality"] = pool["roe"].astype(float)

    # per-date cross-sectional z of each factor, then row-mean over the factors present
    z = factors.copy()
    for col in factors.columns:
        z[col] = factors[col].groupby(pool[date_col]).transform(_zscore)
    conviction = z.mean(axis=1, skipna=True)                            # NaN-factor not penalised

    df[CONVICTION_COL] = np.nan
    df.loc[conviction.index, CONVICTION_COL] = conviction.to_numpy()

    # per-date quintile (1=low … 5=high) among the pool; NaN outside
    def _q(s: pd.Series) -> pd.Series:
        valid = s.dropna()
        if valid.nunique() < 5:
            return pd.Series(np.nan, index=s.index)
        return pd.qcut(s, 5, labels=False, duplicates="drop") + 1
    df[QUINTILE_COL] = df.groupby(date_col)[CONVICTION_COL].transform(_q)
    return df
