import pytest

from interface.backend.schemas.ddi import Citation
from interface.backend.services import assistant_service
from interface.backend.services.assistant_external import explicit_drug_name, extract_drug_names


@pytest.mark.parametrize("text", ["Acevitae", "**Acevitae**  ", "`Acevitae`", "__Acevitae__",
                                   "Tra cứu thuốc **Acevitae**", "Thuốc **Acevitae** là gì?"])
def test_pasted_name(text):
    assert explicit_drug_name(text) == "Acevitae"


@pytest.mark.parametrize("text", ["giải thích", "hello", "test", "https://evil.test", "<script>x</script>",
                                   "**aspirin và warfarin**", "Tra cứu thuốc a\" OR *"])
def test_prose_and_unsafe_markup_not_pasted_name(text):
    assert not explicit_drug_name(text)


@pytest.mark.asyncio
async def test_extract_pasted_name_without_model():
    assert await extract_drug_names("**Acevitae**  ", lambda text: False) == ["Acevitae"]


@pytest.mark.asyncio
@pytest.mark.parametrize("message", ["Acevitae", "**Acevitae**  "])
async def test_chat_pasted_name_uses_lookup(client, monkeypatch, message):
    calls = []
    async def lookup(names, message, unsafe, detail):
        calls.extend(names)
        return "Thông tin nhãn thuốc có nguồn.", [Citation(source_id="openfda")], True
    monkeypatch.setattr(assistant_service, "label_reply", lookup)
    data = (await client.post("/api/v1/assistant/chat", json={"message": message})).json()
    assert calls == ["Acevitae"] and data["status"] == "answered"
    assert "Hãy chọn đơn" not in data["reply"]


@pytest.mark.asyncio
async def test_pasted_name_missing_data_is_explicit(client, monkeypatch):
    async def lookup(names, message, unsafe, detail):
        assert names == ["Acevitae"]
        return "Acevitae: hiện chưa có thông tin trong các nguồn tra cứu.", [], False
    monkeypatch.setattr(assistant_service, "label_reply", lookup)
    data = (await client.post("/api/v1/assistant/chat", json={"message": "**Acevitae**"})).json()
    assert data["status"] == "no_evidence" and "chưa có thông tin" in data["reply"]
    assert "Hãy chọn đơn" not in data["reply"]
