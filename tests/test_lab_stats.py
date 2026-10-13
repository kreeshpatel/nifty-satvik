"""Strategy Lab stats — pure functions on synthetic data with known answers (no engine, no streamlit)."""
from __future__ import annotations

import math

import numpy as np
import pandas as pd
import pytest

from nq.lab import stats as S


def _idx(n: int) -> pd.DatetimeIndex:
    return pd.bdate_range("2020-01-01", periods=n)


def test_perfectly_correlated_assets_are_one_bet():
    x = np.random.default_rng(0).normal(0, 0.01, 200)
    df = pd.DataFrame({"a": x, "b": 2 * x, "c": 3 * x}, index=_idx(200))
    out = S.correlation_variance(df, [1, 1, 1])
    assert out["avg_pairwise_corr"] == pytest.approx(1.0)
    assert out["effective_bets"] == pytest.approx(1.0)
    assert out["top_eigenvalue_share"] == pytest.approx(1.0)
    assert out["diversification_ratio"] == pytest.approx(1.0)
    assert out["variance_shares"]["share"].sum() == pytest.approx(1.0)
    assert out["n"] == 200 and out["uninformative"] is False      # 200 sessions >= the 126 floor


def test_uncorrelated_equal_vol_gives_n_bets():
    rng = np.random.default_rng(1)
    n = 20000                                    # large n so sample rho ~ 0
    df = pd.DataFrame(rng.normal(0, 0.01, (n, 4)), columns=list("abcd"), index=_idx(n))
    out = S.correlation_variance(df, [0.25] * 4)
    assert out["uninformative"] is False
    assert out["effective_bets"] == pytest.approx(4.0, rel=0.02)
    assert out["diversification_ratio"] == pytest.approx(math.sqrt(4), rel=0.02)
    assert out["variance_shares"]["share"].to_numpy() == pytest.approx([0.25] * 4, abs=0.02)


def test_systematic_vs_idiosyncratic_split():
    rng = np.random.default_rng(2)
    n = 5000
    m = pd.Series(rng.normal(0, 0.01, n), index=_idx(n))
    # two names = 1.0 * market + independent noise of equal variance -> R2 of the book ~ 0.5 / (0.5 + 0.25*...)
    df = pd.DataFrame({"a": m + rng.normal(0, 0.01, n), "b": m + rng.normal(0, 0.01, n)}, index=m.index)
    out = S.correlation_variance(df, [0.5, 0.5], market=m)
    assert out["beta_to_market"] == pytest.approx(1.0, abs=0.05)
    # book var = var(m) + var(noise)/2 = 1.5 ; systematic share = 1 / 1.5
    assert out["systematic_var_share"] == pytest.approx(2 / 3, abs=0.03)
    assert out["systematic_var_share"] + out["idiosyncratic_var_share"] == pytest.approx(1.0)


def test_short_window_is_flagged_uninformative():
    df = pd.DataFrame(np.random.default_rng(3).normal(0, 0.01, (60, 3)), columns=list("abc"), index=_idx(60))
    out = S.correlation_variance(df, [1, 1, 1])
    assert out["n"] == 60 and out["uninformative"] is True
    assert S.correlation_variance(df, [1, 1, 1], min_obs=40)["uninformative"] is False


def test_market_exposure_recovers_known_beta_and_alpha():
    rng = np.random.default_rng(4)
    n = 600
    m = pd.Series(rng.normal(0.0004, 0.01, n), index=_idx(n))
    book = 1.5 * m + 0.0002
    out = S.market_exposure(book, m, window=63)
    assert out["beta"] == pytest.approx(1.5)
    assert out["alpha_daily"] == pytest.approx(0.0002)
    assert out["r2"] == pytest.approx(1.0)
    assert out["uninformative"] is False
    assert out["rolling_beta"].dropna().iloc[-1] == pytest.approx(1.5)


def test_market_exposure_splits_drawdown_and_calm_days():
    n = 700
    rng = np.random.default_rng(5)
    m = pd.Series(rng.normal(0.0005, 0.005, n), index=_idx(n))
    m.iloc[300:380] = rng.normal(-0.004, 0.003, 80)          # a ~27% slide: the index sits >10% under its high
    book = pd.Series(rng.normal(0, 0.005, n), index=m.index)  # independent of the index while calm
    book.iloc[300:] = m.iloc[300:] + rng.normal(0, 0.0005, n - 300)   # welded to it from the slide on
    out = S.market_exposure(book, m)
    assert out["drawdown_days"]["n"] > 30 and out["normal_days"]["n"] > 100
    assert out["dd_corr"] > 0.9
    assert out["calm_corr"] < out["dd_corr"] - 0.4      # calm days still include the first welded sessions
    assert out["drawdown_days"]["n"] + out["normal_days"]["n"] == out["n"]


def test_return_tail_known_values():
    # alternating +1% / -0.5% daily -> mean 0.25%, deterministic
    r = np.tile([0.01, -0.005], 250)
    nav = pd.Series(100 * np.cumprod(1 + r), index=_idx(500))
    nav = pd.concat([pd.Series([100.0], index=[nav.index[0] - pd.Timedelta(days=1)]), nav])
    out = S.return_tail(nav, n_boot=200)
    a = np.asarray(r)
    assert out["n"] == 500 and out["uninformative"] is False
    assert out["sharpe"] == pytest.approx(a.mean() / a.std(ddof=1) * math.sqrt(252))
    assert out["var95"] == pytest.approx(-0.005)             # 5th pct of a 2-point distribution
    assert out["cvar95"] == pytest.approx(-0.005)
    assert out["maxdd"] == pytest.approx(-0.005, abs=1e-9)
    assert out["longest_dd_sessions"] == 1
    downside = math.sqrt(np.mean(np.minimum(a, 0) ** 2))
    assert out["sortino"] == pytest.approx(a.mean() / downside * math.sqrt(252))
    assert out["calmar"] == pytest.approx(out["cagr"] / 0.005, rel=1e-6)
    lo, hi = out["sharpe_ci"]
    assert lo <= out["sharpe"] <= hi or math.isnan(lo)


