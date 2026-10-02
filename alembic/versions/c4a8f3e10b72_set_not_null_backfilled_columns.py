"""set NOT NULL on backfilled columns that models declare as non-Optional

Revision ID: c4a8f3e10b72
Revises: b7e2c1d94a30
Create Date: 2026-10-02

`drugs.n_products` va `fda_labels.n_labels` la `Mapped[int]` (khong Optional)
nen SQLAlchemy sinh NOT NULL khi `create_all`. Migration truoc ta them cot
nullable de an toan; sau khi backfill da day du thi ep NOT NULL de DB khop
model. Chay `python db/backfill_mvp_columns.py` truoc migration nay.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "c4a8f3e10b72"
down_revision: Union[str, Sequence[str], None] = "b7e2c1d94a30"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

COLUMNS = [
    ("drugs", "n_products"),
    ("fda_labels", "n_labels"),
]


def upgrade() -> None:
    for table, column in COLUMNS:
        nulls = op.get_bind().execute(
            sa.text(f'SELECT count(*) FROM "{table}" WHERE "{column}" IS NULL')  # noqa: S608
        ).scalar()
        if nulls:
            raise RuntimeError(
                f"{table}.{column} con {nulls} dong NULL: chay db/backfill_mvp_columns.py truoc"
            )
        op.alter_column(
            table, column, existing_type=sa.Integer(), nullable=False
        )


def downgrade() -> None:
    for table, column in COLUMNS:
        op.alter_column(table, column, existing_type=sa.Integer(), nullable=True)