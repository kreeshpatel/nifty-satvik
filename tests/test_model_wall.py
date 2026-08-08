"""Guards for :mod:`nq.paper.model_wall` — the independent second-model stream.

The load-bearing test is ``test_forward_wall_schema_is_untouched``: this module exists BECAUSE the
3-book wall's schema is pinned in ``forward/prereg.md §3``, so the whole design is void if adding it
perturbed that contract.

Tamper tests come in pairs — a mutation must be caught AND an untouched chain must verify — because
a guard that only ever fires, or only ever passes, is not a guard.
"""
from __future__ import annotations

import csv

import pytest

from nq.paper import forward_wall as fw
from nq.paper import model_wall as mw
from nq.paper.forward_wall import IntegrityError

MID = "stpivot-w1"


def _curve(n: int = 5, start_day: int = 2, eq0: float = 1_000_000.0):
    return [{"date": f"2026-08-{start_day + i:02d}", "equity": eq0 * (1 + 0.01 * i),
             "n_positions": 3 + i} for i in range(n)]


@pytest.fixture
def log(tmp_path):
    return tmp_path / f"model_wall_{MID}.csv"


# --------------------------------------------------------------------------- the contract guard
def test_forward_wall_schema_is_untouched():
    """The 3-book wall's pinned contract must be exactly as ``forward/prereg.md §3`` registered it."""
    assert fw.BOOKS == ("base", "veto", "drift")
    assert fw.DATA_FIELDS == ["date", "status",
                              "base_ret", "base_equity", "base_npos",
                              "veto_ret", "veto_equity", "veto_npos",
                              "drift_ret", "drift_equity", "drift_npos", "drift_mult"]
    assert fw.FIELDS == [*fw.DATA_FIELDS, "row_hash"]
    import hashlib
    assert fw.GENESIS == hashlib.sha256(
        b"nifty-satvik/forward-wall/genesis@dataset-pin-20260701").hexdigest()


def test_model_wall_writes_a_separate_file(tmp_path):
    """Off-is-inert: using the model wall must not create or touch forward_wall.csv."""
    mw.update_model_wall(_curve(), model_id=MID, initial_capital=1e6,
                         wall_start="2026-08-02", state_dir=tmp_path)
    assert (tmp_path / f"model_wall_{MID}.csv").exists()
    assert not (tmp_path / "forward_wall.csv").exists()


# --------------------------------------------------------------------------- chain integrity
def test_chain_verifies_after_append(log):
    mw.update_model_wall(_curve(), model_id=MID, initial_capital=1e6,
                         wall_start="2026-08-02", path=log)
    rows = mw.read_verified(MID, path=log)
    assert len(rows) == 5
    ok, bad = mw.verify_chain(rows, MID)
    assert ok and bad == -1


def test_mutated_row_is_caught(log):
    mw.update_model_wall(_curve(), model_id=MID, initial_capital=1e6,
                         wall_start="2026-08-02", path=log)
    rows = list(csv.DictReader(log.open(encoding="utf-8")))
    rows[2]["equity"] = "999999.99"
    with log.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=mw.FIELDS)
        w.writeheader()
        w.writerows(rows)
    ok, bad = mw.verify_chain(list(csv.DictReader(log.open(encoding="utf-8"))), MID)
    assert not ok and bad == 2
    with pytest.raises(IntegrityError):
        mw.read_verified(MID, path=log)


def test_reordered_rows_are_caught(log):
    """Position-sensitive: each hash binds its predecessor."""
    mw.update_model_wall(_curve(), model_id=MID, initial_capital=1e6,
                         wall_start="2026-08-02", path=log)
    rows = list(csv.DictReader(log.open(encoding="utf-8")))
    rows[1], rows[2] = rows[2], rows[1]
    ok, _ = mw.verify_chain(rows, MID)
    assert not ok


def test_back_dating_and_double_run_are_refused(log):
    mw.update_model_wall(_curve(3), model_id=MID, initial_capital=1e6,
                         wall_start="2026-08-02", path=log)
    with pytest.raises(IntegrityError, match="no back-dating"):
        mw.append_row({"date": "2026-08-03", "status": "ok", "ret": 0.0,
                       "equity": 1e6, "npos": 1}, MID, path=log)


def test_genesis_is_per_model_so_streams_cannot_be_spliced(log, tmp_path):
    """A row lifted from one model's log must not verify inside another's."""
    assert mw.model_genesis("A") != mw.model_genesis("B")
    mw.update_model_wall(_curve(3), model_id="A", initial_capital=1e6,
                         wall_start="2026-08-02", state_dir=tmp_path)
    rows = list(csv.DictReader((tmp_path / "model_wall_A.csv").open(encoding="utf-8")))
    assert mw.verify_chain(rows, "A")[0]
    assert not mw.verify_chain(rows, "B")[0], "chains must not be transplantable between models"


def test_gap_row_hashes_into_the_chain(log):
    mw.update_model_wall(_curve(2), model_id=MID, initial_capital=1e6,
                         wall_start="2026-08-02", path=log)
    mw.append_row(mw.gap_row("2026-08-10"), MID, path=log)
    rows = mw.read_verified(MID, path=log)
    assert rows[-1]["status"] == "gap" and rows[-1]["equity"] == ""


# --------------------------------------------------------------------------- the wall_start bound
def test_wall_start_is_required():
    """A new stream has no legacy caller to preserve, so the strict default is the safe one."""
    with pytest.raises(ValueError, match="wall_start is required"):
        mw.update_model_wall(_curve(), model_id=MID, initial_capital=1e6, wall_start="")


def test_sessions_before_wall_start_never_enter_the_log(log):
    """Recomputed history must not become forward evidence (forward/prereg.md §3)."""
    n = mw.update_model_wall(_curve(5, start_day=2), model_id=MID, initial_capital=1e6,
                             wall_start="2026-08-04", path=log)
    rows = mw.read_verified(MID, path=log)
    assert n == 3
    assert [r["date"] for r in rows] == ["2026-08-04", "2026-08-05", "2026-08-06"]


def test_resume_appends_only_new_sessions(log):
    mw.update_model_wall(_curve(3), model_id=MID, initial_capital=1e6,
                         wall_start="2026-08-02", path=log)
    n = mw.update_model_wall(_curve(5), model_id=MID, initial_capital=1e6,
                             wall_start="2026-08-02", path=log)
    assert n == 2
    assert len(mw.read_verified(MID, path=log)) == 5


def test_returns_are_computed_against_the_prior_nav_including_skipped_sessions(log):
    """A session skipped by wall_start still advances the NAV baseline, so the first logged return
    is not silently measured from initial capital."""
    mw.update_model_wall(_curve(5, start_day=2), model_id=MID, initial_capital=1e6,
                         wall_start="2026-08-04", path=log)
    first = mw.read_verified(MID, path=log)[0]
    # equity on 08-04 is 1.02e6 and on 08-03 was 1.01e6 -> ret = 1.02/1.01 - 1
    assert float(first["ret"]) == pytest.approx(1.02 / 1.01 - 1.0, abs=1e-8)


def test_empty_curve_is_a_noop(log):
    assert mw.update_model_wall([], model_id=MID, initial_capital=1e6,
                                wall_start="2026-08-02", path=log) == 0
    assert not log.exists()
