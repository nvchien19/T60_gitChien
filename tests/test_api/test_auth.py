"""Authentication, cookie lifetime and server-enforced role isolation."""
import sqlite3

import pytest

from interface.backend.api.routers.auth import _attempts
from interface.backend.services.auth_service import COOKIE, token_hash

PASSWORD = "Test-password-123"


async def login(client, email, **extra):
    return await client.post("/api/v1/auth/login", json={"email": email, "password": PASSWORD, **extra})


@pytest.mark.asyncio
async def test_login_session_and_logout(client):
    old_token = client.cookies.get(COOKIE)
    client.cookies.clear()
    for path in ["/prescriptions", "/reviews", "/drugs/search", "/sources"]:
        assert (await client.get("/api/v1" + path)).status_code == 401
    assert (await client.get("/health")).status_code == 200
    wrong = await client.post("/api/v1/auth/login", json={"email": "pharmacist@test.vn", "password": "wrong"})
    assert wrong.status_code == 401
    result = await login(client, "PHARMACIST@test.vn", remember=True)
    assert result.status_code == 200
    assert result.json()["role"] == "pharmacist"
    assert "password_hash" not in result.json()
    cookie = result.headers["set-cookie"].lower()
    assert "httponly" in cookie and "samesite=lax" in cookie and "max-age=2592000" in cookie
    token = client.cookies.get(COOKIE)
    assert token != old_token
    assert (await client.get("/api/v1/auth/me")).json()["name"] == "Dược sĩ Test"
    assert (await client.post("/api/v1/auth/logout")).status_code == 204
    client.cookies.set(COOKIE, token, path="/api/v1")
    assert (await client.get("/api/v1/auth/me")).status_code == 401
    client.cookies.clear()
    normal = await login(client, "pharmacist@test.vn")
    assert "max-age" not in normal.headers["set-cookie"].lower()
    token = client.cookies.get(COOKIE)
    with sqlite3.connect("data/test_be.db") as db:
        db.execute("UPDATE auth_sessions SET expires_at='2000-01-01' WHERE token_hash=?", (token_hash(token),))
    assert (await client.get("/api/v1/auth/me")).status_code == 401


@pytest.mark.asyncio
async def test_role_permissions_and_review_round_trip(client):
    rx = (await client.post("/api/v1/prescriptions")).json()["id"]
    result = await client.post("/api/v1/reviews", json={"prescription_id": rx, "message": "Xin bác sĩ xem xét"})
    assert result.status_code == 201
    review_id = result.json()["review_id"]
    patch = {"status": "Đã phản hồi", "response": "Rà soát liều và theo dõi."}
    assert (await client.patch(f"/api/v1/reviews/{review_id}", json=patch)).status_code == 403
    assert (await client.post("/api/v1/reviews", json={"prescription_id": rx, "message": "  "})).status_code == 422
    assert (await login(client, "other@test.vn")).status_code == 200
    assert not (await client.get("/api/v1/reviews", params={"prescription_id": rx})).json()["items"]
    assert (await login(client, "doctor@test.vn")).status_code == 200
    reviews = (await client.get("/api/v1/reviews", params={"prescription_id": rx})).json()["items"]
    assert reviews[0]["creator_name"] == "Dược sĩ Test"
    assert (await client.get(f"/api/v1/prescriptions/{rx}")).status_code == 200
    # Doctors have the same prescription/check capabilities as pharmacists.
    created = await client.post("/api/v1/prescriptions", json={
        "name": "Doctor prescription", "medications": [{"name": "Warfarin"}, {"name": "Aspirin"}],
    })
    assert created.status_code == 201
    doctor_rx = created.json()["id"]
    added = await client.post(f"/api/v1/prescriptions/{doctor_rx}/medications", json={"name": "Warfarin"})
    assert added.status_code == 201
    medications = created.json()["medications"]
    edited = await client.put(f"/api/v1/prescriptions/{doctor_rx}/medications", json=[
        {"id": med["id"], "name": med["name"], "dose": "5 mg"} for med in medications
    ])
    assert edited.status_code == 200
    assert len(edited.json()) == 2
    assert (await client.post(f"/api/v1/prescriptions/{doctor_rx}/checks")).status_code == 201
    assert (await client.get(f"/api/v1/prescriptions/{doctor_rx}/checks")).json()["items"]
    assert (await client.post("/api/v1/reviews", json={"prescription_id": rx, "message": "New"})).status_code == 403
    assert (await client.patch(f"/api/v1/reviews/{review_id}", json={"status": "Đã phản hồi", "response": "  "})).status_code == 422
    answered = await client.patch(f"/api/v1/reviews/{review_id}", json=patch)
    assert answered.status_code == 200
    assert answered.json()["responder_name"] == "Bác sĩ Test"
    assert answered.json()["responded_at"]
    await login(client, "pharmacist@test.vn")
    reviews = (await client.get("/api/v1/reviews", params={"prescription_id": rx})).json()["items"]
    assert reviews[0]["response"] == patch["response"]
    assert reviews[0]["status"] == "Đã phản hồi"


@pytest.mark.asyncio
async def test_csrf_rate_limit_disabled_user(client):
    blocked = await client.post("/api/v1/auth/logout", headers={"origin": "https://attacker.example"})
    assert blocked.status_code == 403
    assert (await client.get("/api/v1/auth/me")).status_code == 200
    token = client.cookies.get(COOKIE)
    with sqlite3.connect("data/test_be.db") as db:
        db.execute("UPDATE users SET active=0 WHERE email='pharmacist@test.vn'")
    try:
        assert (await client.get("/api/v1/auth/me")).status_code == 401
        assert (await login(client, "pharmacist@test.vn")).status_code == 401
    finally:
        with sqlite3.connect("data/test_be.db") as db:
            db.execute("UPDATE users SET active=1 WHERE email='pharmacist@test.vn'")
    _attempts.clear()
    for _ in range(20):
        assert (await client.post("/api/v1/auth/login", json={"email": "missing@test.vn", "password": "wrong"})).status_code == 401
    assert (await login(client, "doctor@test.vn")).status_code == 429
    with sqlite3.connect("data/test_be.db") as db:
        row = db.execute("SELECT token_hash FROM auth_sessions WHERE token_hash=?", (token_hash(token),)).fetchone()
    assert row and row[0] != token


@pytest.mark.asyncio
async def test_account_management_revokes_sessions(client, monkeypatch):
    from argparse import Namespace

    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    from scripts import manage_users

    engine = create_async_engine("sqlite+aiosqlite:///data/test_be.db")
    monkeypatch.setattr(manage_users, "SessionLocal", async_sessionmaker(engine, expire_on_commit=False))
    monkeypatch.setattr(manage_users, "getpass", lambda _: PASSWORD)
    email = "managed@test.vn"
    try:
        await manage_users.manage(Namespace(action="create", email=email, name="Managed Doctor", role="doctor"))
        assert (await login(client, email)).status_code == 200
        assert (await client.get("/api/v1/auth/me")).json()["role"] == "doctor"
        await manage_users.manage(Namespace(action="reset-password", email=email))
        assert (await client.get("/api/v1/auth/me")).status_code == 401
        await login(client, email)
        await manage_users.manage(Namespace(action="disable", email=email))
        assert (await client.get("/api/v1/auth/me")).status_code == 401
        assert (await login(client, email)).status_code == 401
    finally:
        await engine.dispose()
