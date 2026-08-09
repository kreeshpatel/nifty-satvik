"""forward/prereg_swing.md §4 — A-only vs base-swing, evaluated rather than asserted.

§4 was registered 2026-07-13 and implemented nowhere: the only scorecard encoded forward/prereg.md
§10.2, which is the *momentum* wall's doc. So the grading decision this book actually faces was
carried in prose, and a prose gate is a gate nobody can reproduce.

These pin the frozen rule, including the two things easiest to get wrong under pressure at a review:
the insufficient-evidence branch defaults to base-swing (A-only must EARN its place, it does not get
the benefit of the doubt), and the sub-period metrics are read off a CONTINUOUS SLICE of each book's
own curve rather than a fresh-capital re-run from the window start.
"""
from __future__ import annotations

import json
import sys
from datetime import date, timedelta
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import bhanushali_review_scorecard as S  # noqa: E402


def _nav(vals: list[float], start: str = "2026-08-08") -> list[tuple[str, float]]:
    d0 = date.fromisoformat(start)
    return [((d0 + timedelta(days=i * 10)).isoformat(), v) for i, v in enumerate(vals)]


def _write_base(tmp: Path, nav, n_closed: int) -> None:
    (tmp / "base_swing_forward.json").write_text(json.dumps({
        "book": "base-swing", "n_closed": n_closed,
        "nav": [{"date": d, "equity": v} for d, v in nav]}), encoding="utf-8")


@pytest.fixture()
def results_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(S, "RESULTS_DIR", tmp_path)
    return tmp_path


# --------------------------------------------------------------- insufficient evidence
def test_absent_comparator_defaults_to_base_swing(results_dir):
    """Today's real state. The default is NOT the book holding the paper capital."""
    out = S._grading_panel(_nav([100.0, 110.0]), a_closed=99)
    assert out["verdict"].startswith("INSUFFICIENT EVIDENCE")
    assert "default base-swing" in out["verdict"]
    assert "has not accrued" in out["reason"]


def test_below_the_floor_defaults_to_base_swing_even_if_a_only_looks_better(results_dir):
    """A-only winning on both metrics must not promote itself under the 20-closed floor."""
    _write_base(results_dir, _nav([100.0, 80.0, 130.0]), n_closed=5)
    out = S._grading_panel(_nav([100.0, 99.0, 160.0]), a_closed=5)
    assert out["verdict"].startswith("INSUFFICIENT EVIDENCE")
    assert "below the §4 floor" in out["reason"]


def test_the_floor_reads_the_THINNER_book(results_dir):
    _write_base(results_dir, _nav([100.0, 90.0, 120.0]), n_closed=3)
    out = S._grading_panel(_nav([100.0, 95.0, 120.0]), a_closed=500)
    assert out["verdict"].startswith("INSUFFICIENT EVIDENCE")
    assert "3 closed trades in the thinner book" in out["reason"]


# --------------------------------------------------------------- the three decided branches
def test_keep_a_only_when_dd_shallower_and_calmar_holds(results_dir):
    _write_base(results_dir, _nav([100.0, 70.0, 140.0]), n_closed=25)
    out = S._grading_panel(_nav([100.0, 90.0, 140.0]), a_closed=25)
    assert out["verdict"] == "KEEP A-ONLY"
    assert out["maxdd_shallower"] is True


def test_revert_when_maxdd_is_not_shallower(results_dir):
    """The first half of the A-only bargain fails -> revert, whatever Calmar did."""
    _write_base(results_dir, _nav([100.0, 95.0, 200.0]), n_closed=25)
    out = S._grading_panel(_nav([100.0, 60.0, 200.0]), a_closed=25)
    assert out["verdict"] == "REVERT TO BASE-SWING"
    assert out["reason"] == "MaxDD not shallower"


def test_revert_when_calmar_falls_past_the_gap(results_dir):
    _write_base(results_dir, _nav([100.0, 70.0, 400.0]), n_closed=25)
    out = S._grading_panel(_nav([100.0, 90.0, 104.0]), a_closed=25)
    assert out["verdict"] == "REVERT TO BASE-SWING"
    assert out["calmar_delta"] < -S.GRADING_REVERT_CALMAR_GAP


def test_the_gap_between_keep_and_revert_is_surfaced_not_resolved(results_dir):
    """§4 as frozen defines no outcome when DD is shallower but Calmar sits between the 0.05 keep
    bound and the 0.10 revert bound. Picking a side after seeing the data would be inventing a
    threshold, so the scorecard says so and sends it to an amendment."""
    # Constructed over a full year so the annualised numbers are of ordinary size: a 20-day window
    # produces CAGRs in the thousands of percent, where a 0.05 Calmar gap is unreachable.
    #
    #   base    100 -> 70 -> 130   DD -30%, CAGR +30%  => Calmar 1.00
    #   A-only  100 -> 90 -> 109.2 DD -10%, CAGR +9.2% => Calmar 0.92   (delta -0.08, inside the gap)
    yr = [("2026-08-08", 100.0), ("2027-02-08", None), ("2027-08-08", None)]
    base = [(d, v) for (d, _), v in zip(yr, [100.0, 70.0, 130.0])]
    a_only = [(d, v) for (d, _), v in zip(yr, [100.0, 90.0, 109.2])]
    _write_base(results_dir, base, n_closed=25)
    found = S._grading_panel(a_only, a_closed=25)
    if not found["verdict"].startswith("UNDETERMINED"):
        found = None
    assert found is not None, "the gap must be reachable, or the rule has no hole to report"
    assert -S.GRADING_REVERT_CALMAR_GAP <= found["calmar_delta"] < -S.GRADING_KEEP_CALMAR_TOL
    assert found["maxdd_shallower"] is True
    assert "owner amendment" in found["reason"]


