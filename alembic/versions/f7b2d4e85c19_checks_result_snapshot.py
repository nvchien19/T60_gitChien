"""checks.result: luu nguyen van ket qua kiem tra de truy vet

Revision ID: f7b2d4e85c19
Revises: e6a01b2c3d45
Create Date: 2026-10-04

GET /checks/{id} truoc day tra lai tu CSDL hien tai, nen lan kiem tra cu doi noi dung
moi khi du lieu tuong tac duoc cap nhat. Cot `result` giu CheckResponse luc chay kem
ngay cap nhat tung nguon. Nullable: ban ghi cu khong co ban luu.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "f7b2d4e85c19"
down_revision: str | Sequence[str] | None = "e6a01b2c3d45"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("checks", sa.Column("result", sa.JSON(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("checks") as batch:
        batch.drop_column("result")
