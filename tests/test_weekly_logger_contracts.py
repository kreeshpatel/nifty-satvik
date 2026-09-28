"""The watched-book loggers can no longer fail in silence, and a card row can be dated.

B0 of the 2026-09-25 development plan. Three artifacts were in NO output contract at all, so all three
could fail every week while the cron exited 0 — and one of them did exactly that: `run_blend_paper.py`
crashed on every Saturday from inception and `blend_hybrid_paper.json` sat at `n_points: 0` for about
seven weeks. Nothing was broken about the alerting; there was no alert.

The fix has two halves and the second is the one that bites:

  * the contract now lists them as `must_update`, so a path that stops being written goes RED;
  * `check_weekly_loggers.py` proves they advanced to THIS scan's as-of, which is the failure the
    contract alone cannot see — a logger that rewrites the same stale payload every week still "updates"
    the file.

It runs AFTER the commit on purpose, and these tests assert that placement, because the alternative
(making a producer fatal) would abort before the weekly state is committed and trade a silent miss for
a lost week.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import check_weekly_loggers as C  # noqa: E402

WORKFLOW = ROOT / ".github" / "workflows" / "cron-bhanushali-scanner.yml"


def _results(tmp_path: Path, as_of: str, blend: str | None, breadth: str | None,
             rows: int = 1) -> Path:
    r = tmp_path / "results"
    r.mkdir(parents=True, exist_ok=True)
    (r / "signals_today_weekly.json").write_text(
        json.dumps({"generated_at": as_of, "signals": []}), encoding="utf-8")
    if blend is not None:
        (r / "blend_hybrid_paper.json").write_text(
            json.dumps({"asof": blend, "n_points": 59}), encoding="utf-8")
    if breadth is not None:
        (r / "breadth50_forward.json").write_text(
            json.dumps({"asof": breadth, "n_points": 5}), encoding="utf-8")
    # The capital book's two streams, added to the checker on 2026-09-28. A fixture that omits them
    # reports them MISSING and drowns the assertion each test is actually making.
    import gzip
    (r / "brain").mkdir(parents=True, exist_ok=True)
    with gzip.open(r / "brain" / "position_log.csv.gz", "wt", encoding="utf-8", newline="\n") as fh:
        fh.write(f"as_of,tkr\n{as_of},AAA\n")
    (r / "brain" / "management_events.jsonl").write_text(
        json.dumps({"as_of": as_of}) + "\n", encoding="utf-8")
    header = "ticker,signal_date\n"
    body = "".join(f"T{i},2026-09-25\n" for i in range(rows))
    (r / "signal_quality_forward.csv").write_text(header + body, encoding="utf-8")
    return r


def test_all_advanced_is_clean(tmp_path, monkeypatch):
    monkeypatch.setattr(C, "RESULTS", _results(tmp_path, "2026-10-03", "2026-10-03", "2026-10-03"))
    assert C.check() == []


def test_a_logger_stuck_on_last_week_is_caught(tmp_path, monkeypatch):
    """THE failure mode this exists for: the file is present and 'updated', but the week is missing."""
    monkeypatch.setattr(C, "RESULTS", _results(tmp_path, "2026-10-03", "2026-09-26", "2026-10-03"))
    problems = C.check()
    assert len(problems) == 1
    assert "blend_hybrid_paper.json" in problems[0]
    assert "2026-09-26" in problems[0] and "2026-10-03" in problems[0]


def test_a_missing_logger_is_caught(tmp_path, monkeypatch):
    monkeypatch.setattr(C, "RESULTS", _results(tmp_path, "2026-10-03", None, "2026-10-03"))
    assert any("MISSING" in p for p in C.check())


def test_an_empty_quality_table_is_caught(tmp_path, monkeypatch):
    monkeypatch.setattr(C, "RESULTS",
                        _results(tmp_path, "2026-10-03", "2026-10-03", "2026-10-03", rows=0))
    assert any("no rows" in p for p in C.check())


def test_an_unreadable_logger_is_a_failure_not_a_pass(tmp_path, monkeypatch):
    r = _results(tmp_path, "2026-10-03", "2026-10-03", "2026-10-03")
    (r / "blend_hybrid_paper.json").write_text("{not json", encoding="utf-8")
    monkeypatch.setattr(C, "RESULTS", r)
    assert any("unreadable" in p for p in C.check())


def test_a_logger_AHEAD_of_the_scan_is_not_flagged(tmp_path, monkeypatch):
    """Only staleness is a defect. A logger dated later than the scan is odd but not a missed week."""
    monkeypatch.setattr(C, "RESULTS", _results(tmp_path, "2026-10-03", "2026-10-10", "2026-10-03"))
    assert C.check() == []


def test_the_checker_fails_the_job_by_default_and_can_be_softened_locally(tmp_path, monkeypatch):
    monkeypatch.setattr(C, "RESULTS", _results(tmp_path, "2026-10-03", "2026-09-26", "2026-10-03"))
    assert C.main([]) == 1
    assert C.main(["--warn-only"]) == 0


# ------------------------------------------------------------------ the contract and its placement
def test_the_three_artifacts_are_contracted_as_must_update():
    """`must_update_if_produced` only WARNS. These are forward evidence: a missed week is unrecoverable."""
    d = json.loads((ROOT / "results" / "output_contracts.json").read_text(encoding="utf-8"))
    scanner = next(c for c in d["contracts"] if c["job"] == "weekly-scanner")
    for path in ("results/blend_hybrid_paper.json", "results/breadth50_forward.json",
                 "results/signal_quality_forward.csv"):
        assert path in scanner["must_update"], f"{path} can still fail in silence"


def test_the_checker_runs_after_the_commit_step():
    """Placement IS the design. Before the commit, a side-book defect would withhold the live book."""
    text = WORKFLOW.read_text(encoding="utf-8")
    commit_at = text.index("- name: Commit weekly paper state")
    check_at = text.index("- name: Watched-book loggers must have logged this week")
    assert check_at > commit_at, (
        "the logger check must run AFTER the commit — making it earlier would abort the job before the "
        "weekly state is saved, trading a silent miss for a lost week")


def test_the_producer_steps_stay_non_fatal():
    """Deliberate: the producers warn, and the post-commit gate is what goes red."""
    text = WORKFLOW.read_text(encoding="utf-8")
    for producer in ("run_blend_paper.py", "run_breadth50_paper.py"):
        idx = text.index(producer)
        window = text[idx:idx + 400]
        assert "::warning::" in window, f"{producer} became fatal — it runs before the commit"


# ------------------------------------------------------------------ cards_archive as_of
def test_new_card_rows_are_stamped_and_old_ones_are_not_backfilled(tmp_path, monkeypatch):
    import archive_weekly_cards as A
    archive = tmp_path / "cards_archive.jsonl"
    # an existing, undatable row from before the field existed
    archive.write_text(json.dumps({"ticker": "OLD", "signal_date": "2026-08-01"}) + "\n",
                       encoding="utf-8")
    env = tmp_path / "signals_today_weekly.json"
    env.write_text(json.dumps({"generated_at": "2026-10-03",
                               "signals": [{"ticker": "NEW", "signal_date": "2026-10-02"}]}),
                   encoding="utf-8")
    monkeypatch.setattr(A, "ARCHIVE", archive)
    monkeypatch.setattr(A, "ENVELOPE", env)
    assert A.main() == 0

    rows = [json.loads(ln) for ln in archive.read_text(encoding="utf-8").splitlines() if ln.strip()]
    assert len(rows) == 2
    assert "as_of" not in rows[0], "an old row must stay undatable — inventing its date is §3's breach"
    assert rows[1]["as_of"] == "2026-10-03"
