"""Weekly lifecycle report (ADR-0020, Part D): status from a record and a frozen band, never a verdict before week 26."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "pipelines" / "lifecycle"))
import core as C  # noqa: E402
import weekly_status as W  # noqa: E402

BAND = {"strategy": "live_swing", "worst_backtest_drawdown_pct": -40.0, "drawdown_breaker_pct": -50.0,
        "horizons": {str(h): {"cum_return_pct": {"band": {"p5": -10.0, "p25": 0.0, "p50": 8.0, "p75": 15.0, "p95": 30.0}},
                              "drawdown_depth_pct": {"band": {"p5": 1.0, "p25": 3.0, "p50": 6.0, "p75": 10.0, "p95": 20.0}}}
                     for h in C.HORIZONS}}


@pytest.fixture()
def world(tmp_path, monkeypatch):
    for name, sub in (("RECORDS", "records"), ("BANDS", "bands")):
        (tmp_path / sub).mkdir()
        monkeypatch.setattr(W, name, tmp_path / sub)
    monkeypatch.setattr(W, "STAGES", tmp_path / "stages.json")
    monkeypatch.setattr(W, "STATUS_LOG", tmp_path / "status_log.csv")
    (tmp_path / "bands" / "live_swing_bands_2026-01-01.json").write_text(json.dumps(BAND), encoding="utf-8")
    (tmp_path / "stages.json").write_text(json.dumps([{"strategy": "live_swing", "stage": "PAPER", "from": "2026-01-02"}]), encoding="utf-8")
    return tmp_path


def _record(world, navs):
    f = world / "records" / "live_swing.csv"
    import pandas as pd
    for d, v in zip(pd.date_range("2026-01-02", periods=len(navs), freq="W-FRI"), navs):
        C.append_row(f, {"date": str(d.date()), "nav": v})


def test_a_strategy_with_no_record_is_new(world):
    out = W.one("live_swing")
    assert out["status"] == "NEW" and out["weeks"] == 0


def test_red_before_week_26_is_provisional_and_asks_for_no_verdict(world):
    _record(world, [100.0] + [85.0] * 10)                      # -15% after 10 weeks: below the 5th percentile
    out = W.one("live_swing")
    assert out["status"] == "RED" and out["provisional"] is True and out["weeks"] == 10
    assert "no verdict" in out["triggers"][0]


def test_red_after_week_26_opens_a_review(world):
    _record(world, [100.0] + [85.0] * 30)
    out = W.one("live_swing")
    assert out["status"] == "RED" and out["provisional"] is False
    assert out["triggers"][0].startswith("RED: open a review")


def test_the_drawdown_breaker_fires_at_any_age(world):
    _record(world, [100.0, 120.0, 55.0])                       # 54% below the peak; breaker is 50%
    out = W.one("live_swing")
    assert out["status"] == "RED" and "drawdown breaker" in out["triggers"][0]


def test_paper_at_26_weeks_and_green_is_flagged_as_eligible(world):
    _record(world, [100.0 + i for i in range(27)])
    out = W.one("live_swing")
    assert out["status"] == "GREEN" and any("eligible for a PILOT decision" in t for t in out["triggers"])


def test_the_table_fits_one_row_per_strategy(world):
    rows = [W.one(s) for s in W.STRATEGIES]
    assert W.table(rows).count("\n| ") == len(W.STRATEGIES) + 1


# ------------------------------------------------------------------ fills: tracking error only (owner rule, 2026-11-14)
def test_no_model_or_record_code_can_see_the_fills():
    """The scan may read fills for tracking error ONLY. The engine, the scan and the record builder must not mention them."""
    for rel in ("scripts/run_bhanushali_cron.py", "scripts/run_bhanushali_weekly_rank.py", "scripts/run_bhanushali_monitor.py",
                "pipelines/lifecycle/update_records.py", "pipelines/lifecycle/build_bands.py", "nq/engine/rebalance_book.py",
                "nq/engine/portfolio.py"):
        src = (ROOT / rel).read_text(encoding="utf-8")
        for word in ("LIFECYCLE_FILLS_DB_URL", "execution_events", "fills_from_db"):
            assert word not in src, f"{rel} mentions {word}: fills are for tracking error only"


def test_the_published_report_carries_aggregates_only(world, monkeypatch):
    monkeypatch.setattr(W, "fills_from_db", lambda: [{"signal_id": "A__2026-11-02", "side": "BUY", "qty": 7, "price": 123.45}])
    out = W.execution()
    blob = json.dumps(out)
    assert "123.45" not in blob and "A__2026-11-02" not in blob
    assert out["fills_source"] == "app database (read-only)" and out["n_fills_read"] == 1


def test_without_database_access_the_report_says_so(world, monkeypatch):
    monkeypatch.delenv("LIFECYCLE_FILLS_DB_URL", raising=False)
    monkeypatch.setattr(W, "FILLS", world / "missing.json")
    assert "no read access" in W.execution()["note"]
