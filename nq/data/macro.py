"""PIT-clean cross-asset macro factor series (replaces the un-audited `data/macro_data.pkl`).

The audit for finding 0016 found `macro_data.pkl` has NO builder in version control and cannot be
confirmed point-in-time clean — so the orthogonal cross-asset IC it produced is provisional. This module
rebuilds the factors from verifiable raw underlyings (yfinance) with a **TRAILING-ONLY** derivation: every
column at date t uses only data <= t (pct_change / trailing rolling), so truncating the future leaves past
values unchanged. That PIT property is proven by `tests/test_macro_pit.py` (the truncation test).

`derive_macro_factors` is the pure, testable core; `build_macro_series` does the I/O (fetch + persist).
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from config import DATA_DIR

MACRO_PIT_PATH = DATA_DIR / "macro_pit.parquet"
# raw underlyings -> yfinance tickers
UNDERLYINGS = {"crude": "CL=F", "usd": "INR=X", "vix": "^INDIAVIX", "nifty": "^NSEI"}
TREND_WIN = 63  # trailing ROC window for the *_trend factors (like-for-like vs finding 0016's trend betas)


def derive_macro_factors(closes: pd.DataFrame) -> pd.DataFrame:
    """Trailing-only daily factor series from a `{name -> close}` DataFrame indexed by date.

    Every output column at t depends only on data <= t (`pct_change` uses t and t-1; levels are as-of t),
    so `derive_macro_factors(closes.loc[:d])` equals `derive_macro_factors(closes).loc[:d]` — no lookahead.
    """
    out = pd.DataFrame(index=closes.index)
    if "crude" in closes:
        out["crude_ret"] = closes["crude"].pct_change()
        out["crude_trend"] = closes["crude"] / closes["crude"].shift(TREND_WIN) - 1  # trailing 63d ROC
    if "usd" in closes:
        out["usd_ret"] = closes["usd"].pct_change()
        out["usd_trend"] = closes["usd"] / closes["usd"].shift(TREND_WIN) - 1
    if "vix" in closes:
        out["vix_level"] = closes["vix"]
        out["vix_chg"] = closes["vix"].pct_change()
        out["vix_trend"] = closes["vix"] / closes["vix"].shift(TREND_WIN) - 1
    if "nifty" in closes:
        out["nifty_ret"] = closes["nifty"].pct_change()
    return out


def _close(df: pd.DataFrame) -> pd.Series:
    """The Close column from a yfinance frame (single-ticker frames carry a 1-col multi-index)."""
    c = df["Close"]
    return c.iloc[:, 0] if hasattr(c, "columns") else c


def build_macro_series(start: str, end: str, *, path: str | Path = MACRO_PIT_PATH) -> pd.DataFrame:
    """Fetch the raw underlyings from yfinance, derive the trailing-only factors, persist to `path`."""
    import yfinance as yf
    closes: dict[str, pd.Series] = {}
    for name, tkr in UNDERLYINGS.items():
        df = yf.download(tkr, start=start, end=end, progress=False, auto_adjust=True)
        if df is not None and len(df):
            closes[name] = _close(df)
    px = pd.DataFrame(closes)
    px.index = pd.to_datetime(px.index)
    fac = derive_macro_factors(px)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    out = fac.reset_index()
    out = out.rename(columns={out.columns[0]: "date"})
    out.to_parquet(path, index=False)
    return fac


def load_macro_pit(path: str | Path = MACRO_PIT_PATH) -> pd.DataFrame:
    """Load the persisted PIT macro factors, indexed by date."""
    return pd.read_parquet(path).set_index("date").sort_index()
