from typing import Literal

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=5000, description="Tin nhắn từ user")


class ChatResponse(BaseModel):
    response: str = Field(..., description="Phản hồi từ agent")
    analysis: str = Field(default="", description="Phân tích nội bộ")


# ---- Kiểm tra tương tác thuốc - thuốc ----

Severity = Literal["contraindicated", "major", "moderate", "minor", "none"]


class InteractionCheckRequest(BaseModel):
    drugs: list[str] = Field(
        ...,
        min_length=1,
        max_length=20,
        description="Tên thuốc người dùng nhập: biệt dược, hoạt chất, tiếng Việt hoặc tiếng Anh",
    )
    explain: bool = Field(
        default=True,
        description="Dùng LLM (DeepSeek) giải thích từng cặp; false hoặc chưa có API key thì dùng mẫu soạn sẵn",
    )


class DrugSuggestion(BaseModel):
    drug_id: str
    drug_name: str
    alias: str
    score: float


class ResolvedDrug(BaseModel):
    input: str
    status: Literal["ok", "suggest", "unknown"] = Field(
        ..., description="ok: khớp chắc chắn; suggest: khớp gần đúng, cần người dùng xác nhận; unknown: không tìm thấy"
    )
    drug_ids: list[str] = Field(
        default_factory=list, description="Hoạt chất dùng để tra cứu (biệt dược phối hợp có nhiều)"
    )
    drug_names: list[str] = Field(default_factory=list)
    suggestions: list[DrugSuggestion] = Field(
        default_factory=list, description="Ứng viên gần đúng, chưa dùng để tra cứu"
    )


class Mechanism(BaseModel):
    interaction_id: int
    severity: Severity
    severity_vi: str
    mechanism_type: str
    description: str
    management: str | None = None
    references: str
    source_id: str
    source_url: str


class FormNote(BaseModel):
    rule_id: str
    action: str
    severity: Severity
    drug_name: str
    drug_form: str
    effect_vi: str
    management_vi: str
    evidence: str
    source_id: str
    source_url: str


class PairResult(BaseModel):
    drug_ids: list[str]
    drug_names: list[str]
    inputs: list[str] = Field(..., description="Tên người dùng nhập ứng với hai hoạt chất")
    severity: Severity
    severity_vi: str
    mechanisms: list[Mechanism]
    form_notes: list[FormNote] = Field(default_factory=list)
    explanation: str = ""
    explanation_source: Literal["llm", "template", "none"] = "none"
    unsupported_claims: list[str] = Field(
        default_factory=list,
        description="Câu LLM viết ngoài bằng chứng CSDL, đã bị loại khỏi explanation (kèm lý do)",
    )
    guardrail_violations: list[str] = Field(
        default_factory=list, description="Vi phạm trong bản LLM (nếu có) khiến hệ thống dùng bản mẫu"
    )


class DuplicateNote(BaseModel):
    type: Literal["duplicate_active", "duplicate_class"]
    drug_ids: list[str]
    drug_names: list[str]
    inputs: list[str]
    class_name: str | None = None
    message: str


class Finding(BaseModel):
    type: Literal["interaction", "duplicate_active", "duplicate_class"]
    drug_ids: list[str]
    severity: Severity | None = None
    source_id: str | None = None
    record_id: str | None = None


class Citation(BaseModel):
    source_id: str
    record_id: str
    url: str


class InteractionCheckResponse(BaseModel):
    drugs: list[ResolvedDrug]
    pairs: list[PairResult] = Field(..., description="Các cặp có bản ghi, nặng nhất trước")
    duplicates: list[DuplicateNote] = Field(default_factory=list)
    no_record_pairs: list[list[str]] = Field(
        default_factory=list, description="Cặp (tên người dùng nhập) chưa có bản ghi trong CSDL"
    )
    notes: list[str] = Field(default_factory=list)
    summary: str
    disclaimer: str
    findings: list[Finding] = Field(default_factory=list, description="Định dạng giống eval/predictions.jsonl")
    citations: list[Citation] = Field(default_factory=list)
    llm_used: bool = False
