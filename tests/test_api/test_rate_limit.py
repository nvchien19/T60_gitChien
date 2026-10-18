"""Giới hạn số lần gọi API có LLM theo tài khoản."""

import pytest
from fastapi import HTTPException

from interface.backend.services.rate_limit import PerUserLimit, chat_limit


def test_limit_blocks_then_recovers_after_window():
    limit = PerUserLimit("thử", limit=2, window=60)
    limit.hit(1, now=0)
    limit.hit(1, now=1)
    with pytest.raises(HTTPException) as err:
        limit.hit(1, now=2)
    assert err.value.status_code == 429
    assert err.value.headers["Retry-After"] == "59"
    limit.hit(2, now=2)  # tài khoản khác không bị ảnh hưởng
    limit.hit(1, now=61)  # lần gọi lúc 0 đã ra khỏi cửa sổ


@pytest.mark.asyncio
async def test_chat_endpoint_returns_429_when_over_limit(client):
    me = await client.get("/api/v1/auth/me")
    for _ in range(chat_limit.limit):
        chat_limit.hit(me.json()["id"])
    res = await client.post("/api/v1/assistant/chat", json={"message": "Vì sao có tương tác?"})
    assert res.status_code == 429
    assert "Retry-After" in res.headers


@pytest.mark.asyncio
async def test_security_headers(client):
    res = await client.get("/health")
    assert res.headers["X-Content-Type-Options"] == "nosniff"
    assert res.headers["X-Frame-Options"] == "DENY"
    assert res.headers["Referrer-Policy"] == "no-referrer"
