"""Node `guardrail` — cổng chặn cuối trong graph (rule-based, không LLM).

Luôn set `guardrail_result` để router đọc được — tránh nhánh END sớm chạy lệch.
Guardrail tầng 2 (response middleware) nằm ở `interface/backend/api/middleware/`.
"""

from typing import Any

from src.agents.state import AgentState
from src.core.guardrails import guardrail_assert, sanitize_text

MAX_EXPLAIN_RETRIES = 2


async def guardrail_node(state: AgentState) -> dict[str, Any]:
    findings = state.get("ranked_findings") or []

    dropped = len(findings) - len(guardrail_assert([dict(f) for f in findings]))
    kept = guardrail_assert([dict(f) for f in findings])

    ungrounded = [f for f in kept if not (f.get("citations") or [])]
    retried = int(state.get("metadata", {}).get("explain_retries", 0))

    passed = not ungrounded
    reason = ""
    if ungrounded:
        reason = f"{len(ungrounded)} finding thiếu citation nguồn"

    # Response phải được lọc theo ngữ cảnh: nếu cặp nào chưa có bản ghi thì cấm
    # mọi khẳng định "an toàn", kể cả trong chính NO_RECORD_MSG.
    is_no_record = bool(state.get("no_record_pairs")) or not findings

    return {
        "ranked_findings": kept,
        "response": sanitize_text(state.get("response", ""), is_no_record=is_no_record),
        "guardrail_result": {
            "pass": passed,
            "violations": [] if passed else ["missing_citation"],
            "reason": reason,
            "dropped_findings": max(0, dropped),
            "explain_retries": retried,
        },
        "metadata": {"explain_retries": retried, "dropped_findings": max(0, dropped)},
    }


def needs_retry(state: AgentState) -> str:
    """Fail → quay lại `explain` (giới hạn số lần bằng `explain_retries`)."""
    if state.get("guardrail_result", {}).get("pass"):
        return "end"
    if state["metadata"].get("explain_retries", 0) >= MAX_EXPLAIN_RETRIES:
        return "end"
    return "explain"
