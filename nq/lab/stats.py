"""Strategy Lab statistics — pure functions that describe ONE run's book, never judge it.

WHY THIS MODULE EXISTS

The lab lets the owner poke the weekly-swing engine and read the result four ways: how much the held
names move together, how much the book is the index, how good the individual trades are, and what the
return distribution's tail looks like. Every number here is a *description* of a train-window run
(<= 2024-06-30). None of it authorises a change to the live book; a promising reading leaves the lab as a
pre-registered screen (program-laws / verdict-machine), not as a config edit.

The heavy lifting lives in `nq.brain.portfolio` and `nq.brain.excursions` (committed with their own
SPECs); this module only assembles their outputs into the dicts the app prints. Nothing is
re-implemented here except what those modules do not cover (rolling beta, drawdown duration, VaR/CVaR,
MAE/MFE, streak expectation).

CONVENTIONS
  * No I/O, no clock, no network. Plain dicts / DataFrames out, so a test can pin every number.
  * Every function returns ``n`` and ``uninformative``: True when the sample is below the stated minimum
    (:data:`MIN_TRADES` trades or :data:`MIN_SESSIONS` sessions). An uninformative cell is still
    computed — the flag says "do not lean on this", it does not hide the number.
  * Sharpe is raw (rf = 0) on simple daily returns, ddof = 1, annualised by sqrt(252) — the engine's own
    convention, so the lab's number matches `backtest()['sharpe']`.
"""
from __future__ import annotations

import math
from typing import Any, Mapping, Sequence

import numpy as np
import pandas as pd

from nq.brain import portfolio as PF
from nq.brain.excursions import HIT, first_passage, null_p_target_first

MIN_TRADES = 30          # below this a trade statistic is a story, not a measurement
MIN_SESSIONS = 126       # half a trading year of daily returns
TRADING_DAYS = 252
DD_THRESHOLD, DD_LOOKBACK = 0.10, 252      # "market drawdown day": index >= 10% under its 252d high


def _nan() -> float:
    return float("nan")


def _f(x: Any) -> float:
    """float() that keeps NaN as NaN (and turns None into NaN) so dicts stay JSON/Streamlit friendly."""
    return _nan() if x is None else float(x)


# --------------------------------------------------------------------------- correlation & variance
def correlation_variance(holdings_returns: pd.DataFrame, weights: Sequence[float] | pd.Series, *,
                         market: pd.Series | None = None,
                         min_obs: int = MIN_SESSIONS) -> dict[str, Any]:
    """How much of the book is one bet: togetherness of the held names, and its market share.

    ``holdings_returns``: sessions x names of simple daily returns for the names held in one window.
    ``weights``: the book's weights on those names (a Series is aligned by label, a sequence by
    position); they are re-normalised to sum to 1 because the question is about the *shape* of risk, not
    the cash weight.

    Returns avg pairwise correlation, equal-weight effective bets ``N/(1+(N-1)rho)``, the diversification
    ratio, per-name variance shares (a DataFrame summing to 1), the top-eigenvalue share, and the split
    of the weighted portfolio's variance into a systematic part (beta^2 var(market)) and an idiosyncratic
    remainder when ``market`` is given. ``min_obs`` is the session floor for ``uninformative`` — a
    63-day window passes its own lower floor explicitly.
    """
    r = holdings_returns.dropna(axis=1, how="all")
    names = list(r.columns)
    n = int(len(r))
    out: dict[str, Any] = {"n": n, "n_names": len(names), "uninformative": n < min_obs}
    if len(names) < 2 or n < 3:
        out.update(avg_pairwise_corr=_nan(), effective_bets=float(len(names)) if names else _nan(),
                   diversification_ratio=_nan(), top_eigenvalue_share=_nan(),
                   variance_shares=pd.DataFrame(columns=["share", "own", "cov"]),
                   systematic_var_share=_nan(), idiosyncratic_var_share=_nan(), beta_to_market=_nan(),
                   uninformative=True)
        return out
    if isinstance(weights, pd.Series):
        w = weights.reindex(names).fillna(0.0).to_numpy(float)
    else:
        w_all = np.asarray(list(weights), dtype=float)
        w = w_all[[holdings_returns.columns.get_loc(c) for c in names]]
    total = float(w.sum())
    w = w / total if total > 0 else np.full(len(names), 1.0 / len(names))

    r = r.fillna(0.0)                     # a name absent on a day contributes no return that day
    cov = r.cov().to_numpy(float)
    rho = PF.average_pairwise_correlation(r)
    shares = PF.variance_shares(w, cov)
    if not shares.empty:
        shares.index = names
    out.update(avg_pairwise_corr=rho,
               effective_bets=PF.effective_bets(len(names), rho),
               diversification_ratio=PF.diversification_ratio(w, cov),
               top_eigenvalue_share=PF.top_eigenvalue_share(r),
               variance_shares=shares)
    port = pd.Series(r.to_numpy(float) @ w, index=r.index)
    if market is not None:
        mm = PF.market_model(port, market)
        r2 = mm["r2"]
        out.update(beta_to_market=mm["beta"], systematic_var_share=r2,
                   idiosyncratic_var_share=(1.0 - r2) if np.isfinite(r2) else _nan(),
                   market_overlap_n=int(mm["n"]))
    else:
        out.update(beta_to_market=_nan(), systematic_var_share=_nan(), idiosyncratic_var_share=_nan())
    return out


