"""S-F1 — the forward wall has a scheduled producer, and its first run cannot fake forward evidence.

Two separate properties, both of which failed before 2026-08-06:

1. **It runs at all.** `forward/prereg.md` calls the 3-book wall "the only certifier" and specifies a
   DAILY log. `run_paper_cron.py` -> `wall_cron.update_wall` was invoked by no workflow, so it ran
   never and `results/forward_wall.csv` did not exist.
2. **Its first run does not backfill.** The paper book steps from its own inception, so a cold start
   already holds months of sessions. Logging those would enter recomputed history as `ok` rows that
   pass the hash chain and misstate when they were known. The chain cannot catch this — the dates
   strictly increase — so it has to be caught here.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

yaml = pytest.importorskip("yaml")

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

WF = ROOT / ".github" / "workflows" / "cron-forward-wall.yml"
CRON_SRC = (ROOT / "scripts" / "run_paper_cron.py").read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def wf() -> dict:
    # PyYAML parses the bare key `on:` as the boolean True (YAML 1.1). Accept either.
    d = yaml.safe_load(WF.read_text(encoding="utf-8"))
    d["on"] = d.get("on", d.get(True))
    return d


class TestTheWallIsScheduled:
    def test_the_workflow_exists(self):
        assert WF.exists(), "S-F1: the forward wall must have a scheduled producer"

    def test_it_has_a_schedule_not_only_manual_dispatch(self, wf):
        assert wf["on"].get("schedule"), "a dispatch-only workflow still runs never"

    def test_it_runs_on_weekdays(self, wf):
        """NSE trades Mon-Fri; a weekend run would only ever append nothing."""
        crons = [c["cron"] for c in wf["on"]["schedule"]]
        assert any(c.strip().endswith("1-5") for c in crons), crons

    def test_it_runs_after_the_nse_close(self, wf):
        """15:30 IST close = 10:00 UTC. Logging before that logs an unfinished session."""
        for c in (x["cron"] for x in wf["on"]["schedule"]):
            hour = int(c.split()[1])
            assert hour >= 10, f"{c} fires at {hour}:00 UTC, before the 10:00 UTC NSE close"

    def test_it_invokes_the_producer_that_reaches_update_wall(self, wf):
        steps = " ".join(str(s.get("run", "")) for s in wf["jobs"]["wall"]["steps"])
        assert "scripts/run_paper_cron.py" in steps
        assert "update_wall" in (ROOT / "scripts" / "run_paper_cron.py").read_text(encoding="utf-8")

    def test_it_can_write_back(self, wf):
        assert wf["permissions"]["contents"] == "write"

    def test_it_does_not_touch_the_live_swing_book(self, wf):
        """The wall is the momentum sleeve's paper log. It must never write swing artifacts."""
        steps = " ".join(str(s.get("run", "")) for s in wf["jobs"]["wall"]["steps"])
        for forbidden in ("run_bhanushali_cron", "_weekly", "run_zoo_shadow_book", "judge"):
            assert forbidden not in steps, f"the wall cron must not touch {forbidden}"


class TestItCannotPublishAnEmptyGreenRun:
    def test_the_wall_log_is_a_contracted_artifact(self, wf):
        steps = " ".join(str(s.get("run", "")) for s in wf["jobs"]["wall"]["steps"])
        assert "need results/forward_wall.csv" in steps
        assert "need results/forward_wall_start.json" in steps

    def test_there_is_no_silenced_git_add(self, wf):
        """`git add` on an ignored-and-untracked path exits 0 and stages nothing. The `|| true`
        form hid five instances of that defect across this repo's crons."""
        steps = " ".join(str(s.get("run", "")) for s in wf["jobs"]["wall"]["steps"])
        assert "2>/dev/null || true" not in steps

    def test_a_missing_artifact_fails_the_run(self, wf):
        steps = " ".join(str(s.get("run", "")) for s in wf["jobs"]["wall"]["steps"])
        assert 'if [ "$MISSING" = "1" ]' in steps and "exit 1" in steps


class TestTheFirstRunCannotFakeForwardEvidence:
    def test_update_wall_accepts_a_registered_start(self):
        import inspect

        from nq.paper.wall_cron import update_wall
        assert "wall_start" in inspect.signature(update_wall).parameters

    def test_the_cron_actually_passes_one(self):
        """A bound nobody supplies is not a bound."""
        assert "wall_start=ws" in CRON_SRC, (
            "run_paper_cron must pass wall_start; otherwise a cold start backfills the wall")

    def test_the_anchor_lives_under_the_state_dir_not_the_repo_root(self):
        """A root-anchored path let `tests/test_stagee_paper_cron.py` — which runs the cron against a
        2016 fixture — write a real anchor of `2016-12-30` into the repo. Committed, every live
        session would have been after it, so nothing would ever be skipped and the bound would have
        been silently inert. A guard a test can write is not a guard."""
        assert 'Path(state_dir) / "forward_wall_start.json"' in CRON_SRC
        assert "_wall_start(args.state_dir" in CRON_SRC

    def test_the_anchor_refuses_a_date_before_its_own_preregistration(self, tmp_path):
        """Defence in depth for the same failure: even at the right path, a stale cache or fixture
        must not be able to anchor the wall in the past. Uses a CLEAN state dir so the date-guard is
        the path under test — once the live wall committed its results/forward_wall_start.json (which
        it now has), `_wall_start` correctly RETURNS that registered anchor instead of re-deriving,
        which is the separate also-safe path asserted by test_the_anchor_is_never_rewritten_once_it_exists."""
        from run_paper_cron import WALL_PREREG_DATE, _wall_start
        assert WALL_PREREG_DATE == "2026-07-02"      # forward/prereg.md registration date
        with pytest.raises(ValueError, match="predates its own"):
            _wall_start(tmp_path, "2016-12-30")   # the exact date the leak wrote; empty dir => date guard runs

    def test_the_anchor_is_committed_not_computed_each_run(self):
        assert "forward_wall_start.json" in CRON_SRC

    def test_the_anchor_is_never_rewritten_once_it_exists(self):
        """Re-deriving it every run would silently move the wall's start forward after any outage."""
        assert "if f.exists():" in CRON_SRC

    def test_sessions_before_the_registered_start_are_skipped(self):
        src = (ROOT / "nq" / "paper" / "wall_cron.py").read_text(encoding="utf-8")
        assert "if wall_start is not None and d < str(wall_start)[:10]:" in src

    def test_the_default_is_unbounded_so_existing_callers_are_unaffected(self):
        """The engine invariant: the bound is opt-in, so tests and prior call sites stay identical."""
        import inspect

        from nq.paper.wall_cron import update_wall
        assert inspect.signature(update_wall).parameters["wall_start"].default is None


class TestTheS2F3CrossCheckIsPossible:
    def test_the_commit_message_carries_the_actions_run_id(self, wf):
        """S2-F3: a committed artifact is not firing evidence when the artifact is hand-producible.
        S2-F4 leaves cron commits authored as the owner, so the author line cannot distinguish a
        runner commit from a hand-made one. The run id in the message restores the cross-check."""
        steps = " ".join(str(s.get("run", "")) for s in wf["jobs"]["wall"]["steps"])
        assert "github.run_id" in steps

    def test_the_workflow_records_why_S2_F4_was_left_alone(self):
        """An owner door left open on purpose must say so where the next reader will look."""
        t = WF.read_text(encoding="utf-8")
        assert "S2-F4" in t and "owner door" in t
