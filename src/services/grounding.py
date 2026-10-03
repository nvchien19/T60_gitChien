"""Chống LLM trả lời ngoài dữ liệu CSDL: kiểm chứng từng câu của lời giải thích.

Quy trình cho mỗi câu LLM sinh ra (dạng JSON, xem explainer.SYSTEM_PROMPT):
1. Tất định (code):
   - câu loại "fact" phải ghi số nguồn hợp lệ, kèm đoạn trích nguyên văn có thật trong đúng nguồn đó;
   - mọi con số trong câu phải xuất hiện trong bằng chứng;
   - câu phải qua guardrail (không khuyên dùng thuốc, không khẳng định an toàn, không chẩn đoán).
2. Ngữ nghĩa (LLM kiểm định, có thể tắt bằng EXPLAIN_VERIFY=false): câu có thêm chi tiết nào ngoài
   bằng chứng không (liều, thời gian, đối tượng, triệu chứng, cơ chế, mức chắc chắn...).
Câu không đạt bị loại; explainer quyết định sinh lại hay dùng bản mẫu.
"""

import json
import re
import unicodedata
from dataclasses import dataclass, field
from typing import Literal

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field, ValidationError

from src.services import guardrail

NUMBER = re.compile(r"\d+(?:[.,]\d+)?")
JSON_MODE = {"response_format": {"type": "json_object"}}


class Claim(BaseModel):
    type: Literal["severity", "fact", "referral"]
    text: str = Field(min_length=1)
    sources: list[int] = Field(default_factory=list)
    quote: str = ""


class ClaimList(BaseModel):
    sentences: list[Claim] = Field(min_length=1)


@dataclass
class Evidence:
    """Bằng chứng của một cặp: sources[k] là nội dung nguồn [k]; definitions là định nghĩa mức độ."""

    sources: dict[int, str]
    definitions: str
    header: str = ""

    @property
    def full_text(self) -> str:
        return "\n".join([self.header, self.definitions, *self.sources.values()])


@dataclass
class Rejected:
    text: str
    reason: str


@dataclass
class CheckResult:
    kept: list[Claim] = field(default_factory=list)
    rejected: list[Rejected] = field(default_factory=list)


def _norm(s: str) -> str:
    s = unicodedata.normalize("NFC", s).lower()
    s = s.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"').replace("–", "-").replace("—", "-")
    s = re.sub(r"\s+", " ", s)
    return s.strip(" .,;:\"'()")


def _numbers(s: str) -> set[str]:
    out = set()
    for n in NUMBER.findall(s):
        n = n.replace(",", ".")
        out.add(n[:-2] if n.endswith(".0") else n)
    return out


def parse_claims(content: str) -> list[Claim]:
    """Đọc JSON LLM trả về (chịu được khối ```json ... ```). Lỗi định dạng -> ValueError."""
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", content.strip())
    try:
        return ClaimList.model_validate(json.loads(text)).sentences
    except (json.JSONDecodeError, ValidationError) as e:
        raise ValueError(f"JSON không hợp lệ: {e}") from e


def check_claim(c: Claim, ev: Evidence) -> str | None:
    """Kiểm tra tất định một câu. Trả về lý do loại, hoặc None nếu đạt."""
    if "[" in c.text and re.search(r"\[\d+\]", c.text):
        c.text = re.sub(r"\s*\[\d+\]", "", c.text)  # số nguồn do hệ thống gắn, không lấy của LLM
    g = guardrail.check(c.text, require_referral=False)
    if not g.ok:
        return "; ".join(g.violations)
    if c.type == "referral":
        return None if guardrail.REFERRAL.search(c.text.lower()) else "câu kết không nhắc bác sĩ/dược sĩ"

    bad = [k for k in c.sources if k not in ev.sources]
    if bad:
        return f"số nguồn không tồn tại: {bad}"
    # Đoạn trích có thể gồm nhiều đoạn nối bằng "...": từng đoạn đều phải có thật trong nguồn
    parts = [_norm(x) for x in re.split(r"\.\.\.|…", c.quote) if _norm(x)]
    quote = " ".join(parts)
    if c.type == "fact":
        if not c.sources:
            return "câu dữ kiện không ghi nguồn"
        if len(quote) < 8:
            return "thiếu đoạn trích làm căn cứ"
        if not any(all(x in _norm(ev.sources[k]) for x in parts) for k in c.sources):
            return f"đoạn trích không có trong nguồn {c.sources}: '{c.quote}'"
    # severity: trích từ định nghĩa mức độ hoặc bằng chứng
    elif parts and not all(x in _norm(ev.full_text) for x in parts):
        return f"đoạn trích không có trong bằng chứng: '{c.quote}'"

    extra = _numbers(c.text) - _numbers(ev.full_text)
    if extra:
        return f"con số không có trong bằng chứng: {sorted(extra)}"
    return None