# --------------------------------------------------------------------------- market exposure
def market_exposure(book_ret: pd.Series, mkt_ret: pd.Series, window: int = 63) -> dict[str, Any]:
    """Beta / alpha / R^2 vs the index, its rolling path, and the book's tie to the index in a selloff.

    ``dd_corr`` vs ``calm_corr`` is the diversification question that matters: names (and books) that
    are uncorrelated on average often converge on the index when it is >= 10% under its 252-day high.
    The market level is rebuilt from ``mkt_ret`` (compounded), so only returns are needed. Each regime
    cell carries its own ``n`` and is flagged on its own — a 30-day drawdown cell is not a regime.
    """
    both = pd.concat([pd.Series(book_ret, dtype=float), pd.Series(mkt_ret, dtype=float)], axis=1,
                     join="inner").dropna()
    both.columns = ["book", "mkt"]
    n = int(len(both))
    mm = PF.market_model(both["book"], both["mkt"])
    out: dict[str, Any] = {"n": n, "uninformative": n < MIN_SESSIONS, "window": int(window),
                           "beta": mm["beta"], "alpha_daily": mm["alpha_daily"],
                           "alpha_annual": (_f(mm["alpha_daily"]) * TRADING_DAYS),
                           "r2": mm["r2"]}
    cov = both["book"].rolling(window).cov(both["mkt"])
    var = both["mkt"].rolling(window).var()
    out["rolling_beta"] = (cov / var.where(var > 0)).dropna().rename("rolling_beta")

    level = (1.0 + both["mkt"]).cumprod()
    dd = PF.drawdown_regime(level, threshold=DD_THRESHOLD, lookback=DD_LOOKBACK).astype(bool)

    def _cell(mask: pd.Series) -> dict[str, Any]:
        sub = both[mask.to_numpy()]
        k = int(len(sub))
        c = float(sub["book"].corr(sub["mkt"])) if k >= 3 else _nan()
        return {"n": k, "corr": c, "uninformative": k < MIN_TRADES}

    out["drawdown_days"] = _cell(dd)
    out["normal_days"] = _cell(~dd)
    out["dd_corr"], out["calm_corr"] = out["drawdown_days"]["corr"], out["normal_days"]["corr"]
    return out


# --------------------------------------------------------------------------- trade quality
def expected_max_streak(n: int, p: float) -> float:
    """Expected longest run of a p-probability event in ``n`` independent trials.

    Schilling (1990) asymptotic: ``E[L] ~ ln(n(1-p)) / ln(1/p) + gamma / ln(1/p) - 1/2`` (gamma =
    Euler-Mascheroni, 0.5772). It is the yardstick for "the book had a 9-loss streak": streaks are
    expected under independence, and only one beyond this number says the outcomes cluster.
    """
    if n <= 0 or not 0.0 < p < 1.0:
        return _nan()
    lp = math.log(1.0 / p)
    return max(1.0, (math.log(n * (1.0 - p)) + 0.5772156649015329) / lp - 0.5) if n * (1 - p) > 0 else 1.0


def _longest_run(flags: Sequence[bool]) -> int:
    best = cur = 0
    for f in flags:
        cur = cur + 1 if f else 0
        best = max(best, cur)
    return best


