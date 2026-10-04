"""Password hashing and opaque server-side sessions."""
import hashlib
import hmac
import secrets
from datetime import UTC, datetime
from urllib.parse import urlsplit

from fastapi import Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from interface.backend.config import get_settings
from interface.backend.db.models.tables import AuthSession, User
from interface.backend.db.session import get_session

COOKIE = "medication_session"


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt),
                            n=32768, r=8, p=1, maxmem=64 * 1024 * 1024).hex()
    return f"scrypt${salt}${digest}"


def verify_password(password: str, encoded: str) -> bool:
    try:
        algorithm, salt, digest = encoded.split("$")
        if algorithm != "scrypt":
            return False
        candidate = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt),
                                   n=32768, r=8, p=1, maxmem=64 * 1024 * 1024).hex()
        return hmac.compare_digest(candidate, digest)
    except (ValueError, TypeError):
        return False


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def check_origin(request: Request):
    if request.method in {"GET", "HEAD", "OPTIONS"}:
        return
    origin = request.headers.get("origin")
    allowed = {x.strip().rstrip("/") for x in get_settings().cors_origins.split(",")}
    base = urlsplit(str(request.base_url))
    allowed.add(f"{base.scheme}://{base.netloc}")
    if request.headers.get("sec-fetch-site") == "cross-site" or (origin and origin.rstrip("/") not in allowed):
        raise HTTPException(403, "Nguồn yêu cầu không được phép")


async def current_user(request: Request, db: AsyncSession = Depends(get_session)) -> User:
    check_origin(request)
    token = request.cookies.get(COOKIE, "")
    session = await db.get(AuthSession, token_hash(token)) if token else None
    if not session:
        raise HTTPException(401, "Vui lòng đăng nhập để tiếp tục")
    expiry = session.expires_at
    if expiry.tzinfo is None:
        expiry = expiry.replace(tzinfo=UTC)
    if expiry <= datetime.now(UTC):
        raise HTTPException(401, "Phiên đăng nhập đã hết hạn")
    user = await db.get(User, session.user_id)
    if not user or not user.active:
        raise HTTPException(401, "Tài khoản không khả dụng")
    return user


async def pharmacist(user: User = Depends(current_user)) -> User:
    if user.role != "pharmacist":
        raise HTTPException(403, "Chức năng này dành cho dược sĩ")
    return user


async def doctor(user: User = Depends(current_user)) -> User:
    if user.role != "doctor":
        raise HTTPException(403, "Chức năng này dành cho bác sĩ")
    return user


async def find_user(db: AsyncSession, email: str) -> User | None:
    return (await db.execute(select(User).where(User.email == email.strip().lower()))).scalar_one_or_none()
