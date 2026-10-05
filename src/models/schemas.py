"""Schema Pydantic của lõi AI.

Định nghĩa thật nằm ở `interface.backend.schemas.chat` (sau khi tách lớp web).
Module này chỉ re-export, nên `from src.models.schemas import PairResult` vẫn chạy
đúng như trước và không tạo thêm nơi phải đồng bộ khi schema đổi.
"""

from interface.backend.schemas.chat import (
    ChatRequest,
    ChatResponse,
    Citation,
    DrugSuggestion,
    DuplicateNote,
    Finding,
    FormNote,
    InteractionCheckRequest,
    InteractionCheckResponse,
    Mechanism,
    PairResult,
    ResolvedDrug,
    Severity,
)

__all__ = [
    "ChatRequest",
    "ChatResponse",
    "Citation",
    "DrugSuggestion",
    "DuplicateNote",
    "Finding",
    "FormNote",
    "InteractionCheckRequest",
    "InteractionCheckResponse",
    "Mechanism",
    "PairResult",
    "ResolvedDrug",
    "Severity",
]
