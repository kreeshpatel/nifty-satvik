"""The prediction-ledger producer: honest stamps, idempotent appends, path-based resolution."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import run_prediction_producer as R  # noqa: E402
from nq.brain import predictions as P  # noqa: E402

ENV = {"generated_at": "2026-10-16", "signals": [
    {"ticker": "AAA", "signal_date": "2026-10-16", "status": "FRESH", "entry": 100.0, "stop": 90.0, "target": 120.0},
    {"ticker": "OLD", "signal_date": "2026-10-09", "status": "ACTIVE", "entry": 100.0, "stop": 90.0, "target": 120.0},
    {"ticker": "BAD", "signal_date": "2026-10-16", "status": "FRESH", "entry": 100.0, "stop": 110.0, "target": 120.0},
]}


def _path(rows):
    idx = pd.bdate_range("2026-10-15", periods=len(rows))
    return pd.DataFrame({"High": [h for h, _ in rows], "Low": [lo for _, lo in rows]}, index=idx)


def test_only_fresh_well_formed_cards_are_forecast_at_the_null():
    f = R.forecasts_for(ENV)
    assert [x["subject"] for x in f] == ["AAA:2026-10-16"]
    import math
    assert f[0]["probability"] == pytest.approx(math.log(100 / 90) / (math.log(120 / 100) + math.log(100 / 90)))
    assert f[0]["stamped_at"] < f[0]["resolve_by"]


@pytest.fixture()
def wired(tmp_path, monkeypatch):
    cards = tmp_path / "signals_today_weekly.json"
    cards.write_text(json.dumps(ENV), encoding="utf-8")
    monkeypatch.setattr(R, "CARDS", cards)
    return tmp_path / "ledger.jsonl"


def test_a_rerun_appends_nothing(wired):
    R.main(["--ledger", str(wired), "--today", "2026-10-17", "--no-resolve"])
    R.main(["--ledger", str(wired), "--today", "2026-10-17", "--no-resolve"])
    rows = P.read_verified(wired)
    assert len(rows) == 1 and rows[0]["basis"] == "first_passage_null"


def test_a_stale_envelope_is_refused_not_backdated(wired):
    R.main(["--ledger", str(wired), "--today", "2026-10-28", "--no-resolve"])
    assert not wired.exists() or P.read_verified(wired) == []


def test_resolution_reads_the_path_after_the_signal_and_counts_a_both_bar_as_stop():
    pred = {"subject": "AAA:2026-10-16"}
    lv = {"AAA:2026-10-16": {"entry": 100.0, "stop": 90.0, "target": 120.0}}
    # the signal-day bar (10-16) touches the target but must be ignored: the path starts after it
    hit = _path([(100, 99), (121, 99), (101, 95), (125, 100)])
    assert R.resolve_one(pred, {"AAA": hit}, lv) == (True, "2026-10-20")
    both = _path([(100, 99), (100, 99), (121, 89)])
    assert R.resolve_one(pred, {"AAA": both}, lv) == (False, "2026-10-19")
    undecided = _path([(100, 99), (110, 95)])
    assert R.resolve_one(pred, {"AAA": undecided}, lv) is None


def test_the_cron_runs_the_producer_before_the_commit_and_commits_the_ledger():
    wf = (ROOT / ".github" / "workflows" / "cron-bhanushali-scanner.yml").read_text(encoding="utf-8")
    assert wf.index("run_prediction_producer.py") < wf.index("- name: Commit weekly paper state")
    assert "results/brain/prediction_ledger.jsonl" in wf
