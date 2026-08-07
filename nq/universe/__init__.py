"""Point-in-time tradable universe — the service every backtest must go through.

The single largest data risk in Indian mid/small caps is survivorship: using today's index list for
a 2018 decision silently deletes everyone who failed. The published estimates put the overstatement
at roughly 1-4 percentage points a year generally, and materially higher in the small-cap tail, with
drawdowns understated on top. That is first-order — larger than most signal effects anyone tests.

So membership is resolved **as of each date** from the corrected PIT reconstruction, and every
screen below reads trailing data only.

Size bands
----------
The repo holds Nifty-500 PIT membership but **no Midcap-150 constituent history**, so the midcap
band is reconstructed by ranking eligible members on trailing 63-day median turnover:

    LARGE = ranks 1-100 · MID = 101-250 · SMALL = 251+

Bands are recomputed at every date from trailing data, so a name migrates as it would have in life.
This is an approximation of the published index and is labelled as one wherever it is used — it is
not the NSE constituent list.

Screens
-------
============  ==========================================================================
liquidity     trailing 63d median turnover >= ``MIN_TURNOVER`` (Rs 5cr)
history       >= ``MIN_HISTORY`` sessions of prices (the momentum indices require >= 1yr)
price floor   close >= ``MIN_PRICE`` — keeps sub-Rs 10 names out
circuit       excluded when the absolute daily return reaches 19.5% on >= 20% of the
              prior 126 sessions
============  ==========================================================================

**Declared coverage gaps, stated rather than assumed away.** There is no ASM/GSM surveillance
history and no circuit-band feed in this repo. The circuit screen above is a *proxy computed from
returns* — it detects names that repeatedly move like they are hitting bands, which is not the same
as knowing they were. It approximates the NSE momentum-index tradability rule ("non-F&O stocks
ineligible if they hit upper/lower circuit on >= 20% of trading days in the trailing 6 months")
without the underlying feed. Any readout built on this universe carries that caveat.
"""
from __future__ import annotations

from collections.abc import Mapping
from datetime import date

import numpy as np
import pandas as pd

__all__ = ["build_universe", "size_bands", "BANDS", "MIN_TURNOVER", "MIN_HISTORY", "MIN_PRICE",
           "CIRCUIT_MOVE", "CIRCUIT_FRAC", "TURNOVER_WINDOW"]

MIN_TURNOVER = 5e7          # Rs 5 cr trailing median daily turnover
MIN_HISTORY = 252           # >= 1 year of sessions
MIN_PRICE = 10.0            # rupees
TURNOVER_WINDOW = 63
CIRCUIT_MOVE = 0.195        # |daily return| at/above this looks like a band hit
CIRCUIT_FRAC = 0.20         # excluded if it happens on >= this share of the last 126 sessions
CIRCUIT_WINDOW = 126

BANDS: dict[str, tuple[int, int]] = {"LARGE": (0, 100), "MID": (100, 250), "SMALL": (250, 10_000)}


def size_bands(rank: np.ndarray) -> np.ndarray:
    """Map a 1-based turnover rank to a band label; NaN rank -> empty string."""
    out = np.full(len(rank), "", dtype=object)
    for name, (lo, hi) in BANDS.items():
        out[(rank > lo) & (rank <= hi)] = name
    return out


