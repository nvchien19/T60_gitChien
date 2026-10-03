"""Giải thích từng cặp tương tác thuốc - thuốc bằng LLM (DeepSeek), bám bằng chứng trong CSDL.

- LLM chỉ được dùng phần BẰNG CHỨNG lấy từ Postgres (mô tả, khuyến cáo xử trí, quy tắc dạng bào chế).
- LLM trả JSON theo từng câu, mỗi câu kèm số nguồn và đoạn trích nguyên văn; src/services/grounding.py kiểm
  chứng từng câu (đoạn trích, con số, guardrail, LLM kiểm định). Câu ngoài bằng chứng bị loại; có câu bị loại thì
  sinh lại một lần kèm phản hồi; vẫn không đạt, lỗi API hoặc chưa có API key thì dùng bản mẫu soạn sẵn.
- Câu "chưa có bản ghi" và câu miễn trừ do code viết cố định, không qua LLM.
"""

import asyncio
import logging

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage

from src.config import get_settings
from src.models.schemas import PairResult
from src.services import guardrail
from src.services.grounding import JSON_MODE, Evidence, Rejected, assemble, check_claims, parse_claims, verify_claims

log = logging.getLogger(__name__)

SEVERITY_VI = {
    "contraindicated": "Chống chỉ định",
    "major": "Nghiêm trọng",
    "moderate": "Trung bình",
    "minor": "Nhẹ",
    "none": "Không đáng kể (theo nguồn)",
}
SEVERITY_RANK = {"contraindicated": 4, "major": 3, "moderate": 2, "minor": 1, "none": 0}

# Vì sao một cặp được xếp ở mức này (theo định nghĩa mức độ của DDInter)
WHY_LEVEL = {
    "contraindicated": "Nguồn xếp mức CHỐNG CHỈ ĐỊNH: phối hợp này có thể gây hậu quả nghiêm trọng, đe dọa tính mạng, "
    "nên nguồn khuyến cáo nhân viên y tế không dùng đồng thời hai thuốc.",
    "major": "Nguồn xếp mức NGHIÊM TRỌNG: tương tác có ý nghĩa lâm sàng cao, có thể gây hại nặng hoặc cần can thiệp y tế; "
    "nguồn khuyến cáo nhân viên y tế chỉ phối hợp khi lợi ích vượt nguy cơ và có theo dõi.",
    "moderate": "Nguồn xếp mức TRUNG BÌNH: tương tác có ý nghĩa lâm sàng vừa phải, có thể làm tăng tác dụng phụ hoặc "
    "giảm hiệu quả điều trị, thường cần theo dõi khi dùng chung.",
    "minor": "Nguồn xếp mức NHẸ: ý nghĩa lâm sàng thấp, ảnh hưởng thường hạn chế; dù vậy bác sĩ/dược sĩ vẫn cần biết "
    "bạn đang dùng cả hai thuốc.",
    "none": "Nguồn ghi nhận không có ảnh hưởng đáng kể với dạng bào chế được nêu.",
}

MECHANISM_VI = {
    "metabolism": "chuyển hóa (thuốc này làm thay đổi tốc độ gan/enzym xử lý thuốc kia, nên nồng độ thuốc trong máu "
    "có thể tăng hoặc giảm)",
    "synergy": "hiệp đồng (hai thuốc tác động cùng chiều nên tác dụng hoặc tác dụng phụ cộng dồn)",
    "antagonism": "đối kháng (hai thuốc tác động ngược chiều, có thể làm giảm hiệu quả của nhau)",
    "absorption": "hấp thu (thuốc này làm thay đổi lượng thuốc kia được hấp thu vào cơ thể)",
    "excretion": "thải trừ (thuốc này làm thay đổi tốc độ đào thải thuốc kia qua thận hoặc mật)",
    "distribution": "phân bố (thay đổi cách thuốc gắn protein hoặc được vận chuyển trong cơ thể)",
    "other": "cơ chế khác hoặc chưa được nguồn phân loại",
}

