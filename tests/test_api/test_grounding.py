"""Test kiểm chứng từng câu của lời giải thích (src/services/grounding.py), không gọi LLM."""

import pytest

from src.services.grounding import Claim, Evidence, assemble, check_claim, parse_claims

EV = Evidence(
    sources={
        1: "[1] Nguồn ddinter - mức Trung bình; nhóm cơ chế: synergy\n"
        "    Mô tả: NSAIDs may potentiate the risk of CNS toxicity. Patients with a history of seizures "
        "may be at greater risk. Doses above 1.3 g/day for more than 1 week.",
        2: "[2] Quy tắc dạng bào chế R1 - Tác động: AUC giảm 62%, Cmax giảm 80%.",
    },
    definitions="ĐỊNH NGHĨA MỨC ĐỘ:\n- Trung bình: tương tác có ý nghĩa lâm sàng vừa phải",
)


def fact(text, quote, sources=(1,)):
    return Claim(type="fact", text=text, sources=list(sources), quote=quote)


@pytest.mark.parametrize(
    "claim",
    [
        fact("Có thể tăng nguy cơ độc tính thần kinh.", "may potentiate the risk of CNS toxicity"),
        fact("Liều trên 1,3 g/ngày trong hơn 1 tuần.", "Doses above 1.3 g/day"),  # 1,3 = 1.3
        fact("AUC giảm 62%.", "AUC giảm 62%", sources=[2]),
        fact("Người có tiền sử co giật có thể nguy cơ cao hơn.", "NSAIDs may potentiate ... history of seizures"),
        Claim(type="severity", text="Mức trung bình vì ý nghĩa lâm sàng vừa phải.", quote="ý nghĩa lâm sàng vừa phải"),
        Claim(type="referral", text="Hãy hỏi bác sĩ hoặc dược sĩ."),
    ],
)
def test_grounded_claims_pass(claim):
    assert check_claim(claim, EV) is None


@pytest.mark.parametrize(
    "claim, reason",
    [
        (fact("AUC giảm 62%.", "AUC giảm 62%", sources=[1]), "không có trong nguồn"),  # trích đúng chữ nhưng sai nguồn
        (fact("Gặp ở 5% người bệnh.", "may potentiate the risk"), "con số"),
        (fact("Tăng nguy cơ.", "may potentiate ... liver failure"), "không có trong nguồn"),
        (fact("Tăng nguy cơ.", "risk"), "thiếu đoạn trích"),
        (fact("Tăng nguy cơ.", "may potentiate the risk", sources=[9]), "không tồn tại"),
        (Claim(type="referral", text="Theo dõi thêm."), "bác sĩ"),
        (fact("Bạn nên ngừng thuốc ngay.", "may potentiate the risk"), "lời khuyên"),
    ],
)
def test_ungrounded_claims_are_rejected(claim, reason):
    assert reason in (check_claim(claim, EV) or "")


def test_llm_citation_markers_are_replaced_by_system():
    c = fact("Tăng nguy cơ [7].", "may potentiate the risk")
    assert check_claim(c, EV) is None
    assert assemble([c]) == "Tăng nguy cơ [1]."


def test_assemble_puts_referral_last():
    text = assemble([Claim(type="referral", text="Hãy hỏi bác sĩ"), fact("Tăng nguy cơ", "x", sources=[1, 2])])
    assert text == "Tăng nguy cơ [1][2].\n\nHãy hỏi bác sĩ."


def test_parse_claims_accepts_code_fence_and_rejects_garbage():
    fenced = '```json\n{"sentences": [{"type": "referral", "text": "Hỏi bác sĩ."}]}\n```'
    assert parse_claims(fenced)[0].type == "referral"
    with pytest.raises(ValueError):
        parse_claims("không phải JSON")
