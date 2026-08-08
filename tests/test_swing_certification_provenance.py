"""The swing book's certified numbers must not silently re-base when the trial counter moves.

`scripts/run_bhanushali_weekly_rank.py:977` computes the run of record's Deflated Sharpe as::

    n_tr = cumulative_n_trials()
    dsr  = _dsr_from_bootstrap(arr, n_tr, (ci.lower, ci.upper))

and then gates on `DSR > 0.95` at `:983`. `cumulative_n_trials()` reads the **live** counter. That
counter was reset 138 -> 0 -> 2 by owner decision on 2026-08-07, while the pinned certification
DSR 0.894 was computed at **n_trials 114** (`forward/prereg_swing.md`).

`nq.validation.dsr.deflated_sharpe_ratio` subtracts `expected_max_sharpe(n_trials)`, which is
strictly increasing in the trial count, so DSR is strictly *decreasing* in it. Re-running the run of
record today, with no strategy change whatsoever, therefore produces a **higher** DSR against the
same gate — and the printed verdict can move from UNDERPOWERED toward PROMOTE for no reason except
that a counter was reset.

That is not an argument against the reset, which was a deliberate owner decision with its reasoning
recorded in `n_trials.json`. It is an argument that **a certified number and the trial count it was
deflated at are one fact, not two**, and must travel together. Nothing in the suite asserted the
certification triple before this file: `grep -rn "1.132" tests/` matched only fixture price digits.

These tests pin the provenance, not the strategy. They do not re-run the book.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
PREREG = ROOT / "forward" / "prereg_swing.md"
N_TRIALS = ROOT / "diagnostics" / "research" / "n_trials.json"
RUNNER = ROOT / "scripts" / "run_bhanushali_weekly_rank.py"

# The certification of record, from forward/prereg_swing.md section 1.
CERTIFIED = {"sharpe": "1.132", "cagr": "24.7", "maxdd": "42.4", "dsr": "0.894", "n_trials": "114"}


@pytest.fixture(scope="module")
def prereg() -> str:
    return PREREG.read_text(encoding="utf-8")


@pytest.mark.parametrize("field,value", sorted(CERTIFIED.items()))
def test_the_certification_triple_is_still_recorded(prereg: str, field: str, value: str):
    """Sharpe, CAGR, drawdown, DSR and the trial count it was deflated at."""
    assert value in prereg, (
        f"forward/prereg_swing.md no longer records the certified {field} = {value}. This is the "
        f"only place the swing book's certification lives; the runnable pipeline recomputes DSR "
        f"against the LIVE counter and cannot reproduce it."
    )


def test_the_dsr_is_never_quoted_without_its_trial_count(prereg: str):
    """0.894 at 114 trials and 0.894 at 2 trials are different claims. The document must not let a
    reader pick up the first number without the second."""
    for m in re.finditer(r"0\.894", prereg):
        window = prereg[max(0, m.start() - 400): m.end() + 400]
        assert "114" in window, (
            "a DSR of 0.894 appears without n_trials = 114 within 400 characters. A deflated "
            "Sharpe is meaningless without the count it was deflated at."
        )


def test_the_live_counter_has_moved_away_from_the_certified_one():
    """The condition that makes this whole file necessary. If the counter ever returns to 114 this
    test fails and the reasoning above should be re-read rather than the test deleted."""
    live = json.loads(N_TRIALS.read_text(encoding="utf-8"))["cumulative_n_trials"]
    assert live != int(CERTIFIED["n_trials"]), (
        f"the live counter is back at {live}, matching the certification. Re-read this module's "
        f"docstring: the hazard it describes is currently dormant, not fixed."
    )


def test_the_runner_still_reads_the_live_counter_and_is_therefore_not_reproducible():
    """A characterization test, deliberately asserting the CURRENT defective behaviour so that
    fixing it is a visible, intentional diff rather than a silent one.

    The fix is to make the trial count an explicit argument to the run of record, so a re-run
    reproduces the certified verdict instead of re-basing it. When that happens, this test should
    fail — and it should be replaced by one asserting the count is passed in, not deleted.
    """
    src = RUNNER.read_text(encoding="utf-8")
    assert "n_tr = cumulative_n_trials()" in src, (
        "the run of record no longer reads the live counter. If the trial count is now an explicit "
        "argument, that is the intended fix: replace this test with one pinning the explicit value."
    )
    assert "dsr > 0.95" in src, "the DSR gate moved; re-derive whether the re-basing hazard survives"
