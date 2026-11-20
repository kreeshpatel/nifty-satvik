"""Layer-gate harness for the company-engine study (pre-registration 0153, section b).

Input: a (symbol, date, score) panel. Every statistic runs only on forward returns whose exit date is on
or before 2024-06-30. This is enforced by ``nq.research.holdout.assert_pre_holdout``.

Definitions. Sessions come from the cleaned OHLCV calendar. The universe is PIT Nifty 500 members on the
signal date.

* **Forward excess return, horizon h, delay d.** Enter at the close d sessions after the signal date and
  exit h sessions later. The excess is the stock's return minus the equal-weight return of all members
  over the same window.
* **Decile spread.** Per signal date: mean of the top score decile minus mean of the bottom decile.
  Reported as the mean over weekly signal dates, with a Newey-West t at lag ceil(h/5).
* **Rank IC.** Per-date Spearman between score and forward excess; mean, with Newey-West t at lag ceil(h/5).
* **Gross alpha.**
  * The portfolio is the top score decile, equal weight, rebalanced weekly and held 5 sessions after
    the delay.
  * alpha = mean(r_p − β·r_m), where r_m is the equal-weight member return over the same week and β
    is the full-sample OLS slope. That is the static mix of β in the market and 1 − β in cash, gross,
    with a cash rate of 0.
  * Annualised ×52, with a Newey-West lag-8 t on the weekly series.
* **Tradable slice.** The same alpha restricted to names whose 63-session median traded value
  (close × volume) is at least ₹5 cr.
* **Correlation to the 0001 ranker.** Mean per-date Spearman between the score and NSE's Normalized
  Momentum Score (12m and 6m vol-adjusted, skip 21) on common names.
* **Delay sweep.** Gross alpha for each delay from 0 to 5.
* **By year.** Yearly alpha. The decline test is the OLS slope of yearly alpha on year: t ≤ −2 means a
  significant decline.
* **Low-momentum tercile.** Gross alpha computed within the bottom NMS tercile. Its 95% interval must
  not straddle zero.
* **Turnover.** Weekly one-way change of the top-decile set, ×52.
* **Friction test.**
  * friction = annual turnover × 2 legs × 2 (event-day multiplier) × per-leg cost, plus tax drag.
  * The per-leg cost is brokerage + STT + MID-cap slippage from ``config``.
  * Tax drag = 20% STCG × 1.04 cess × max(alpha, 0).
  * The test passes when friction < gross alpha.
* **Holm.** Step-down adjustment of two-sided p-values across a registered list.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
import pandas as pd

from nq.research.holdout import TRAIN_END, assert_pre_holdout

T_PASS = 2.6
ADV_MIN_RUPEES = 5e7          # Rs 5 crore
STCG = 0.20 * 1.04


def leg_cost() -> float:
    import config
    return config.BROKERAGE_PCT + config.STT_PCT + config.SLIPPAGE["MID_CAP"]


@dataclass
class Market:
    close: pd.DataFrame       # sessions x symbols
    member: pd.DataFrame      # bool, PIT Nifty 500 member on that session
    adv: pd.DataFrame         # 63-session median traded value (Rs)


def load_market(start: str = "2016-01-01") -> Market:
    from nq.data.membership import load_membership
    from nq.data.ohlcv import clean_ohlcv_dict, load_ohlcv_cache
    d = dict(pd.read_pickle(_data("ohlcv_backfill.pkl")))
    d.update(load_ohlcv_cache())
    d = clean_ohlcv_dict(d)
    close = pd.DataFrame({k: v["Close"] for k, v in d.items()}).sort_index().loc[start:]
    vol = pd.DataFrame({k: v["Volume"] for k, v in d.items()}).reindex_like(close)
    adv = (close * vol).rolling(63, min_periods=40).median()
    mem = load_membership() or {}
    member = pd.DataFrame(False, index=close.index, columns=close.columns)
    for s in close.columns:
        for a, b in mem.get(s.upper(), []):
            member.loc[pd.Timestamp(a):pd.Timestamp(b), s] = True
    return Market(close=close, member=member, adv=adv)


def _data(name):
    from pathlib import Path
    return Path(__file__).resolve().parents[2] / "data" / name


# ---------------------------------------------------------------------------------------------- stats
def nw_t(x: np.ndarray, lag: int) -> tuple[float, float]:
    """Mean and Newey-West t-statistic of a 1-d series (Bartlett kernel)."""
    x = np.asarray(x, float)
    x = x[np.isfinite(x)]
    n = len(x)
    if n < 10:
        return float("nan"), float("nan")
    m = x.mean()
    e = x - m
    v = e @ e / n
    for k in range(1, min(lag, n - 1) + 1):
        v += 2 * (1 - k / (lag + 1)) * (e[k:] @ e[:-k]) / n
    return float(m), float(m / math.sqrt(v / n)) if v > 0 else float("nan")


def p_two(t: float) -> float:
    return float(math.erfc(abs(t) / math.sqrt(2))) if np.isfinite(t) else float("nan")


def holm(pvals: dict[str, float]) -> dict[str, float]:
    items = sorted(pvals.items(), key=lambda kv: kv[1])
    m, out, run = len(items), {}, 0.0
    for i, (k, p) in enumerate(items):
        run = max(run, min(1.0, (m - i) * p))
        out[k] = run
    return out


# ---------------------------------------------------------------------------------------------- core
def weekly_dates(idx: pd.DatetimeIndex) -> pd.DatetimeIndex:
    s = pd.Series(idx, index=idx)
    return pd.DatetimeIndex(s.groupby(idx.to_period("W-FRI")).max().values)


def fwd_returns(close: pd.DataFrame, h: int, delay: int) -> tuple[pd.DataFrame, pd.Series]:
    """Per signal session: close[t+delay+h]/close[t+delay]-1, plus the exit date of each signal session."""
    ent = close.shift(-delay)
    ex = close.shift(-(delay + h))
    exit_dt = pd.Series(close.index, index=close.index).shift(-(delay + h))
    return ex / ent - 1, exit_dt


def _guarded(r: pd.DataFrame, exit_dt: pd.Series, dates: pd.DatetimeIndex, unseal_token=None):
    ok = exit_dt.reindex(dates)
    keep = dates[ok.notna().to_numpy() & (ok <= pd.Timestamp(TRAIN_END)).to_numpy()] if unseal_token is None \
        else dates[ok.notna().to_numpy()]
    assert_pre_holdout(pd.Series(1.0, index=pd.DatetimeIndex(ok.reindex(keep).values)),
                       unseal_token=unseal_token, what="forward-return exit dates")
    return r.reindex(keep), keep


class Gate:
    def __init__(self, mkt: Market, unseal_token: str | None = None):
        self.m = mkt
        self.tok = unseal_token
        self.dates = weekly_dates(mkt.close.index)
        self._cache: dict = {}

    def excess(self, h: int, delay: int) -> pd.DataFrame:
        key = ("ex", h, delay)
        if key not in self._cache:
            r, exit_dt = fwd_returns(self.m.close, h, delay)
            r, keep = _guarded(r, exit_dt, self.dates, self.tok)
            mem = self.m.member.reindex(keep)
            r = r.where(mem)
            self._cache[key] = (r.sub(r.mean(axis=1), axis=0), r.mean(axis=1), r)
        return self._cache[key][0]

    def raw(self, h: int, delay: int):
        self.excess(h, delay)
        _, mkt, r = self._cache[("ex", h, delay)]
        return r, mkt

    def align(self, score: pd.DataFrame, h: int = 5, delay: int = 0) -> pd.DataFrame:
        ex = self.excess(h, delay)
        s = score.reindex(index=ex.index, columns=ex.columns)
        return s.where(ex.notna())

    # --- statistics
    def decile_spread(self, score: pd.DataFrame, h: int, delay: int = 0) -> dict:
        ex = self.excess(h, delay)
        s = self.align(score, h, delay)
        pct = s.rank(axis=1, pct=True)
        top = ex.where(pct > 0.9).mean(axis=1)
        bot = ex.where(pct <= 0.1).mean(axis=1)
        m, t = nw_t((top - bot).to_numpy(), math.ceil(h / 5))
        return {"h": h, "spread_mean": m, "t_nw": t, "n_dates": int((top - bot).notna().sum())}

    def rank_ic(self, score: pd.DataFrame, h: int, delay: int = 0) -> dict:
        ex = self.excess(h, delay)
        s = self.align(score, h, delay)
        ic = s.rank(axis=1).corrwith(ex.where(s.notna()).rank(axis=1), axis=1)
        m, t = nw_t(ic.to_numpy(), math.ceil(h / 5))
        return {"h": h, "ic_mean": m, "t_nw": t}

    def top_mask(self, score: pd.DataFrame, delay: int = 0, tradable: bool = False,
                 within: pd.DataFrame | None = None) -> pd.DataFrame:
        s = self.align(score, 5, delay)
        if tradable:
            s = s.where(self.m.adv.reindex_like(s) >= ADV_MIN_RUPEES)
        if within is not None:
            s = s.where(within.reindex_like(s).fillna(False).astype(bool))
        return s.rank(axis=1, pct=True) > 0.9

    def alpha(self, score: pd.DataFrame | None = None, delay: int = 0, tradable: bool = False,
              within: pd.DataFrame | None = None, mask: pd.DataFrame | None = None) -> dict:
        r, mkt = self.raw(5, delay)
        top = self.top_mask(score, delay, tradable, within) if mask is None else mask
        if score is not None:
            # market = EW of the names the score covers (members with a score), not all members: comparing a
            # seasoned-stock subset to a market that includes fresh listings biased the null (t mean +0.5).
            mkt = r.where(self.align(score, 5, delay).notna()).mean(axis=1)
        rp = r.where(top).mean(axis=1)
        ok = rp.notna() & mkt.notna()
        rp, mk = rp[ok], mkt[ok]
        if len(rp) < 20:
            return {"alpha_ann": float("nan"), "t_nw": float("nan"), "beta": float("nan"), "n_weeks": len(rp)}
        beta = float(np.cov(rp, mk, ddof=1)[0, 1] / np.var(mk, ddof=1))
        exr = rp - beta * mk
        m, t = nw_t(exr.to_numpy(), 8)
        return {"alpha_ann": m * 52, "t_nw": t, "beta": beta, "n_weeks": int(len(rp)), "_weekly": exr}

    def turnover(self, score: pd.DataFrame) -> float:
        top = self.top_mask(score)
        prev = top.shift(1)
        both = (top & prev.fillna(False).astype(bool)).sum(axis=1)
        n = top.sum(axis=1)
        to = (1 - both / n.where(n > 0)).iloc[1:]
        return float(to.mean() * 52)

    def corr_to(self, score: pd.DataFrame, ref: pd.DataFrame) -> float:
        s = self.align(score)
        r = ref.reindex_like(s).where(s.notna())
        s = s.where(r.notna())
        return float(s.rank(axis=1).corrwith(r.rank(axis=1), axis=1).mean())

    def evaluate(self, score: pd.DataFrame, ref_0001: pd.DataFrame | None = None) -> dict:
        a = self.alpha(score)
        wk = a.pop("_weekly", pd.Series(dtype=float))
        yearly = wk.groupby(wk.index.year).mean() * 52 if len(wk) else pd.Series(dtype=float)
        slope_t = float("nan")
        if len(yearly) >= 3:
            x = yearly.index.to_numpy(float)
            X = np.c_[np.ones_like(x), x]
            b, res, *_ = np.linalg.lstsq(X, yearly.to_numpy(), rcond=None)
            e = yearly.to_numpy() - X @ b
            se = math.sqrt((e @ e) / (len(x) - 2) / ((x - x.mean()) ** 2).sum())
            slope_t = float(b[1] / se) if se > 0 else float("nan")
        delays = {d: {k: v for k, v in self.alpha(score, delay=d).items() if k != "_weekly"} for d in range(6)}
        trad = {k: v for k, v in self.alpha(score, tradable=True).items() if k != "_weekly"}
        to = self.turnover(score)
        fric = to * 2 * 2 * leg_cost() + STCG * max(a["alpha_ann"], 0)
        out = {"decile_21": self.decile_spread(score, 21), "decile_63": self.decile_spread(score, 63),
               "ic_21": self.rank_ic(score, 21), "ic_63": self.rank_ic(score, 63), "alpha": a,
               "tradable": trad, "delay_sweep": delays, "by_year": yearly.round(4).to_dict(),
               "decline_slope_t": slope_t, "turnover_ann": to, "friction_ann": fric,
               "friction_pass": bool(fric < a["alpha_ann"]) if np.isfinite(a["alpha_ann"]) else False}
        if ref_0001 is not None:
            out["corr_0001"] = self.corr_to(score, ref_0001)
            terc = ref_0001.rank(axis=1, pct=True) <= 1 / 3
            lo = self.alpha(score, within=terc)
            lo.pop("_weekly", None)
            se = abs(lo["alpha_ann"] / lo["t_nw"]) if lo["t_nw"] else float("nan")
            lo["straddles_zero"] = bool(lo["alpha_ann"] - 1.96 * se < 0 < lo["alpha_ann"] + 1.96 * se)
            out["low_mom_tercile"] = lo
        out["pass_t"] = bool(abs(a["t_nw"]) >= T_PASS and a["alpha_ann"] > 0)
        return out


def nms_panel(mkt: Market) -> pd.DataFrame:
    """0001's ranker: NSE Normalized Momentum Score over PIT N500 members (weekly dates x symbols)."""
    from nq.signals import nse_momentum_score, vol_adjusted_return
    c = mkt.close
    mr12 = pd.DataFrame({s: vol_adjusted_return(c[s].to_numpy(), 252) for s in c}, index=c.index)
    mr6 = pd.DataFrame({s: vol_adjusted_return(c[s].to_numpy(), 126) for s in c}, index=c.index)
    wd = weekly_dates(c.index)
    mem = mkt.member.reindex(wd)
    long = pd.DataFrame({"mr12": mr12.reindex(wd).where(mem).stack(), "mr6": mr6.reindex(wd).where(mem).stack()})
    long = long.dropna().reset_index().rename(columns={"level_0": "date", "level_1": "symbol"})
    long.columns = ["date", "symbol", "mr12", "mr6"]
    out = nse_momentum_score(long)
    return out.pivot(index="date", columns="symbol", values="nms")