SOURCE_VI = {"ddinter": "DDInter 2.0", "openfda": "nhãn thuốc FDA", "patel2020": "Patel 2020", "pkddip": "PK-DDIP"}

REFERRAL_SENTENCE = "Hãy trao đổi với bác sĩ hoặc dược sĩ để được tư vấn cho trường hợp cụ thể của bạn."

SYSTEM_PROMPT = """Bạn là trợ lý dược lâm sàng, giải thích tương tác thuốc - thuốc bằng tiếng Việt cho người dùng phổ thông.

Nội dung cần giải thích, CHỈ dựa vào ĐỊNH NGHĨA MỨC ĐỘ và BẰNG CHỨNG được cung cấp:
1. Mức độ tương tác và VÌ SAO cặp thuốc được xếp ở mức đó.
   - Chống chỉ định hoặc Nghiêm trọng: hậu quả nguy hiểm có thể xảy ra theo bằng chứng, vì sao đáng lo.
   - Trung bình hoặc Nhẹ: vì sao ảnh hưởng chỉ ở mức này, theo những gì bằng chứng nêu; không nói là vô hại.
2. Cơ chế, diễn giải dễ hiểu.
3. Vài dấu hiệu chính cần chú ý (tối đa 4), chỉ khi bằng chứng có nêu.
4. Một câu kết đề nghị người dùng trao đổi với bác sĩ hoặc dược sĩ.

Chỉ trả về MỘT đối tượng JSON:
{"sentences": [{"type": "severity" | "fact" | "referral", "text": "...", "sources": [1], "quote": "..."}]}
- "severity": 1 câu về mức độ và vì sao ở mức đó. "quote" chép nguyên văn một đoạn ngắn từ ĐỊNH NGHĨA MỨC ĐỘ
  hoặc BẰNG CHỨNG; "sources" có thể rỗng.
- "fact": mỗi câu MỘT ý lấy từ bằng chứng. "sources" là số thứ tự bằng chứng. "quote" chép NGUYÊN VĂN từng chữ,
  giữ nguyên ngôn ngữ gốc (thường là tiếng Anh), 4-30 từ, là đoạn trong chính nguồn đó làm căn cứ cho câu.
- "referral": đúng 1 câu cuối, "sources": [], "quote": "".

Quy tắc bắt buộc:
- Mỗi câu chỉ được chứa thông tin có trong nguồn được ghi. KHÔNG thêm liều, thời gian, tần suất, đối tượng, triệu chứng,
  cơ chế, tên thuốc khác hay suy luận ngoài bằng chứng, kể cả điều bạn biết là đúng. Không chắc thì bỏ câu đó.
- Giữ mức chắc chắn như nguồn: nguồn nói "may/có thể" thì không viết "sẽ".
- Bằng chứng không mô tả cơ chế thì viết một câu "fact" nói nguồn chỉ xếp nhóm cơ chế, trích phần "nhóm cơ chế".
- Không ghi [1], [2] trong "text" (hệ thống tự gắn).
- Không khuyên ngưng, bỏ, dừng, đổi hay thay thuốc; không đề xuất liều hay cách dùng. Khuyến cáo xử trí trong bằng chứng
  dành cho nhân viên y tế: tối đa một câu dạng "nguồn khuyến cáo nhân viên y tế ...", không nêu liều, không nhắc
  thuốc thay thế hay thuốc nên ưu tiên.
- Không chẩn đoán, không suy đoán bệnh của người dùng.
- Không dùng các cụm "an toàn", "không sao", "không nguy hiểm", "không có tương tác".
- Gọi thuốc theo tên người dùng nhập; chỉ thêm hoạt chất trong ngoặc khi tên nhập là biệt dược.
- TÓM TẮT, không dịch nguyên văn cả đoạn: tổng cộng 4-7 câu, mỗi câu tối đa 35 từ, cả bài tối đa 170 từ.
  Dấu hiệu cần chú ý: gộp vào MỘT câu, tối đa 4 dấu hiệu chính. Khuyến cáo cho nhân viên y tế: đúng MỘT câu.
- Không viết câu miễn trừ trách nhiệm (hệ thống tự thêm)."""


