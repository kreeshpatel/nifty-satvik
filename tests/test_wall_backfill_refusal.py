"""A stalled wall must not catch up by reconstructing the sessions it missed.

`update_wall` appends one `ok` row per base session after the wall's last logged date. In daily
operation that is exactly one row. After a stall it is however many sessions the stall lasted — and
in the log, and in the hash chain, those rows are indistinguishable from rows written on the day.

`forward/prereg.md` §3 rule 4 settles which is allowed:

    "No back-dating. A row's date must be strictly after the last; a missed day is a gap, never
    reconstructed."

This became live rather than theoretical on 2026-08-28: `run_paper_cron` took the `min_bars` default
on a 15-day top-up, the OHLCV cache stopped advancing, and the wall logged nothing from 2026-08-24
to 2026-08-28 while committing a daily-log message each day. Fixing the cache alone would have made
the next run append five reconstructed `ok` rows into an append-only, hash-chained, pre-registered
record — unremovable afterwards without breaking the chain.

So the catch-up is refused by default and a person decides. Refusing costs a re-run; the alternative
cannot be undone. The same reasoning, and the same shape, as
`nq.paper.wall_cron._assert_veto_arm_live`.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import run_paper_cron as R  # noqa: E402

HEADER = ("date,status,base_ret,base_nav,base_n,veto_ret,veto_nav,veto_n,"
          "drift_ret,drift_nav,drift_n,chain,hash\n")


class _Book:
    """Only what the guard reads: the stepped sessions."""

    def __init__(self, *dates: str):
        self.equity_curve = [{"date": d, "value": 1_000_000.0} for d in dates]


def _wall(tmp_path: Path, *dates: str) -> Path:
    body = "".join(f"{d},ok,0.0,1000000.0,10,0.0,1000000.0,10,0.0,1000000.0,10,1.0000,deadbeef\n"
                   for d in dates)
    (tmp_path / "forward_wall.csv").write_text(HEADER + body, encoding="utf-8")
    return tmp_path


def _check(state_dir, book, *, wall_start="2026-07-02", allow=False):
    return R._assert_no_silent_backfill(state_dir, book, wall_start=wall_start, allow=allow)


# --------------------------------------------------------------------------- the incident
def test_the_five_session_catch_up_is_refused(tmp_path):
    """Exactly what the next run would have written: wall at 08-21, book through 08-28."""
    d = _wall(tmp_path, "2026-08-20", "2026-08-21")
    book = _Book("2026-08-21", "2026-08-24", "2026-08-25", "2026-08-26", "2026-08-27", "2026-08-28")
    with pytest.raises(R.WallBackfillRefused, match="5 unlogged sessions"):
        _check(d, book)


def test_the_refusal_quotes_the_rule_and_names_both_doors(tmp_path):
    d = _wall(tmp_path, "2026-08-21")
    book = _Book("2026-08-24", "2026-08-25", "2026-08-26")
    with pytest.raises(R.WallBackfillRefused) as e:
        _check(d, book)
    msg = str(e.value)
    assert "a missed day is a gap, never reconstructed" in msg   # the registered rule, verbatim
    assert "--allow-wall-backfill" in msg                        # door (a)
    assert "`gap` markers" in msg                                # door (b)
    assert "2026-08-24 .. 2026-08-26" in msg                     # which sessions


# --------------------------------------------------------------------------- what must NOT fire
def test_the_ordinary_one_session_append_is_untouched(tmp_path):
    """The daily case. A guard that fired here would stop the wall every day it worked."""
    _check(_wall(tmp_path, "2026-08-27"), _Book("2026-08-27", "2026-08-28"))


def test_a_same_day_rerun_appends_nothing_and_passes(tmp_path):
    _check(_wall(tmp_path, "2026-08-28"), _Book("2026-08-27", "2026-08-28"))


def test_a_cold_wall_is_bounded_by_wall_start_not_by_this(tmp_path):
    """With no rows yet there is nothing to reconstruct RELATIVE TO. `_wall_start` is the control
    that stops a cold book's months of recomputed history entering the log; duplicating it here
    would refuse every legitimate first run."""
    _check(tmp_path, _Book("2026-08-26", "2026-08-27", "2026-08-28"))


def test_sessions_before_the_registered_start_are_not_counted(tmp_path):
    """They can never be logged, so they cannot make a catch-up look larger than it is."""
    d = _wall(tmp_path, "2026-08-27")
    book = _Book("2026-06-01", "2026-06-02", "2026-06-03", "2026-08-28")
    _check(d, book, wall_start="2026-08-01")


# --------------------------------------------------------------------------- the explicit door
def test_allow_is_an_explicit_decision_not_a_default(tmp_path):
    d = _wall(tmp_path, "2026-08-21")
    book = _Book("2026-08-24", "2026-08-25", "2026-08-26")
    with pytest.raises(R.WallBackfillRefused):
        _check(d, book)
    _check(d, book, allow=True)


def test_the_flag_exists_and_defaults_to_off():
    """A door that is open by default is not a door. Read the parser, not the docstring."""
    import contextlib
    import io
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), pytest.raises(SystemExit):
        R.main(["--help"])
    assert "--allow-wall-backfill" in buf.getvalue()
    # store_true, so absent-from-argv means False — the refusal is what a bare cron run gets.
    import inspect
    assert inspect.signature(R._assert_no_silent_backfill).parameters["allow"].default is False


# --------------------------------------------------------------------------- wiring
def test_the_cron_calls_the_guard_before_it_appends():
    """Order is the whole point: after `update_wall` the rows are already in the file."""
    src = (ROOT / "scripts" / "run_paper_cron.py").read_text(encoding="utf-8")
    assert src.index("_assert_no_silent_backfill(") < src.index("wrote = update_wall(")
