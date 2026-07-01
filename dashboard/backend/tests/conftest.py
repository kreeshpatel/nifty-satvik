"""Pytest config for dashboard/backend tests.

Sets up:
  * Stable env vars (JWT_SECRET, ENCRYPTION_KEY, DATABASE_URL -> sqlite)
  * Shared in-memory SQLite engine (StaticPool) so TestClient's threadpool
    sees the same DB as fixtures
  * Monkey-patch `database.engine` + `database.SessionLocal` so
    endpoints that use SessionLocal() directly (e.g. /ws) hit the
    test DB, not production Postgres
  * FastAPI TestClient wired to the real app
  * Factory fixtures for admin / non-admin users + auth cookies

Run:
  cd dashboard/backend && python -m pytest tests/

Not part of the root pytest run because the backend has its own
config.py shim + its own import layout. Keeping tests scoped here
avoids cross-contamination with the src/ test suite.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any, Generator

# --- Env vars must be set BEFORE importing any backend module -----
os.environ.setdefault("JWT_SECRET", "test-only-secret-do-not-use-in-prod")
# A valid Fernet key (32-byte url-safe base64); safe for tests.
os.environ.setdefault("ENCRYPTION_KEY", "JK7D4hZDdqKRZ2E6vR-5VQ4zPHpxnD_m0zBqUWJZbL8=")
# Any non-empty URL — we override the engine post-import anyway
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

# --- Make backend importable ---------------------------------------
BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker, Session  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

import database  # noqa: E402
from database import Base, User  # noqa: E402


# -------------------------------------------------------------------
# Shared in-memory engine: created ONCE per test, monkey-patched onto
# the database module so any `SessionLocal()` call (including the /ws
# handler's direct use) reaches the same in-memory DB.
# -------------------------------------------------------------------


@pytest.fixture
def engine() -> Generator[Any, None, None]:
    """Shared in-memory SQLite engine for the test's duration."""
    eng = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(eng)

    # Monkey-patch the database module so production code paths that
    # do `from database import SessionLocal` or `database.engine` hit
    # the in-memory engine. Restore afterwards for test isolation.
    prev_engine = database.engine
    prev_session = database.SessionLocal
    database.engine = eng
    database.SessionLocal = sessionmaker(
        autocommit=False, autoflush=False, bind=eng
    )
    try:
        yield eng
    finally:
        database.engine = prev_engine
        database.SessionLocal = prev_session
        Base.metadata.drop_all(eng)
        eng.dispose()


@pytest.fixture
def db_session(engine: Any) -> Generator[Session, None, None]:
    """SQLAlchemy Session wired to the in-memory engine."""
    TestingSession = sessionmaker(
        autocommit=False, autoflush=False, bind=engine
    )
    session = TestingSession()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client(engine: Any) -> Generator[TestClient, None, None]:
    """FastAPI TestClient with get_db + SessionLocal rewired to our engine."""
    # Import main AFTER the engine fixture has monkey-patched
    # database.SessionLocal so main.py's endpoints pick it up
    import main as app_module
    from database import get_db

    TestingSession = sessionmaker(
        autocommit=False, autoflush=False, bind=engine
    )

    def override_get_db() -> Generator[Session, None, None]:
        s = TestingSession()
        try:
            yield s
        finally:
            s.close()

    app_module.app.dependency_overrides[get_db] = override_get_db
    with TestClient(app_module.app) as c:
        yield c
    app_module.app.dependency_overrides.clear()


# -------------------------------------------------------------------
# User factory + auth-cookie helpers
# -------------------------------------------------------------------


def _hash_password(pw: str) -> str:
    from auth import pwd_context
    return pwd_context.hash(pw)


def _issue_access_cookie_value(user_id: int) -> str:
    """Mint an access JWT directly.

    We mint rather than going through /auth/login so tests skip the
    bcrypt round trip and don't need to track per-user passwords.
    """
    from jose import jwt
    from datetime import datetime, timedelta
    payload = {
        "sub": str(user_id),
        "exp": datetime.utcnow() + timedelta(minutes=15),
    }
    return jwt.encode(payload, os.environ["JWT_SECRET"], algorithm="HS256")


@pytest.fixture
def make_user(db_session: Session) -> Any:
    """Factory: make_user(name='A', is_admin=False) -> User.

    Creates a fresh User with a bcrypt-hashed password. Each call
    produces a unique email.
    """
    counter = {"n": 0}

    def _factory(name: str = "Test", is_admin: bool = False) -> User:
        counter["n"] += 1
        user = User(
            email=f"test-{counter['n']}-{name.lower()}@example.com",
            password_hash=_hash_password("password123"),
            name=name,
            is_active=True,
            is_admin=is_admin,
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        return user

    return _factory


@pytest.fixture
def auth_cookies() -> Any:
    """Factory: auth_cookies(user) -> {"nq_access": "<jwt>"}.

    Pass to TestClient calls as cookies=auth_cookies(user).
    """
    def _factory(user: User) -> dict[str, str]:
        token = _issue_access_cookie_value(user.id)
        return {"nq_access": token}

    return _factory
