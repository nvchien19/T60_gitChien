from unittest.mock import AsyncMock

import pytest

from interface.backend.config import get_settings
from interface.backend.schemas.ddi import Citation, FindingOut
from interface.backend.services import assistant_llm


@pytest.fixture(autouse=True)
def settings(monkeypatch):
    monkeypatch.setattr(get_settings(), "deepseek_api_key", "sk-test-private")


def data():
    cite = Citation(source_id="ddinter", source_name="DDInter")
    finding = FindingOut(pair=["Warfarin", "Aspirin"], severity="major", severity_vi="Nghiêm trọng",
                         mechanism="Có thể tăng nguy cơ chảy máu.",
                         management="Nguồn khuyến cáo tránh phối hợp Warfarin và Aspirin.", citations=[cite])
    return [finding], [cite]


MECHANISM = {"sentences": [{"type": "fact", "text": "Có thể tăng nguy cơ chảy máu.",
                           "sources": [1], "quote": "Có thể tăng nguy cơ chảy máu."}]}
DIRECT = {"sentences": [{"type": "fact", "text": "Nguồn khuyến cáo tránh phối hợp Warfarin và Aspirin.",
                        "sources": [1], "quote": "Nguồn khuyến cáo tránh phối hợp Warfarin và Aspirin."}]}
IRRELEVANT = {"answers_question": False, "results": [{"id": 1, "supported": True}]}
RELEVANT = {"answers_question": True, "results": [{"id": 1, "supported": True}]}


@pytest.mark.asyncio
async def test_supported_but_irrelevant_answer_repaired(monkeypatch):
    fake = AsyncMock(side_effect=[MECHANISM, IRRELEVANT, DIRECT, RELEVANT])
    monkeypatch.setattr(assistant_llm, "provider_json", fake)
    text, reason = await assistant_llm.explain("cần tránh sử dụng gì?", *data())
    assert reason == "" and "Warfarin và Aspirin" in text and "[1]" in text
    assert fake.call_count == 4
    initial = fake.call_args_list[0].args[1]
    assert initial["question"] == "cần tránh sử dụng gì?"
    assert initial["answer_focus"] == "list_warned_combinations_first"
    assert "source_recommendation" in str(initial["evidence"])
    assert fake.call_args_list[1].args[1]["question"] == "cần tránh sử dụng gì?"
    assert "revision" in fake.call_args_list[2].args[1]


@pytest.mark.asyncio
async def test_twice_irrelevant_never_shown(monkeypatch):
    monkeypatch.setattr(assistant_llm, "provider_json", AsyncMock(
        side_effect=[MECHANISM, IRRELEVANT, MECHANISM, IRRELEVANT]))
    assert await assistant_llm.explain("cần tránh sử dụng gì?", *data()) == ("", "irrelevant_answer")


@pytest.mark.asyncio
async def test_relevance_verdict_required(monkeypatch):
    monkeypatch.setattr(assistant_llm, "provider_json", AsyncMock(side_effect=[
        DIRECT, {"results": [{"id": 1, "supported": True}]}]))
    assert await assistant_llm.explain("cần tránh sử dụng gì?", *data()) == ("", "provider_unavailable")


@pytest.mark.asyncio
async def test_repair_does_not_bypass_grounding(monkeypatch):
    ungrounded = {"sentences": [{"type": "fact", "text": "Warfarin gây chảy máu 99%.",
                    "sources": [1], "quote": "Có thể tăng nguy cơ chảy máu."}]}
    monkeypatch.setattr(assistant_llm, "provider_json", AsyncMock(side_effect=[
        MECHANISM, IRRELEVANT, ungrounded]))
    assert await assistant_llm.explain("cần tránh sử dụng gì?", *data()) == ("", "ungrounded_output")


@pytest.mark.asyncio
async def test_api_source_recommendation_reaches_model_not_raw_response(client, monkeypatch):
    fake = AsyncMock(side_effect=[
        {"sentences": [{"type": "fact", "text": "Warfarin và Aspirin có mức Nghiêm trọng theo nguồn.",
                        "sources": [1], "quote": '"severity_vi": "Nghiêm trọng"'}]}, RELEVANT])
    monkeypatch.setattr(assistant_llm, "provider_json", fake)
    rx = (await client.post("/api/v1/prescriptions", json={"medications": [
        {"name": "warfarin"}, {"name": "aspirin"}]})).json()["id"]
    check = (await client.post(f"/api/v1/prescriptions/{rx}/checks")).json()["check_id"]
    result = (await client.post("/api/v1/assistant/chat", json={"prescription_id": rx,
        "check_id": check, "message": "cần tránh sử dụng gì?"})).json()
    assert result["llm_used"] and "Warfarin và Aspirin" in result["reply"]
    assert "Lien he bac si/duoc si" in str(fake.call_args_list[0].args[1]["evidence"])
    assert result["findings"][0]["management"] == ""
    assert result["findings"][0]["original_management"] == ""


@pytest.mark.asyncio
async def test_avoidance_fallback_lists_verified_pairs_not_mechanisms(client, monkeypatch):
    generic = {"sentences": [{"type": "fact", "text": "Tang nguy co chay mau khi dung chung.",
                   "sources": [1], "quote": "Tang nguy co chay mau khi dung chung."}]}
    monkeypatch.setattr(assistant_llm, "provider_json", AsyncMock(side_effect=[
        generic, IRRELEVANT, generic, IRRELEVANT]))
    rx = (await client.post("/api/v1/prescriptions", json={"medications": [
        {"name": "warfarin"}, {"name": "aspirin"}]})).json()["id"]
    check = (await client.post(f"/api/v1/prescriptions/{rx}/checks")).json()["check_id"]
    result = (await client.post("/api/v1/assistant/chat", json={"prescription_id": rx,
        "check_id": check, "message": "cần tránh sử dụng gì?"})).json()
    assert result["fallback_reason"] == "irrelevant_answer" and not result["llm_used"]
    assert "Warfarin + Aspirin" in result["reply"] and "[1]" in result["reply"]
    assert "không tự động" in result["reply"]
    assert "Tang nguy co chay mau" not in result["reply"]
