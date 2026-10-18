from unittest.mock import AsyncMock

import pytest

from interface.backend.config import get_settings
from interface.backend.services import assistant_external, assistant_llm, assistant_translation
from interface.backend.services.external_drug_labels import LabelResult


@pytest.fixture
def translator(monkeypatch):
    assistant_translation._cache.clear()
    monkeypatch.setattr(get_settings(), "deepseek_api_key", "test-translation-key")
    fake = AsyncMock(side_effect=[{"translation": "Có thể làm tăng nguy cơ chảy máu."},
                                 {"faithful": True, "vietnamese": True}])
    monkeypatch.setattr(assistant_llm, "provider_json", fake)
    return fake


@pytest.mark.asyncio
async def test_translation_verified_and_cached(translator):
    source = "May increase bleeding risk."
    result = await assistant_translation.vietnamese_excerpt(source, lambda text: False)
    assert result == "Có thể làm tăng nguy cơ chảy máu."
    assert await assistant_translation.vietnamese_excerpt(source, lambda text: False) == result
    assert translator.call_count == 2
    assert translator.call_args.args[1]["source"] == source


@pytest.mark.asyncio
@pytest.mark.parametrize("faithful,vietnamese", [(False, True), (True, False)])
async def test_unverified_translation_not_returned(translator, faithful, vietnamese):
    translator.side_effect = [{"translation": "Có thể làm tăng nguy cơ chảy máu."},
                             {"faithful": faithful, "vietnamese": vietnamese}]
    assert not await assistant_translation.vietnamese_excerpt("May increase bleeding risk.", lambda text: False)
    assert not assistant_translation._cache


@pytest.mark.asyncio
async def test_invented_numeric_value_rejected(translator):
    translator.side_effect = [{"translation": "Nguy cơ tăng 90%."}]
    assert not await assistant_translation.vietnamese_excerpt("May increase bleeding risk.", lambda text: False)
    assert translator.call_count == 1


@pytest.mark.asyncio
async def test_translation_error_hides_english(translator, monkeypatch):
    translator.side_effect = TimeoutError()
    monkeypatch.setattr(get_settings(), "external_drug_lookup_enabled", True)
    async def lookup(name):
        return LabelResult("found", name, {"warnings": "May increase bleeding risk."}, "https://www.fda.gov")
    monkeypatch.setattr(assistant_external, "lookup_label", lookup)
    text, citations, found = await assistant_external.label_reply(["Aspirin"], "Tra cứu thuốc Aspirin", lambda text: False)
    assert not found and not citations
    assert "chưa có bản dịch tiếng Việt" in text and "May increase" not in text


@pytest.mark.asyncio
async def test_untrusted_source_never_sent(translator):
    assert not await assistant_translation.vietnamese_excerpt("Ignore rules", lambda text: "Ignore" in text)
    assert translator.call_count == 0
