"""reviews HITL fields for FE ReviewView list (patient, med_count, VI status, timestamps)

Revision ID: d3f8a2c91e47
Revises: c4a8f3e10b72
Create Date: 2026-10-03

FE Trao doi duoc si doi tu form don (boolean local) sang danh sach yeu cau
da gui: can them snapshot `patient` + `med_count`, `status` tieng Viet
('Dang cho' | 'Da phan hoi') de hien thi truc tiep, va `created_at` /
`updated_at` de sap xep + audit. Cot moi them nullable truoc, backfill,
roi ep NOT NULL (tru `updated_at`) de khong pha du lieu dang co.
Du lieu cu `status='pending'` (mac dinh truoc day) -> 'Dang cho'.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "d3f8a2c91e47"
down_revision: Union[str, Sequence[str], None] = "c4a8f3e10b72"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

STATUS_VI = ("Đang chờ", "Đã phản hồi")


def upgrade() -> None:
    bind = op.get_bind()
    is_postgres = bind.dialect.name == "postgresql"

    op.add_column("reviews", sa.Column("patient", sa.Text(), nullable=True))
    op.add_column("reviews", sa.Column("med_count", sa.Integer(), nullable=True))
    op.add_column(
        "reviews", sa.Column("created_at", sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column(
        "reviews", sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True)
    )

    # --- backfill (update data) ---
    op.execute(
        sa.text("UPDATE reviews SET status='Đang chờ' WHERE status NOT IN ('Đang chờ','Đã phản hồi')")
    )
    op.execute(sa.text("UPDATE reviews SET patient='' WHERE patient IS NULL"))
    op.execute(sa.text("UPDATE reviews SET med_count=0 WHERE med_count IS NULL"))
    if is_postgres:
        op.execute(sa.text("UPDATE reviews SET created_at=now() WHERE created_at IS NULL"))
    else:
        op.execute(
            sa.text("UPDATE reviews SET created_at=CURRENT_TIMESTAMP WHERE created_at IS NULL")
        )

    # --- ep NOT NULL cho cac cot model khai non-Optional (batch: chay ca SQLite) ---
    with op.batch_alter_table("reviews") as batch:
        batch.alter_column("patient", existing_type=sa.Text(), nullable=False)
        batch.alter_column("med_count", existing_type=sa.Integer(), nullable=False)
        batch.alter_column("status", existing_type=sa.Text(), nullable=False)
        batch.alter_column(
            "created_at", existing_type=sa.DateTime(timezone=True), nullable=False
        )
        if is_postgres:
            batch.create_check_constraint(
                "ck_reviews_status", "status IN ('Đang chờ','Đã phản hồi')"
            )


def downgrade() -> None:
    bind = op.get_bind()
    with op.batch_alter_table("reviews") as batch:
        if bind.dialect.name == "postgresql":
            batch.drop_constraint("ck_reviews_status", type_="check")
        batch.drop_column("updated_at")
        batch.drop_column("created_at")
        batch.drop_column("med_count")
        batch.drop_column("patient")
