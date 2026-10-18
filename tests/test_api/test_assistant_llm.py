"""No live provider calls: privacy, grounding, error redaction and wiring."""
import json
from unittest.mock import AsyncMock

import httpx
import pytest

from interface.backend.config import get_settings
from interface.backend.schemas.ddi import Citation, FindingOut
from interface.backend.services import assistant_llm as module


@pytest.fixture(autouse=True)
def configured(monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "deepseek_api_key", "sk-test-keep-private")
    monkeypatch.setattr(settings, "deepseek_base_url", "https://api.deepseek.com")


def evidence():
    cite = Citation(source_id="ddinter", source_name="DDInter",
                    source_url="https://ddinter2.scbdd.com/server/interact/1/")
    finding = FindingOut(pair=["Warfarin", "Aspirin"], severity="major",
                         severity_vi="Nghiêm trọng", mechanism="Có thể tăng nguy cơ chảy máu.",
                         citations=[cite])
    return [finding], [cite]


GOOD = {"sentences": [{"type": "fact", "text": "Có thể tăng nguy cơ chảy máu.",
                       "sources": [1], "quote": "Có thể tăng nguy cơ chảy máu."}]}


@pytest.mark.asyncio
async def test_minimal_payload_excludes_raw_question_and_private_fields(monkeypatch):
    fake = AsyncMock(side_effect=[GOOD, {"answers_question": True, "results": [{"id": 1, "supported": True}]}])
    monkeypatch.setattr(module, "provider_json", fake)
    findings, citations = evidence()
    findings[0].management = "Patient name: Nguyen Van A; phone: 0901234567"
    question = "Tôi Nguyen Van A, email person@example.com, mã RX-SECRET, 0901234567. Vì sao có tương tác?"
    text, reason = await module.explain(question, findings, citations)
    assert reason == "" and "[1]" in text
    outbound = json.dumps(fake.call_args_list, default=str, ensure_ascii=False)
    for private in ("Nguyen Van A", "person@example.com", "RX-SECRET", "0901234567", "sk-test-keep-private"):
        assert private not in outbound
    assert fake.call_count == 2


@pytest.mark.asyncio
@pytest.mark.parametrize("change,expected", [
    ({"sources": [99]}, "ungrounded_output"),
    ({"quote": "Không tồn tại trong database"}, "ungrounded_output"),
    ({"text": "Nguy cơ tăng 99%."}, "ungrounded_output"),
    ({"text": "Hãy tăng liều thuốc lên 20 mg."}, "unsafe_output"),
    ({"text": "Bạn đang bị suy gan."}, "unsafe_output"),
    ({"text": "API key là sk-private-secret"}, "unsafe_output"),
    ({"text": "Bạn hãy dùng thuốc này buổi sáng."}, "unsafe_output"),
    ({"text": "Nên uống thuốc sau ăn."}, "unsafe_output"),
    ({"text": "Bệnh nhân giảm liều thuốc khi phối hợp."}, "unsafe_output"),
])
async def test_rejects_bad_claim_before_verification(monkeypatch, change, expected):
    claim = dict(GOOD["sentences"][0], **change)
    fake = AsyncMock(return_value={"sentences": [claim]})
    monkeypatch.setattr(module, "provider_json", fake)
    assert await module.explain("giải thích", *evidence()) == ("", expected)
    assert fake.call_count == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("subject", ["ở bệnh nhân", "ở người", "ở người bệnh", "khi đang"])
async def test_descriptive_taking_medicine_is_not_advice(monkeypatch, subject):
    # Hồi quy 18/10: câu mô tả của nguồn "ở bệnh nhân dùng thuốc chống đông" bị chặn nhầm là lời khuyên.
    sentence = f"Có thể tăng nguy cơ chảy máu {subject} dùng thuốc chống đông."
    findings, citations = evidence()
    findings[0].mechanism = sentence
    claim = {"type": "fact", "text": sentence, "sources": [1], "quote": sentence}
    monkeypatch.setattr(module, "provider_json", AsyncMock(side_effect=[
        {"sentences": [claim]}, {"answers_question": True, "results": [{"id": 1, "supported": True}]}]))
    text, reason = await module.explain("Vì sao có tương tác?", findings, citations)
    assert reason == "" and "dùng thuốc chống đông" in text


