"""Point-in-time fundamentals — the solvency (D/E) and value/quality join.

The long-horizon universe filter keeps only **solvent low-debt** names (``0 <= D/E < 1.5``).
That gate must be point-in-time: each decision date may use only the most-recently-published
annual report **strictly before** it — otherwise the backtest trades on figures the market
had not yet seen (a P0 leakage; see ``skills/leakage-audit`` §2).

Source: the carried Screener scrape ``data/fundamentals_pit_screener.pkl`` — a
``{ticker -> DataFrame}`` store indexed by ``available_date`` (when the figure became public)
with columns ``period_end, eps_ttm, book_value_ps, roe, debt_equity``.

The join is ``merge_asof(direction="backward", allow_exact_matches=False)`` — strictly
``available_date < decision_date``. ``allow_exact_matches=False`` is load-bearing: it forbids
a same-day filing from leaking in. ``low_debt = -debt_equity`` (higher = less leverage).

Ported verbatim (behaviour-preserving) from the validated source (``long_horizon/data/sheets.py``).
"""
from __future__ import annotations

import pickle
from collections.abc import Mapping
from pathlib import Path

import numpy as np
import pandas as pd

from config import DATA_DIR

FUND_STORE_PATH = DATA_DIR / "fundamentals_pit_screener.pkl"

# The value/quality factors produced by the PIT join.
VALUE_QUALITY_COLS: tuple[str, ...] = ("ep", "bp", "roe", "low_debt")


def load_fund_store(path: str | Path = FUND_STORE_PATH) -> dict | None:
    """Load the PIT fundamentals store ``{ticker -> frame}`` from disk. Returns ``None`` if
    the file is missing or corrupt (callers then leave the value columns all-NaN)."""
    path = Path(path)
    try:
        with open(path, "rb") as f:
            return pickle.load(f)
    except FileNotFoundError:
        print(f"[fundamentals] store not found at {path}; value cols will be NaN")
        return None
    except Exception as exc:
        print(f"[fundamentals] store corrupt or unreadable ({exc}); value cols will be NaN")
        return None


def value_quality_series(
    ticker: str, store: Mapping[str, pd.DataFrame] | None,
    dates: pd.DatetimeIndex, close: np.ndarray,
) -> dict[str, np.ndarray]:
    """Per-date value/quality factor values for one ticker, PIT-safe (strict-before).

    ``dates`` MUST be sorted ascending (the caller sorts the feature frame), so the
    ``merge_asof`` output is row-aligned to ``dates`` with no reordering. Returns a dict with
    arrays for ``ep`` (earnings/price), ``bp`` (book/price), ``roe``, and ``low_debt``
    (= ``-debt_equity``). All-NaN when the store has no row for the ticker.
    """
    n = len(dates)
    out: dict[str, np.ndarray] = {k: np.full(n, np.nan) for k in VALUE_QUALITY_COLS}
    fr = store.get(ticker) if store else None
    if fr is None or len(fr) == 0:
        return out
    right = fr.copy()
    # Normalize both merge keys to ns — the OHLCV index is often [s] while the fundamentals
    # store is [us]; merge_asof requires identical key dtypes.
    right["avail"] = pd.to_datetime(right.index).astype("datetime64[ns]")
    cols = [c for c in ("eps_ttm", "book_value_ps", "roe", "debt_equity") if c in right.columns]
    right = right[["avail", *cols]].sort_values("avail")
    left = pd.DataFrame({"date": pd.to_datetime(dates).astype("datetime64[ns]")})
    merged = pd.merge_asof(
        left, right, left_on="date", right_on="avail",
        direction="backward", allow_exact_matches=False,   # strict: avail < date
    )
    eps = merged["eps_ttm"].to_numpy(dtype=float) if "eps_ttm" in merged else np.full(n, np.nan)
    bvps = merged["book_value_ps"].to_numpy(dtype=float) if "book_value_ps" in merged else np.full(n, np.nan)
    roe = merged["roe"].to_numpy(dtype=float) if "roe" in merged else np.full(n, np.nan)
    de = merged["debt_equity"].to_numpy(dtype=float) if "debt_equity" in merged else np.full(n, np.nan)
    safe = close > 0
    out["ep"] = np.where(safe, eps / np.where(safe, close, 1.0), np.nan)
    out["bp"] = np.where(safe, bvps / np.where(safe, close, 1.0), np.nan)
    out["roe"] = roe
    out["low_debt"] = -de   # higher = less leverage
    return out
