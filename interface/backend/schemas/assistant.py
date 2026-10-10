"""Validated contract for the evidence-only medication assistant."""
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from interface.backend.schemas.ddi import Citation, FindingOut


class ConversationTurn(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=3000)


class AssistantRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    prescription_id: str = Field(default="", max_length=100)
    check_id: str = Field(default="", max_length=100)
    message: str = Field(min_length=1, max_length=5000)
    history: list[ConversationTurn] = Field(default_factory=list, max_length=8)

    @field_validator("message")
    @classmethod
    def nonempty(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Nhập câu hỏi về kết quả kiểm tra")
        return value


class AssistantResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    reply: str
    mode: Literal["evidence-only"] = "evidence-only"
    status: Literal["answered", "needs_clarification", "no_evidence", "out_of_scope"]
    check_id: str = ""
    findings: list[FindingOut] = Field(default_factory=list)
    citations: list[Citation] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    llm_used: bool = False
    fallback_reason: Literal["", "not_configured", "not_applicable", "privacy_blocked", "context_limit",
                             "no_supported_answer", "unsafe_output", "ungrounded_output",
                             "unverified_output", "provider_unavailable", "ambiguous_question",
                             "out_of_scope_question", "treatment_request", "irrelevant_answer"] = ""
    disclaimer: str
