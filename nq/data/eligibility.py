"""Universe-eligibility predicates + the cross-sectional rank — pure, reusable transforms.

Three building blocks that turn a per-(ticker, date) panel into the **eligible, ranked**
universe the long-horizon scan selects from. Kept in the data layer (pure, unit-testable) and
composed by the Stage-2 engine panel builder — single source of truth, no duplication:

  * :func:`restrict_to_large_mid` — keep only LARGE+MID names (trailing rolling-median 20d
    rupee ADV >= the floor). Point-in-time (trailing only → no lookahead) and spike-robust (a
    flash-pumped small cap has high *spot* ADV but a low trailing-*median*, so it never enters).
  * :func:`solvent_universe_mask` — keep solvent low-debt names (``0 <= D/E < de_max``), with a
    financial branch that re-admits a healthy bank/NBFC whose D/E is merely unavailable (NaN)
    but whose ROE > 0 (D/E is ill-defined for deposit-takers).
  * :func:`cross_sectional_rank` — per-date percentile rank of the signal in ``(0, 1]`` where
    **1.0 = best** (largest slope), so the entry gate selects ``trend_rank >= 1 - q``.

Ported verbatim (behaviour-preserving) from the validated source ``ohlc_panel.py``.
"""
from __future__ import annotations

import pandas as pd

from config import ADV_PERSISTENCE_WINDOW, DE_MAX, FINANCIAL_SECTORS


def restrict_to_large_mid(
    panel: pd.DataFrame, *, min_adv_rs: float, persistence_window: int = ADV_PERSISTENCE_WINDOW,
    adv_col: str = "adv_rupees_20d", date_col: str = "date",
) -> tuple[pd.DataFrame, dict]:
    """Keep only large+mid rows, dropping the small-cap tail BEFORE ranking.

    A ``(ticker, date)`` qualifies when the ticker's TRAILING rolling-median 20d rupee ADV
    over ``persistence_window`` sessions is >= ``min_adv_rs``. Returns ``(filtered_panel,
    report)``. The cross-sectional rank is computed WITHIN this universe, so small caps are
    absent from the ranking entirely, not merely skipped at entry.
    """
    df = panel.sort_values(["ticker", date_col]).copy()
    med = df.groupby("ticker")[adv_col].transform(
        lambda s: s.rolling(persistence_window, min_periods=persistence_window // 2).median())
    keep = med >= float(min_adv_rs)
    out = df[keep].copy()
    report = {
        "min_adv_rs": float(min_adv_rs), "persistence_window": persistence_window,
        "rows_before": int(len(df)), "rows_after": int(len(out)),
        "tickers_before": int(df["ticker"].nunique()),
        "tickers_after": int(out["ticker"].nunique()) if len(out) else 0,
    }
    return out, report


def solvent_universe_mask(
    df: pd.DataFrame, *, de_max: float = DE_MAX, debt_col: str = "low_debt",
    roe_col: str = "roe", sector_col: str = "sector",
    financial_sectors: frozenset[str] = FINANCIAL_SECTORS,
) -> pd.Series:
    """Single source of truth for the long-horizon solvency keep-mask.

    Returns a boolean ``pd.Series`` aligned to ``df.index`` (True = keep)::

        keep if  (0 <= D/E < de_max)
              OR (sector is FINANCIAL  AND  D/E is NaN  AND  ROE > 0)

    where ``low_debt = -debt_equity``, so the leverage gate ``0 <= D/E < de_max`` is
    ``(-de_max < low_debt) & (low_debt <= 0)``.

    The financial branch re-admits a bank/NBFC whose D/E is merely unavailable (NaN) but which
    is healthy (ROE > 0) — without it the entire deposit-taking block drops for a DATA reason,
    not a leverage one. Invariants: a non-financial row behaves exactly as the bare leverage
    gate; a financial with D/E present uses the leverage gate; a financial with D/E NaN and
    ROE <= 0 (or NaN) stays dropped. The rule only ADDS healthy D/E-missing financials.
    """
    low_debt = pd.to_numeric(df.get(debt_col), errors="coerce")
    # Leverage gate: 0 <= D/E < de_max  <=>  -de_max < low_debt <= 0. NaN -> False on both
    # comparisons, so a NaN-D/E name fails the leverage gate by default.
    leverage_ok = (low_debt > -float(de_max)) & (low_debt <= 0)

    if sector_col in df.columns and roe_col in df.columns:
        roe = pd.to_numeric(df[roe_col], errors="coerce")
        is_financial = df[sector_col].isin(financial_sectors)
        de_missing = low_debt.isna()
        financial_ok = is_financial & de_missing & (roe > 0)
    else:
        financial_ok = pd.Series(False, index=df.index)

    return (leverage_ok | financial_ok).fillna(False)


def cross_sectional_rank(
    panel: pd.DataFrame, signal_col: str, *, date_col: str = "date",
    out_col: str = "trend_rank", higher_is_better: bool = True,
) -> pd.DataFrame:
    """Add a per-date cross-sectional percentile rank of ``signal_col`` in ``(0, 1]`` where
    **1.0 = best**. For a higher-is-better signal the LARGEST value maps to 1.0 —
    ``Series.rank(ascending=True, pct=True, method="first")``. NaN signal → NaN rank (the name
    is unrankable that day, e.g. still in warm-up)."""
    out = panel.copy()
    out[out_col] = (
        out.groupby(date_col)[signal_col]
        .rank(ascending=higher_is_better, pct=True, method="first")
    )
    return out
