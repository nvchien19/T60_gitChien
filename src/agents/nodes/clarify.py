"""Node `clarify` — dừng lại hỏi lại user khi còn thuốc `suggest`/`unknown`.

Không tự đoán: `suggest` bắt buộc người dùng xác nhận (ARCHITECTURE.md §7.3).
"""

from typing import Any

from src.agents.state import AgentState
from src.core.guardrails import DISCLAIMER, HANDOFF


async def clarify_node(state: AgentState) -> dict[str, Any]:
    pending = state.get("pending_clarifications") or []
    lines = ["Mình cần bạn xác nhận thêm trước khi tra cứu:"]
    for item in pending:
        sug = item.get("suggestions") or []
        options = "; ".join(
            f"{s.get('canonical_name') or s.get('drug_id')} ({round(float(s.get('score', 0)) * 100)}%)"
            for s in sug
        )
        if options:
            lines.append(f"- \"{item['input']}\" → có thể là: {options}")
        else:
            lines.append(f"- \"{item['input']}\" — chưa có bản ghi trong CSDL ({item.get('note', '')})")
    text = "\n".join([*lines, HANDOFF, DISCLAIMER])
    return {"response": text, "analysis": "\n".join(lines), "citations": []}
