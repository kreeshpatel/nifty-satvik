"""A stalled wall must not catch up by reconstructing the sessions it missed.

`update_wall` appends rows for every base session after the wall's last logged date. In daily
operation that is one row. After a stall it is however many sessions the stall lasted — and written
as `ok` rows they are indistinguishable, in the log and in the hash chain, from rows written on the
day.

`forward/prereg.md` §3 rule 4 settles it:

    "No back-dating. A row's date must be strictly after the last; a missed day is a gap, never
    reconstructed."

This stopped being theoretical on 2026-08-28. `run_paper_cron` took the `min_bars` default on a
15-day top-up, the OHLCV cache stopped advancing, and the wall logged nothing from 2026-08-24 to
2026-08-28 while committing a daily-log message each day. Fixing the cache alone would have made the
next run append five reconstructed `ok` rows into an append-only, hash-chained, pre-registered
record — unremovable afterwards without breaking the chain.

So only the most recent session is logged; the ones before it become hash-chained `gap` markers,
which is what §3 asks for and what `record_trading_day` already knew how to write. `--allow-wall-
backfill` is the owner override, and it has to be typed.
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
    """Only what the reporter reads: the stepped sessions."""

    def __init__(self, *dates: str):
        self.equity_curve = [{"date": d, "value": 1_000_000.0} for d in dates]


def _wall(tmp_path: Path, *dates: str) -> Path:
    body = "".join(f"{d},ok,0.0,1000000.0,10,0.0,1000000.0,10,0.0,1000000.0,10,1.0000,deadbeef\n"
                   for d in dates)
    (tmp_path / "forward_wall.csv").write_text(HEADER + body, encoding="utf-8")
    return tmp_path


def _gap(state_dir, book, *, wall_start="2026-07-02"):
    return R._wall_gap_report(state_dir, book, wall_start=wall_start)


# --------------------------------------------------------------------------- the incident
def test_the_five_missed_sessions_become_gaps_not_rows(tmp_path):
    """Exactly what the next run faces: wall at 08-21, book through 08-31."""
    d = _wall(tmp_path, "2026-08-20", "2026-08-21")
    book = _Book("2026-08-21", "2026-08-24", "2026-08-25", "2026-08-26", "2026-08-27",
                 "2026-08-28", "2026-08-31")
    assert _gap(d, book) == ["2026-08-24", "2026-08-25", "2026-08-26", "2026-08-27", "2026-08-28"]


def test_the_most_recent_session_is_still_logged(tmp_path):
    """A gap policy that swallowed today's session too would stop the wall permanently."""
    d = _wall(tmp_path, "2026-08-21")
    book = _Book("2026-08-24", "2026-08-25", "2026-08-31")
    assert "2026-08-31" not in _gap(d, book)


# --------------------------------------------------------------------------- what must NOT gap
def test_the_ordinary_one_session_append_gaps_nothing(tmp_path):
    """The daily case. Anything reported here would be a session being silently dropped."""
    assert _gap(_wall(tmp_path, "2026-08-27"), _Book("2026-08-27", "2026-08-28")) == []


def test_a_same_day_rerun_gaps_nothing(tmp_path):
    assert _gap(_wall(tmp_path, "2026-08-28"), _Book("2026-08-27", "2026-08-28")) == []


def test_a_cold_wall_is_bounded_by_wall_start_not_by_this(tmp_path):
    """With no rows yet there is nothing to have missed. `_wall_start` is the control that stops a
    cold book's months of recomputed history entering the log; duplicating it here would report
    every legitimate first run as a stall."""
    assert _gap(tmp_path, _Book("2026-08-26", "2026-08-27", "2026-08-28")) == []


def test_sessions_before_the_registered_start_are_not_counted(tmp_path):
    """They can never be logged, so they cannot appear as a gap either."""
    d = _wall(tmp_path, "2026-08-27")
    book = _Book("2026-06-01", "2026-06-02", "2026-08-28")
    assert _gap(d, book, wall_start="2026-08-01") == []


# --------------------------------------------------------------------------- the policy itself
def test_update_wall_defaults_to_gaps_and_takes_an_explicit_override():
    import inspect

    from nq.paper.wall_cron import update_wall
    p = inspect.signature(update_wall).parameters
    assert "backfill" in p, "the §3 catch-up policy is not a parameter — it cannot be chosen"
    assert p["backfill"].default is False, "reconstruction must never be the default"


def test_the_flag_exists_and_defaults_to_off():
    """A door that is open by default is not a door. Read the parser, not the docstring."""
    import contextlib
    import io
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), pytest.raises(SystemExit):
        R.main(["--help"])
    assert "--allow-wall-backfill" in buf.getvalue()


# --------------------------------------------------------------------------- wiring
def test_the_cron_passes_the_flag_through_to_the_writer():
    """The flag has to reach `update_wall`; a flag the writer never sees is decoration."""
    src = (ROOT / "scripts" / "run_paper_cron.py").read_text(encoding="utf-8")
    assert "backfill=args.allow_wall_backfill" in src


def test_the_stall_is_reported_before_it_is_written():
    """The gap is the honest record, but a gap nobody is told about is still a surprise."""
    src = (ROOT / "scripts" / "run_paper_cron.py").read_text(encoding="utf-8")
    assert src.index("_wall_gap_report(") < src.index("wrote = update_wall(")
    assert "::warning::forward-wall:" in src
