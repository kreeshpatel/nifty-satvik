"""The watched swing x low-vol blend (0107, prereg_swing §7) must actually accrue.

`run_backtest` returns its equity curve as a list of {"date", "equity"} records. The logger passed that to
`pd.Series(..., dtype=float)`, which raises; the scanner step is non-fatal, so the blend logged zero points
every week from its 2026-07-04 inception and the only symptom was a warning line in the Actions log.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import run_blend_paper as B  # noqa: E402

DATES = pd.bdate_range("2026-07-06", periods=6)


@pytest.fixture
def run(tmp_path, monkeypatch):
    swing = pd.DataFrame({"date": DATES, "total_value": [1_000_000, 1_010_000, 1_000_000, 1_020_000,
                                                         1_030_000, 1_030_000]})
    swing.to_csv(tmp_path / "portfolio_history_weekly.csv", index=False)
    records = [{"date": str(d.date()), "equity": v}
               for d, v in zip(DATES, [500.0, 505.0, 510.0, 505.0, 515.0, 520.0])]
    monkeypatch.setattr(B, "RESULTS_DIR", tmp_path)
    monkeypatch.setattr(B, "OUT", tmp_path / "blend_hybrid_paper.json")
    monkeypatch.setattr(B, "_lowvol_nav", lambda _start: records)       # the REAL return shape
    monkeypatch.setattr(sys, "argv", ["run_blend_paper.py"])

    def _go():
        assert B.main() == 0
        return json.loads((tmp_path / "blend_hybrid_paper.json").read_text(encoding="utf-8"))
    return _go


def test_the_list_of_records_curve_no_longer_crashes_and_accrues(run):
    state = run()
    assert state["n_points"] == len(DATES)
    assert state["asof"] == str(DATES[-1].date())


def test_the_blend_is_the_owner_weighted_mix_of_the_two_legs(run):
    state = run()
    sw = pd.Series([1_000_000, 1_010_000, 1_000_000, 1_020_000, 1_030_000, 1_030_000], dtype=float).pct_change()
    lv = pd.Series([500.0, 505.0, 510.0, 505.0, 515.0, 520.0]).pct_change()
    want = 1_000_000.0 * (1 + (0.60 * sw + 0.40 * lv).fillna(0.0)).prod()
    assert state["blend_nav"] == pytest.approx(want, abs=0.01)
    assert state["swing_weight"] == 0.6


def test_the_series_shape_is_still_accepted():
    s = B._curve_to_series(pd.Series([1.0, 2.0], index=["2026-07-06", "2026-07-07"]))
    assert isinstance(s.index, pd.DatetimeIndex) and s.dtype == float
    assert B._curve_to_series([]).empty
