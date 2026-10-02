"""AgentState — hợp đồng dữ liệu đi qua LangGraph (ARCHITECTURE.md §6.1).

Mọi field đều optional (`total=False`): node chỉ set thứ nó chịu trách nhiệm.
Dữ liệu tra cứu (`catalog`, `interactions`) do `interface/backend/agent_adapter`
nạp từ DB rồi đưa vào state — lõi AI không bao giờ tự truy vấn DB.
"""

from __future__ import annotations

from typing import Any, TypedDict


class AgentState(TypedDict, total=False):
    # Input
    query: str
    raw_drugs: list[str]

    # Catalog do backend inject: {"aliases": [AliasRow...], "drug_names": {drug_id: name}}
    catalog: dict[str, Any]

    # Tra cứu — record thô từ CSDL (backend đã query sẵn)
    interactions: list[dict[str, Any]]
    duplicate_acts: list[dict[str, Any]]

    # Kết quả từng node
    normalized: list[dict[str, Any]]
    pending_clarifications: list[dict[str, Any]]
    ranked_findings: list[dict[str, Any]]
    no_record_pairs: list[list[str]]
    citations: list[dict[str, Any]]
    max_severity: str
    response: str
    analysis: str
    guardrail_result: dict[str, Any]

    # Routing / trace
    error: str
    metadata: dict[str, Any]
