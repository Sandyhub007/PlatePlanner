from sqladmin.authentication import AuthenticationBackend
from starlette.requests import Request

from src.database.session import SessionLocal
from src.database.models import User
from src.auth.security import verify_password


class AdminAuthBackend(AuthenticationBackend):
    """Session-based admin authentication for sqladmin."""

    async def login(self, request: Request) -> bool:
        form = await request.form()
        email = form.get("username", "")
        password = form.get("password", "")

        db = SessionLocal()
        try:
            user = db.query(User).filter(User.email == email).first()
            if not user:
                return False
            if not user.hashed_password or not verify_password(password, user.hashed_password):
                return False
            if not getattr(user, "is_admin", False):
                return False

            request.session.update({"admin_email": user.email})
            return True
        finally:
            db.close()

    async def logout(self, request: Request) -> bool:
        request.session.clear()
        return True

    async def authenticate(self, request: Request) -> bool:
        admin_email = request.session.get("admin_email")
        if not admin_email:
            return False

        db = SessionLocal()
        try:
            user = db.query(User).filter(
                User.email == admin_email,
                User.is_admin == True,
                User.is_active == True,
            ).first()
            return user is not None
        finally:
            db.close()
