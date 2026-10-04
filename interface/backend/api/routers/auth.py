import secrets
import time
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.concurrency import run_in_threadpool

from interface.backend.config import get_settings
from interface.backend.db.models.tables import AuthSession, User
from interface.backend.db.session import get_session
from interface.backend.schemas.auth import LoginRequest, UserOut
from interface.backend.services.auth_service import (
    COOKIE,
    check_origin,
    current_user,
    find_user,
    hash_password,
    token_hash,
    verify_password,
)

router = APIRouter(prefix="/auth", tags=["auth"])
# Per-worker limiter; deploy a shared gateway limiter when running multiple workers.
_attempts: dict[str, list[float]] = {}
_dummy_hash = hash_password(secrets.token_urlsafe(32))


def user_out(user: User) -> UserOut:
    return UserOut(id=user.id, email=user.email, name=user.name, role=user.role)


@router.post("/login", response_model=UserOut)
async def login(payload: LoginRequest, request: Request, response: Response,
                db: AsyncSession = Depends(get_session)):
    check_origin(request)
    now = time.monotonic()
    for stale in [key for key, values in _attempts.items() if not values or values[-1] < now - 600]:
        del _attempts[stale]
    key = request.client.host if request.client else "unknown"
    attempts = [t for t in _attempts.get(key, []) if t > now - 600]
    if len(attempts) >= 20 or (key not in _attempts and len(_attempts) >= 5000):
        raise HTTPException(429, "Đăng nhập quá nhiều lần. Vui lòng thử lại sau 10 phút.", headers={"Retry-After": "600"})
    _attempts[key] = attempts + [now]
    user = await find_user(db, payload.email)
    valid = await run_in_threadpool(verify_password, payload.password, user.password_hash if user else _dummy_hash)
    if not user or not valid or not user.active:
        raise HTTPException(401, "Email hoặc mật khẩu không đúng")
    old = request.cookies.get(COOKIE)
    if old:
        await db.execute(delete(AuthSession).where(AuthSession.token_hash == token_hash(old)))
    await db.execute(delete(AuthSession).where(AuthSession.expires_at <= datetime.now(UTC)))
    token = secrets.token_urlsafe(48)
    lifetime = 30 * 86400 if payload.remember else 8 * 3600
    db.add(AuthSession(token_hash=token_hash(token), user_id=user.id,
                       expires_at=datetime.now(UTC) + timedelta(seconds=lifetime)))
    await db.commit()
    response.set_cookie(COOKIE, token, httponly=True, samesite="lax", path="/api/v1",
                        secure=get_settings().app_env == "production",
                        max_age=lifetime if payload.remember else None)
    response.headers["Cache-Control"] = "no-store"
    return user_out(user)


@router.get("/me", response_model=UserOut)
async def me(response: Response, user: User = Depends(current_user)):
    response.headers["Cache-Control"] = "no-store"
    return user_out(user)


@router.post("/logout", status_code=204)
async def logout(request: Request, db: AsyncSession = Depends(get_session)):
    check_origin(request)
    token = request.cookies.get(COOKIE)
    if token:
        await db.execute(delete(AuthSession).where(AuthSession.token_hash == token_hash(token)))
        await db.commit()
    response = Response(status_code=204)
    response.delete_cookie(COOKIE, path="/api/v1", httponly=True, samesite="lax",
                           secure=get_settings().app_env == "production")
    return response