def build_universe(
    ohlcv: Mapping[str, pd.DataFrame],
    membership: Mapping[str, list[tuple[date, date]]] | None,
    *,
    start: str | None = None,
    end: str | None = None,
    min_turnover: float = MIN_TURNOVER,
    min_history: int = MIN_HISTORY,
    min_price: float = MIN_PRICE,
    apply_circuit_screen: bool = True,
) -> pd.DataFrame:
    """Return a tidy long panel with prices, liquidity, size band and an ``eligible`` flag.

    Columns: ``date ticker open high low close volume adv_rupees_20d turnover_63d bars
    is_member liq_ok hist_ok price_ok circuit_ok eligible turnover_rank size_band``.

    ``eligible`` is the AND of every screen.

    ``eligible`` is the AND of every screen. Individual flags are kept so a readout can say *which*
    screen removed a name rather than reporting an opaque count — a universe that shrinks for an
    unexamined reason is how a backtest quietly becomes a different experiment.
    """
    frames = []
    for tkr in sorted(ohlcv):
        df = ohlcv[tkr]
        if df is None or len(df) < 2 or "Close" not in df.columns:
            continue
        idx = pd.DatetimeIndex(df.index)
        c = df["Close"].to_numpy(float)
        v = (df["Volume"].to_numpy(float) if "Volume" in df.columns
             else np.zeros(len(c), dtype=float))
        tv = pd.Series(c * v)

        mem = np.ones(len(idx), dtype=bool)
        if membership is not None:
            periods = membership.get(tkr.upper())
            if not periods:
                continue
            mem = np.zeros(len(idx), dtype=bool)
            for a, b in periods:
                mem |= (idx >= pd.Timestamp(a)) & (idx <= pd.Timestamp(b))
            if not mem.any():
                continue

        ret = pd.Series(c).pct_change().abs()
        circuit_frac = (ret >= CIRCUIT_MOVE).rolling(
            CIRCUIT_WINDOW, min_periods=CIRCUIT_WINDOW // 2).mean().to_numpy()

        frames.append(pd.DataFrame({
            "date": idx, "ticker": tkr,
            "open": df["Open"].to_numpy(float), "high": df["High"].to_numpy(float),
            "low": df["Low"].to_numpy(float), "close": c, "volume": v,
            "adv_rupees_20d": tv.rolling(20, min_periods=10).mean().to_numpy(),
            "turnover_63d": tv.rolling(TURNOVER_WINDOW,
                                       min_periods=TURNOVER_WINDOW // 2).median().to_numpy(),
            "bars": np.arange(1, len(c) + 1),
            "is_member": mem,
            "circuit_frac": circuit_frac,
        }))

    if not frames:
        return pd.DataFrame()
    p = pd.concat(frames, ignore_index=True)
    if start:
        p = p[p["date"] >= pd.Timestamp(start)]
    if end:
        p = p[p["date"] <= pd.Timestamp(end)]
    if p.empty:
        return p.reset_index(drop=True)

    p["liq_ok"] = p["turnover_63d"] >= min_turnover
    p["hist_ok"] = p["bars"] >= min_history
    p["price_ok"] = p["close"] >= min_price
    p["circuit_ok"] = (~(p["circuit_frac"] >= CIRCUIT_FRAC)) if apply_circuit_screen else True
    p["eligible"] = (p["is_member"] & p["liq_ok"] & p["hist_ok"] & p["price_ok"]
                     & p["circuit_ok"]).fillna(False)

    # size band from turnover rank AMONG ELIGIBLE NAMES ONLY, per date
    p["turnover_rank"] = np.nan
    elig = p["eligible"]
    p.loc[elig, "turnover_rank"] = (p.loc[elig]
                                    .groupby("date")["turnover_63d"]
                                    .rank(ascending=False, method="first"))
    p["size_band"] = size_bands(p["turnover_rank"].to_numpy())
    return p.sort_values(["date", "ticker"]).reset_index(drop=True)


def screen_report(panel: pd.DataFrame) -> dict:
    """How many names each screen removed — so universe shrinkage is attributable, not mysterious."""
    if panel.empty:
        return {}
    n = len(panel)
    counts = {f"{k}_fail": int((~panel[k]).sum()) for k in
              ("is_member", "liq_ok", "hist_ok", "price_ok", "circuit_ok") if k in panel}
    per_day = panel[panel["eligible"]].groupby("date")["ticker"].nunique()
    bands = (panel[panel["eligible"]].groupby(["date", "size_band"])["ticker"].nunique()
             .groupby("size_band").mean().round(1).to_dict())
    return {
        "rows": n, "eligible_rows": int(panel["eligible"].sum()),
        **counts,
        "mean_eligible_per_day": round(float(per_day.mean()), 1) if len(per_day) else 0.0,
        "min_eligible_per_day": int(per_day.min()) if len(per_day) else 0,
        "mean_per_band": bands,
        "caveat": ("size bands are reconstructed from trailing turnover rank, NOT NSE constituent "
                   "lists; the circuit screen is a returns-based proxy, not a surveillance feed"),
    }