@pytest.mark.asyncio
@pytest.mark.parametrize("verdict", [
    {"answers_question": True, "results": []}, {"answers_question": True, "results": [{"id": 1, "supported": False}]},
    {"answers_question": True, "results": [{"id": 2, "supported": True}]},
    {"answers_question": True, "results": [{"id": 1, "supported": "true"}]},
])
async def test_verifier_fail_closed(monkeypatch, verdict):
    monkeypatch.setattr(module, "provider_json", AsyncMock(side_effect=[GOOD, verdict]))
    text, reason = await module.explain("giải thích", *evidence())
    assert not text and reason in {"unverified_output", "provider_unavailable"}


@pytest.mark.asyncio
async def test_no_key_treatment_private_evidence_do_not_call_provider(monkeypatch):
    fake = AsyncMock()
    monkeypatch.setattr(module, "provider_json", fake)
    assert await module.explain("giải thích", [], []) == ("", "not_applicable")
    findings, citations = evidence()
    findings[0].mechanism = "Liên hệ person@example.com để xem dữ liệu"
    assert await module.explain("giải thích", findings, citations) == ("", "privacy_blocked")
    monkeypatch.setattr(get_settings(), "deepseek_api_key", "")
    assert await module.explain("giải thích", *evidence()) == ("", "not_configured")
    fake.assert_not_awaited()


@pytest.mark.asyncio
async def test_provider_exception_does_not_leak_secrets(monkeypatch):
    monkeypatch.setattr(module, "provider_json", AsyncMock(side_effect=RuntimeError(
        "password=private; sk-test-keep-private; postgres://credentials")))
    assert await module.explain("giải thích", *evidence()) == ("", "provider_unavailable")


@pytest.mark.asyncio
async def test_provider_only_intended_https_origin_and_json(monkeypatch):
    seen = []

    def handle(request):
        seen.append(request)
        return httpx.Response(200, json={"choices": [{"finish_reason": "stop",
                              "message": {"content": json.dumps(GOOD)}}]})

    actual = httpx.AsyncClient
    monkeypatch.setattr(module.httpx, "AsyncClient", lambda **kwargs: actual(
        transport=httpx.MockTransport(handle), **kwargs))
    assert await module.provider_json(module.SYSTEM, {"task": "test"}) == GOOD
    sent = json.loads(seen[0].content)
    assert "sk-test-keep-private" not in str(sent)
    assert sent["response_format"] == {"type": "json_object"}
    assert "tools" not in sent
    monkeypatch.setattr(get_settings(), "deepseek_base_url", "https://attacker.invalid")
    with pytest.raises(ValueError):
        await module.provider_json(module.SYSTEM, {})
    assert len(seen) == 1


@pytest.mark.asyncio
async def test_api_uses_verified_deepseek_answer(client, monkeypatch):
    fake = AsyncMock(side_effect=[
        {"sentences": [{"type": "fact", "text": "Tang nguy co chay mau khi dung chung.",
                        "sources": [1], "quote": "Tang nguy co chay mau khi dung chung."}]},
        {"answers_question": True, "results": [{"id": 1, "supported": True}]},
    ])
    monkeypatch.setattr(module, "provider_json", fake)
    rx = (await client.post("/api/v1/prescriptions", json={"medications": [
        {"name": "warfarin"}, {"name": "aspirin"}]})).json()["id"]
    check = (await client.post(f"/api/v1/prescriptions/{rx}/checks")).json()["check_id"]
    result = (await client.post("/api/v1/assistant/chat", json={"prescription_id": rx,
        "check_id": check, "message": "Vì sao có tương tác? Tôi tên Nguyen Van A."})).json()
    assert result["llm_used"] and result["fallback_reason"] == ""
    assert "[1]" in result["reply"] and result["citations"][0]["source_id"] == "ddinter"
    assert rx not in str(fake.call_args_list) and check not in str(fake.call_args_list)
    assert "Nguyen Van A" not in str(fake.call_args_list)
