"""The clustered interval the 2026-11-17 audit asked for: trades in one week are not independent observations."""
from __future__ import annotations

import numpy as np
import pytest

from nq.lab.stats import cluster_bootstrap_mean


def test_the_point_mean_is_the_plain_mean():
    r = cluster_bootstrap_mean([1.0, 2.0, 3.0, 4.0], ["w1", "w1", "w2", "w2"], n_boot=200)
    assert r["mean"] == pytest.approx(2.5)
    assert (r["n"], r["n_clusters"]) == (4, 2)


def test_one_cluster_gets_no_interval_because_it_cannot_speak_to_between_week_variation():
    r = cluster_bootstrap_mean([1.0, 2.0, 3.0], ["w1", "w1", "w1"], n_boot=200)
    assert r["ci95"] is None and r["n_clusters"] == 1


def test_clustering_widens_the_interval_when_trades_inside_a_week_move_together():
    """40 weeks x 10 identical trades: the real sample is 40 observations, not 400."""
    rng = np.random.default_rng(7)
    weekly = rng.normal(0, 1, 40)
    v = np.repeat(weekly, 10)
    clustered = cluster_bootstrap_mean(v, np.repeat([f"w{i}" for i in range(40)], 10), n_boot=1000)
    as_if_independent = cluster_bootstrap_mean(v, [f"t{i}" for i in range(400)], n_boot=1000)
    cw = clustered["ci95"][1] - clustered["ci95"][0]
    iw = as_if_independent["ci95"][1] - as_if_independent["ci95"][0]
    assert cw > 2.5 * iw, (cw, iw)


def test_nans_are_dropped_and_an_empty_sample_is_not_an_error():
    r = cluster_bootstrap_mean([1.0, float("nan")], ["w1", "w2"], n_boot=50)
    assert r["n"] == 1 and r["ci95"] is None
    e = cluster_bootstrap_mean([], [], n_boot=50)
    assert e["n"] == 0 and e["ci95"] is None


def test_it_is_deterministic_under_the_pinned_seed():
    a = cluster_bootstrap_mean([1.0, 2.0, 3.0, 9.0], ["a", "a", "b", "c"], n_boot=300)
    b = cluster_bootstrap_mean([1.0, 2.0, 3.0, 9.0], ["a", "a", "b", "c"], n_boot=300)
    assert a["ci95"] == b["ci95"]
