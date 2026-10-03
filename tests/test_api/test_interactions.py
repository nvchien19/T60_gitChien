"""Test /api/v1/interactions/check với CSDL và LLM giả lập (không gọi Postgres hay DeepSeek)."""

import json
import re
from types import SimpleNamespace

import psycopg
import pytest

from src.main import app
from src.services import guardrail
from src.services.ddi_repository import ClassMember, DrugMatch, FormRule, Interaction, get_repository
from src.services.explainer import SEVERITY_VI, template_explanation
from src.services.llm import get_explainer_llm

URL = "/api/v1/interactions/check"
NAMES = {
    "D14": "Acetaminophen",
    "D1951": "Warfarin",
    "D900": "Ibuprofen",
    "D83": "Amoxicillin",
    "D394": "Clavulanic acid",
    "D500": "Diclofenac",
    "D600": "Dihydroergotamine",
    "D700": "Clarithromycin",
}
ALIASES = {
    "panadol": ["D14"],
    "efferalgan": ["D14"],
    "warfarin": ["D1951"],
    "ibuprofen": ["D900"],
    "augmentin": ["D394", "D83"],
    "diclofenac": ["D500"],
    "dihydroergotamine": ["D600"],
    "clarithromycin": ["D700"],
}
RANK = {"contraindicated": 4, "major": 3, "moderate": 2, "minor": 1}


def ddi(iid, a, b, severity, mech="synergy"):
    return Interaction(
        interaction_id=iid,
        drug_a=a,
        drug_a_name=NAMES[a],
        drug_b=b,
        drug_b_name=NAMES[b],
        severity=severity,
        severity_rank=RANK[severity],
        severity_vi=SEVERITY_VI[severity],
        mechanism_id=iid * 10,
        mechanism_type=mech,
        description=f"{NAMES[a]} may potentiate {NAMES[b]}.",
        management="Monitor INR.",
        references="[1] Ref",
        source_id="ddinter",
        source_url=f"https://ddinter2.scbdd.com/server/interact/{iid}/",
    )


INTERACTIONS = [
    ddi(4554, "D14", "D1951", "moderate"),
    ddi(10470, "D900", "D1951", "major"),
    ddi(111, "D83", "D394", "minor"),
    ddi(222, "D500", "D900", "moderate"),
    ddi(333, "D600", "D700", "major", "metabolism"),
]
RULES = [
    FormRule(
        rule_id="R3",
        drug_id="D600",
        drug_name="Dihydroergotamine",
        drug_form="any",
        other_drug_id="D700",
        other_drug_name="Clarithromycin",
        severity="contraindicated",
        action="raise_severity",
        effect_vi="Tăng nồng độ dihydroergotamin, gây co mạch.",
        management_vi="Chống chỉ định.",
        evidence="Nhãn FDA",
        source_id="openfda",
        source_url="https://dailymed.nlm.nih.gov/",
    )
]
CLASSES = [
    ClassMember("nonsteroidal anti-inflammatories", "D900", "Ibuprofen", 1),
    ClassMember("nonsteroidal anti-inflammatories", "D500", "Diclofenac", 1),
]


class FakeRepo:
    async def find_drug(self, query, max_results=5):
        key = query.lower()
        if key in ALIASES:
            return [DrugMatch(i, NAMES[i], key, "brand_vi", "ok", 1.0) for i in ALIASES[key]]
        if key == "asprin":
            return [DrugMatch("D20", "Aspirin", "aspirin", "inn_en", "suggest", 0.5)]
        return []

    async def interactions_among(self, ids):
        return [i for i in INTERACTIONS if i.drug_a in ids and i.drug_b in ids]

    async def form_rules_among(self, ids):
        return [r for r in RULES if r.drug_id in ids and r.other_drug_id in ids]

    async def class_members(self, ids):
        return [c for c in CLASSES if c.drug_id in ids]


