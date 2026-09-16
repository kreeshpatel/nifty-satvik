"""nq.brain.excursions — the null and the path measurement must be right before any number is read.

The plan's verification line pins two values of the null for a +8% / −4% setup at 32% annual volatility:
34.7% with no log drift, 37.3% at μ = +15%. The path function is pinned on hand-built bars, including the
conservative same-bar convention.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from nq.brain import excursions as X  # noqa: E402


# --------------------------------------------------------------------------- the null
def test_driftless_null_is_b_over_a_plus_b():
    p = X.null_p_target_first(100.0, 96.0, 108.0)
    assert p == pytest.approx(0.3466, abs=5e-4)                      # the plan's 34.7%


def test_drifted_null_matches_the_plan_value():
    p = X.null_p_target_first(100.0, 96.0, 108.0, mu=0.15, sigma=0.32)
    assert p == pytest.approx(0.3726, abs=5e-4)                      # the plan's 37.3%


def test_zero_log_drift_collapses_to_the_driftless_formula():
    sigma = 0.30
    mu = 0.5 * sigma * sigma                                           # nu = 0 exactly
    assert X.null_p_target_first(100, 90, 120, mu=mu, sigma=sigma) == pytest.approx(
        X.null_p_target_first(100, 90, 120), rel=1e-9)


def test_a_2r_target_is_about_one_third_by_chance():
    """In R terms (arithmetic), 2:1 is 1/3; the log-space null is close to it for small risk."""
    p = X.null_p_target_first(100.0, 99.0, X.target_at(100.0, 99.0, 2.0))
    assert p == pytest.approx(1 / 3, abs=0.005)


def test_the_null_is_monotone_in_the_target():
    ps = [X.null_p_target_first(100, 92, X.target_at(100, 92, k)) for k in (0.5, 1, 1.5, 2, 3)]
    assert all(a > b for a, b in zip(ps, ps[1:]))


def test_bad_geometry_is_refused():
    with pytest.raises(ValueError):
        X.null_p_target_first(100, 101, 110)
    with pytest.raises(ValueError):
        X.null_p_target_first(100, 90, 110, mu=0.1)                   # drift without sigma


def test_the_null_agrees_with_simulation():
    """Monte Carlo on fine-stepped GBM, continuous barriers approximated by small steps."""
    rng = np.random.default_rng(7)
    mu, sigma, dt, n_paths, steps = 0.15, 0.32, 1 / 2520, 4000, 25200
    a, b = math.log(1.08), math.log(1 / 0.96)
    nu = mu - 0.5 * sigma ** 2
    x = np.zeros(n_paths)
    done = np.zeros(n_paths, dtype=bool)
    hit = np.zeros(n_paths, dtype=bool)
    for _ in range(steps):
        live = ~done
        if not live.any():
            break
        x[live] += nu * dt + sigma * math.sqrt(dt) * rng.standard_normal(live.sum())
        up, dn = live & (x >= a), live & (x <= -b)
        hit |= up
        done |= up | dn
    sim = hit[done].mean()
    assert sim == pytest.approx(X.null_p_target_first(100, 96, 108, mu=mu, sigma=sigma), abs=0.03)


# --------------------------------------------------------------------------- the path
def test_target_first():
    p = X.first_passage([101, 104, 109, 103], [99, 100, 102, 95], entry=100, stop=96, target=108)
    assert p.outcome == X.HIT and p.sessions == 2


def test_stop_first():
    p = X.first_passage([101, 102, 109], [97, 95, 100], entry=100, stop=96, target=108)
    assert p.outcome == X.STOPPED and p.sessions == 1
    assert p.mfe_r_before_stop == pytest.approx(0.25)                  # best high 101 before the stop bar


def test_a_bar_touching_both_counts_as_the_stop():
    p = X.first_passage([101, 110], [99, 95], entry=100, stop=96, target=108)
    assert p.outcome == X.STOPPED and p.sessions == 1


def test_neither_touched_is_unresolved():
    p = X.first_passage([101, 103], [98, 97], entry=100, stop=96, target=108)
    assert p.outcome == X.UNRESOLVED and p.sessions is None


def test_the_entry_session_itself_can_decide():
    assert X.first_passage([108.5], [99], entry=100, stop=96, target=108).sessions == 0


# --------------------------------------------------------------------------- bands and bootstrap
@pytest.mark.parametrize("r, band", [(0.0, "r<5%"), (0.0499, "r<5%"), (0.05, "5%<=r<10%"),
                                     (0.0999, "5%<=r<10%"), (0.10, "r>=10%"), (0.3, "r>=10%")])
def test_risk_bands(r, band):
    assert X.risk_band(r) == band


def test_cluster_bootstrap_centres_on_the_difference_and_widens_with_clustering():
    obs = [1, 1, 1, 1, 0, 0, 0, 0]
    null = [0.5] * 8
    point, lo, hi = X.cluster_bootstrap_diff(obs, null, ["A", "A", "A", "A", "B", "B", "B", "B"], n_boot=500)
    assert point == pytest.approx(0.0)
    _, lo_ind, hi_ind = X.cluster_bootstrap_diff(obs, null, list("ABCDEFGH"), n_boot=500)
    assert (hi - lo) > (hi_ind - lo_ind), "two perfectly clustered names must give a wider CI than 8 independent"


def test_a_stop_capped_at_exactly_ten_percent_is_banded_by_the_spec_not_by_float_noise():
    for entry in (297.5, 1374.89, 653.0, 3173.5):
        stop = entry * 0.90
        assert X.risk_band((entry - stop) / entry) == "r>=10%"


# --------------------------------------------------------------------------- the live stop rule (A2.2)
def _path(highs, lows, closes, week_end):
    return (np.array(highs, float), np.array(lows, float), np.array(closes, float), np.array(week_end, bool))


def test_an_intraweek_dip_below_the_stop_does_not_stop_the_live_rule():
    h, lo, c, we = _path([101, 102, 109], [95, 99, 100], [99, 100, 105], [False, True, False])
    assert X.passage_outcomes(h, lo, c, we, entry=100, stop=96, ks=[2.0], weekly_stop=False) == [X.STOPPED]
    assert X.passage_outcomes(h, lo, c, we, entry=100, stop=96, ks=[2.0], weekly_stop=True) == [X.HIT]


def test_a_weekly_close_below_the_stop_stops_the_live_rule():
    h, lo, c, we = _path([102.5, 99, 109], [97, 94, 100], [99, 95, 105], [False, True, False])   # +0.5R = 102 hit first
    assert X.passage_outcomes(h, lo, c, we, entry=100, stop=96, ks=[0.5, 2.0], weekly_stop=True) == [X.HIT, X.STOPPED]


def test_passage_outcomes_matches_first_passage_on_the_continuous_rule():
    rng = np.random.default_rng(3)
    for _ in range(200):
        c = 100 * np.cumprod(1 + rng.normal(0, 0.02, 60))
        h, lo = c * 1.01, c * 0.99
        we = np.arange(60) % 5 == 4
        got = X.passage_outcomes(h, lo, c, we, entry=100, stop=95, ks=[1.0, 2.0], weekly_stop=False)
        want = [X.first_passage(h, lo, entry=100, stop=95, target=X.target_at(100, 95, k)).outcome for k in (1.0, 2.0)]
        assert got == want
