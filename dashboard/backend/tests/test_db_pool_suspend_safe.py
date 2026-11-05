"""The DB pool must survive the Fly machine's suspend/resume (2026-11-05 login outage).

A pooled socket open at suspend is dead on resume. Without recycling and TCP timeouts, pre_ping blocked
on it for ~15 minutes inside the event loop and froze the whole app.
"""
import database


def test_pool_recycles_connections_older_than_a_suspend():
    assert database.POOL_RECYCLE_S <= 600


def test_postgres_connections_fail_fast_on_a_dead_socket():
    a = database._PG_CONNECT_ARGS
    assert a["connect_timeout"] <= 15
    assert a["tcp_user_timeout"] <= 15_000
    assert a["keepalives"] == 1


def test_engine_uses_the_settings_when_configured():
    if database.engine is None:
        return
    assert database.engine.pool._recycle == database.POOL_RECYCLE_S
    assert database.engine.pool._pre_ping is True