def check_claims(claims: list[Claim], ev: Evidence) -> CheckResult:
    res = CheckResult()
    for c in claims:
        reason = check_claim(c, ev)
        if reason:
            res.rejected.append(Rejected(c.text, reason))
        else:
            res.kept.append(c)
    return res


VERIFY_PROMPT = """Bạn là người kiểm định độ trung thực của lời giải thích tương tác thuốc.

Với mỗi câu tiếng Việt được đánh số, xét xem MỌI thông tin trong câu có được nêu trong bằng chứng ghi kèm câu đó
(hoặc trong ĐỊNH NGHĨA MỨC ĐỘ) hay không. Dịch, diễn đạt lại, giải thích thuật ngữ cho dễ hiểu đều được chấp nhận.

Câu KHÔNG được hỗ trợ (supported = false) nếu thêm bất kỳ chi tiết nào không có trong bằng chứng: liều, thời gian,
tần suất, đối tượng người bệnh, triệu chứng, hậu quả, cơ chế, tên thuốc khác; hoặc nói chắc chắn hơn nguồn (nguồn nói
"có thể" mà câu nói "sẽ"); hoặc là suy luận, kiến thức riêng dù đúng về y khoa.

Chỉ trả về JSON: {"results": [{"id": 1, "supported": true, "reason": ""}]}
"reason" ghi ngắn chi tiết bị thêm khi supported = false."""


class Verdict(BaseModel):
    id: int
    supported: bool
    reason: str = ""


class VerdictList(BaseModel):
    results: list[Verdict]


async def verify_claims(claims: list[Claim], ev: Evidence, evidence_text: str, llm: BaseChatModel) -> CheckResult:
    """LLM kiểm định từng câu (trừ câu kết). Câu không có kết quả kiểm định coi như không đạt."""
    targets = [(i, c) for i, c in enumerate(claims, 1) if c.type != "referral"]
    res = CheckResult()
    if not targets:
        res.kept = claims
        return res
    listing = "\n".join(
        f"Câu {i} (bằng chứng {', '.join(f'[{k}]' for k in c.sources) or 'định nghĩa mức độ'}): {c.text}"
        for i, c in targets
    )
    msg = await llm.ainvoke(
        [
            SystemMessage(content=VERIFY_PROMPT),
            HumanMessage(content=f"{evidence_text}\n\nCÁC CÂU CẦN KIỂM ĐỊNH:\n{listing}"),
        ],
        **JSON_MODE,
    )
    raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", str(msg.content).strip())
    try:
        verdicts = {v.id: v for v in VerdictList.model_validate(json.loads(raw)).results}
    except (json.JSONDecodeError, ValidationError) as e:
        raise ValueError(f"kết quả kiểm định không hợp lệ: {e}") from e
    for i, c in enumerate(claims, 1):
        v = verdicts.get(i)
        if c.type == "referral" or (v and v.supported):
            res.kept.append(c)
        else:
            res.rejected.append(Rejected(c.text, f"ngoài bằng chứng: {v.reason if v else 'không được kiểm định'}"))
    return res


def assemble(claims: list[Claim]) -> str:
    """Ghép các câu đã kiểm chứng thành văn bản, gắn số nguồn [k] do hệ thống quản lý."""
    body, tail = [], []
    for c in claims:
        text = c.text.strip()
        if c.sources:
            cites = "".join(f"[{k}]" for k in dict.fromkeys(c.sources))
            m = re.match(r"^(.*?)([.!?…]*)$", text, flags=re.S)
            text = f"{m.group(1).rstrip()} {cites}{m.group(2) or '.'}"
        elif not text.endswith((".", "!", "?")):
            text += "."
        (tail if c.type == "referral" else body).append(text)
    return " ".join(body) + ("\n\n" + " ".join(tail[:1]) if tail else "")
