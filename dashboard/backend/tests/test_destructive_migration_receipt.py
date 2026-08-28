"""A destructive migration must log how much it destroyed, through a channel someone reads.

**Why this file exists.** `user_holdings` was dropped on 2026-08-28 with what was meant to be a
receipt: a `RAISE NOTICE` inside a `DO $$ ... $$` block reporting the row count. Postgres sends
notices on the CLIENT channel — psycopg2 stashes them on `connection.notices` and SQLAlchemy logs
nothing — so the line never reached the app log. The drop itself worked; the evidence of what it
cost did not, and for a destructive migration that evidence cannot be reconstructed afterwards.

The deeper cause is that the migration helpers lived nested inside `init_db()`, where nothing
could import them and therefore nothing tested them. They are module-level now, and this file is
the test that would have caught it: it asserts the count reaches the logger, not merely that the
SQL ran.
"""
from __future__ import annotations

import logging

import pytest
from sqlalchemy import text


@pytest.fixture()
def scratch_table(db_session):
    """A throwaway table with three rows, on the test engine."""
    import database as db

    with db.engine.begin() as conn:
        conn.execute(text("DROP TABLE IF EXISTS receipt_probe"))
        conn.execute(text("CREATE TABLE receipt_probe (id INTEGER PRIMARY KEY, v TEXT)"))
        conn.execute(text("INSERT INTO receipt_probe (id, v) VALUES (1,'a'),(2,'b'),(3,'c')"))
    yield "receipt_probe"
    with db.engine.begin() as conn:
        conn.execute(text("DROP TABLE IF EXISTS receipt_probe"))


def test_counts_the_rows_it_is_about_to_destroy(scratch_table):
    import database as db

    assert db._count_rows(scratch_table) == 3


def test_an_absent_table_counts_as_none_not_zero(db_session):
    """None and 0 are different facts: "there was nothing to lose" versus "we could not look".
    Collapsing them is how a failed count reads as an empty table."""
    import database as db

    assert db._count_rows("table_that_never_existed") is None


def test_the_count_reaches_the_LOGGER_before_the_drop(scratch_table, caplog):
    """The whole point. Not "did the SQL run" — did the number reach a channel someone reads."""
    import database as db

    with caplog.at_level(logging.INFO, logger="niftyquant.db_migration"):
        db._run_destructive_migration(
            "receipt_probe_drop", scratch_table, f"DROP TABLE IF EXISTS {scratch_table}")

    receipt = [r for r in caplog.records if "destroying them now" in r.getMessage()]
    assert receipt, f"no destruction receipt logged; saw {[r.getMessage() for r in caplog.records]}"
    assert "3 row(s)" in receipt[0].getMessage()
    # WARNING, not INFO: this is the one migration class that cannot be re-run to find out.
    assert receipt[0].levelno == logging.WARNING
    assert db._count_rows(scratch_table) is None          # and it actually dropped


def test_an_empty_table_is_reported_without_alarming(db_session, caplog):
    import database as db

    with db.engine.begin() as conn:
        conn.execute(text("DROP TABLE IF EXISTS receipt_empty"))
        conn.execute(text("CREATE TABLE receipt_empty (id INTEGER PRIMARY KEY)"))
    with caplog.at_level(logging.INFO, logger="niftyquant.db_migration"):
        db._run_destructive_migration(
            "receipt_empty_drop", "receipt_empty", "DROP TABLE IF EXISTS receipt_empty")

    assert any("is empty" in r.getMessage() for r in caplog.records)
    assert not any(r.levelno >= logging.WARNING for r in caplog.records)


def test_a_table_name_that_is_not_an_identifier_is_refused(db_session):
    """The name is interpolated into SQL that no bind parameter can carry, so the guard is the
    only thing between this helper and an injection if a caller ever stops being a literal."""
    import database as db

    assert db._count_rows("users; DROP TABLE users") is None
    assert db._count_rows("") is None
