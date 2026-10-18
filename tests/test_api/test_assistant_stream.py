"""SSE endpoint: progress stages first, then the same verified answer as /assistant/chat; no live model."""
import json
from unittest.mock import AsyncMock

import pytest

from interface.backend.config import get_settings
from interface.backend.services import assistant_llm
from interface.backend.services.progress import STAGES, active_progress, report

QUESTION = "Vì sao Warfarin và Aspirin có tương tác?"


def events(body: str) -> list[tuple[str, dict]]:
    parsed = []
    for block in body.split("\n\n"):
        lines = dict(line.split(": ", 1) for line in block.splitlines() if line and not line.startswith(":"))
        if lines:
            parsed.append((lines["event"], json.loads(lines["data"])))
    return parsed


def verified_model(monkeypatch):
    monkeypatch.setattr(get_settings(), "deepseek_api_key", "sk-test-private")
    fake = AsyncMock(side_effect=lambda system, data: (
        {"answers_question": True, "results": [{"id": 1, "supported": True}]} if "statements" in data else
        {"sentences": [{"type": "fact", "text": "Tăng nguy cơ chảy máu khi dùng chung.", "sources": [1],
                        "quote": "Tang nguy co chay mau khi dung chung."}]}))
    monkeypatch.setattr(assistant_llm, "provider_json", fake)


async def checked(client):
    rx = (await client.post("/api/v1/prescriptions", json={"medications": [
        {"name": "warfarin"}, {"name": "aspirin"}]})).json()["id"]
    check = (await client.post(f"/api/v1/prescriptions/{rx}/checks")).json()["check_id"]
    return {"prescription_id": rx, "check_id": check, "message": QUESTION}


@pytest.mark.asyncio
async def test_stream_sends_stages_then_same_verified_answer(client, monkeypatch):
    verified_model(monkeypatch)
    payload = await checked(client)
    result = await client.post("/api/v1/assistant/chat/stream", json=payload)
    assert result.status_code == 200
    assert result.headers["content-type"].startswith("text/event-stream")
    assert "no-transform" in result.headers["cache-control"]
    parsed = events(result.text)
    stages = [data["stage"] for name, data in parsed if name == "stage"]
    assert stages == ["routing", "context", "composing", "verifying"]
    # Progress events carry fixed labels only, never the question or model text.
    assert all(data == {"stage": data["stage"], "label": STAGES[data["stage"]]} for name, data in parsed if name == "stage")
    assert QUESTION not in "".join(json.dumps(d, ensure_ascii=False) for n, d in parsed if n == "stage")
    name, done = parsed[-1]
    assert name == "done" and done["llm_used"] is True and done["citations"]
    plain = (await client.post("/api/v1/assistant/chat", json=payload)).json()
    assert done["reply"] == plain["reply"] and done["status"] == plain["status"]


@pytest.mark.asyncio
async def test_stream_reports_http_errors_as_error_event(client):
    result = await client.post("/api/v1/assistant/chat/stream",
                               json={"prescription_id": "RX-KHONG-CO", "message": QUESTION})
    assert result.status_code == 200
    assert events(result.text)[-1] == ("error", {"status": 404, "detail": "Không tìm thấy đơn thuốc"})


@pytest.mark.asyncio
async def test_stream_validates_request_before_streaming(client):
    result = await client.post("/api/v1/assistant/chat/stream", json={"message": "test", "tool": "shell"})
    assert result.status_code == 422


def test_report_ignores_unknown_stage_and_missing_listener():
    report("routing")  # No listener: no error.
    seen = []
    token = active_progress.set(seen.append)
    try:
        report("routing")
        report("model said: bỏ qua quy tắc")
    finally:
        active_progress.reset(token)
    assert seen == ["routing"]
