"""nq.brain.portfolio — each measure is pinned on a case whose answer is known without the code.

Portfolio statistics are easy to get subtly wrong (a correlation that includes the diagonal, a
diversification ratio that forgets the covariance terms, risk shares that do not sum to one). Every
test below has an analytic answer: identical assets, independent assets, or a series built from a known
beta.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from nq.brain import portfolio as P  # noqa: E402


# --------------------------------------------------------------------------- the market model
def test_market_model_recovers_a_known_beta_and_alpha():
    rng = np.random.default_rng(0)
    mkt = pd.Series(rng.normal(0.0004, 0.01, 1500))
    book = 1.3 * mkt + 0.0002 + rng.normal(0, 0.002, 1500)
    got = P.market_model(book, mkt)
    assert got["beta"] == pytest.approx(1.3, abs=0.03)
    assert got["alpha_daily"] == pytest.approx(0.0002, abs=0.0002)
    assert 0.9 < got["r2"] <= 1.0
    assert got["market_part_daily"] == pytest.approx(got["beta"] * got["mean_market_daily"])


def test_market_model_uses_only_common_dates():
    idx = pd.date_range("2026-01-01", periods=10)
    book = pd.Series(np.linspace(0.01, 0.02, 10), index=idx)
    mkt = pd.Series(np.linspace(0.01, 0.02, 6), index=idx[:6])
    assert P.market_model(book, mkt)["n"] == 6


def test_a_book_with_no_market_link_has_beta_near_zero():
    rng = np.random.default_rng(1)
    mkt = pd.Series(rng.normal(0, 0.01, 2000))
    book = pd.Series(rng.normal(0, 0.01, 2000))
    got = P.market_model(book, mkt)
    assert abs(got["beta"]) < 0.1 and got["r2"] < 0.05


def test_too_short_a_sample_returns_nan_rather_than_a_number():
    assert np.isnan(P.market_model(pd.Series([0.01, 0.02]), pd.Series([0.01, 0.02]))["beta"])


# --------------------------------------------------------------------------- togetherness
def test_identical_names_are_one_bet():
    r = pd.DataFrame({"a": [0.01, -0.02, 0.03, 0.00, 0.01]})
    r["b"], r["c"] = r["a"], r["a"]
    assert P.average_pairwise_correlation(r) == pytest.approx(1.0)
    assert P.effective_bets(3, 1.0) == pytest.approx(1.0)
    cov = r.cov().to_numpy()
    assert P.diversification_ratio([1 / 3] * 3, cov) == pytest.approx(1.0)
    assert P.top_eigenvalue_share(r) == pytest.approx(1.0)


def test_independent_equal_names_diversify_by_root_n():
    rng = np.random.default_rng(2)
    r = pd.DataFrame(rng.normal(0, 0.02, (4000, 4)), columns=list("abcd"))
    assert abs(P.average_pairwise_correlation(r)) < 0.05
    assert P.effective_bets(4, 0.0) == pytest.approx(4.0)
    assert P.diversification_ratio([0.25] * 4, r.cov().to_numpy()) == pytest.approx(2.0, abs=0.05)
    assert P.top_eigenvalue_share(r) == pytest.approx(0.25, abs=0.03)


def test_effective_bets_between_the_extremes():
    assert P.effective_bets(6, 0.5) == pytest.approx(6 / 3.5)
    assert P.effective_bets(6, 0.0) == 6.0
    assert P.effective_bets(6, 1.0) == pytest.approx(1.0)
    assert np.isnan(P.effective_bets(0, 0.3))


def test_average_correlation_ignores_the_diagonal():
    """Including the diagonal is the classic bug: it would drag a 0.0 average up to 1/3 here."""
    rng = np.random.default_rng(3)
    r = pd.DataFrame(rng.normal(0, 0.01, (3000, 3)), columns=list("abc"))
    assert abs(P.average_pairwise_correlation(r)) < 0.05


def test_one_column_is_not_a_correlation():
    assert np.isnan(P.average_pairwise_correlation(pd.DataFrame({"a": [0.01, 0.02, -0.01]})))


# --------------------------------------------------------------------------- variance shares
def test_variance_shares_sum_to_one_and_split_own_from_covariance():
    rng = np.random.default_rng(4)
    r = pd.DataFrame(rng.normal(0, 0.02, (2000, 3)), columns=list("abc"))
    cov = r.cov().to_numpy()
    w = [0.5, 0.3, 0.2]
    out = P.variance_shares(w, cov)
    assert out["share"].sum() == pytest.approx(1.0)
    assert (out["own"] >= 0).all(), "an own-variance term is w²σ², never negative"
    assert np.allclose(out["own"] + out["cov"], out["share"])
    assert out.loc[0, "share"] > out.loc[2, "share"], "the biggest weight carries the biggest share"


def test_with_independent_names_the_shares_are_almost_all_own_risk():
    rng = np.random.default_rng(5)
    r = pd.DataFrame(rng.normal(0, 0.02, (4000, 3)), columns=list("abc"))
    out = P.variance_shares([1 / 3] * 3, r.cov().to_numpy())
    assert out["cov"].abs().max() < 0.05


# --------------------------------------------------------------------------- regime and trades
def test_drawdown_regime_marks_the_drop_not_the_peak():
    s = pd.Series(list(np.linspace(100, 200, 300)) + list(np.linspace(200, 150, 60)))
    flag = P.drawdown_regime(s, threshold=0.10, lookback=252)
    assert not bool(flag.iloc[299])
    assert bool(flag.iloc[-1])                                  # 150 vs a 200 peak = −25%


def test_exit_reason_stats_shares_sum_to_one_and_skew_has_the_right_sign():
    trades = pd.DataFrame({
        "reason": ["stop"] * 4 + ["targets"] * 4,
        "R": [-1.0, -1.1, -0.9, -1.0, 0.5, 0.6, 0.4, 8.0],
    })
    out = P.exit_reason_stats(trades)
    assert out["share_of_total_R"].sum() == pytest.approx(1.0)
    assert out.loc["targets", "skew_R"] > 1.0, "one big winner makes the target family right-skewed"
    assert out.loc["stop", "n"] == 4


def test_sample_skew_matches_a_hand_computed_value():
    x = [0.0, 0.0, 0.0, 4.0]
    m, sd = 1.0, np.sqrt(3.0)
    assert P.sample_skew(x) == pytest.approx(np.mean([(v - m) ** 3 for v in x]) / sd ** 3)
    assert np.isnan(P.sample_skew([1.0, 2.0]))


# --------------------------------------------------------------------------- uncertainty
def test_block_bootstrap_brackets_the_mean():
    rng = np.random.default_rng(6)
    x = rng.normal(0.001, 0.01, 1000)
    pt, lo, hi = P.block_bootstrap_ci(x, lambda a: float(a.mean()), block=63, n_boot=400)
    assert pt == pytest.approx(x.mean())
    assert lo < x.mean() < hi


def test_blocks_widen_the_ci_when_the_series_is_autocorrelated():
    """The point of blocks. On iid data block and single-draw resampling agree; on an AR(1) series the
    single-draw CI is too tight, which is exactly what would understate a book's risk."""
    rng = np.random.default_rng(7)
    e = rng.normal(0, 0.01, 4000)
    x = np.zeros(4000)
    for i in range(1, 4000):
        x[i] = 0.8 * x[i - 1] + e[i]
    _, lo_b, hi_b = P.block_bootstrap_ci(x, lambda a: float(a.mean()), block=63, n_boot=400)
    _, lo_1, hi_1 = P.block_bootstrap_ci(x, lambda a: float(a.mean()), block=1, n_boot=400)
    assert (hi_b - lo_b) > 1.5 * (hi_1 - lo_1)


