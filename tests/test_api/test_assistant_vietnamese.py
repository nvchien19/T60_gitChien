import pytest
import pytest_asyncio
from sqlalchemy import delete

from interface.backend.db.models.tables import Check, ContentTranslation, FdaLabel
from interface.backend.db.session import get_session
from interface.backend.main import app
from interface.backend.repositories.translations import source_hash
from interface.backend.services import assistant_service

SET_ID = "baf998de-78ac-4bbc-99ab-940d737c2dc5"
ORIGINAL = "Do not use with a documented allergy."
VI = "Chống chỉ định khi có dị ứng đã được ghi nhận."


@pytest_asyncio.fixture
async def stored_label(client):
    async for db in app.dependency_overrides[get_session]():
        db.add(FdaLabel(label_set_id=SET_ID, brand_names="Keytruda", drug_ids=[],
                        contraindications=ORIGINAL, source_id="openfda"))
        db.add(ContentTranslation(source_table="fda_labels", source_id=SET_ID,
                                  field="contraindications", language="vi",
                                  source_hash=source_hash(ORIGINAL), translated_text=VI,
                                  provider="test", reviewed=False))
        await db.commit()
    yield
    async for db in app.dependency_overrides[get_session]():
        await db.execute(delete(ContentTranslation).where(ContentTranslation.source_id == SET_ID))
        await db.execute(delete(FdaLabel).where(FdaLabel.label_set_id == SET_ID))
        await db.commit()


@pytest.mark.asyncio
@pytest.mark.parametrize("detail", ["brief", "expanded"])
async def test_stored_vietnamese_before_api(client, stored_label, monkeypatch, detail):
    async def forbidden(*args, **kwargs):
        pytest.fail("Stored translated label must win over external API")
    monkeypatch.setattr(assistant_service, "label_reply", forbidden)
    data = (await client.post("/api/v1/assistant/chat", json={
        "message": "Tra cứu thuốc Keytruda", "detail": detail})).json()
    assert data["status"] == "answered" and VI in data["reply"]
    assert ORIGINAL not in data["reply"] and "bản dịch máy đã lưu" in data["reply"]
    assert "Chống chỉ định:\n" in data["reply"] and "\n\n" in data["reply"]
    assert data["citations"][0]["source_id"] == "openfda"
    assert not data["findings"]


@pytest.mark.asyncio
async def test_stale_translation_not_used(client, stored_label, monkeypatch):
    from interface.backend.config import get_settings
    monkeypatch.setattr(get_settings(), "deepseek_api_key", "")
    async for db in app.dependency_overrides[get_session]():
        row = await db.get(FdaLabel, SET_ID)
        row.contraindications = "Updated source contraindication."
        await db.commit()
    data = (await client.post("/api/v1/assistant/chat", json={
        "message": "Chống chỉ định của thuốc Keytruda"})).json()
    assert VI not in data["reply"] and "Updated source contraindication" not in data["reply"]
    assert "chưa có bản dịch tiếng Việt đã kiểm chứng" in data["reply"]
    assert data["status"] == "no_evidence"


@pytest.mark.asyncio
async def test_missing_topic_falls_back_not_unrelated_local_text(client, stored_label, monkeypatch):
    calls = []
    async def external(names, message, unsafe, detail):
        calls.extend(names)
        return "Trích đoạn chỉ định từ nguồn ngoài.", [], True
    monkeypatch.setattr(assistant_service, "label_reply", external)
    data = (await client.post("/api/v1/assistant/chat", json={
        "message": "Thuốc Keytruda có tác dụng gì?"})).json()
    assert calls == ["Keytruda"] and VI not in data["reply"]


@pytest.mark.asyncio
async def test_explanation_prefers_translated_management(client, monkeypatch):
    from interface.backend.config import get_settings
    monkeypatch.setattr(get_settings(), "deepseek_api_key", "")
    rx = (await client.post("/api/v1/prescriptions", json={"medications": [
        {"name": "warfarin"}, {"name": "aspirin"}]})).json()["id"]
    check_id = (await client.post(f"/api/v1/prescriptions/{rx}/checks")).json()["check_id"]
    async for db in app.dependency_overrides[get_session]():
        check = await db.get(Check, check_id)
        result = dict(check.result)
        rows = [dict(row) for row in result["findings"]]
        rows[0]["management"] = "Nguồn khuyến cáo đánh giá nguy cơ chảy máu."
        rows[0]["original_management"] = "Assess bleeding risk."
        result["findings"] = rows
        check.result = result
        await db.commit()
    seen = []
    async def explain(message, findings, citations, **kwargs):
        seen.extend(findings)
        return "", "not_configured"
    monkeypatch.setattr(assistant_service, "explain", explain)
    await client.post("/api/v1/assistant/chat", json={
        "prescription_id": rx, "check_id": check_id, "message": "Vì sao có tương tác?"})
    assert seen[0].management == "Nguồn khuyến cáo đánh giá nguy cơ chảy máu."
