"""
Promote an existing user to admin and optionally set an admin password.

Usage:
    python -m src.scripts.promote_admin <email>
    python -m src.scripts.promote_admin <email> --set-password
"""
import sys
import getpass

from src.database.session import SessionLocal
from src.database.models import User
from src.auth.security import get_password_hash


def promote(email: str, set_password: bool = False) -> None:
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email).first()
        if not user:
            print(f"ERROR: No user found with email '{email}'")
            sys.exit(1)

        if set_password:
            password = getpass.getpass("Set admin password: ")
            confirm = getpass.getpass("Confirm password: ")
            if password != confirm:
                print("ERROR: Passwords do not match.")
                sys.exit(1)
            if len(password) < 8:
                print("ERROR: Password must be at least 8 characters.")
                sys.exit(1)
            user.hashed_password = get_password_hash(password)
            print(f"Password set for '{email}'.")

        user.is_admin = True
        db.commit()
        print(f"SUCCESS: '{email}' is now an admin. Login at /admin")
    finally:
        db.close()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python -m src.scripts.promote_admin <email> [--set-password]")
        sys.exit(1)

    email_arg = sys.argv[1]
    set_pw = "--set-password" in sys.argv
    promote(email_arg, set_pw)