MAX_TEXT = 1500  # cắt mô tả rất dài để giữ prompt gọn


def _clip(s: str | None) -> str:
    s = (s or "").strip()
    return s if len(s) <= MAX_TEXT else s[:MAX_TEXT].rsplit(" ", 1)[0] + " ..."


def _mechanisms_vi(mechanism_type: str) -> str:
    parts = [MECHANISM_VI.get(t.strip(), t.strip()) for t in mechanism_type.split(";") if t.strip()]
    return "; ".join(parts) or MECHANISM_VI["other"]


def build_evidence(pair: PairResult) -> tuple[str, Evidence]:
    """Khối BẰNG CHỨNG gửi cho LLM và bản có cấu trúc để kiểm chứng.

    Số [k] trùng thứ tự mechanisms rồi form_notes trong response.
    """
    a, b = pair.drug_names
    header = "\n".join(
        [
            f"Cặp hoạt chất: {a} + {b}",
            f"Tên người dùng nhập: {', '.join(pair.inputs)}",
            f"Mức độ tổng hợp (mức cao nhất giữa các nguồn): {pair.severity_vi} ({pair.severity})",
        ]
    )
    levels = dict.fromkeys(
        [pair.severity, *(m.severity for m in pair.mechanisms), *(n.severity for n in pair.form_notes)]
    )
    definitions = "ĐỊNH NGHĨA MỨC ĐỘ:\n" + "\n".join(f"- {SEVERITY_VI[lv]}: {WHY_LEVEL[lv]}" for lv in levels)
    sources: dict[int, str] = {}
    for m in pair.mechanisms:
        k = len(sources) + 1
        lines = [
            f"[{k}] Nguồn {m.source_id} (bản ghi {m.interaction_id}) - mức {SEVERITY_VI[m.severity]}; "
            f"nhóm cơ chế: {m.mechanism_type}",
            f"    Mô tả: {_clip(m.description)}",
        ]
        if m.management:
            lines.append(f"    Khuyến cáo xử trí (dành cho nhân viên y tế): {_clip(m.management)}")
        sources[k] = "\n".join(lines)
    for n in pair.form_notes:
        k = len(sources) + 1
        sources[k] = "\n".join(
            [
                f"[{k}] Quy tắc dạng bào chế {n.rule_id} ({n.source_id}) - mức {SEVERITY_VI[n.severity]}; "
                f"áp dụng cho {n.drug_name} dạng {n.drug_form}",
                f"    Tác động: {n.effect_vi}",
                f"    Xử trí (dành cho nhân viên y tế): {n.management_vi}",
            ]
        )
    text = "\n\n".join([header, definitions, "BẰNG CHỨNG:\n" + "\n".join(sources.values())])
    return text, Evidence(sources=sources, definitions=definitions, header=header)


def template_explanation(pair: PairResult) -> str:
    """Bản giải thích soạn sẵn, chỉ dùng dữ liệu CSDL. Dùng khi không có LLM hoặc LLM vi phạm guardrail."""
    a, b = pair.inputs if len(pair.inputs) == 2 else pair.drug_names
    out = [f"{a} và {b}: {WHY_LEVEL[pair.severity]}"]
    k = 0
    for m in pair.mechanisms:
        k += 1
        out.append(
            f"Theo {SOURCE_VI.get(m.source_id, m.source_id)} [{k}], mức {SEVERITY_VI[m.severity].lower()}, nhóm cơ chế: "
            f"{_mechanisms_vi(m.mechanism_type)}."
        )
    if not pair.mechanisms and pair.form_notes:
        out.append("Mức này đến từ quy tắc theo dạng bào chế nên chỉ đúng với dạng được nêu dưới đây.")
    if pair.mechanisms:
        out.append("Mô tả chi tiết và khuyến cáo xử trí cho nhân viên y tế (tiếng Anh) nằm trong nguồn trích dẫn.")
    for n in pair.form_notes:
        k += 1
        out.append(f"Lưu ý theo dạng bào chế [{k}]: {n.effect_vi}")
    out.append(REFERRAL_SENTENCE)
    return " ".join(out)