def trade_quality(ledger: pd.DataFrame, ohlcv: Mapping[str, pd.DataFrame], *,
                  target_r: float = 2.0) -> dict[str, Any]:
    """Distribution, excursions, capture, 2R-vs-null and streaks for a closed-trade ledger.

    ``ledger`` needs ``tkr, entry, stop0, R, entry_date, exit_date`` (the R94 ledger's own columns).
    ``ohlcv`` maps ticker -> DataFrame with High/Low (any case) indexed by date.

    * MAE / MFE are the worst / best excursion between entry and exit bars, in R of the initial risk
      ``entry - stop0``. MAE is reported positive (adverse distance).
    * ``capture = R / MFE`` per trade with MFE > 0: how much of the best-seen move the exit kept. The
      aggregate ``capture_agg`` = sum(R)/sum(MFE) is the weighted version; a few tiny-MFE trades blow
      up the per-trade median otherwise.
    * ``hit_2r`` is the share of trades whose High reached ``entry + target_r * risk`` before the
      stop-price (Low <= stop0) within the trade's own life, compared with the mean driftless first-passage
      null ``b/(a+b)`` (`nq.brain.excursions.null_p_target_first`) over the same entries. An excess over
      the null is the only part the entry can claim. Open-at-window trades count as not-hit.
    * Streaks are in exit order; the expectation is :func:`expected_max_streak` at the observed win rate.
    """
    d = pd.DataFrame(ledger).copy()
    n = int(len(d))
    out: dict[str, Any] = {"n": n, "uninformative": n < MIN_TRADES}
    if n == 0:
        return out
    R = d["R"].astype(float)
    qs = R.quantile([0.05, 0.25, 0.5, 0.75, 0.95])
    wins = R > 0
    out["R"] = {"mean": float(R.mean()), "median": float(R.median()), "std": float(R.std(ddof=1)) if n > 1 else _nan(),
                "skew": PF.sample_skew(R), "q05": float(qs[0.05]), "q25": float(qs[0.25]),
                "q75": float(qs[0.75]), "q95": float(qs[0.95]), "sum": float(R.sum()),
                "win_rate": float(wins.mean())}
    if "reason" in d:
        out["by_exit_reason"] = PF.exit_reason_stats(d)

    rows = []
    for t in d.itertuples(index=False):
        frame = ohlcv.get(t.tkr)
        entry, stop = float(t.entry), float(t.stop0)
        if frame is None or not (stop < entry):
            continue
        cols = {str(c).lower(): c for c in frame.columns}
        if "high" not in cols or "low" not in cols:
            continue
        idx = pd.DatetimeIndex(frame.index)
        sel = (idx >= pd.Timestamp(t.entry_date)) & (idx <= pd.Timestamp(t.exit_date))
        hi = frame.loc[sel, cols["high"]].to_numpy(float)
        lo = frame.loc[sel, cols["low"]].to_numpy(float)
        if hi.size == 0:
            continue
        risk = entry - stop
        target = entry + target_r * risk
        fp = first_passage(hi, lo, entry=entry, stop=stop, target=target)
        rows.append({"tkr": t.tkr, "R": float(t.R),
                     "mfe_r": float((np.nanmax(hi) - entry) / risk),
                     "mae_r": float((entry - np.nanmin(lo)) / risk),
                     "hit": fp.outcome == HIT,
                     "null_p": null_p_target_first(entry, stop, target)})
    ex = pd.DataFrame(rows)
    out["n_with_bars"] = int(len(ex))
    if len(ex):
        pos = ex[ex["mfe_r"] > 0]
        out["excursion"] = {"mfe_r_mean": float(ex["mfe_r"].mean()), "mfe_r_median": float(ex["mfe_r"].median()),
                            "mae_r_mean": float(ex["mae_r"].mean()), "mae_r_median": float(ex["mae_r"].median()),
                            "capture_median": float((pos["R"] / pos["mfe_r"]).median()) if len(pos) else _nan(),
                            "capture_agg": float(pos["R"].sum() / pos["mfe_r"].sum()) if len(pos) and pos["mfe_r"].sum() > 0 else _nan()}
        out["hit_target"] = {"target_r": float(target_r), "hit_rate": float(ex["hit"].mean()),
                             "null_rate": float(ex["null_p"].mean()),
                             "excess": float(ex["hit"].mean() - ex["null_p"].mean()), "n": int(len(ex))}
        out["excursions_table"] = ex
    else:
        out["excursion"], out["hit_target"] = {}, {}

    order = d.assign(_x=pd.to_datetime(d["exit_date"])).sort_values("_x", kind="stable")
    ow = (order["R"].astype(float) > 0).tolist()
    p = float(np.mean(ow))
    out["streaks"] = {"longest_win": _longest_run(ow), "longest_loss": _longest_run([not x for x in ow]),
                      "expected_longest_win": expected_max_streak(n, p),
                      "expected_longest_loss": expected_max_streak(n, 1.0 - p),
                      "formula": "E[L] ~ (ln(n(1-p)) + gamma) / ln(1/p) - 1/2 (Schilling 1990), p = P(event)"}
    return out


# --------------------------------------------------------------------------- return & tail
def _sharpe(a: np.ndarray) -> float:
    a = np.asarray(a, dtype=float)
    sd = a.std(ddof=1) if a.size > 1 else 0.0
    return float(a.mean() / sd * math.sqrt(TRADING_DAYS)) if sd > 0 else _nan()