def test_var_cvar_on_known_sample():
    # 100 returns -0.10 .. +0.89 in 0.01 steps -> 5th pct = -0.0505, cvar = mean of those <= it = -0.075
    r = np.arange(-10, 90) / 100.0
    nav = pd.Series(np.concatenate([[1.0], np.cumprod(1 + r)]), index=_idx(101))
    out = S.return_tail(nav, n_boot=50)
    assert out["var95"] == pytest.approx(np.quantile(r, 0.05))
    assert out["cvar95"] == pytest.approx(r[r <= out["var95"]].mean())
    assert out["uninformative"] is True                       # 100 sessions < 126


def test_longest_drawdown_duration():
    nav = pd.Series([1, 2, 1.5, 1.8, 1.9, 2.1, 2.0, 2.05, 2.2], index=_idx(9), dtype=float)
    assert S.longest_drawdown_sessions(nav) == 3          # 1.5,1.8,1.9 below the 2.0 peak
    assert S.longest_drawdown_sessions(pd.Series([1.0, 2.0, 3.0], index=_idx(3))) == 0


def test_expected_max_streak_formula():
    # fair coin, n=1000: log2(500) + gamma/ln2 - 1/2 ~ 8.97 + 0.83 - 0.5 = 9.30
    assert S.expected_max_streak(1000, 0.5) == pytest.approx(9.30, abs=0.05)
    assert math.isnan(S.expected_max_streak(10, 0.0))
    assert math.isnan(S.expected_max_streak(0, 0.5))


def _bars(n: int, hi: float, lo: float, start="2021-01-04") -> pd.DataFrame:
    return pd.DataFrame({"High": [hi] * n, "Low": [lo] * n}, index=pd.bdate_range(start, periods=n))


def test_trade_quality_excursions_hit_and_streaks():
    # entry 100, stop 90 (risk 10); bars never touch the stop (low 95), high 125 -> MFE 2.5R, MAE 0.5R
    bars = _bars(10, hi=125.0, lo=95.0)
    start = bars.index[0]
    end = bars.index[-1]
    rows = []
    # 6 trades: outcomes W W W L L W  (R given), all on the same bars
    for i, R in enumerate([2.0, 1.0, 3.0, -1.0, -1.0, 0.5]):
        rows.append({"tkr": "AAA", "entry": 100.0, "stop0": 90.0, "R": R, "entry_date": start,
                     "exit_date": end + pd.Timedelta(days=i)})
    out = S.trade_quality(pd.DataFrame(rows), {"AAA": bars})
    assert out["n"] == 6 and out["uninformative"] is True
    assert out["R"]["win_rate"] == pytest.approx(4 / 6)
    assert out["R"]["mean"] == pytest.approx(np.mean([2, 1, 3, -1, -1, 0.5]))
    ex = out["excursion"]
    assert ex["mfe_r_mean"] == pytest.approx(2.5) and ex["mae_r_mean"] == pytest.approx(0.5)
    assert ex["capture_agg"] == pytest.approx(4.5 / (6 * 2.5))
    ht = out["hit_target"]
    assert ht["hit_rate"] == 1.0                                  # high 125 >= 120 (2R) and never stopped
    assert ht["null_rate"] == pytest.approx(math.log(100 / 90) / (math.log(120 / 100) + math.log(100 / 90)))
    assert out["streaks"]["longest_win"] == 3 and out["streaks"]["longest_loss"] == 2


def test_trade_quality_counts_a_stop_before_target_as_not_hit():
    bars = _bars(5, hi=110.0, lo=89.0)           # touches the stop (89 <= 90), never 2R
    led = pd.DataFrame([{"tkr": "B", "entry": 100.0, "stop0": 90.0, "R": -1.0,
                         "entry_date": bars.index[0], "exit_date": bars.index[-1]}])
    out = S.trade_quality(led, {"B": bars})
    assert out["hit_target"]["hit_rate"] == 0.0
    assert out["excursion"]["mae_r_mean"] == pytest.approx(1.1)


def test_holdings_weights_and_correlation_at_use_only_past_bars():
    idx = _idx(200)
    rng = np.random.default_rng(7)
    x = rng.normal(0, 0.01, 200)
    rets = pd.DataFrame({"A": x, "B": x, "C": rng.normal(0, 0.01, 200)}, index=idx)
    d = idx[150]
    pl = pd.DataFrame({"date": [d, d, d], "tkr": ["A", "B", "Z"], "notional": [60.0, 40.0, 0.0]})
    w = S.holdings_weights(pl, d)
    assert w.to_dict() == pytest.approx({"A": 0.6, "B": 0.4})
    c = S.correlation_at(pl, rets, d, window=63)
    assert c["avg_pairwise_corr"] == pytest.approx(1.0) and c["n"] == 63 and c["uninformative"] is False
    assert c["corr_matrix"].shape == (2, 2)
    ts = S.correlation_timeseries(pl, rets, [d], window=63)
    assert ts.loc[d, "effective_bets"] == pytest.approx(1.0)


def test_trade_quality_empty_ledger():
    out = S.trade_quality(pd.DataFrame(columns=["tkr", "entry", "stop0", "R", "entry_date", "exit_date"]), {})
    assert out["n"] == 0 and out["uninformative"] is True