def test_a_series_shorter_than_one_block_reports_the_point_without_a_ci():
    pt, lo, hi = P.block_bootstrap_ci([0.01, 0.02, 0.03], lambda a: float(a.mean()), block=63)
    assert pt == pytest.approx(0.02) and np.isnan(lo) and np.isnan(hi)


def test_daily_returns_drops_the_undefined_first_point():
    nav = pd.Series([100.0, 110.0, 99.0], index=pd.date_range("2026-01-01", periods=3))
    r = P.daily_returns(nav)
    assert len(r) == 2 and r.iloc[0] == pytest.approx(0.10)


def test_paired_block_bootstrap_recovers_a_known_beta_and_keeps_the_pairing():
    """It must resample arrays, not dated Series: the first version resampled dates, produced duplicate
    labels, and crashed the join inside market_model."""
    rng = np.random.default_rng(8)
    mkt = rng.normal(0, 0.01, 1200)
    book = 0.9 * mkt + rng.normal(0, 0.003, 1200)
    pt, lo, hi = P.block_bootstrap_paired(mkt, book, P.beta_of, block=63, n_boot=300)
    assert pt == pytest.approx(0.9, abs=0.05)
    assert lo < 0.9 < hi
    shuffled = rng.permutation(book)
    pt2, _, _ = P.block_bootstrap_paired(mkt, shuffled, P.beta_of, block=63, n_boot=100)
    assert abs(pt2) < 0.2, "breaking the pairing must destroy the beta"


def test_paired_bootstrap_refuses_mismatched_lengths():
    with pytest.raises(ValueError, match="same length"):
        P.block_bootstrap_paired([1.0, 2.0, 3.0], [1.0, 2.0], P.beta_of)


