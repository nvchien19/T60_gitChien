"""add missing MVP columns to match db/mvp_schema.sql

Revision ID: b7e2c1d94a30
Revises: 1fc1afa9e06f
Create Date: 2026-10-02

Cot moi them deu nullable de khong pha du lieu dang co.
Cot co chu dich rieng trong models (id surrogate PK, embedding) giu nguyen.
Gia tri duoc backfill tu data/mvp/*.csv boi db/backfill_mvp_columns.py
(data/ bi .gitignore nen migration khong duoc phu thuoc CSV).
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "b7e2c1d94a30"
down_revision: Union[str, Sequence[str], None] = "1fc1afa9e06f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

NEW_COLUMNS = {
    "drugs": [
        ("source_id", sa.Text()),
        ("n_products", sa.Integer()),
    ],
    "products": [
        ("packaging", sa.Text()),
    ],
    "food_interactions": [
        ("drug_name", sa.Text()),
    ],
    "disease_interactions": [
        ("drug_name", sa.Text()),
    ],
    "ara_interactions": [
        ("victim", sa.Text()),
        ("ara_text", sa.Text()),
    ],
    "pk_ddi": [
        ("perpetrator_name", sa.Text()),
        ("victim_name", sa.Text()),
        ("perpetrator_drugbank", sa.Text()),
        ("victim_drugbank", sa.Text()),
    ],
    "fda_labels": [
        ("product_type", sa.Text()),
        ("all_substances_mapped", sa.Boolean()),
        ("do_not_use", sa.Text()),
        ("ask_doctor_or_pharmacist", sa.Text()),
        ("n_labels", sa.Integer()),
        ("source_url", sa.Text()),
    ],
    "dosage_form_rules": [
        ("drug_name", sa.Text()),
        ("other_drug_name", sa.Text()),
    ],
}


def upgrade() -> None:
    for table, columns in NEW_COLUMNS.items():
        for name, type_ in columns:
            op.add_column(table, sa.Column(name, type_, nullable=True))

    op.create_table(
        "ingredient_map",
        sa.Column("key", sa.Text(), nullable=False),
        sa.Column("example_name", sa.Text(), nullable=False),
        sa.Column("n_products", sa.Integer(), nullable=False),
        sa.Column("method", sa.Text(), nullable=False),
        sa.Column("score", sa.Integer(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("drug_ids", sa.Text()),
        sa.Column("drug_names", sa.Text()),
        sa.Column("dav_drug_id", sa.String()),
        sa.PrimaryKeyConstraint("key", name=op.f("pk_ingredient_map")),
    )
    op.create_index(
        "ix_ingredient_map_dav_drug_id", "ingredient_map", ["dav_drug_id"], unique=False
    )


def downgrade() -> None:
    op.drop_index("ix_ingredient_map_dav_drug_id", table_name="ingredient_map")
    op.drop_table("ingredient_map")
    for table, columns in NEW_COLUMNS.items():
        for name, _ in reversed(columns):
            op.drop_column(table, name)