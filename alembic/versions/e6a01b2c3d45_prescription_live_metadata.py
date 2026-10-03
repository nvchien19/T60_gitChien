"""Persist prescription names and creation dates for live frontend."""
from alembic import op
import sqlalchemy as sa

revision = "e6a01b2c3d45"
down_revision = "d3f8a2c91e47"
branch_labels = None
depends_on = None

def upgrade():
    op.add_column("prescriptions", sa.Column("name", sa.Text(), nullable=False, server_default=""))
    # Existing records have no known creation date; keep it null.
    op.add_column("prescriptions", sa.Column("created_at", sa.DateTime(timezone=True), nullable=True))

def downgrade():
    with op.batch_alter_table("prescriptions") as batch:
        batch.drop_column("created_at")
        batch.drop_column("name")