def claims(*sentences):
    """JSON giống DeepSeek trả về cho prompt sinh giải thích."""
    return json.dumps({"sentences": list(sentences)}, ensure_ascii=False)


SEVERITY = {
    "type": "severity",
    "text": "Cặp này ở mức nghiêm trọng vì có ý nghĩa lâm sàng cao.",
    "sources": [],
    "quote": "tương tác có ý nghĩa lâm sàng cao",
}
FACT = {
    "type": "fact",
    "text": "Ibuprofen có thể làm tăng tác dụng của Warfarin.",
    "sources": [1],
    "quote": "Ibuprofen may potentiate Warfarin",
}
REFERRAL = {"type": "referral", "text": "Hãy trao đổi với bác sĩ hoặc dược sĩ.", "sources": [], "quote": ""}
GOOD = claims(SEVERITY, FACT, REFERRAL)


class FakeLLM:
    """LLM giả: `replies` lần lượt cho các lượt sinh; `unsupported` là các câu bị LLM kiểm định đánh trượt."""

    def __init__(self, *replies, unsupported=(), error=None):
        self.replies, self.unsupported, self.error = list(replies), set(unsupported), error
        self.gen_calls = self.verify_calls = 0

    async def ainvoke(self, messages, **kwargs):
        if self.error:
            raise self.error
        human = messages[-1].content
        if messages[0].content.startswith("Bạn là người kiểm định"):
            self.verify_calls += 1
            items = re.findall(r"^Câu (\d+) \([^)]*\): (.*)$", human, flags=re.M)
            results = [
                {"id": int(i), "supported": t not in self.unsupported, "reason": "thêm chi tiết"} for i, t in items
            ]
            return SimpleNamespace(content=json.dumps({"results": results}))
        self.gen_calls += 1
        return SimpleNamespace(content=self.replies[min(self.gen_calls, len(self.replies)) - 1])


@pytest.fixture
def use(request):
    """Ghi đè repository/LLM của API; tự gỡ sau mỗi test."""

    def _use(llm=None, repo=None):
        app.dependency_overrides[get_repository] = lambda: repo or FakeRepo()
        app.dependency_overrides[get_explainer_llm] = lambda: llm

    yield _use
    app.dependency_overrides.clear()


def full_text(body):
    parts = [body["summary"], body["disclaimer"], *body["notes"], *[d["message"] for d in body["duplicates"]]]
    return " ".join(parts + [p["explanation"] for p in body["pairs"]])


@pytest.mark.asyncio
async def test_check_without_llm_uses_template(client, use):
    use(llm=None)
    r = await client.post(URL, json={"drugs": ["Panadol", "Warfarin", "Ibuprofen", "Efferalgan"]})
    assert r.status_code == 200
    body = r.json()
    assert [p["severity"] for p in body["pairs"]] == ["major", "moderate"]  # nặng nhất trước
    assert body["pairs"][0]["inputs"] == ["Ibuprofen", "Warfarin"]
    assert all(p["explanation_source"] == "template" and p["explanation"] for p in body["pairs"])
    assert not body["llm_used"]
    assert any("DEEPSEEK_API_KEY" in n for n in body["notes"])
    # Panadol + Efferalgan cùng paracetamol: trùng hoạt chất, không tính là "chưa có bản ghi"
    assert [d["type"] for d in body["duplicates"]] == ["duplicate_active"]
    assert sorted(map(sorted, body["no_record_pairs"])) == [["Efferalgan", "Ibuprofen"], ["Ibuprofen", "Panadol"]]
    assert {
        "source_id": "ddinter",
        "record_id": "4554",
        "url": "https://ddinter2.scbdd.com/server/interact/4554/",
    } in body["citations"]
    assert guardrail.check(full_text(body)).ok
    assert "tham khảo" in body["disclaimer"]


