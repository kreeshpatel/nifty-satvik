"""Residual-momentum ranks — the canonical first-party home (was inline in scripts/run_residual_momentum).

`residual_ranks(panel, factors)` computes, per name, a monthly residual-momentum score: regress the
trailing 252 daily returns on the FF-India factors [mkt, hml], take the information ratio of the
residuals over t-252..t-21 (skip the recent month, Blitz-Huij-Martens), assign it strict-before
(month-end t -> dates > t), and cross-sectionally percentile-rank it per day. Used by the residual
backtests (0077/0078) and the forward-wall veto book (nq.paper.wall_cron).

PIT-safe: the regression is trailing-only; the score is applied strict-before; the factors' HML `bp`
came through value_quality_series' strict-before availability join (see nq.data.fundamentals).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

REG_WIN = 252   # trailing days for the factor regression
SKIP = 21       # skip the recent month in the residual IR (BHM)
MIN_XSEC = 15   # (kept for callers that x-sec rank downstream)


def residual_ranks(panel: pd.DataFrame, factors: pd.DataFrame) -> pd.DataFrame:
    """Long df [date, ticker, resid_rank] — monthly residual-momentum IR, strict-before, x-sec ranked.

    `panel` needs columns [date, ticker, close] (date datetime64); `factors` is indexed by date with
    columns [mkt, hml] (daily factor returns)."""
    rows = []
    for tkr, g in panel[["date", "ticker", "close"]].sort_values("date").groupby("ticker"):
        g = g.drop_duplicates("date")
        s = pd.Series(g["close"].to_numpy(float), index=pd.DatetimeIndex(g["date"].to_numpy()))
        df = pd.concat([s.pct_change().rename("r"), factors], axis=1, join="inner").dropna()
        if len(df) < REG_WIN + SKIP + 5:
            continue
        idx = df.index
        y_all = df["r"].to_numpy(float)
        x_all = np.column_stack([np.ones(len(df)), df["mkt"].to_numpy(float), df["hml"].to_numpy(float)])
        me = pd.Series(np.arange(len(idx)), index=idx).groupby(idx.to_period("M")).last().to_numpy()
        sc: dict[pd.Timestamp, float] = {}
        for pos in me:
            if pos < REG_WIN - 1:
                continue
            xw, yw = x_all[pos - REG_WIN + 1:pos + 1], y_all[pos - REG_WIN + 1:pos + 1]
            coef = np.linalg.lstsq(xw, yw, rcond=None)[0]
            resid = (yw - xw @ coef)[:-SKIP]
            if resid.std() > 0 and resid.size > 50:
                sc[idx[pos]] = float(resid.mean() / resid.std())
        if not sc:
            continue
        right = pd.DataFrame({"avail": list(sc.keys()), "score": list(sc.values())}).sort_values("avail")
        m = pd.merge_asof(pd.DataFrame({"date": idx}), right, left_on="date", right_on="avail",
                          direction="backward", allow_exact_matches=False)   # strict-before
        rows.append(pd.DataFrame({"date": idx, "ticker": tkr, "score": m["score"].to_numpy()}))
    long = pd.concat(rows, ignore_index=True).dropna(subset=["score"])
    long["resid_rank"] = long.groupby("date")["score"].rank(pct=True)
    return long[["date", "ticker", "resid_rank"]]
