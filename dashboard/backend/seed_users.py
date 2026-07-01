"""Bootstrap N users in bulk — Sprint 1 multi-user seeding helper.

Usage (CLI):
    python seed_users.py --config users.json

Usage (env var with JSON inline):
    SEED_USERS_JSON='[{"email":"you@x.com","password":"...","name":"Me","is_admin":true},...]' \
      python seed_users.py

Example users.json:
    [
      {"email": "me@example.com",    "password": "a-strong-pw", "name": "Me",     "is_admin": true},
      {"email": "dad@example.com",   "password": "a-strong-pw", "name": "Dad",    "is_admin": false},
      {"email": "sister@example.com","password": "a-strong-pw", "name": "Sister", "is_admin": false}
    ]

Idempotent: existing users are updated (password, admin status, active
flag) rather than duplicated. Emails are normalized to lowercase.

For the bootstrap admin user, prefer `create_admin.py` — it's the
older, specialized tool. This script is the multi-user version that
matches Sprint 1's "admin creates three test users" deliverable.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any


def seed_users(users: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Create or update the given users. Returns a summary list.

    Each summary row: {"email", "id", "action": "created"|"updated",
    "is_admin": bool}. Password is never echoed back.
    """
    from database import Base, SessionLocal, User, engine
    from passlib.context import CryptContext

    if not engine:
        raise RuntimeError(
            "DATABASE_URL is not configured. Set it in env before seeding."
        )

    Base.metadata.create_all(bind=engine)
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

    summary: list[dict[str, Any]] = []
    db = SessionLocal()
    try:
        for spec in users:
            email = str(spec["email"]).lower().strip()
            name = str(spec.get("name", "")).strip() or email
            password = str(spec["password"])
            is_admin = bool(spec.get("is_admin", False))

            existing = db.query(User).filter(User.email == email).first()
            if existing:
                existing.password_hash = pwd_context.hash(password)
                existing.name = name
                existing.is_admin = is_admin
                existing.is_active = True
                existing.failed_login_attempts = 0
                existing.locked_until = None
                db.commit()
                summary.append({
                    "email": email, "id": existing.id,
                    "action": "updated", "is_admin": is_admin,
                })
                continue

            user = User(
                email=email,
                password_hash=pwd_context.hash(password),
                name=name,
                is_admin=is_admin,
                is_active=True,
            )
            db.add(user)
            db.commit()
            db.refresh(user)
            summary.append({
                "email": email, "id": user.id,
                "action": "created", "is_admin": is_admin,
            })
    finally:
        db.close()
    return summary


def _load_from_args() -> list[dict[str, Any]]:
    """Resolve the seed list from CLI args or env vars.

    Prefers --config file, then SEED_USERS_JSON env var. Errors out
    with a clear message if neither is provided.
    """
    parser = argparse.ArgumentParser(description="Seed multi-user accounts")
    parser.add_argument(
        "--config", default="",
        help="Path to JSON file with list of {email,password,name,is_admin}",
    )
    args = parser.parse_args()

    raw: str
    if args.config:
        with open(args.config, "r", encoding="utf-8") as f:
            raw = f.read()
    else:
        raw = os.getenv("SEED_USERS_JSON", "")

    if not raw:
        print(
            "No seed config provided. Pass --config users.json or set "
            "SEED_USERS_JSON env var to a JSON array."
        )
        sys.exit(1)

    try:
        users = json.loads(raw)
    except json.JSONDecodeError as e:
        print(f"Failed to parse JSON: {e}")
        sys.exit(1)

    if not isinstance(users, list):
        print("Seed config must be a JSON array of user objects.")
        sys.exit(1)

    return users


if __name__ == "__main__":
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass

    spec = _load_from_args()
    summary = seed_users(spec)
    print(f"Seeded {len(summary)} users:")
    for row in summary:
        tier = "ADMIN" if row["is_admin"] else "user"
        print(f"  [{row['action']:>7}] {row['email']:<40} id={row['id']:>3}  {tier}")