@pytest.mark.asyncio
async def test_grounded_llm_explanation_is_used(client, use):
    llm = FakeLLM(GOOD)
    use(llm=llm)
    body = (await client.post(URL, json={"drugs": ["Ibuprofen", "Warfarin"]})).json()
    pair = body["pairs"][0]
    assert pair["explanation_source"] == "llm" and body["llm_used"]
    # Số nguồn do hệ thống gắn; câu kết tách đoạn
    assert "Ibuprofen có thể làm tăng tác dụng của Warfarin [1]." in pair["explanation"]
    assert pair["explanation"].endswith("\n\nHãy trao đổi với bác sĩ hoặc dược sĩ.")
    assert pair["unsupported_claims"] == []
    assert (llm.gen_calls, llm.verify_calls) == (1, 1)


BAD_FACTS = [
    {**FACT, "text": "Bạn nên ngưng warfarin ngay."},  # khuyên ngưng thuốc
    {**FACT, "text": "Hai thuốc này dùng chung an toàn."},  # khẳng định an toàn
    {**FACT, "text": "Nên đổi sang paracetamol."},  # khuyên đổi thuốc
    {**FACT, "sources": [3]},  # nguồn không tồn tại
    {**FACT, "sources": []},  # câu dữ kiện không ghi nguồn
    {**FACT, "quote": "Ibuprofen causes liver failure"},  # đoạn trích bịa
    {**FACT, "text": "Ibuprofen làm tăng tác dụng của Warfarin ở 30% người bệnh."},  # con số ngoài bằng chứng
]


@pytest.mark.asyncio
@pytest.mark.parametrize("bad", BAD_FACTS)
async def test_ungrounded_sentences_fall_back_to_template(client, use, bad):
    llm = FakeLLM(claims(SEVERITY, bad, REFERRAL))
    use(llm=llm)
    pair = (await client.post(URL, json={"drugs": ["Ibuprofen", "Warfarin"]})).json()["pairs"][0]
    assert pair["explanation_source"] == "template"
    assert len(pair["unsupported_claims"]) == 2  # bị loại ở cả lượt đầu và lượt sinh lại
    assert llm.gen_calls == 2
    assert guardrail.check(pair["explanation"]).ok


@pytest.mark.asyncio
async def test_bad_sentence_is_dropped_and_retry_uses_feedback(client, use):
    extra = {**FACT, "text": "Nguy cơ này rõ hơn khi dùng kéo dài."}
    llm = FakeLLM(claims(SEVERITY, FACT, extra, REFERRAL), GOOD, unsupported={extra["text"]})
    use(llm=llm)
    pair = (await client.post(URL, json={"drugs": ["Ibuprofen", "Warfarin"]})).json()["pairs"][0]
    assert pair["explanation_source"] == "llm"
    assert "kéo dài" not in pair["explanation"]
    assert pair["unsupported_claims"] == [f"{extra['text']} (ngoài bằng chứng: thêm chi tiết)"]
    assert llm.gen_calls == 2


@pytest.mark.asyncio
async def test_verifier_rejecting_all_facts_falls_back_to_template(client, use):
    use(llm=FakeLLM(GOOD, unsupported={FACT["text"]}))
    pair = (await client.post(URL, json={"drugs": ["Ibuprofen", "Warfarin"]})).json()["pairs"][0]
    assert pair["explanation_source"] == "template"
    assert pair["guardrail_violations"]


@pytest.mark.asyncio
async def test_invalid_json_falls_back_to_template(client, use):
    use(llm=FakeLLM("Ibuprofen làm tăng nguy cơ chảy máu [1]. Hỏi bác sĩ."))
    pair = (await client.post(URL, json={"drugs": ["Ibuprofen", "Warfarin"]})).json()["pairs"][0]
    assert pair["explanation_source"] == "template"
    assert "JSON" in pair["guardrail_violations"][0]


@pytest.mark.asyncio
async def test_llm_error_falls_back_to_template(client, use):
    use(llm=FakeLLM(error=TimeoutError("deepseek timeout")))
    pair = (await client.post(URL, json={"drugs": ["Ibuprofen", "Warfarin"]})).json()["pairs"][0]
    assert pair["explanation_source"] == "template" and pair["explanation"]


