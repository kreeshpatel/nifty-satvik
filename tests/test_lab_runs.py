"""Strategy Lab run plumbing — cache key, multiplicity ledger, the CUT assertion, DSR wiring.

The real engine is NOT run here (minutes, and it needs the pinned price caches); `replay()` is smoke-run by
hand. Nothing in this file imports streamlit.
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd
import pytest

from nq.lab import runs as L


def _frame(start: str, n: int) -> pd.DataFrame:
    idx = pd.bdate_range(start, periods=n)
    return pd.DataFrame({"Open": 1.0, "High": 1.0, "Low": 1.0, "Close": 1.0, "Volume": 1.0}, index=idx)


def test_config_hash_is_deterministic_and_order_free():
    a = L.config_hash({"ext_cap": 0.2, "exit": "live"})
    b = L.config_hash({"exit": "live", "ext_cap": 0.20})
    assert a == b and len(a) == 64
    assert L.config_hash() == L.config_hash(L.DEFAULT_CONFIG)          # default == live


def test_config_hash_separates_different_configs():
    assert L.config_hash({"ext_cap": None}) != L.config_hash({"ext_cap": 0.2})
    assert L.config_hash({"exit": "base"}) != L.config_hash({"exit": "live"})
    assert L.config_hash({"uncapped": True}) != L.config_hash()


def test_config_validation():
    with pytest.raises(ValueError):
        L.normalize_config({"bogus": 1})
    with pytest.raises(ValueError):
        L.normalize_config({"exit": "wild"})
    with pytest.raises(ValueError):
        L.normalize_config({"start": "2018-06-01"})        # reported stats start no earlier than 2019
    with pytest.raises(ValueError):
        L.normalize_config({"start": "2024-07-01"})


def test_ledger_counts_distinct_configs_only(tmp_path):
    p = tmp_path / "lab_runs.jsonl"
    assert L.n_configs_tried(p) == 0
    assert L.record_run({"ext_cap": 0.2}, 1.1, p) is True
    assert L.record_run({"ext_cap": 0.20, "exit": "live"}, 1.2, p) is False   # same canonical config
    assert L.record_run({"ext_cap": None}, 0.9, p) is True
    assert L.record_run({"ext_cap": None}, 0.9, p) is False
    assert L.n_configs_tried(p) == 2
    rows = [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines()]
    assert len(rows) == 2
    assert set(rows[0]) == {"config_hash", "config", "ran_at", "sharpe"}
    assert rows[0]["config_hash"] == L.config_hash({"ext_cap": 0.2})


def test_nan_sharpe_is_recorded_as_null(tmp_path):
    p = tmp_path / "r.jsonl"
    L.record_run({}, float("nan"), p)
    assert json.loads(p.read_text(encoding="utf-8"))["sharpe"] is None


def test_cut_assertion_rejects_a_series_past_the_cut():
    ok = {"A": _frame("2024-05-01", 20)}                      # ends 2024-05-28
    assert L.assert_within_cut(ok) <= pd.Timestamp(L.CUT)
    bad = {"A": _frame("2024-06-17", 20)}                     # runs into July
    with pytest.raises(L.CutViolation):
        L.assert_within_cut(bad)
    assert issubclass(L.CutViolation, AssertionError)


def test_cut_universe_truncates_then_passes():
    u = {"A": _frame("2024-05-01", 120), "STUB": _frame("2024-06-01", 5)}
    out = L.cut_universe(u, min_bars=10)
    assert "STUB" not in out                                  # too short after the cut
    assert out["A"].index.max() <= pd.Timestamp(L.CUT)


def test_deflation_gets_harsher_with_more_trials():
    n_ret = 1400
    d1 = L.deflated_sharpe(1.2, n_ret, 1)
    d50 = L.deflated_sharpe(1.2, n_ret, 50)
    assert d1["sr0_annual"] == 0.0
    assert d50["sr0_annual"] > d1["sr0_annual"]
    assert d50["deflated_sharpe"] < d1["deflated_sharpe"] == pytest.approx(1.2)
    assert d50["dsr"] < d1["dsr"]
    assert d1["n_obs"] == n_ret // 63
    assert np.isnan(L.deflated_sharpe(1.2, 50, 3)["dsr"])     # too few windows to say anything


def test_deflated_sharpe_is_the_repo_dsr():
    from nq.validation.dsr import deflated_sharpe_ratio
    n_obs = 1400 // 63
    expect = deflated_sharpe_ratio(1.0 / np.sqrt(4), n_obs, n_trials=7, sharpe_variance=1.0 / n_obs)
    assert L.deflated_sharpe(1.0, 1400, 7)["dsr"] == pytest.approx(expect)


def test_replay_returns_cached_result_without_engine(tmp_path):
    cfg = L.normalize_config({"ext_cap": 0.15})
    res = {"config": cfg, "config_hash": L.config_hash(cfg), "sharpe": 0.8, "nav": pd.Series(dtype=float),
           "ledger": pd.DataFrame(), "position_log": pd.DataFrame(), "event_log": pd.DataFrame(),
           "maxdd": -0.1, "cagr": 0.1, "n_trades": 0, "last_bar": "2024-06-28", "seconds": 1.0, "cached": False}
    pd.to_pickle(res, tmp_path / f"{res['config_hash']}.pkl")
    runs_path = tmp_path / "runs.jsonl"
    got = L.replay(cfg, cache_dir=tmp_path, runs_path=runs_path)
    assert got["cached"] is True and got["sharpe"] == 0.8
    L.replay(cfg, cache_dir=tmp_path, runs_path=runs_path)                    # second hit: still one row
    assert L.n_configs_tried(runs_path) == 1