# --------------------------------------------------------------- window handling
def test_the_window_is_the_intersection_of_the_two_records(results_dir):
    """base-swing began logging five weeks late and §3 forbids backfilling, so the comparison can
    only run over what both books hold."""
    # Same 10-day grid, base starting two steps in, so the two records genuinely share dates.
    _write_base(results_dir, _nav([100.0, 110.0, 120.0], start="2026-08-28"), n_closed=25)
    out = S._grading_panel(_nav([100.0, 105.0, 111.0, 118.0], start="2026-08-08"), a_closed=25)
    assert out["common_window"] == {"from": "2026-08-28", "to": "2026-09-07"}
    assert out["a_only"]["from"] == "2026-08-28" and out["a_only"]["n_points"] == 2
    assert out["base_swing"]["from"] == "2026-08-28" and out["base_swing"]["n_points"] == 2


def test_metrics_are_a_continuous_slice_not_a_fresh_capital_rerun():
    """The phantom-0.762 defect, pinned. A drawdown that happened BEFORE the window must not be
    counted inside it, and the window's own peak is its starting point -- not a reset to par."""
    nav = _nav([100.0, 50.0, 100.0, 90.0])          # -50% early, then a -10% dip inside the window
    full = S._window_metrics(nav, nav[0][0], nav[-1][0])
    sliced = S._window_metrics(nav, nav[2][0], nav[-1][0])
    assert full["maxdd_pct"] == pytest.approx(-50.0, abs=0.01)
    assert sliced["maxdd_pct"] == pytest.approx(-10.0, abs=0.01), "the earlier crash is outside"
    assert sliced["from"] == nav[2][0] and sliced["n_points"] == 2


def test_a_too_short_window_is_insufficient_not_a_verdict(results_dir):
    _write_base(results_dir, [("2026-09-01", 100.0)], n_closed=25)
    out = S._grading_panel([("2026-09-01", 100.0)], a_closed=25)
    assert out["verdict"].startswith("INSUFFICIENT EVIDENCE")


def test_window_metrics_refuses_degenerate_input():
    assert S._window_metrics([], "2026-01-01", "2026-12-31") is None
    assert S._window_metrics(_nav([100.0]), "2026-01-01", "2026-12-31") is None
    assert S._window_metrics(_nav([0.0, 100.0]), "2026-01-01", "2027-12-31") is None


# --------------------------------------------------------------- the thresholds themselves
def test_thresholds_match_the_frozen_doc():
    """Tighten-only. If a relaxation ever lands here, §4 is void and its clock restarts -- so the
    numbers are held to the doc rather than to whatever the code happens to say."""
    doc = (ROOT / "forward" / "prereg_swing.md").read_text(encoding="utf-8")
    assert S.GRADING_FLOOR_CLOSED == 20 and "< 20 forward closed trades per book" in doc
    assert S.GRADING_KEEP_CALMAR_TOL == 0.05 and "Calmar ≥ base-swing − 0.05" in doc
    assert S.GRADING_REVERT_CALMAR_GAP == 0.10 and "0.10 below" in doc


def test_the_panel_discloses_the_limb_it_does_not_implement(results_dir):
    """§4's insufficient-evidence clause also fires on overlapping CIs, which this panel does not
    compute. A gate that silently implements three of four branches is worse than one that says so,
    because the missing branch is the one that would have said 'not yet'."""
    _write_base(results_dir, _nav([100.0, 70.0, 140.0]), n_closed=25)
    out = S._grading_panel(_nav([100.0, 90.0, 140.0]), a_closed=25)
    assert out["verdict"] == "KEEP A-ONLY"
    assert "CI-overlap limb" in out["not_implemented"]
    assert "provisional" in out["not_implemented"]


def test_the_promote_gate_declares_its_mixed_units():
    """§10.2's promote gate compares a GROSS expectancy against a NET drawdown. That is a real unit
    mismatch and it makes the gate easier to clear than it reads. Recomputing expectancy net would
    change what a pre-committed threshold means -- an amendment at a review date, not a code edit --
    so the artifact states the units instead of quietly reconciling them."""
    import subprocess

    subprocess.run([sys.executable, str(ROOT / "scripts" / "bhanushali_review_scorecard.py")],
                   check=True, capture_output=True, cwd=ROOT)
    card = json.loads((ROOT / "results" / "weekly_review_scorecard.json").read_text(encoding="utf-8"))
    units = card["gates"]["promote"]["_units"]
    assert "GROSS" in units and "NET" in units
    assert "not in the same unit" in units
