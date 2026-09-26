"""Track P2's estimators, checked against what they are supposed to be — not against themselves.

A shrinkage intensity or a noise share is a number nobody can eyeball, so each test here pins the
function to a property that would fail if the formula were wrong: known Marchenko-Pastur edges, a
planted factor that must stick out of the bulk, and — the one that matters — a simulation in which
the shrunk covariance has to beat the sample covariance at recovering a covariance we chose.
"""

from __future__ import annotations

import numpy as np
import pytest

from nq.brain import estimation as E


# ------------------------------------------------------------------------------ Marchenko-Pastur
def test_the_bulk_edges_are_the_textbook_ones():
    lo, hi = E.marchenko_pastur_edges(1.0)
    assert lo == pytest.approx(0.0)
    assert hi == pytest.approx(4.0)
    lo, hi = E.marchenko_pastur_edges(0.25)
    assert lo == pytest.approx(0.25)     # (1 - 0.5)^2
    assert hi == pytest.approx(2.25)     # (1 + 0.5)^2


def test_pure_noise_sits_inside_the_bulk_and_a_planted_factor_does_not():
    rng = np.random.default_rng(0)
    t, n = 63, 5
    noise = rng.standard_normal((t, n))
    noise_corr = np.corrcoef(noise, rowvar=False)
    assert E.mp_noise_share(noise_corr, n / t) >= 0.8

    # one common factor in every name: the top eigenvalue must escape the noise band
    factor = rng.standard_normal((t, 1))
    loaded = 0.9 * factor + 0.4 * rng.standard_normal((t, n))
    loaded_corr = np.corrcoef(loaded, rowvar=False)
    assert E.mp_noise_share(loaded_corr, n / t) < E.mp_noise_share(noise_corr, n / t)


def test_the_shape_ratio_must_be_positive():
    with pytest.raises(ValueError):
        E.marchenko_pastur_edges(0.0)


# ------------------------------------------------------------------------------ Ledoit-Wolf
def _draw(rng, cov, t):
    return rng.multivariate_normal(np.zeros(len(cov)), cov, size=t)


def test_shrinkage_beats_the_sample_covariance_at_recovering_a_known_one():
    """The whole point of shrinkage, stated as the test: on an 8-name, 63-session sample — this book's
    actual shape — the shrunk estimate must be closer to the truth than the sample matrix.

    THE TRUTH HERE IS DELIBERATELY *OUTSIDE* THE TARGET FAMILY. An earlier version of this test used a
    constant off-diagonal correlation, which IS the constant-correlation target: shrinking toward the
    exact true model cannot lose, so the test passed for free and would have passed just as well with
    delta* hard-wired to 1.0. A three-factor heterogeneous correlation makes the target wrong, so
    beating the sample matrix is a real claim about the estimator (red-team read, 2026-09-25).
    """
    rng = np.random.default_rng(7)
    n, t, draws = 8, 63, 60
    loadings = np.array([[0.9, 0.1, 0.0], [0.8, 0.2, 0.1], [0.7, -0.3, 0.2], [0.2, 0.8, 0.0],
                         [0.1, 0.7, 0.3], [0.0, 0.1, 0.9], [-0.2, 0.0, 0.8], [0.3, -0.4, 0.5]])
    base = loadings @ loadings.T
    base += np.diag(1.0 - np.diag(base))            # unit diagonal: a correlation matrix
    sd = np.linspace(0.01, 0.035, n)
    truth = base * np.outer(sd, sd)
    off = ~np.eye(n, dtype=bool)
    assert np.std(base[off]) > 0.2, "the truth must NOT be a constant-correlation matrix"

    sample_err, shrunk_err = [], []
    for _ in range(draws):
        x = _draw(rng, truth, t)
        xc = x - x.mean(axis=0)
        s = (xc.T @ xc) / t
        delta, shrunk = E.ledoit_wolf_shrinkage(x)
        assert 0.0 <= delta <= 1.0
        sample_err.append(np.linalg.norm(s - truth))
        shrunk_err.append(np.linalg.norm(shrunk - truth))
    assert np.mean(shrunk_err) < np.mean(sample_err)


def test_the_shrunk_matrix_stays_a_covariance_matrix():
    rng = np.random.default_rng(3)
    x = rng.standard_normal((63, 5)) * 0.02
    _, shrunk = E.ledoit_wolf_shrinkage(x)
    assert np.allclose(shrunk, shrunk.T)
    assert np.linalg.eigvalsh(shrunk).min() > -1e-12


def test_more_data_needs_less_shrinkage_when_there_is_structure_to_find():
    """δ* falls with T — but ONLY against a truth the constant-correlation target gets wrong.

    The earlier version of this test used a constant-correlation truth and compared 0.996 against
    0.973, with 27 of 30 short draws and 24 of 30 long draws hard-CLIPPED at 1.0. It was testing the
    clip, not the estimator. Against heterogeneous structure the fall is unambiguous.
    """
    rng = np.random.default_rng(11)
    loadings = np.array([[0.9, 0.0], [0.8, 0.2], [0.1, 0.9], [0.0, 0.8], [0.4, -0.5]])
    base = loadings @ loadings.T
    base += np.diag(1.0 - np.diag(base))
    truth = base * 0.02 ** 2
    short = np.median([E.ledoit_wolf_shrinkage(_draw(rng, truth, 63))[0] for _ in range(30)])
    long = np.median([E.ledoit_wolf_shrinkage(_draw(rng, truth, 2000))[0] for _ in range(30)])
    assert short > long
    assert long < 0.5, f"with 2000 observations the sample matrix should carry the day, got {long}"


