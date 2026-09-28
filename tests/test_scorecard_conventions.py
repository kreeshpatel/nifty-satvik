"""Every gate the review reads must say, in its own output, which convention and which BOOK it used.

The regression test for the `prod-fix` that added them (2026-09-27). Until then the scorecard printed
four gates whose readings were ambiguous (binder §9.1-9.4) over inputs drawn from two different books
(finding 0146), and neither fact was recoverable from the file the review actually reads.

The assertions are deliberately about STRUCTURE and SOURCE, not about values: a test that pinned
`sharpe == -0.7310` would go red every Saturday and be deleted within a month. What must not drift is
that each gate declares its convention, that the declaration cites the pre-registration section that
ratified it, and that the one gate whose two sides are different quantities keeps saying so.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import bhanushali_review_scorecard as S  # noqa: E402

SCORECARD = ROOT / "results" / "weekly_review_scorecard.json"


@pytest.fixture(scope="module")
def card() -> dict:
    if not SCORECARD.is_file():
        pytest.skip("no scorecard has been generated yet")
    return json.loads(SCORECARD.read_text(encoding="utf-8"))


def test_the_two_books_are_named_once_and_differ():
    """0146's whole point: these are not the same book, so they cannot share a label."""
    assert "uncapped" in S.BOOK_UNCAPPED.lower()
    assert "capped" in S.BOOK_CAPPED.lower()
    assert S.BOOK_UNCAPPED != S.BOOK_CAPPED


@pytest.mark.parametrize("gate", ["readiness", "promote", "kill", "halt"])
def test_every_gate_declares_a_convention_and_cites_its_authority(card, gate):
    g = card["gates"][gate]
    conv = g.get("convention")
    assert conv, f"gate {gate!r} does not say what convention its inputs are measured under"
    # the halt gate legitimately cites §5 first (the grid is written into the halt rule itself) and
    # §11.3 second, so require both the document and a §11 subsection rather than a literal prefix
    authority = conv.get("authority", "")
    assert "prereg_swing.md" in authority and "§11" in authority, (
        f"gate {gate!r}'s convention cites no ratifying section — an unratified convention is just a "
        f"preference. Got: {authority!r}")


@pytest.mark.parametrize("gate,expected", [("readiness", "uncapped"), ("kill", "capped"),
                                          ("halt", "capped")])
def test_each_gate_names_the_book_its_inputs_come_from(card, gate, expected):
    book = card["gates"][gate]["convention"]["book"]
    assert expected in book.lower(), f"gate {gate!r} names book {book!r}, expected {expected!r}"


def test_the_promote_gate_names_both_of_its_books(card):
    """It mixes them: expectancy is the tracker's, MaxDD is the capital book's."""
    conv = card["gates"]["promote"]["convention"]
    assert "uncapped" in conv["expectancy_book"].lower()
    assert "capped" in conv["maxdd_book"].lower()
    assert conv["expectancy_book"] != conv["maxdd_book"]


def test_the_kill_gate_states_the_ratified_sharpe_reading(card):
    """§11.1. If this ever flips to excess-return it is a review decision, not a silent edit."""
    conv = card["gates"]["kill"]["convention"]
    assert "rf = 0" in conv["sharpe"]
    assert "NOT below the risk-free rate" in conv["means"]
    assert "TIGHTENS" in conv["excess_return_reading_would_be"]


def test_the_halt_gate_states_the_daily_grid(card):
    """§11.3. The grid is part of the rule now, because a coarser one can only understate a drawdown."""
    conv = card["gates"]["halt"]["convention"]
    assert conv["grid"] == "daily"
    assert "UNDERSTATE" in conv["why_the_grid_matters"]


def test_the_section_4_floor_keeps_declaring_that_its_two_sides_differ(card):
    """The finding, pinned in the artifact the review reads.

    When §4's floor is repaired this assertion flips and someone must update it deliberately — which is
    the point. `same_quantity: False` is the scorecard admitting, in its own output, that it applies one
    threshold to two different quantities.
    """
    conv = card["swing_grading"].get("convention")
    assert conv, "the §4 grading panel does not declare which books its two closure counts come from"
    assert conv["same_quantity"] is False
    assert conv["a_only_closed_book"] != conv["base_swing_closed_book"]
    assert "0146" in conv["authority"]


def test_the_expectancy_precondition_is_stated_with_the_live_count(card):
    """§11.4: below 30 closed, expectancy is published AS uninformative — so the gate says so."""
    conv = card["gates"]["promote"]["convention"]
    assert ">=30 closed" in conv["expectancy_informative"]
    assert str(card["forward"]["n_closed"]) in conv["expectancy_informative"]


def test_the_conventions_are_additive_and_change_no_threshold():
    """A prod-fix that moved a gate would be a prod-override. These constants are the guard on that."""
    assert (S.READY_CLOSED, S.READY_QUARTERS) == (40, 4)
    assert (S.PROMOTE_EXPECTANCY_R, S.PROMOTE_MAXDD) == (0.10, -0.25)
    assert S.KILL_SHARPE == 0.0
    assert S.GRADING_FLOOR_CLOSED == 20
