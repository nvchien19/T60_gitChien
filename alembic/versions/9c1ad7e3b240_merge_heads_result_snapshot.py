"""Merge heads: auth_roles + checks.result snapshot.

Revision ID: 9c1ad7e3b240
Revises: a8c13d4e5f67, f7b2d4e85c19

Hai nhánh cùng tách từ e6a01b2c3d45 (f7b02c3d4e56→a8c13d4e5f67 và
f7b2d4e85c19) khiến `alembic upgrade head` lỗi multiple heads và DB thật
bị kẹt ở a8c13d4e5f67, thiếu cột checks.result → POST
/prescriptions/{id}/checks lỗi 500 (UndefinedColumn). Merge này không đổi
schema, chỉ gom đầu để upgrade áp dụng nốt f7b2d4e85c19.
"""

from collections.abc import Sequence

revision: str = "9c1ad7e3b240"
down_revision: str | Sequence[str] | None = ("a8c13d4e5f67", "f7b2d4e85c19")
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