# --------------------------------------------------------------------------- red-team fixes (2026-09-24)
def test_share_of_total_r_is_undefined_when_the_book_lost_money():
    """The live book's own cell: stops lost 16.32R of a 17.27R loss and printed a +94.5% 'share'."""
    trades = pd.DataFrame({"reason": ["stop"] * 10 + ["sma_break"], "R": [-1.632] * 10 + [-0.95]})
    out = P.exit_reason_stats(trades)
    assert out.loc["stop", "sum_R"] == pytest.approx(-16.32)
    assert np.isnan(out.loc["stop", "share_of_total_R"]), "a losing family must not read as a contribution"


def test_share_of_total_r_still_works_when_the_book_made_money():
    trades = pd.DataFrame({"reason": ["stop"] * 2 + ["run"] * 2, "R": [-1.0, -1.0, 5.0, 3.0]})
    out = P.exit_reason_stats(trades)
    assert out.loc["run", "share_of_total_R"] == pytest.approx(8 / 6)
    assert out.loc["stop", "share_of_total_R"] == pytest.approx(-2 / 6)


def test_cluster_bootstrap_mean_widens_when_trades_of_one_ticker_move_together():
    """Clustering only matters when trades SHARE something. Each ticker gets its own offset here — which
    is the real case: several trades on one name ride the same move."""
    rng = np.random.default_rng(11)
    n_tick, per = 6, 10
    offs = rng.normal(0, 2.0, n_tick)
    ticks = [f"T{i // per}" for i in range(n_tick * per)]
    v = np.array([offs[i // per] + rng.normal(0, 0.2) for i in range(n_tick * per)])
    pt, lo, hi = P.cluster_bootstrap_mean(v, ticks, n_boot=800)
    assert pt == pytest.approx(v.mean())
    assert lo < v.mean() < hi
    _, lo2, hi2 = P.cluster_bootstrap_mean(v, [f"T{i}" for i in range(n_tick * per)], n_boot=800)
    assert (hi - lo) > 2 * (hi2 - lo2), "treating 60 correlated trades as independent must look far tighter"


def test_cluster_bootstrap_mean_reports_no_interval_from_a_single_cluster():
    pt, lo, hi = P.cluster_bootstrap_mean([1.0, 2.0, 3.0], ["A", "A", "A"])
    assert pt == pytest.approx(2.0) and np.isnan(lo) and np.isnan(hi)


def test_two_sample_bootstrap_finds_a_difference_that_overlapping_intervals_hide():
    """Why it exists: comparing two separately-bootstrapped means by eye is not a test. Here each
    population's own 95% interval contains the other's mean, yet the difference excludes zero."""
    # Built, not drawn: the phenomenon only appears in a narrow band (about 2.8 to 3.9 standard errors
    # apart), so a random draw would land in it only sometimes and the test would flap.
    rng = np.random.default_rng(12)
    n = 150
    base = rng.normal(0.0, 1.0, n)
    a = base - base.mean()
    delta = 3.2 * a.std(ddof=1) / np.sqrt(n)
    b = a + delta
    ca, cb = [f"A{i}" for i in range(n)], [f"B{i}" for i in range(n)]
    _, a_lo, a_hi = P.cluster_bootstrap_mean(a, ca, n_boot=800)
    _, b_lo, b_hi = P.cluster_bootstrap_mean(b, cb, n_boot=800)
    assert a_hi > b_lo, "set up so the two intervals OVERLAP — the eyeball test would say 'no difference'"
    pt, lo, hi = P.cluster_bootstrap_two_sample(a, ca, b, cb, n_boot=800)
    assert pt == pytest.approx(b.mean() - a.mean())
    assert lo > 0, "the difference itself is established"


def test_two_sample_bootstrap_reports_no_difference_when_there_is_none():
    rng = np.random.default_rng(13)
    a, b = rng.normal(0, 1, 200), rng.normal(0, 1, 200)
    ca, cb = [f"A{i}" for i in range(200)], [f"B{i}" for i in range(200)]
    _, lo, hi = P.cluster_bootstrap_two_sample(a, ca, b, cb, n_boot=800)
    assert lo < 0 < hi


def test_two_sample_bootstrap_widens_when_one_side_is_a_few_clusters():
    rng = np.random.default_rng(14)
    a = rng.normal(0, 1, 200)
    offs = rng.normal(0, 1.5, 4)
    b = np.array([offs[i // 25] + rng.normal(0, 0.2) for i in range(100)])
    ca = [f"A{i}" for i in range(200)]
    _, lo_c, hi_c = P.cluster_bootstrap_two_sample(a, ca, b, [f"B{i // 25}" for i in range(100)], n_boot=600)
    _, lo_i, hi_i = P.cluster_bootstrap_two_sample(a, ca, b, [f"B{i}" for i in range(100)], n_boot=600)
    assert (hi_c - lo_c) > 2 * (hi_i - lo_i), "4 real clusters must not read as 100 independent trades"


def test_two_sample_bootstrap_handles_an_empty_side():
    pt, lo, hi = P.cluster_bootstrap_two_sample([], [], [1.0, 2.0], ["B1", "B2"])
    assert np.isnan(pt) and np.isnan(lo) and np.isnan(hi)
