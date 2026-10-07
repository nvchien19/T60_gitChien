"""Node `explain` — diễn giải tiếng Việt dễ hiểu, mọi kết luận kèm citation.

Deterministic: chỉ dùng dữ liệu đã truy xuất, không suy diễn từ trí nhớ mô hình.
Disclaimer gắn cứng, không tắt được.
"""

from typing import Any

from src.agents.state import AgentState
from src.core.guardrails import DISCLAIMER, HANDOFF, NO_RECORD_MSG
from src.tools.ranker import SEVERITY_VI

SYMBOL = {"contraindicated": "⛔", "major": "!", "moderate": "△", "minor": "·",
          "duplicate_class": "=", "duplicate_active": "="}


async def explain_node(state: AgentState) -> dict[str, Any]:
    findings = state.get("ranked_findings") or []

    citations: list[dict[str, Any]] = []
    index: dict[tuple, int] = {}

    def cite(c: dict[str, Any]) -> str:
        key = (c.get("source_id"), c.get("source_url"), c.get("label"), c.get("record_id"))
        if key not in index:
            index[key] = len(citations) + 1
            citations.append(c)
        return f"[{index[key]}]"

    lines: list[str] = []
    if findings:
        for f in findings:
            sev = f.get("severity", "unknown")
            names = f.get("pair_names") or f.get("pair") or []
            symbol = SYMBOL.get(sev, "!")
            summary = (f.get("summary") or f.get("mechanism") or "").strip()
            marks = "".join(cite(c) for c in (f.get("citations") or []))
            lines.append(
                f"{symbol} {', '.join(names)} — {SEVERITY_VI.get(sev, sev)}. {summary} {marks}".strip()
            )
    else:
        lines.append(NO_RECORD_MSG)

    if state.get("no_record_pairs"):
        pairs = "; ".join(", ".join(p) for p in state["no_record_pairs"])
        lines.append(f"Chưa có bản ghi trong CSDL cho: {pairs}.")

    body = "\n".join(lines)
    text = "\n".join([body, HANDOFF, DISCLAIMER]) if findings else "\n".join([body, DISCLAIMER])

    return {
        "response": text,
        "citations": citations,
        "analysis": body,
        "max_severity_vi": SEVERITY_VI.get(state.get("max_severity", ""), ""),
    }
