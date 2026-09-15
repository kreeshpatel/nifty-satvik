"""B′ reaches the live cron, and the card reads a demerged holding correctly.

`tests/test_r94_demerger.py` proves the engine. This file proves the three places between the engine and
the owner where B′ could still be lost:

  * THE REGISTER — `load_demerger_rows` reads the addendum new events are registered in, and keeps only
    demergers the cleaner deliberately LEFT as a cliff. HEG must come through with retained 0.373773.
  * THE WIRING — every `R94.backtest` call in `main` receives the events. A book left out would disagree
    with the other two about the same holding (the paper NAV crediting HEG while the signal ledger stops
    it out, say).
  * THE CARD — a demerger multiplies `frac_left` by the retained ratio without selling a share. Read
    naively, HEG's 0.37 is "63% sold" and the card says the +2R target was booked on a position that has
    never sold anything. Tranche progress is read in shares: frac_left / ca_scale. And the runner line on
    the card must come from the demerger-adjusted series the engine is using, not the raw one.
"""
from __future__ import annotations

import ast
import inspect
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import run_bhanushali_cron as C  # noqa: E402

PLAN = {"tranches": [
    {"pct": 40, "type": "target", "level": 130.6},
    {"pct": 40, "type": "pattern", "arm": 163.25},
    {"pct": 20, "type": "runner", "level": 110.0},
]}
R_HEG = 0.373773

HEADER = "symbol,ex_date,kind,subject,implied_factor,series_return,resolution,source\n"


# --------------------------------------------------------------------------- the register
def test_the_committed_addendum_yields_heg():
    rows = C.load_demerger_rows()
    heg = [r for r in rows if r[0] == "HEG"]
    assert heg == [("HEG", "2026-09-07", pytest.approx(R_HEG, abs=1e-6))]


def test_only_demergers_left_as_a_cliff_are_loaded(tmp_path):
    f = tmp_path / "ca.csv"
    f.write_text("# comment lines are allowed\n" + HEADER
                 + "AAA,2026-10-01,demerger,Demerger,1.0,-0.30,LEFT_UNADJUSTED_AS_INTENDED,src\n"
                 + "BBB,2026-10-01,demerger,Demerger,0.7,-0.001,ADJUSTED,src\n"
                 + "CCC,2026-10-01,split,Split,0.5,-0.50,LEFT_UNADJUSTED_AS_INTENDED,src\n",
                 encoding="utf-8")
    assert C.load_demerger_rows(f) == [("AAA", "2026-10-01", pytest.approx(0.70))]


def test_a_row_that_is_not_a_demerger_ratio_is_refused(tmp_path):
    f = tmp_path / "ca.csv"
    f.write_text(HEADER + "AAA,2026-10-01,demerger,Demerger,1.0,0.05,LEFT_UNADJUSTED_AS_INTENDED,src\n",
                 encoding="utf-8")
    with pytest.raises(ValueError, match="does not describe a demerger"):
        C.load_demerger_rows(f)


def test_a_missing_register_runs_the_book_as_before(tmp_path):
    assert C.load_demerger_rows(tmp_path / "absent.csv") == []


# --------------------------------------------------------------------------- the wiring
def test_every_book_in_main_receives_the_demerger_events():
    tree = ast.parse(inspect.getsource(C.main))
    calls = [n for n in ast.walk(tree) if isinstance(n, ast.Call)
             and isinstance(n.func, ast.Attribute) and n.func.attr == "backtest"
             and isinstance(n.func.value, ast.Name) and n.func.value.id == "R94"]
    assert len(calls) == 3, f"expected the paper, uncapped and base-swing books, found {len(calls)} backtest calls"
    for c in calls:
        kw = {k.arg: k.value for k in c.keywords if k.arg}
        assert "demerger_events" in kw, f"a backtest call on line {c.lineno} of main() gets no demerger events"
        assert isinstance(kw["demerger_events"], ast.Name) and kw["demerger_events"].id == "ca_events", (
            "all three books must share ONE events object, or they can disagree about the same holding")


# --------------------------------------------------------------------------- the card
def test_a_demerger_alone_books_no_tranche():
    """HEG on the paper book: nothing sold, frac_left 0.37 only because the value shrank."""
    s = C._exit_stage(PLAN, {"frac_left": R_HEG, "ca_scale": R_HEG})
    assert s["fraction_remaining"] == 1.0
    assert s["target_booked"] is False and s["pattern_booked"] is False
    assert s["fraction_sold"] == 0.0


def test_a_demerger_after_the_target_tranche_still_reads_as_one_tranche_sold():
    """40% sold at +2R, then the demerger: 0.6 x r of the value, 60% of the shares."""
    s = C._exit_stage(PLAN, {"frac_left": 0.6 * R_HEG, "ca_scale": R_HEG})
    assert s["fraction_remaining"] == 0.6
    assert s["target_booked"] is True and s["pattern_booked"] is False


def test_without_a_demerger_the_card_is_unchanged():
    assert C._exit_stage(PLAN, {"frac_left": 0.6}) == C._exit_stage(PLAN, {"frac_left": 0.6, "ca_scale": 1.0})


def test_the_runner_line_comes_from_the_series_the_engine_uses():
    P = {"HEG": {"wsma_at": {1: 700.0, 2: 690.0}}}
    p = {"ca_view": {"wsma_at": {1: 261.6, 2: 257.9}}}
    assert C._sma44_now(P, "HEG") == 690.0
    assert C._sma44_now(P, "HEG", p) == 257.9
    assert C._sma44_now(P, "HEG", {"en": 1.0}) == 690.0
