"""The swing book's certified numbers must not silently re-base when the trial counter moves.

FIXED 2026-08-09. `scripts/run_bhanushali_weekly_rank.py` used to compute the run of record's
Deflated Sharpe as::

    n_tr = cumulative_n_trials()          # the LIVE counter
    dsr  = _dsr_from_bootstrap(arr, n_tr, (ci.lower, ci.upper))

and gate on `DSR > 0.95`. It now deflates at the pinned `CERTIFIED_N_TRIALS = 114` and reports the
live and lifetime counts alongside. These tests pin that fix; the last one checks the hazard was
real rather than theoretical.

Why it mattered: `cumulative_n_trials()` reads the **live** counter, which was reset 138 -> 0 -> 2
by owner decision on 2026-08-07, while the certification DSR 0.894 was computed at **n_trials 114**
(`forward/prereg_swing.md`).

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


def test_the_certified_count_is_pinned_in_code_and_matches_the_document():
    """The fix for the re-basing hazard: the run of record deflates at a PINNED count, and that
    constant is tied to the pre-registration rather than to a mutable counter."""
    src = RUNNER.read_text(encoding="utf-8")
    m = re.search(r"^CERTIFIED_N_TRIALS\s*=\s*(\d+)", src, re.M)
    assert m, "run_bhanushali_weekly_rank no longer pins a certification trial count"
    assert m.group(1) == CERTIFIED["n_trials"], (
        f"code pins n_trials={m.group(1)} but forward/prereg_swing.md certifies at "
        f"{CERTIFIED['n_trials']}. The certified number and the count it was deflated at are one "
        f"fact; they may not disagree."
    )


def test_the_gate_reads_the_pinned_count_not_the_live_counter():
    """`dsr` — the variable the `dsr > 0.95` gate reads — must be computed from the pinned count.
    This is the regression test for the defect: on the pre-fix code it was
    `n_tr = cumulative_n_trials()` feeding straight into the gate."""
    src = RUNNER.read_text(encoding="utf-8")
    assert "dsr = _dsr_from_bootstrap(arr, CERTIFIED_N_TRIALS," in src, (
        "the run of record's gated DSR is no longer deflated at the pinned certification count"
    )
    assert "n_tr = cumulative_n_trials()" not in src, (
        "the live counter is feeding the gate again — this is the exact defect this file exists for"
    )
    assert "dsr > 0.95" in src, "the DSR gate moved; re-derive whether the re-basing hazard survives"


def test_the_live_and_lifetime_counts_are_still_reported():
    """Pinning must not hide the other two numbers. The live count is what a NEW trial would be
    judged at, and the lifetime count is the statistically defensible denominator — suppressing
    either would trade one blind spot for another."""
    src = RUNNER.read_text(encoding="utf-8")
    for name in ("cumulative_n_trials()", "lifetime_n_trials()"):
        assert name in src, f"{name} is no longer reported alongside the pinned certification"


def test_the_rebasing_hazard_was_real_and_would_have_flipped_the_gate():
    """Guard the guard, numerically. If DSR were insensitive to the trial count this whole file
    would be theatre. Uses 0001's committed per-window signature, the same basis the runner uses."""
    from nq.validation.dsr import deflated_sharpe_ratio

    kw = dict(n_observations=37, skewness=0.145, kurtosis=2.704, sharpe_variance=0.0947)
    at_reset = deflated_sharpe_ratio(0.5035, n_trials=2, **kw)
    at_cert = deflated_sharpe_ratio(0.5035, n_trials=114, **kw)
    assert at_reset > at_cert, "DSR is not decreasing in the trial count; re-derive the hazard"
    assert at_reset - at_cert > 0.25, (
        f"the re-basing moved DSR by only {at_reset - at_cert:.3f}. If the counts genuinely no "
        f"longer matter, this file's premise is stale and should be re-argued, not relaxed."
    )
