"""Tests for seed_users.py — Sprint 1 deliverable: three users bootstrap."""

from __future__ import annotations

from typing import Any

import pytest
from sqlalchemy.orm import Session

from database import User
from seed_users import seed_users


SPRINT_1_USERS: list[dict[str, Any]] = [
    {"email": "owner@example.com",  "password": "test-pw-owner",  "name": "Owner",  "is_admin": True},
    {"email": "dad@example.com",    "password": "test-pw-dad",    "name": "Dad",    "is_admin": False},
    {"email": "sister@example.com", "password": "test-pw-sister", "name": "Sister", "is_admin": False},
]


def test_seed_creates_three_users(
    engine: Any, db_session: Session
) -> None:
    """The canonical Sprint 1 bootstrap: one admin + two regular users."""
    summary = seed_users(SPRINT_1_USERS)
    assert len(summary) == 3
    assert {r["action"] for r in summary} == {"created"}
    assert [r["is_admin"] for r in summary] == [True, False, False]

    rows = db_session.query(User).order_by(User.id).all()
    assert [u.email for u in rows] == [
        "owner@example.com",
        "dad@example.com",
        "sister@example.com",
    ]
    assert [u.is_admin for u in rows] == [True, False, False]
    assert all(u.is_active for u in rows)


def test_seed_is_idempotent_on_rerun(
    engine: Any, db_session: Session
) -> None:
    """Re-running the seed with same emails updates, doesn't duplicate."""
    # First run — create
    seed_users(SPRINT_1_USERS)
    assert db_session.query(User).count() == 3

    # Second run — same emails, modified names
    modified = [dict(u, name=u["name"] + " v2") for u in SPRINT_1_USERS]
    summary = seed_users(modified)
    assert db_session.query(User).count() == 3, "seed duplicated users"
    assert {r["action"] for r in summary} == {"updated"}

    for u in db_session.query(User).all():
        assert u.name.endswith(" v2"), f"{u.email} name wasn't updated"


def test_seed_normalizes_email_to_lowercase(
    engine: Any, db_session: Session
) -> None:
    seed_users([
        {"email": "MixedCase@Example.COM", "password": "pw", "name": "X"}
    ])
    u = db_session.query(User).first()
    assert u is not None
    assert u.email == "mixedcase@example.com"


def test_seed_allows_login_with_seeded_password(
    engine: Any, db_session: Session, client: Any
) -> None:
    """End-to-end: seeded password hash should successfully authenticate
    via the real /auth/login endpoint."""
    seed_users([
        {"email": "logintest@example.com", "password": "my-secret-pw",
         "name": "Login Tester", "is_admin": False}
    ])

    r = client.post(
        "/api/auth/login",
        json={"email": "logintest@example.com", "password": "my-secret-pw"},
    )
    assert r.status_code == 200, (
        f"login failed: {r.status_code} {r.text[:200]}"
    )
    body = r.json()
    assert body["user"]["email"] == "logintest@example.com"
    assert body["user"]["is_admin"] is False


def test_seed_default_is_non_admin(
    engine: Any, db_session: Session
) -> None:
    """Omitting is_admin defaults to False — safety default."""
    seed_users([
        {"email": "noflag@example.com", "password": "pw", "name": "No Flag"}
    ])
    u = db_session.query(User).filter(User.email == "noflag@example.com").one()
    assert u.is_admin is False


def test_seed_all_three_users_can_authenticate_independently(
    engine: Any, db_session: Session, client: Any
) -> None:
    """After seeding, each of the three users can log in on their own
    — covers the Sprint 1 checkpoint deliverable end-to-end."""
    seed_users(SPRINT_1_USERS)

    for spec in SPRINT_1_USERS:
        r = client.post(
            "/api/auth/login",
            json={"email": spec["email"], "password": spec["password"]},
        )
        assert r.status_code == 200, (
            f"{spec['email']} login failed: {r.status_code} {r.text[:200]}"
        )
        user_block = r.json()["user"]
        assert user_block["email"] == spec["email"].lower()
        assert user_block["is_admin"] is spec["is_admin"]
