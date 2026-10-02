"""Node `rank` — xếp mức nghiêm trọng deterministic (không LLM).

Mức lấy từ bản ghi nguồn; `no_record` tách riêng, không trộn vào thứ hạng.
"""

from typing import Any

from src.agents.state import AgentState
from src.tools.ranker import SEVERITY_VI, rank_findings


async def rank_node(state: AgentState) -> dict[str, Any]:
    merged, max_sev, no_record = rank_findings(state.get("interactions") or [])
    for item in merged:
        item.setdefault("severity_vi", SEVERITY_VI.get(item.get("severity", ""), ""))
    return {
        "ranked_findings": merged,
        "max_severity": max_sev,
        "no_record_pairs": no_record,
    }
