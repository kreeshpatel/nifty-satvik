"""Canonical cached WEEKLY panel for the swing research substrate.

One source of truth for weekly candles so the ~10 swing scripts that each re-derive weekly
(some ISO-week, some ``resample("W-FRI")``) stop drifting. The aggregation here is
**byte-identical to the 0094 book's** ISO-week grouping in
``scripts/run_bhanushali_weekly_rank.prep_weekly_rank`` (the sequential same-(year,week) run
grouping of lines 62-73), so the 44-SMA-touch subset of the Stage-1 substrate reconciles with
the live book. The only *additions* over that function are **weekly volume** (sum) and the
tidy long-frame shape — both read-only extras that the frozen 0094 run never touches.

Public API:
    build_weekly_panel(ohlcv)        -> tidy long DataFrame (pure, deterministic)
    load_weekly_panel(ohlcv, cache)  -> cached wrapper (data/weekly_panel.parquet + .meta.json)

Weekly columns per (ticker, week_end): o, h, l, c, v, sma44, slope44, n_days.
``sma44`` = 44-week SMA of weekly close; ``slope44`` = wsma / wsma.shift(13) - 1 (the live
SLOPE_LOOKBACK=13). Both NaN until enough history — callers gate on them exactly as the book does.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

from config import DATA_DIR

WEEKLY_PANEL_CACHE = DATA_DIR / "weekly_panel.parquet"
WEEKLY_PANEL_META = DATA_DIR / "weekly_panel.meta.json"

# Frozen to match the live book (run_bhanushali_weekly_rank.SLOPE_LOOKBACK / the 44-week SMA).
SMA_LEN = 44
SLOPE_LOOKBACK = 13
MIN_DAILY_BARS = 300  # same floor as prep(): skip thinly-listed names


def _iso_week_groups(idx: pd.DatetimeIndex) -> list[list[int]]:
    """Sequential runs of equal ISO (year, week) — identical to prep_weekly_rank lines 62-70.

    Dates must be sorted ascending (they are, coming off a DatetimeIndex). Returns a list of
    lists of positional indices, one inner list per weekly bucket in chronological order.
    """
    iso = idx.isocalendar()
    keys = list(zip(iso["year"].to_numpy(), iso["week"].to_numpy()))
    weeks: list[list[int]] = []
    cur: list[int] = []
    prev = None
    for i, k in enumerate(keys):
        if prev is not None and k != prev:
            weeks.append(cur)
            cur = []
        cur.append(i)
        prev = k
    if cur:
        weeks.append(cur)
    return weeks


def build_weekly_panel(ohlcv: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Aggregate a daily ``{ticker -> OHLCV DataFrame}`` to a tidy weekly long-frame.

    Pure and deterministic: no I/O, no clock. Frames must be title-cased
    ``Open/High/Low/Close/Volume`` on a DatetimeIndex (the repo convention). Names with fewer
    than ``MIN_DAILY_BARS`` daily rows are skipped (matches ``prep``).
    """
    frames = []
    for tkr in sorted(ohlcv):  # sort => deterministic row order regardless of dict order
        df = ohlcv[tkr]
        if len(df) < MIN_DAILY_BARS:
            continue
        idx = pd.to_datetime(df.index)
        o, h, l, c = (df[x].to_numpy(float) for x in ("Open", "High", "Low", "Close"))
        v = df["Volume"].to_numpy(float) if "Volume" in df.columns else np.full(len(c), np.nan)
        weeks = _iso_week_groups(idx)
        wopen = np.array([o[g[0]] for g in weeks])
        whigh = np.array([h[g].max() for g in weeks])
        wlow = np.array([l[g].min() for g in weeks])
        wclose = np.array([c[g[-1]] for g in weeks])
        wvol = np.array([np.nansum(v[g]) for g in weeks])
        wend = pd.DatetimeIndex([idx[g[-1]] for g in weeks])
        ndays = np.array([len(g) for g in weeks])
        wsma = pd.Series(wclose).rolling(SMA_LEN).mean().to_numpy()
        slope = np.full(len(wsma), np.nan)
        slope[SLOPE_LOOKBACK:] = wsma[SLOPE_LOOKBACK:] / wsma[:-SLOPE_LOOKBACK] - 1.0
        frames.append(pd.DataFrame(dict(
            ticker=tkr, week_end=wend, o=wopen, h=whigh, l=wlow, c=wclose, v=wvol,
            sma44=wsma, slope44=slope, n_days=ndays)))
    if not frames:
        return pd.DataFrame(columns=["ticker", "week_end", "o", "h", "l", "c", "v",
                                     "sma44", "slope44", "n_days"])
    panel = pd.concat(frames, ignore_index=True)
    return panel


def _panel_hash(panel: pd.DataFrame) -> str:
    """Content hash of the numeric panel — determinism gate / cache key."""
    h = hashlib.sha256()
    h.update(str(panel.shape).encode())
    h.update(pd.util.hash_pandas_object(panel, index=False).values.tobytes())
    return h.hexdigest()


def load_weekly_panel(ohlcv: dict[str, pd.DataFrame] | None = None, cache: bool = True,
                      rebuild: bool = False) -> pd.DataFrame:
    """Load the cached weekly panel, rebuilding from ``ohlcv`` when stale or requested.

    If ``cache`` and a fresh parquet exists (and not ``rebuild``), load it. Otherwise build
    from ``ohlcv`` (required in that case), persist parquet + a ``.meta.json`` sidecar carrying
    the content hash / shape, and return it.
    """
    if cache and not rebuild and WEEKLY_PANEL_CACHE.exists():
        return pd.read_parquet(WEEKLY_PANEL_CACHE)
    if ohlcv is None:
        raise ValueError("weekly_panel cache miss and no ohlcv provided to build it")
    panel = build_weekly_panel(ohlcv)
    if cache:
        panel.to_parquet(WEEKLY_PANEL_CACHE, index=False)
        WEEKLY_PANEL_META.write_text(json.dumps({
            "rows": int(len(panel)),
            "tickers": int(panel["ticker"].nunique()),
            "content_sha256": _panel_hash(panel),
            "sma_len": SMA_LEN,
            "slope_lookback": SLOPE_LOOKBACK,
        }, indent=2))
    return panel
