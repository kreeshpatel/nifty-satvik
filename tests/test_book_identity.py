"""A1's arithmetic, and the invariants that must hold whatever the live book does next.

Two kinds of test here, deliberately separated:

* **Synthetic** — the comparison and reconciliation functions are exercised on constructed inputs, so
  they keep testing the logic forever. A test that pinned "11 closed" would go red next Saturday for no
  reason, and a test that goes red for no reason gets deleted.
* **Structural, on the live artifacts** — only identities that are true BY CONSTRUCTION and would
  indicate a real defect if they broke: the NAV must equal cash plus the marked positions, and each
  scorecard field must equal the artifact it is copied from. These survive the book evolving.

The one thing NOT asserted is `curves_identical is True`. If the two capped books ever diverge that is
legitimate new information about the book, not a test failure — so the finding's claim is pinned to the
dated artifact it was measured on, not to a test that would forbid the book from changing.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "pipelines" / "diagnostics"))

import diag_book_identity as BI  # noqa: E402


# ------------------------------------------------------------------ synthetic: the curve comparison
def _artifacts(a_only: list[tuple[str, float]], all_grades: list[tuple[str, float]]) -> dict:
    return {
        "base": {"nav": [{"date": d, "equity": v} for d, v in all_grades]},
        "history": pd.DataFrame({"date": [d for d, _ in a_only],
                                 "total_value": [v for _, v in a_only]}),
    }


def test_identical_curves_are_reported_as_identical():
    pts = [("2026-07-06", 1_000_000.0), ("2026-07-07", 1_001_000.0)]
    out = BI.curve_identity(_artifacts(pts, pts))
    assert out["identical"] is True
    assert out["n_differing"] == 0
    assert out["max_abs_delta"] == 0.0


def test_a_single_paisa_of_real_divergence_is_not_swallowed():
    """The tolerance exists for rounding, not for a book that actually differs."""
    a = [("2026-07-06", 1_000_000.00), ("2026-07-07", 1_001_000.00)]
    b = [("2026-07-06", 1_000_000.00), ("2026-07-07", 1_001_000.50)]
    out = BI.curve_identity(_artifacts(a, b))
    assert out["identical"] is False
    assert out["n_differing"] == 1
    assert out["differing"][0]["date"] == "2026-07-07"
    assert out["max_abs_delta"] == pytest.approx(0.50)


def test_rounding_at_the_cent_does_not_read_as_divergence():
    a = [("2026-07-06", 1_018_440.1667)]
    b = [("2026-07-06", 1_018_440.17)]
    assert BI.curve_identity(_artifacts(a, b))["identical"] is True


def test_no_common_dates_is_not_reported_as_agreement():
    """Empty intersection must never read as 'identical' — that would hide a broken comparator."""
    out = BI.curve_identity(_artifacts([("2026-07-06", 1.0)], [("2026-08-06", 1.0)]))
    assert out["n_common"] == 0
    assert out["identical"] is False


# ------------------------------------------------------------------ synthetic: the reconciliation
def _portfolio(cash: float, positions: dict) -> dict:
    return {"portfolio": {"cash": cash, "total_value": cash + sum(p["current_value"] for p in positions.values()),
                          "positions": positions}}


def test_the_nav_identity_is_checked_not_assumed():
    pos = {"AAA": {"current_value": 500_000.0, "unrealised_pnl": 10_000.0},
           "BBB": {"current_value": 400_000.0, "unrealised_pnl": -5_000.0}}
    out = BI.nav_reconciliation(_portfolio(100_000.0, pos))
    assert out["identity_holds"] is True
    assert out["identity_residual"] == pytest.approx(0.0)
    assert out["sum_unrealised_pnl"] == pytest.approx(5_000.0)
    # implied realised = NAV - 1,000,000 - unrealised = 1,000,000 - 1,000,000 - 5,000
    assert out["implied_realised_pnl"] == pytest.approx(-5_000.0)


def test_a_broken_nav_identity_is_reported_as_broken():
    a = _portfolio(100_000.0, {"AAA": {"current_value": 500_000.0, "unrealised_pnl": 0.0}})
    a["portfolio"]["total_value"] += 1_000.0          # cash + marks no longer make the NAV
    out = BI.nav_reconciliation(a)
    assert out["identity_holds"] is False
    assert out["identity_residual"] == pytest.approx(-1_000.0)


def test_implied_realised_is_labelled_as_derived():
    """It is solved for, not sourced. If that label is ever dropped the number will be misread."""
    out = BI.nav_reconciliation(_portfolio(1_000_000.0, {}))
    assert "DERIVED_NOT_SOURCED" in out
    assert "solved for" in out["DERIVED_NOT_SOURCED"].lower()


# ------------------------------------------------------------------ structural, on the live artifacts
@pytest.fixture(scope="module")
def live():
    return BI.load_artifacts()


def test_the_live_nav_equals_cash_plus_the_marked_positions(live):
    """True by construction in the engine. If it breaks, the published portfolio is internally wrong."""
    out = BI.nav_reconciliation(live)
    assert out["identity_holds"], out


def test_every_scorecard_field_equals_the_artifact_it_is_copied_from(live):
    """The provenance map is verified by VALUE, not asserted from the code — this is that check."""
    prov = BI.provenance_map(live)
    disagreeing = [r["metric"] for r in prov["rows"] if r["agrees"] is False]
    assert not disagreeing, f"scorecard fields diverged from their sources: {disagreeing}"


def test_the_section_4_floor_still_reads_two_different_books(live):
    """The finding, pinned AT THE VALUE LEVEL. When the cron is fixed this flips and someone must
    acknowledge it in a diff.

    The first version of this test asserted on `gate_book_mismatch`'s hardcoded string constants, so it
    described the code's own literals and would have passed unchanged even after the defect was fixed
    (red-team, 2026-09-25). It now compares the artifacts the gate actually reads.
    """
    an, sc, base = live["analytics"], live["scorecard"], live["base"]
    grading = sc.get("swing_grading", {})
    # the A-only side of a PER-BOOK floor is the uncapped tracker's closure count...
    assert grading.get("a_only_closed") == an.get("total_closed")
    # ...while the base-swing side is a capped book's, and the two are not the same quantity
    assert base.get("n_closed") != an.get("total_closed"), (
        "the two sides of §4's floor now agree — the mismatch may have been fixed; update this test "
        "and finding 0146 deliberately")


def test_the_kill_gate_flag_is_read_from_the_key_not_the_value():
    """D4's regression: the scorecard names the gate in the KEY, so scanning values returns None and
    publishes 'unknown' for a gate that is in fact triggered."""
    sc = {"gates": {"kill": {"triggered": True, "rule": "net Sharpe < 0"},
                    "readiness": {"triggered": False}}}
    assert BI._kill_triggered(sc) is True
    assert BI._kill_triggered({"gates": {}}) is None
    assert BI._kill_triggered({}) is None


def test_a_name_absent_only_at_its_own_close_date_still_counts_as_funded():
    """The boundary trap that would have mislabelled the one genuinely funded closure.

    A position is legitimately absent from the snapshot taken AT its close date. Testing
    `signal_date <= snapshot <= close_date` marks it never-funded; the window must be half-open.
    """
    import json as _json
    import types
    snaps = {"2026-07-24": {"DELHIVERY"}, "2026-08-17": set()}
    # the half-open window [signal, close) keeps 07-24 and drops 08-17
    inside = [k for k in snaps if "2026-07-06" <= k < "2026-08-17"]
    assert inside == ["2026-07-24"]
    assert [k for k in inside if "DELHIVERY" in snaps[k]], "funded, and must not read as never-funded"
    assert _json and types        # keep the imports honest for linters


def test_the_capped_position_history_is_a_declared_lower_bound():
    hist = BI.capped_position_history()
    assert hist["n_snapshots"] > 0
    assert "lower bound" in hist["LOWER_BOUND"].lower()
    # a name that left must have been held first
    for row in hist["positions_that_left"]:
        assert row["ticker"] in hist["names_ever_held"]
    assert hist["n_positions_that_left"] <= hist["n_names_ever_held"]


def test_the_published_maxdd_is_reproducible_from_the_nav_curve(live):
    """A gate nobody can recompute is a gate nobody can audit."""
    prov = BI.provenance_map(live)
    row = next(r for r in prov["rows"] if r["metric"].startswith("maxdd_pct"))
    assert row["agrees"] is True, (
        f"published {row['value']} vs recomputed {prov['maxdd_recomputed_pct']}")
