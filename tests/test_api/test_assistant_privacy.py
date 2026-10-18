import pytest
from sqlalchemy import update

from interface.backend.db.models.tables import Check
from interface.backend.db.session import get_session
from interface.backend.main import app
from interface.backend.services.assistant_service import safe_url


@pytest.mark.asyncio
async def test_sensitive_evidence_not_returned_even_in_fallback(client, monkeypatch):
    from unittest.mock import AsyncMock

    from interface.backend.services import assistant_service

    fake = AsyncMock()
    monkeypatch.setattr(assistant_service, "explain", fake)
    rx = (await client.post("/api/v1/prescriptions", json={"medications": [
        {"name": "warfarin"}, {"name": "aspirin"}]})).json()["id"]
    check_id = (await client.post(f"/api/v1/prescriptions/{rx}/checks")).json()["check_id"]
    async for db in app.dependency_overrides[get_session]():
        check = await db.get(Check, check_id)
        data = dict(check.result)
        finding = dict(data["findings"][0])
        finding["mechanism"] = "Patient name: Nguyen Van A, private@example.com 0901234567"
        data["findings"] = [finding]
        await db.execute(update(Check).where(Check.id == check_id).values(result=data))
        await db.commit()
    result = await client.post("/api/v1/assistant/chat", json={
        "prescription_id": rx, "check_id": check_id, "message": "giải thích"})
    assert result.status_code == 200 and not result.json()["findings"]
    assert "private@example.com" not in result.text and "Nguyen Van A" not in result.text
    assert not result.json()["llm_used"]
    fake.assert_not_awaited()


@pytest.mark.parametrize("url", [
    "https://source.example/path?token=secret",
    "https://user:password@source.example/path",
    "javascript:alert(1)", "https://source.example/#credential",
])
def test_citation_url_excludes_credentials(url):
    assert safe_url(url) == ""
