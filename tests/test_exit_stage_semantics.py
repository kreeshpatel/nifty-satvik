"""`exit_stage` must describe what LEFT the book, not what was decided.

THE DEFECT. The booking flags were read off the engine's trigger state — `t1_done` / `pt_done` —
which is set when an exit is DECIDED at the weekly close. The shares leave at the next session's
open, and `frac_left` only decrements then. So BAJAJ-AUTO's live card on 2026-09-04 carried:

    target_40_booked: true, pattern_40_booked: true, fraction_remaining: 0.6

Two of three tranches reported sold while 60% was still held. It was not cosmetic:
`SignalsV3.jsx`'s `trancheDone` reads these flags to pick the next action, so the card told the
holder to hold the runner while a 40% sell order was pending for Monday.

THE FIX. Derive the flags from `frac_left`, against the SAME plan the card renders, so they cannot
disagree with `fraction_remaining`; and move the queued tranche to `pending_exit`, which is the one
thing on the card with a deadline.

The old key names are gone on purpose. `target_40_booked` hardcoded 40 while the size comes from cfg
(`tp1_frac` / `pattern_frac`), so it would have become a second lie the first time config-P was
retuned. `exit_stage` is not in `results/output_contracts.json` and `SignalsV3.jsx` was the only
consumer, so the rename costs nothing.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import run_bhanushali_cron as C  # noqa: E402

# config-P's shape: 40% at the +2R target, 40% on the blow-off, 20% runner.
PLAN = {"tranches": [
    {"pct": 40, "type": "target", "level": 188.18},
    {"pct": 40, "type": "pattern", "arm": 191.53},
    {"pct": 20, "type": "runner", "level": 163.23},
]}


def stage(frac, *, pending=None, pending_frac=None, plan=PLAN):
    p = {"frac_left": frac}
    if pending is not None:
        p["pending"] = pending
    if pending_frac is not None:
        p["pending_frac"] = pending_frac
    return C._exit_stage(plan, p)


# --------------------------------------------------------------------------- the incident
def test_the_bajaj_auto_card_no_longer_claims_two_tranches_sold():
    """Its real state: the pattern exit was DECIDED, nothing beyond the target had been sold."""
    s = stage(0.6, pending=("part", "pattern"), pending_frac=0.4)
    assert s["target_booked"] is True, "40% was genuinely sold"
    assert s["pattern_booked"] is False, "the pattern tranche had not left the book"
    assert s["fraction_remaining"] == 0.6
    assert s["pending_exit"]["reason"] == "pattern"
    assert s["pending_exit"]["fraction"] == 0.4


def test_the_flags_can_never_contradict_fraction_remaining():
    """The property that makes the defect unrepresentable: both come from frac_left."""
    for frac in (1.0, 0.8, 0.6, 0.4, 0.2, 0.0):
        s = stage(frac)
        sold = round(1.0 - frac, 2)
        assert s["fraction_sold"] == sold
        assert s["target_booked"] == (sold >= 0.39), frac
        assert s["pattern_booked"] == (sold >= 0.79), frac


# --------------------------------------------------------------------------- the ladder
@pytest.mark.parametrize("frac,target,pattern,runner", [
    (1.0, False, False, True),    # untouched
    (0.6, True, False, True),     # target tranche filled
    (0.2, True, True, True),      # target + pattern filled, runner held
    (0.0, True, True, False),     # fully out
])
def test_each_rung_of_the_ladder(frac, target, pattern, runner):
    s = stage(frac)
    assert (s["target_booked"], s["pattern_booked"], s["runner_open"]) == (target, pattern, runner)


def test_rounding_does_not_flip_a_boundary():
    """frac_left is rounded to 2dp upstream, so 0.6 must read as exactly-target-booked, not short."""
    assert stage(0.6)["target_booked"] is True
    assert stage(0.61)["target_booked"] is True
    assert stage(0.62)["target_booked"] is False, "a tranche that did not fill must not read booked"


# --------------------------------------------------------------------------- pending
def test_no_pending_order_reads_as_none():
    assert stage(0.6)["pending_exit"] is None


def test_a_full_exit_reports_the_whole_remainder():
    s = stage(0.6, pending=("full", "stop"))
    assert s["pending_exit"] == {"kind": "full", "reason": "stop", "fraction": 0.6,
                                 "fills": "next session's open"}


def test_pending_says_when_it_fills():
    """A fraction with no deadline is not actionable; the card's only timed line is this one."""
    assert "next session" in stage(0.6, pending=("part", "pattern"), pending_frac=0.4)["pending_exit"]["fills"]


