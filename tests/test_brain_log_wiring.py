"""The engine's two observation hooks must actually be USED, and their output persisted.

`position_log` (881a5ec) and `event_log` (c361272) were both merged and then passed by NOTHING. The
hooks existed, the weekly scan never used them, and every Saturday that passed was a week of holdings
and management history permanently lost — capability with no data, which is the most expensive kind of
half-finished work because it looks done.

These tests pin the wiring itself, not just the writer:

  * the cron passes BOTH logs to the CAPITAL book's backtest (0146: the book that would hold positions);
  * the engine actually fills them on the hermetic fixture, so the assertion is not vacuous;
  * `_write_brain_logs` persists both, stamped with the scan's as-of;
  * an EMPTY week is written, not skipped — "no management event this week" is a fact, and a missing
    file is not the way to say it.
"""

from __future__ import annotations

import gzip
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import run_bhanushali_cron as C  # noqa: E402

LIVE_SCALED = dict(scaled_exit=dict(tp1_r=2.0, tp1_frac=0.40, tp2_r=3.0, tp2_frac=0.0,
                                   pattern_frac=0.40, pattern_arm_r=2.5, runner_sma_buffer=0.0))


def test_the_cron_passes_both_logs_to_the_capital_book():
    """Source-level, because the failure mode was 'the hook exists and nobody calls it'."""
    src = (ROOT / "scripts" / "run_bhanushali_cron.py").read_text(encoding="utf-8")
    assert "position_log=plog" in src and "event_log=elog" in src, "the hooks are still unused"
    # and they go to out_paper, the capital book — not the uncapped tracker
    head = src[src.index("out_paper = R94.backtest"):src.index("out_paper = R94.backtest") + 600]
    assert "position_log=plog" in head and "event_log=elog" in head


@pytest.fixture(scope="module")
def engine_logs():
    """Run the engine on the hermetic fixture with both logs attached."""
    import run_bhanushali_weekly_rank as R94
    from build_r94_golden_fixture import synth_universe
    ohlcv, _ = synth_universe()
    prep = R94.prep_weekly_rank(ohlcv)
    plog: list = []
    elog: list = []
    R94.backtest(prep, None, ledger=[], ext_cap=0.20, max_risk_pct=0.10, max_notional_pct=0.20,
                 position_log=plog, event_log=elog, **LIVE_SCALED)
    return plog, elog


def test_the_engine_actually_fills_both_logs(engine_logs):
    plog, elog = engine_logs
    assert plog, "no position-day rows — the assertion below would be vacuous"
    assert elog, "no management events — the fixture exercised no tranche, ratchet or trail"


def test_both_files_are_written_and_stamped(tmp_path, engine_logs):
    plog, elog = engine_logs
    C._write_brain_logs(plog, elog, "2026-10-03", tmp_path)
    with gzip.open(tmp_path / "brain" / "position_log.csv.gz", "rt", encoding="utf-8") as fh:
        head = fh.readline().strip().split(",")
    assert head[0] == "as_of" and "shares" in head and "notional" in head
    rows = [json.loads(ln) for ln in
            (tmp_path / "brain" / "management_events.jsonl").read_text(encoding="utf-8").splitlines()]
    assert rows and all(r["as_of"] == "2026-10-03" for r in rows)
    assert {"event_type", "trade_id", "event_date"} <= set(rows[0])


def test_an_empty_week_is_written_not_skipped(tmp_path):
    """A week with no management event is a real week. A missing file is not how to say so."""
    C._write_brain_logs([], [], "2026-10-03", tmp_path)
    assert (tmp_path / "brain" / "management_events.jsonl").exists()
    pos = tmp_path / "brain" / "position_log.csv.gz"
    assert pos.exists()
    with gzip.open(pos, "rt", encoding="utf-8") as fh:
        assert "shares" in fh.readline(), "the header must survive an empty week"


def test_the_rebuild_is_deterministic(tmp_path, engine_logs):
    """Rebuilt from inception every run, so two writes of the same input must be byte-identical."""
    plog, elog = engine_logs
    a, b = tmp_path / "a", tmp_path / "b"
    C._write_brain_logs(plog, elog, "2026-10-03", a)
    C._write_brain_logs(plog, elog, "2026-10-03", b)
    assert (a / "brain" / "management_events.jsonl").read_bytes() == \
           (b / "brain" / "management_events.jsonl").read_bytes()


# ------------------------------------------------------------------ the freshness gate
def _stub(tmp_path, as_of, stream_as_of):
    import check_weekly_loggers as K
    r = tmp_path / "results"
    (r / "brain").mkdir(parents=True, exist_ok=True)
    (r / "signals_today_weekly.json").write_text(json.dumps({"generated_at": as_of}), encoding="utf-8")
    for n in ("blend_hybrid_paper.json", "breadth50_forward.json"):
        (r / n).write_text(json.dumps({"asof": as_of, "n_points": 1}), encoding="utf-8")
    (r / "signal_quality_forward.csv").write_text("ticker\nAAA\n", encoding="utf-8")
    with gzip.open(r / "brain" / "position_log.csv.gz", "wt", encoding="utf-8", newline="\n") as fh:
        fh.write("as_of,tkr\n" + (f"{stream_as_of},AAA\n" if stream_as_of else ""))
    (r / "brain" / "management_events.jsonl").write_text(
        (json.dumps({"as_of": stream_as_of}) + "\n") if stream_as_of else "", encoding="utf-8")
    return K, r


def test_a_stale_stream_is_caught(tmp_path, monkeypatch):
    K, r = _stub(tmp_path, "2026-10-10", "2026-10-03")
    monkeypatch.setattr(K, "RESULTS", r)
    problems = K.check()
    assert any("position_log" in p for p in problems)
    assert any("management_events" in p for p in problems)


def test_a_fresh_stream_is_clean(tmp_path, monkeypatch):
    K, r = _stub(tmp_path, "2026-10-10", "2026-10-10")
    monkeypatch.setattr(K, "RESULTS", r)
    assert K.check() == []


def test_an_empty_event_stream_is_not_a_failure(tmp_path, monkeypatch):
    """Empty is legitimate — a week can genuinely contain no tranche, ratchet or halt."""
    K, r = _stub(tmp_path, "2026-10-10", None)
    monkeypatch.setattr(K, "RESULTS", r)
    assert K.check() == []


def test_a_missing_stream_is_a_failure(tmp_path, monkeypatch):
    K, r = _stub(tmp_path, "2026-10-10", "2026-10-10")
    (r / "brain" / "management_events.jsonl").unlink()
    monkeypatch.setattr(K, "RESULTS", r)
    assert any("MISSING" in p for p in K.check())