def _feedback(rejected: list[Rejected]) -> str:
    lines = "\n".join(f'- "{r.text}" -> {r.reason}' for r in rejected)
    return (
        "\n\nLẦN TRƯỚC CÁC CÂU SAU BỊ LOẠI vì không bám bằng chứng. Viết lại toàn bộ, bỏ các chi tiết bị nêu, "
        f"chép đoạn trích đúng nguyên văn:\n{lines}"
    )


async def _generate(
    pair: PairResult, llm: BaseChatModel, verify: bool, feedback: str = ""
) -> tuple[str, list[Rejected]]:
    """Một vòng sinh + kiểm chứng. Trả về (văn bản, các câu bị loại); văn bản rỗng nếu không còn câu dữ kiện nào."""
    evidence_text, ev = build_evidence(pair)
    msg = await llm.ainvoke(
        [SystemMessage(content=SYSTEM_PROMPT), HumanMessage(content=evidence_text + feedback)], **JSON_MODE
    )
    res = check_claims(parse_claims(str(msg.content)), ev)
    kept, rejected = res.kept, res.rejected
    if verify and kept:
        vres = await verify_claims(kept, ev, evidence_text, llm)
        kept, rejected = vres.kept, rejected + vres.rejected
    if not any(c.type == "fact" for c in kept):
        return "", rejected
    text = assemble(kept)
    if not guardrail.REFERRAL.search(text.lower()):
        text = f"{text}\n\n{REFERRAL_SENTENCE}"
    return text, rejected


async def explain_pair(pair: PairResult, llm: BaseChatModel | None, *, verify: bool | None = None) -> None:
    """Điền explanation / explanation_source / unsupported_claims / guardrail_violations cho một cặp."""
    if verify is None:
        verify = get_settings().explain_verify
    if llm is not None:
        rejected: list[Rejected] = []
        try:
            text, rej = await _generate(pair, llm, verify)
            rejected += rej
            if rej or not text:  # có câu ngoài bằng chứng: sinh lại một lần kèm phản hồi
                text, rej = await _generate(pair, llm, verify, _feedback(rej))
                rejected += rej
            pair.unsupported_claims = [f"{r.text} ({r.reason})" for r in rejected]
            if text and guardrail.check(text).ok:
                pair.explanation, pair.explanation_source = text, "llm"
                return
            pair.guardrail_violations = ["không còn câu dữ kiện nào bám bằng chứng sau khi kiểm chứng"]
            log.warning("LLM giải thích không bám bằng chứng (%s + %s): %s", *pair.drug_names, rejected)
        except Exception as e:  # lỗi mạng, hết hạn mức, sai key, JSON hỏng...: dùng bản mẫu
            pair.guardrail_violations = [f"lỗi gọi LLM: {e}"]
            log.warning("Gọi LLM giải thích thất bại (%s + %s): %s", *pair.drug_names, e)
    pair.explanation, pair.explanation_source = template_explanation(pair), "template"


async def explain_pairs(
    pairs: list[PairResult], llm: BaseChatModel | None, *, max_llm_pairs: int = 8, concurrency: int = 4
) -> None:
    """Giải thích các cặp (đã xếp nặng nhất trước). Chỉ max_llm_pairs cặp đầu gọi LLM, còn lại dùng bản mẫu."""
    sem = asyncio.Semaphore(concurrency)

    async def run(i: int, p: PairResult) -> None:
        async with sem:
            await explain_pair(p, llm if i < max_llm_pairs else None)

    await asyncio.gather(*(run(i, p) for i, p in enumerate(pairs)))
