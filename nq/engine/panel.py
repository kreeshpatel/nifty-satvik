"""Build the ranked, eligible panel the scan + backtest consume.

Two pieces:

  * :func:`build_ohlc_panel` — join, per ticker, the cleaned intraday OHLCV with the carried
    trend/risk feature columns into one long ``(ticker, date)`` panel. The OHLCV prices and the
    scale-free factors (slope / ATR% / ADV) come from the SAME cleaned series, so there is no
    adjusted/unadjusted mismatch within a trade.
  * :func:`compose_ranked_panel` — the full universe-construction pipeline, orchestrating the
    Stage-1 data-layer predicates (no duplication): PIT membership mask → CA-aware OHLCV clean →
    panel join → large+mid ADV restriction → PIT D/E join → solvency mask → cross-sectional rank.
    The output feeds straight into :func:`nq.engine.portfolio.simulate`.

This mirrors the validated golden-fixture build pipeline; only the research-only forward/MFE/MAE
label columns (never read by the simulator, which walks OHLC) are omitted to keep the LH path lean.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence

import pandas as pd

from config import ADV_MID_CAP_RS

from ..data.eligibility import cross_sectional_rank, restrict_to_large_mid, solvent_universe_mask
from ..data.features import SIGNAL
from ..data.fundamentals import value_quality_series
from ..data.membership import filter_features_dict
from ..data.ohlcv import clean_ohlcv_dict

_OHLC = ("open", "high", "low", "close", "volume")
_DEFAULT_CARRY: tuple[str, ...] = (SIGNAL, "atr_pct_63", "adv_rupees_20d", "sector")


def build_ohlc_panel(
    features: Mapping[str, pd.DataFrame],
    ohlcv: Mapping[str, pd.DataFrame],
    *,
    carry: Sequence[str] = _DEFAULT_CARRY,
    horizon: int = 63,
    min_rows: int | None = None,
    date_col: str = "date",
) -> pd.DataFrame:
    """Join cleaned OHLCV (title-cased input → lower-cased columns) with the carried factor columns
    per ticker, inner-joined on the shared trading dates so signal and price align exactly. Returns
    a long ``date, ticker, open, high, low, close, volume`` + carried-factor panel."""
    need = min_rows if min_rows is not None else horizon + 5
    frames: list[pd.DataFrame] = []
    for ticker, fdf in features.items():
        odf = ohlcv.get(ticker) if ohlcv else None
        if fdf is None or odf is None or len(fdf) < need or len(odf) < need:
            continue
        o = odf.rename(columns={c: c.lower() for c in odf.columns})
        if not {"open", "high", "low", "close"}.issubset(o.columns):
            continue
        o = o[[c for c in _OHLC if c in o.columns]].copy()
        o.index = pd.to_datetime(o.index)
        f = fdf.copy()
        f.index = pd.to_datetime(f.index)
        carry_cols = [c for c in carry if c in f.columns]
        df = o.join(f[carry_cols], how="inner").sort_index()
        if len(df) < need:
            continue
        df[date_col] = df.index
        df["ticker"] = ticker
        frames.append(df.reset_index(drop=True))
    if not frames:
        return pd.DataFrame()
    panel = pd.concat(frames, ignore_index=True)
    front = [c for c in [date_col, "ticker", *_OHLC] if c in panel.columns]
    return panel[front + [c for c in panel.columns if c not in front]]


def compose_ranked_panel(
    features: Mapping[str, pd.DataFrame],
    ohlcv: Mapping[str, pd.DataFrame],
    *,
    fund_store: Mapping[str, pd.DataFrame] | None,
    membership: dict | None = None,
    min_adv_rs: float = ADV_MID_CAP_RS,
    signal: str = SIGNAL,
    carry: Sequence[str] = _DEFAULT_CARRY,
) -> pd.DataFrame:
    """Build the ranked, eligible panel: PIT membership mask → CA-aware OHLCV clean → OHLC+feature
    join → large+mid ADV restriction → PIT D/E join → solvency mask → cross-sectional rank. Returns
    the long panel with a ``trend_rank`` column (1.0 = best), ready for ``simulate``."""
    feats = filter_features_dict(dict(features), membership) if membership is not None else features
    panel = build_ohlc_panel(feats, clean_ohlcv_dict(ohlcv), carry=carry)
    if panel.empty:
        return panel
    uni, _ = restrict_to_large_mid(panel, min_adv_rs=min_adv_rs)
    if uni.empty:
        return uni
    parts: list[pd.DataFrame] = []
    for tkr, g in uni.groupby("ticker", sort=False):
        g = g.sort_values("date").copy()
        vq = value_quality_series(tkr, fund_store, pd.DatetimeIndex(pd.to_datetime(g["date"])),
                                  g["close"].to_numpy(float))
        g["low_debt"] = vq["low_debt"]
        g["roe"] = vq["roe"]
        parts.append(g)
    uni = pd.concat(parts, ignore_index=True)
    uni = uni[solvent_universe_mask(uni)].copy()
    if uni.empty:
        return uni
    return cross_sectional_rank(uni, signal, out_col="trend_rank")