@pytest.mark.asyncio
async def test_explain_false_does_not_call_llm(client, use):
    llm = FakeLLM(GOOD)
    use(llm=llm)
    body = (await client.post(URL, json={"drugs": ["Ibuprofen", "Warfarin"], "explain": False})).json()
    assert llm.gen_calls == 0 and body["pairs"][0]["explanation_source"] == "template"


@pytest.mark.asyncio
async def test_unknown_and_fuzzy_names_are_not_looked_up(client, use):
    use()
    body = (await client.post(URL, json={"drugs": ["asprin", "abcxyz", "Warfarin"]})).json()
    status = {d["input"]: d for d in body["drugs"]}
    assert status["asprin"]["status"] == "suggest" and status["asprin"]["drug_ids"] == []
    assert status["asprin"]["suggestions"][0]["alias"] == "aspirin"
    assert status["abcxyz"]["status"] == "unknown"
    assert body["pairs"] == []
    assert "Cần ít nhất 2 thuốc" in body["summary"]
    assert guardrail.check(full_text(body)).ok


@pytest.mark.asyncio
async def test_combination_product_internal_pair_is_ignored(client, use):
    use()
    body = (await client.post(URL, json={"drugs": ["Augmentin", "Warfarin"]})).json()
    assert body["drugs"][0]["drug_names"] == ["Clavulanic acid", "Amoxicillin"]
    assert body["pairs"] == []  # amoxicillin-clavulanat nằm chung một biệt dược
    assert body["no_record_pairs"] == [["Augmentin", "Warfarin"]]
    assert any("không có nghĩa là dùng chung an toàn" in n for n in body["notes"])


@pytest.mark.asyncio
async def test_raise_severity_rule_and_class_duplicate(client, use):
    use()
    body = (await client.post(URL, json={"drugs": ["Dihydroergotamine", "Clarithromycin"]})).json()
    pair = body["pairs"][0]
    assert pair["severity"] == "contraindicated" and pair["form_notes"][0]["rule_id"] == "R3"
    assert {
        "type": "interaction",
        "drug_ids": pair["drug_ids"],
        "severity": "contraindicated",
        "source_id": "openfda",
        "record_id": "R3",
    } in body["findings"]

    body = (await client.post(URL, json={"drugs": ["Ibuprofen", "Diclofenac"]})).json()
    assert [d["type"] for d in body["duplicates"]] == ["duplicate_class"]


@pytest.mark.asyncio
async def test_database_error_returns_503(client, use):
    class BrokenRepo(FakeRepo):
        async def find_drug(self, query, max_results=5):
            raise psycopg.OperationalError("connection refused")

    use(repo=BrokenRepo())
    r = await client.post(URL, json={"drugs": ["Panadol", "Warfarin"]})
    assert r.status_code == 503


@pytest.mark.asyncio
async def test_request_validation(client, use):
    use()
    assert (await client.post(URL, json={"drugs": []})).status_code == 422


@pytest.mark.parametrize("severity", ["contraindicated", "major", "moderate", "minor"])
def test_templates_pass_guardrail(severity):
    from src.models.schemas import Mechanism, PairResult

    pair = PairResult(
        drug_ids=["D1", "D2"],
        drug_names=["A", "B"],
        inputs=["A", "B"],
        severity=severity,
        severity_vi=SEVERITY_VI[severity],
        mechanisms=[
            Mechanism(
                interaction_id=1,
                severity=severity,
                severity_vi=SEVERITY_VI[severity],
                mechanism_type="metabolism;synergy",
                description="x",
                references="r",
                source_id="ddinter",
                source_url="u",
            )
        ],
    )
    text = template_explanation(pair)
    assert guardrail.check(text).ok, guardrail.check(text).violations
    assert "[1]" in text