def test_shrinkage_intensity_is_not_a_noise_statistic():
    """The misreading this file exists to prevent, pinned as an assertion.

    δ* = (π − ρ)/(γT), and γ is the squared distance from the sample matrix to the CONSTANT-CORRELATION
    target. On pure noise every pairwise correlation is the same in expectation, so the target is
    nearly perfect and δ* → 1 **at any sample size** — including T = 2000, where estimation error is
    negligible. Track P2 originally read "δ* = 0.98" as "98% of the covariance is noise". It is not
    that. It says a single average correlation is nearly a sufficient summary.
    """
    rng = np.random.default_rng(20260925)
    for t_obs in (63, 252, 2000):
        d = np.median([E.ledoit_wolf_shrinkage(rng.standard_normal((t_obs, 8)))[0] for _ in range(20)])
        assert d > 0.9, (
            f"iid noise at T={t_obs} gave delta*={d:.3f}; if this ever falls, the interpretation in "
            f"research/findings/0145 must be revisited")


def test_a_degenerate_sample_is_refused_rather_than_guessed():
    with pytest.raises(ValueError):
        E.ledoit_wolf_shrinkage(np.zeros((1, 5)))


# ------------------------------------------------------------------------------ weighting schemes
def test_every_scheme_is_long_only_fully_invested_and_capped():
    rng = np.random.default_rng(5)
    x = rng.standard_normal((63, 6)) * 0.02
    cov = np.cov(x, rowvar=False)
    mu = x.mean(axis=0)
    cap = 0.30
    for w in (E.equal_weights(6),
              E.inverse_vol_weights(np.sqrt(np.diag(cov)), cap),
              E.min_variance_weights(cov, cap),
              E.max_sharpe_weights(mu, cov, cap),
              E.max_return_weights(mu, cap)):
        assert w.sum() == pytest.approx(1.0)
        assert (w >= -1e-12).all()
        assert w.max() <= cap + 1e-9


def test_minimum_variance_leans_on_the_quietest_name():
    cov = np.diag([0.04, 0.01, 0.0025])          # sd 20% / 10% / 5%
    w = E.min_variance_weights(cov)
    assert w[2] > w[1] > w[0]
    # uncorrelated and diagonal: the analytic optimum is proportional to 1/variance
    expected = (1 / np.diag(cov)) / (1 / np.diag(cov)).sum()
    assert w == pytest.approx(expected, abs=1e-3)


def test_max_sharpe_concentrates_when_one_name_dominates():
    mu = np.array([0.10, 0.0, 0.0])
    cov = np.eye(3) * 0.01
    w = E.max_sharpe_weights(mu, cov)
    assert w[0] > 0.95


def test_max_sharpe_is_defined_when_every_expectation_is_negative():
    """A long-only book that cannot step aside still has a least-bad mix. Stepping aside is a
    different axis (exposure, 0095) and must not leak into a weighting answer."""
    mu = np.array([-0.01, -0.05, -0.02])
    cov = np.diag([0.01, 0.01, 0.01])
    w = E.max_sharpe_weights(mu, cov)
    assert w.sum() == pytest.approx(1.0)
    assert w[0] > w[1]                        # least-bad gets the most


def test_inverse_vol_is_inverse_vol():
    w = E.inverse_vol_weights(np.array([0.01, 0.02, 0.04]))
    assert w == pytest.approx(np.array([4, 2, 1]) / 7, abs=1e-9)


def test_the_cap_waterfills_rather_than_truncating():
    """Truncating and renormalising re-breaches the cap; the excess has to go to the uncapped names."""
    w = E._apply_cap(np.array([0.7, 0.2, 0.1]), 0.4)
    assert w.sum() == pytest.approx(1.0)
    assert w.max() <= 0.4 + 1e-9
    assert w[1] > w[2]                        # relative order among the uncapped is preserved


def test_a_cap_below_the_equal_weight_is_met_not_silently_breached():
    w = E.max_return_weights(np.array([3.0, 2.0, 1.0]), cap=0.2)
    assert w.sum() == pytest.approx(1.0)
    assert w.max() <= 1 / 3 + 1e-9            # 0.2 is infeasible for n=3; 1/n is the binding cap


def test_max_return_is_the_ceiling_it_claims_to_be():
    mu = np.array([0.05, -0.01, 0.02])
    w = E.max_return_weights(mu, cap=0.5)
    assert w[0] == pytest.approx(0.5)
    assert w[2] == pytest.approx(0.5)         # the cap forces the second-best in, not the worst
    assert w[1] == pytest.approx(0.0)
    # no feasible capped weighting can beat it
    rng = np.random.default_rng(2)
    for _ in range(200):
        other = E._apply_cap(rng.random(3), 0.5)
        assert other @ mu <= w @ mu + 1e-9


# ------------------------------------------------------------------------------ reading the result
def test_sharpe_matches_the_hand_computation():
    r = np.array([0.001, -0.002, 0.003, 0.0005, 0.0015])
    expected = r.mean() / r.std(ddof=1) * np.sqrt(252)
    assert E.sharpe(r) == pytest.approx(expected)


def test_sharpe_refuses_a_sample_it_cannot_describe():
    assert np.isnan(E.sharpe(np.array([0.01])))
    assert np.isnan(E.sharpe(np.array([0.01, 0.01, 0.01])))     # zero dispersion


def test_the_resolution_floor_is_the_programmes_and_is_sign_blind():
    assert E.DSHARPE_HALF_WIDTH == 0.59
    assert not E.resolvable(0.30)
    assert not E.resolvable(-0.58)
    assert E.resolvable(-0.60)
    assert E.resolvable(0.59)
