"""Cầu nối backend → lõi AI.

Đây là **nơi duy nhất** trong `interface/backend` được import `src.*`. Nhờ đó ranh giới
phụ thuộc giữ được một chiều: `interface.backend → src`, `src` không import ngược lại.

Trách nhiệm:
  1. Nạp catalog (aliases + tên thuốc) từ DB → inject vào `AgentState.catalog`.
  2. Tra bản ghi tương tác từ CSDL → inject vào `AgentState.interactions`.
  3. Lấy graph đã compile (`get_agent()`) và `ainvoke`.

Lõi AI không bao giờ tự truy vấn DB, không ghi DB.

`langgraph` là dependency **mềm**: thiếu nó thì `agent_available()` trả False và
`/chat` trả 503, phần còn lại của API vẫn boot.
"""

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from interface.backend.services.check_service import (
    fetch_interaction_records,
    load_catalog,
    normalize_list,
)
from src.agents.nodes.normalize import split_drugs

__all__ = ["run_agent", "get_agent", "agent_available"]

_AGENT_IMPORT_ERROR: str | None = None


def get_agent():
    """Lazy import + proxy của `src.agents.graph.get_agent`."""
    global _AGENT_IMPORT_ERROR
    try:
        from src.agents.graph import get_agent as _get_agent
    except Exception as e:  # thieu langgraph -> P0 van chay exact-match
        _AGENT_IMPORT_ERROR = str(e)
        return None
    _AGENT_IMPORT_ERROR = None
    return _get_agent()


def agent_available() -> bool:
    """True nếu LangGraph cài được — dùng cho `/status` và `/chat`."""
    return get_agent() is not None


async def run_agent(db: AsyncSession, query: str,
                    drug_names: list[str] | None = None) -> dict[str, Any]:
    """Chạy agent cho một câu hỏi, nạp trước dữ liệu tra cứu từ DB."""
    agent = get_agent()
    if agent is None:
        raise RuntimeError(f"Agent chưa sẵn sàng: {_AGENT_IMPORT_ERROR}")

    raw_drugs = drug_names or split_drugs(query)
    aliases, drug_name_map = await load_catalog(db)

    # Agent chỉ nhận `interactions` cho các cặp đã biết drug_id — chuẩn hóa ở đây
    # (backend được phép đọc DB; lõi AI thì không).
    normalized = await normalize_list(db, raw_drugs)
    ok_ids = [n.drug_id for n in normalized if n.status == "ok" and n.drug_id]
    name_by_id = {n.drug_id: (n.canonical_name or n.input) for n in normalized if n.drug_id}
    records = await fetch_interaction_records(db, ok_ids, name_by_id) if len(ok_ids) >= 2 else []

    state: dict[str, Any] = {
        "query": query,
        "raw_drugs": raw_drugs,
        "catalog": {"aliases": aliases, "drug_names": drug_name_map},
        "interactions": records,
        "metadata": {},
    }
    return await agent.ainvoke(state)
