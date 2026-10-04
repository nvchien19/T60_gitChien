"""Keep Vietnamese translations separately from reloadable source tables."""
from alembic import op
import sqlalchemy as sa

revision = "f7b02c3d4e56"
down_revision = "e6a01b2c3d45"
branch_labels = None
depends_on = None

def upgrade():
    op.create_table("content_translations",
        sa.Column("source_table", sa.String(), nullable=False),
        sa.Column("source_id", sa.String(), nullable=False),
        sa.Column("field", sa.String(), nullable=False),
        sa.Column("language", sa.String(), nullable=False),
        sa.Column("source_hash", sa.String(64), nullable=False),
        sa.Column("translated_text", sa.Text(), nullable=False),
        sa.Column("provider", sa.String(), nullable=False),
        sa.Column("reviewed", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("source_table", "source_id", "field", "language"))

def downgrade():
    op.drop_table("content_translations")
