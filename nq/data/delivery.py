"""PIT-clean NSE security-wise DELIVERY features (census candidate #1; pre-reg 0118).

Raw = data/_delivery_raw.parquet (scripts/harvest_delivery.py: MTO + sec_bhavdata daily archive files,
EQ/BE rows). PUBLICATION ASSUMPTION (stated, encoded): each daily file is published the SAME EVENING
after settlement processing (~18:00 IST) and is never restated -> a row dated T is available strictly
after T's close and before any decision that uses a window ending at T (our joins consume features at
dates <= the signal-week Friday; the entry decision executes the following week). Availability
therefore equals the trade date, usable post-close.

`derive_delivery_features` is the pure, trailing-only core (0017's macro.py pattern): every output at
date t uses only rows <= t, so truncating the future leaves past values unchanged — proven by
tests/test_delivery_pit.py. The alias map (data/delisted_alias_map.json) is applied at build time so
delisted members join under their canonical universe ticker.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from config import DATA_DIR

DELIVERY_RAW_PATH = DATA_DIR / "_delivery_raw.parquet"
DELIVERY_PIT_PATH = DATA_DIR / "delivery_pit.parquet"
ALIAS_MAP_PATH = DATA_DIR / "delisted_alias_map.json"

FEATURES = ("dlv_med21", "dlv_trend", "dlv_dwn21", "dlv_med21_z")


def apply_alias_map(raw: pd.DataFrame, alias_path: Path = ALIAS_MAP_PATH) -> pd.DataFrame:
    """Map archive symbols to canonical universe tickers (delisted aliases). Unknown symbols pass
    through unchanged (build-time universe filtering happens downstream)."""
    if not Path(alias_path).exists():
        return raw
    m = json.loads(Path(alias_path).read_text())
    # accept either {alias: canonical} or {canonical: alias}/list forms — normalize to alias->canonical
    amap: dict[str, str] = {}
    for k, v in m.items():
        if isinstance(v, str):
            amap[k] = v
        elif isinstance(v, (list, tuple)):
            for a in v:
                amap[str(a)] = k
    out = raw.copy()
    out["symbol"] = out["symbol"].map(lambda s: amap.get(s, s))
    return out


def derive_delivery_features(panel: pd.DataFrame) -> pd.DataFrame:
    """Trailing-only per-(symbol,date) delivery features.

    ``panel`` columns: symbol, date, deliv_pct, and optionally ``ret`` (that symbol's daily close
    return, for the down-day conditional). Output adds the FEATURES columns; every value at date t
    depends only on rows of that symbol with date <= t (rolling/trailing ops only), so
    ``derive(panel[panel.date <= D])`` == ``derive(panel).loc[date <= D]`` (the truncation property).
    """
    p = panel.sort_values(["symbol", "date"]).copy()
    g = p.groupby("symbol", sort=False)["deliv_pct"]
    p["dlv_med21"] = g.transform(lambda x: x.rolling(21, min_periods=10).median())
    m5 = g.transform(lambda x: x.rolling(5, min_periods=3).mean())
    m21 = g.transform(lambda x: x.rolling(21, min_periods=10).mean())
    p["dlv_trend"] = m5 - m21
    if "ret" in p.columns:
        dwn = p["deliv_pct"].where(p["ret"] < 0)
        p["dlv_dwn21"] = dwn.groupby(p["symbol"], sort=False).transform(
            lambda x: x.rolling(21, min_periods=5).median())
    else:
        p["dlv_dwn21"] = np.nan
    r = p.groupby("symbol", sort=False)["dlv_med21"]
    mu = r.transform(lambda x: x.rolling(252, min_periods=63).mean())
    sd = r.transform(lambda x: x.rolling(252, min_periods=63).std(ddof=0))
    p["dlv_med21_z"] = (p["dlv_med21"] - mu) / sd.replace(0, np.nan)
    return p
