"""Truy vấn CSDL tương tác thuốc (Postgres, schema `mvp`, nạp bằng db/load_mvp.py).

Chỉ đọc. Mọi kết luận về tương tác đều lấy từ các bảng/hàm trong db/mvp_schema.sql:
`mvp.find_drug` (chuẩn hóa tên), `mvp.interactions_among` (tương tác thuốc–thuốc),
`mvp.dosage_form_rules` (ghi chú theo dạng bào chế), `mvp.duplication_classes` (trùng nhóm thuốc).
"""

import asyncio
from dataclasses import dataclass
from typing import Protocol

import psycopg
from psycopg.rows import dict_row

from src.config import get_settings


@dataclass
class DrugMatch:
    drug_id: str
    drug_name: str
    alias: str
    alias_type: str
    status: str  # ok | suggest
    score: float


@dataclass
class Interaction:
    interaction_id: int
    drug_a: str
    drug_a_name: str
    drug_b: str
    drug_b_name: str
    severity: str
    severity_rank: int
    severity_vi: str
    mechanism_id: int
    mechanism_type: str
    description: str
    management: str | None
    references: str
    source_id: str
    source_url: str
    drug_a_name_vi: str | None = None
    drug_b_name_vi: str | None = None


@dataclass
class FormRule:
    rule_id: str
    drug_id: str
    drug_name: str
    drug_form: str
    other_drug_id: str
    other_drug_name: str
    severity: str
    action: str  # raise_severity | form_specific | no_interaction_for_form
    effect_vi: str
    management_vi: str
    evidence: str
    source_id: str
    source_url: str


@dataclass
class ClassMember:
    class_name: str
    drug_id: str
    drug_name: str
    max_concurrent: int


class DDIRepository(Protocol):
    async def find_drug(self, query: str, max_results: int = 5) -> list[DrugMatch]: ...

    async def interactions_among(self, drug_ids: list[str]) -> list[Interaction]: ...

    async def form_rules_among(self, drug_ids: list[str]) -> list[FormRule]: ...

    async def class_members(self, drug_ids: list[str]) -> list[ClassMember]: ...


SQL_FIND = """
SELECT drug_id, drug_name, alias, alias_type, status, score
FROM mvp.find_drug(%s, %s)
"""

SQL_INTERACTIONS = """
SELECT interaction_id, drug_a, drug_a_name, drug_a_name_vi, drug_b, drug_b_name, drug_b_name_vi,
       severity, severity_rank, severity_vi, mechanism_id, mechanism_type, description, management,
       "references" AS references, source_id, source_url
FROM mvp.interactions_among(%s)
"""

SQL_FORM_RULES = """
SELECT DISTINCT rule_id, drug_id, drug_name, drug_form, other_drug_id, other_drug_name, severity, action,
       effect_vi, management_vi, evidence, source_id, source_url
FROM mvp.dosage_form_rules
WHERE drug_id = ANY (%s) AND other_drug_id = ANY (%s)
ORDER BY rule_id, drug_name, other_drug_name
"""

SQL_CLASSES = """
SELECT DISTINCT class_name, drug_id, drug_name, max_concurrent
FROM mvp.duplication_classes
WHERE drug_id = ANY (%s)
ORDER BY class_name, drug_name
"""


class PostgresDDIRepository:
    """Mỗi lời gọi mở một kết nối ngắn; đủ cho MVP (chưa cần pool).

    Dùng psycopg đồng bộ trong thread vì chế độ async của psycopg không chạy trên ProactorEventLoop
    (event loop mặc định của Python trên Windows).
    """

    def __init__(self, dsn: str | None = None):
        self.dsn = dsn or get_settings().database_url

    def _fetch_sync(self, sql: str, params: tuple) -> list[dict]:
        with psycopg.connect(self.dsn, row_factory=dict_row, connect_timeout=5) as conn:
            return conn.execute(sql, params).fetchall()

    async def _fetch(self, sql: str, params: tuple) -> list[dict]:
        return await asyncio.to_thread(self._fetch_sync, sql, params)

    async def find_drug(self, query: str, max_results: int = 5) -> list[DrugMatch]:
        rows = await self._fetch(SQL_FIND, (query, max_results))
        return [DrugMatch(**r) for r in rows]

    async def interactions_among(self, drug_ids: list[str]) -> list[Interaction]:
        if len(drug_ids) < 2:
            return []
        rows = await self._fetch(SQL_INTERACTIONS, (drug_ids,))
        return [Interaction(**r) for r in rows]

    async def form_rules_among(self, drug_ids: list[str]) -> list[FormRule]:
        if len(drug_ids) < 2:
            return []
        rows = await self._fetch(SQL_FORM_RULES, (drug_ids, drug_ids))
        return [FormRule(**r) for r in rows]

    async def class_members(self, drug_ids: list[str]) -> list[ClassMember]:
        if len(drug_ids) < 2:
            return []
        rows = await self._fetch(SQL_CLASSES, (drug_ids,))
        return [ClassMember(**r) for r in rows]


def get_repository() -> DDIRepository:
    return PostgresDDIRepository()
