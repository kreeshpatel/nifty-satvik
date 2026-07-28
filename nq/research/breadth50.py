"""breadth-50 watched-pair construction (feasibility memo §3; Oct-1 proposal) — BUILT COLD.

Pure construction machinery, cfg-gated OFF by absence: this module is wired into NO cron and NO
engine path; the golden master is byte-identical because nothing imports it at runtime. Activation
(if ever) happens via the Oct-1 amendment, not here. Construction only — this module computes
holdings and weights; it evaluates NOTHING.

The two books, per the frozen proposal:
  EW: top-50 by weekly CRS strength, equal weight 2%.
  SW: same 50 names, tilt = 0.5 + 1.5 * dlv_pctile  (dlv_med21 percentile within the 50 — the 0118
      gradient, definition verbatim), then *0.5 if a known results event sits within 14cd of the
      entry-week Monday (the 0120 flag, definition verbatim), clipped to [0.5, 2.0], renormalized.

CRS note (documented, not hidden): the per-week cross-sectional crs_dist here uses the engine's own
formula (weekly RS vs the Nifty-50 index, SMA40 of RS, dist = RS/SMA40 - 1) computed panel-wide;
the signal engine materializes the identical quantity only at signal weeks. Reconciliation against
engine values at signal weeks is part of the dry-run.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

TILT_LO, TILT_HI = 0.5, 2.0
N_BOOK = 50
EVENT_WINDOW_CD = 14


def weekly_crs_dist(closes: pd.DataFrame, index_close: pd.Series,
                    asof: pd.Timestamp) -> pd.Series:
    """Cross-sectional crs_dist at the last completed W-FRI week <= asof.

    closes: daily close panel (columns=tickers). index_close: the Nifty-50 daily close series.
    RS = weekly close / index weekly close; dist = RS / SMA40(RS) - 1 (the engine's formula).
    """
    wc = closes.resample("W-FRI").last()
    wi = index_close.resample("W-FRI").last()
    wc = wc[wc.index <= asof]
    wi = wi[wi.index <= asof]
    rs = wc.div(wi, axis=0)
    sma40 = rs.rolling(40).mean()
    dist = rs.iloc[-1] / sma40.iloc[-1] - 1.0
    return dist.dropna()


def select_top50(crs: pd.Series, eligible: set[str] | None = None) -> list[str]:
    s = crs.dropna()
    if eligible is not None:
        s = s[s.index.isin(eligible)]
    return list(s.sort_values(ascending=False).head(N_BOOK).index)


def sw_tilts(names: list[str], dlv_med21: pd.Series, event_flag: pd.Series) -> pd.Series:
    """The frozen SW tilt: 0.5 + 1.5*dlv_pctile (within the 50), *0.5 on the event flag, clipped."""
    d = dlv_med21.reindex(names)
    pct = d.rank(pct=True).fillna(0.5)                     # missing delivery -> neutral percentile
    tilt = 0.5 + 1.5 * pct
    ev = event_flag.reindex(names).fillna(False).astype(bool)
    tilt = tilt.where(~ev, tilt * 0.5)
    return tilt.clip(TILT_LO, TILT_HI)


def build_books(crs: pd.Series, dlv_med21: pd.Series, event_flag: pd.Series,
                eligible: set[str] | None = None) -> pd.DataFrame:
    """-> DataFrame[name, crs, dlv_med21, event_flag, w_ew, w_sw]; both weight columns sum to 1."""
    names = select_top50(crs, eligible)
    tilt = sw_tilts(names, dlv_med21, event_flag)
    out = pd.DataFrame({
        "crs": crs.reindex(names),
        "dlv_med21": dlv_med21.reindex(names),
        "event_flag": event_flag.reindex(names).fillna(False).astype(bool),
        "w_ew": 1.0 / len(names),
        "w_sw": (tilt / tilt.sum()).to_numpy(),
    }, index=pd.Index(names, name="ticker"))
    assert np.isclose(out["w_ew"].sum(), 1.0) and np.isclose(out["w_sw"].sum(), 1.0)
    return out
