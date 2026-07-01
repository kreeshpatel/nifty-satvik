"""
Create the first admin user. Run once after deploy:

    python create_admin.py --email you@example.com --password yourpassword --name "Your Name"

Or set env vars:
    ADMIN_EMAIL=you@example.com ADMIN_PASSWORD=secret ADMIN_NAME="Your Name" python create_admin.py
"""

import os
import sys
import argparse
from dotenv import load_dotenv

load_dotenv()

from database import engine, Base, SessionLocal, User
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def create_admin(email: str, password: str, name: str):
    if not engine:
        print("ERROR: DATABASE_URL not set")
        sys.exit(1)

    # Create tables if they don't exist
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        existing = db.query(User).filter(User.email == email.lower().strip()).first()
        if existing:
            # Reset password and ensure admin status (idempotent)
            existing.password_hash = pwd_context.hash(password)
            existing.is_admin = True
            existing.is_active = True
            existing.failed_login_attempts = 0
            existing.locked_until = None
            db.commit()
            print(f"Admin {email} updated — password reset, admin status confirmed.")
            return

        user = User(
            email=email.lower().strip(),
            password_hash=pwd_context.hash(password),
            name=name.strip(),
            is_admin=True,
            is_active=True,
        )
        db.add(user)
        db.commit()
        print(f"Admin created: {email} (id={user.id})")
    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Create admin user")
    parser.add_argument("--email", default=os.getenv("ADMIN_EMAIL", ""))
    parser.add_argument("--password", default=os.getenv("ADMIN_PASSWORD", ""))
    parser.add_argument("--name", default=os.getenv("ADMIN_NAME", "Admin"))
    args = parser.parse_args()

    if not args.email or not args.password:
        print("Usage: python create_admin.py --email you@example.com --password secret --name 'Your Name'")
        sys.exit(1)

    create_admin(args.email, args.password, args.name)
