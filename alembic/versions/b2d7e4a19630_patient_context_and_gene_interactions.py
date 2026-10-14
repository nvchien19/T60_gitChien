"""Store patient context and CPIC gene interactions."""

import sqlalchemy as sa

from alembic import op

revision = "b2d7e4a19630"
down_revision = "9c1ad7e3b240"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("prescriptions", sa.Column("patient_context", sa.JSON(), nullable=True))
    op.create_table(
        "gene_interactions",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=False),
        sa.Column("drug_id", sa.String(), sa.ForeignKey("drugs.drug_id"), nullable=True),
        sa.Column("drug_name", sa.Text(), nullable=False),
        sa.Column("genes", sa.JSON(), nullable=False),
        sa.Column("lookupkey", sa.JSON(), nullable=False),
        sa.Column("implication_text", sa.Text()),
        sa.Column("recommendation", sa.Text()),
        sa.Column("classification", sa.Text()),
        sa.Column("population", sa.Text()),
        sa.Column("comments", sa.Text()),
        sa.Column("guideline_name", sa.Text()),
        sa.Column("guideline_url", sa.Text()),
        sa.Column("source_id", sa.String(), sa.ForeignKey("sources.source_id"), nullable=False),
    )
    op.create_index("ix_gene_interactions_drug_id", "gene_interactions", ["drug_id"])


def downgrade() -> None:
    op.drop_index("ix_gene_interactions_drug_id", table_name="gene_interactions")
    op.drop_table("gene_interactions")
    with op.batch_alter_table("prescriptions") as batch:
        batch.drop_column("patient_context")
