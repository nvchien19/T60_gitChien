"""Node `rank` — xếp mức nghiêm trọng deterministic (không LLM).

Mức lấy từ bản ghi nguồn; `no_record` tách riêng, không trộn vào thứ hạng.
"""

from typing import Any

from src.agents.state import AgentState
from src.tools.ranker import SEVERITY_VI, rank_findings


async def rank_node(state: AgentState) -> dict[str, Any]:
    records = state.get("interactions") or []
    merged, max_sev, _ = rank_findings(records)
    # hiển thị tên thuốc, không phải mã nội bộ
    no_record = [r.get("pair_names") or r["pair"] for r in records if r.get("match_type") == "no_record"]
    for item in merged:
        item.setdefault("severity_vi", SEVERITY_VI.get(item.get("severity", ""), ""))
    return {
        "ranked_findings": merged,
        "max_severity": max_sev,
        "no_record_pairs": no_record,
    }
