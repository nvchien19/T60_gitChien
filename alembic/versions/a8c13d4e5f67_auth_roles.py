"""User accounts, sessions and doctor review responses."""
import sqlalchemy as sa

from alembic import op

revision = "a8c13d4e5f67"
down_revision = "f7b02c3d4e56"
branch_labels = None
depends_on = None


def upgrade():
    # Development startup may have created the new tables before Alembic runs.
    inspector = sa.inspect(op.get_bind())
    for table, expected in {
        "users": {"id", "email", "name", "role", "password_hash", "active"},
        "auth_sessions": {"token_hash", "user_id", "expires_at"},
    }.items():
        if inspector.has_table(table):
            actual = {column["name"] for column in inspector.get_columns(table)}
            if not expected <= actual:
                raise RuntimeError(f"Existing {table} table does not match the authentication schema")
    if not inspector.has_table("users"):
        op.create_table("users",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("email", sa.String(254), nullable=False, unique=True),
            sa.Column("name", sa.String(150), nullable=False),
            sa.Column("role", sa.String(20), nullable=False),
            sa.Column("password_hash", sa.Text(), nullable=False),
            sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.CheckConstraint("role IN ('doctor','pharmacist')", name="ck_users_role"))
    if not inspector.has_table("auth_sessions"):
        op.create_table("auth_sessions",
            sa.Column("token_hash", sa.String(64), primary_key=True),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False))
    inspector = sa.inspect(op.get_bind())
    indexes = {index["name"] for index in inspector.get_indexes("auth_sessions")}
    for column in ("user_id", "expires_at"):
        if f"ix_auth_sessions_{column}" not in indexes:
            op.create_index(f"ix_auth_sessions_{column}", "auth_sessions", [column])
    columns = {column["name"] for column in inspector.get_columns("reviews")}
    foreign_keys = {fk["name"] for fk in inspector.get_foreign_keys("reviews")}
    indexes = {index["name"] for index in inspector.get_indexes("reviews")}
    with op.batch_alter_table("reviews") as batch:
        for column in (
            sa.Column("created_by", sa.Integer(), nullable=True),
            sa.Column("creator_name", sa.Text(), nullable=False, server_default=""),
            sa.Column("response", sa.Text(), nullable=False, server_default=""),
            sa.Column("responded_by", sa.Integer(), nullable=True),
            sa.Column("responder_name", sa.Text(), nullable=False, server_default=""),
        ):
            if column.name not in columns:
                batch.add_column(column)
        for column in ("created_by", "responded_by"):
            constraint = f"fk_reviews_{column}_users"
            if constraint not in foreign_keys:
                batch.create_foreign_key(constraint, "users", [column], ["id"])
        if "ix_reviews_created_by" not in indexes:
            batch.create_index("ix_reviews_created_by", ["created_by"])


def downgrade():
    with op.batch_alter_table("reviews") as batch:
        batch.drop_index("ix_reviews_created_by")
        batch.drop_constraint("fk_reviews_created_by_users", type_="foreignkey")
        batch.drop_constraint("fk_reviews_responded_by_users", type_="foreignkey")
        for name in ["responder_name", "responded_by", "response", "creator_name", "created_by"]:
            batch.drop_column(name)
    op.drop_table("auth_sessions")
    op.drop_table("users")