def longest_drawdown_sessions(nav: pd.Series) -> int:
    """Longest run of consecutive sessions spent strictly below the running equity peak."""
    s = pd.Series(nav, dtype=float).dropna()
    return _longest_run((s < s.cummax()).tolist())


def return_tail(nav: pd.Series, *, n_boot: int = 1000) -> dict[str, Any]:
    """Headline risk/return of a NAV curve plus the left tail and an honest Sharpe interval.

    * Sortino uses downside deviation about 0: ``sqrt(mean(min(r,0)^2))``, annualised the same way.
    * CAGR uses calendar years ``(last - first).days / 365.25`` (never session counts).
    * VaR95 / CVaR95 are 1-day *historical* (5th-percentile return and the mean of returns at or below
      it), reported as returns (negative = loss).
    * ``sharpe_ci`` is a 63-day block bootstrap (`PF.block_bootstrap_ci`): daily returns of a book that
      holds for weeks are autocorrelated, so an iid interval would be too tight.
    """
    s = pd.Series(nav, dtype=float).dropna().sort_index()
    r = PF.daily_returns(s)
    n = int(len(r))
    out: dict[str, Any] = {"n": n, "uninformative": n < MIN_SESSIONS}
    if n < 3:
        return out
    a = r.to_numpy(float)
    years = (s.index[-1] - s.index[0]).days / 365.25
    cagr = float((s.iloc[-1] / s.iloc[0]) ** (1.0 / years) - 1.0) if years > 0 and s.iloc[0] > 0 else _nan()
    dd = s / s.cummax() - 1.0
    maxdd = float(dd.min())
    downside = math.sqrt(float(np.mean(np.minimum(a, 0.0) ** 2)))
    var95 = float(np.quantile(a, 0.05))
    tail = a[a <= var95]
    point, lo, hi = PF.block_bootstrap_ci(a, _sharpe, n_boot=n_boot)
    out.update(sharpe=_sharpe(a),
               sortino=float(a.mean() / downside * math.sqrt(TRADING_DAYS)) if downside > 0 else _nan(),
               cagr=cagr, maxdd=maxdd,
               calmar=(cagr / abs(maxdd)) if maxdd < 0 and np.isfinite(cagr) else _nan(),
               longest_dd_sessions=longest_drawdown_sessions(s),
               var95=var95, cvar95=float(tail.mean()) if tail.size else var95,
               sharpe_ci=(lo, hi), years=float(years), drawdown=dd.rename("drawdown"))
    return out


# --------------------------------------------------------------------------- holdings over time
def holdings_weights(position_log: pd.DataFrame, date: pd.Timestamp) -> pd.Series:
    """Notional weights of the names held at the close of ``date`` (empty Series if none)."""
    pl = position_log
    if pl.empty:
        return pd.Series(dtype=float)
    day = pl[pd.to_datetime(pl["date"]) == pd.Timestamp(date)]
    w = day.groupby("tkr")["notional"].sum()
    w = w[w > 0]
    return w / w.sum() if len(w) else w


def correlation_at(position_log: pd.DataFrame, returns: pd.DataFrame, date: pd.Timestamp, *,
                   window: int = 63, market: pd.Series | None = None) -> dict[str, Any]:
    """:func:`correlation_variance` for the names held on ``date``, over the trailing ``window`` sessions.

    The window is backward-looking from ``date`` (no future bars), and the floor for ``uninformative``
    is the window length itself: a full 63-session window is as informative as this view gets.
    """
    w = holdings_weights(position_log, date)
    names = [t for t in w.index if t in returns.columns]
    win = returns.loc[:pd.Timestamp(date), names].tail(window)
    mkt = None if market is None else market.reindex(win.index)
    out = correlation_variance(win, w.reindex(names), market=mkt, min_obs=window)
    out["date"] = pd.Timestamp(date)
    out["corr_matrix"] = win.corr() if len(names) >= 2 else pd.DataFrame()
    return out


def correlation_timeseries(position_log: pd.DataFrame, returns: pd.DataFrame, dates: Sequence[pd.Timestamp], *,
                           window: int = 63) -> pd.DataFrame:
    """Held-name count, average pairwise correlation and effective bets on each of ``dates``."""
    rows = []
    for d in dates:
        c = correlation_at(position_log, returns, d, window=window)
        rows.append({"date": pd.Timestamp(d), "n_held": c["n_names"], "avg_corr": c["avg_pairwise_corr"],
                     "effective_bets": c["effective_bets"]})
    return pd.DataFrame(rows).set_index("date") if rows else pd.DataFrame(
        columns=["n_held", "avg_corr", "effective_bets"])