# --------------------------------------------------------------------------- plan-driven, not hardcoded
def test_the_thresholds_follow_THE_PLAN_not_a_constant():
    """The old keys baked in 40. With a 50/30/20 plan the booking points must move with it, or the
    flags drift the first time config-P is retuned."""
    plan = {"tranches": [{"pct": 50, "type": "target"}, {"pct": 30, "type": "pattern"},
                         {"pct": 20, "type": "runner"}]}
    assert stage(0.5, plan=plan)["target_booked"] is True
    assert stage(0.6, plan=plan)["target_booked"] is False, "60% held means 40% sold, under the 50% rung"
    assert stage(0.2, plan=plan)["pattern_booked"] is True


def test_two_target_tranches_book_on_the_last_one():
    """tp1 and tp2 are both type 'target'. `target_booked` must mean both have cleared, not one."""
    plan = {"tranches": [{"pct": 30, "type": "target"}, {"pct": 30, "type": "target"},
                         {"pct": 40, "type": "runner"}]}
    assert stage(0.7, plan=plan)["target_booked"] is False, "only tp1 filled"
    assert stage(0.4, plan=plan)["target_booked"] is True, "both target tranches filled"


def test_a_plan_with_no_tranches_does_not_crash():
    s = stage(1.0, plan={})
    assert s["target_booked"] is False and s["pattern_booked"] is False
    assert s["fraction_remaining"] == 1.0


# --------------------------------------------------------------------------- the consumer
def test_the_frontend_reads_the_new_keys_and_not_the_old():
    """The rename is only safe because there is exactly one consumer. Assert it moved with the
    producer — a half-applied rename silently falls back to `undefined`, i.e. 'nothing booked',
    which is the same class of wrong answer in the other direction."""
    src = (ROOT / "frontend" / "src" / "pages" / "SignalsV3.jsx").read_text(encoding="utf-8")
    for gone in ("target_40_booked", "pattern_40_booked", "runner_20_open"):
        assert gone not in src, f"SignalsV3 still reads the removed key {gone}"
    for needed in ("stage.target_booked", "stage.pattern_booked", "stage.runner_open",
                   "stage.pending_exit"):
        assert needed in src, f"SignalsV3 does not read {needed}"


def test_the_producer_emits_no_stale_key():
    src = (ROOT / "scripts" / "run_bhanushali_cron.py").read_text(encoding="utf-8")
    for gone in ('"target_40_booked"', '"pattern_40_booked"', '"runner_20_open"'):
        assert gone not in src, f"the producer still emits {gone}"


def test_the_trigger_flags_are_no_longer_what_booking_means():
    """`t1_done` / `pt_done` are the engine's DECISION state. If they reappear as the source of a
    booking flag, the defect is back.

    Parsed, not grepped: the docstring names both flags in order to say they are NOT the source, so
    a substring scan flags the sentence that states the rule. (Second time today — the signal-quality
    seal test had the same bug.) Only string literals in executable code count.
    """
    import ast
    import inspect
    fn = ast.parse(inspect.getsource(C._exit_stage)).body[0]
    body = fn.body[1:] if (fn.body and isinstance(fn.body[0], ast.Expr)
                           and isinstance(fn.body[0].value, ast.Constant)) else fn.body
    literals = {n.value for stmt in body for n in ast.walk(stmt)
                if isinstance(n, ast.Constant) and isinstance(n.value, str)}
    assert "t1_done" not in literals and "pt_done" not in literals, (
        "_exit_stage reads the trigger flags again — booking must come from frac_left")
    assert "frac_left" in literals
