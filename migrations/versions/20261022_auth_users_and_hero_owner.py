"""Add Week 11 users, hero ownership, and missing Week 10 timestamps.

Revision ID: 20261022_auth
Revises: 4158b1105b0d
"""

from alembic import op
import sqlalchemy as sa

revision = "20261022_auth"
down_revision = "4158b1105b0d"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "user",
        sa.Column("username", sa.String(), nullable=False),
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("hashed_password", sa.String(), nullable=False),
        sa.Column("role", sa.Enum("user", "admin", name="role"), nullable=False),
    )
    op.create_index("ix_user_username", "user", ["username"], unique=True)

    # The old status migration allowed NULL, but HeroPublic requires a valid enum.
    op.execute("UPDATE hero SET status = 'active' WHERE status IS NULL")
    sqlite = op.get_bind().dialect.name == "sqlite"
    with op.batch_alter_table("hero", recreate="always" if sqlite else "auto") as batch:
        batch.alter_column(
            "status",
            existing_type=sa.Enum("active", "retired", name="herostatus"),
            nullable=False,
        )
        batch.add_column(sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False,
            server_default=sa.func.now(),
        ))
        # Legacy heroes remain unowned: only an admin may modify them.
        batch.add_column(sa.Column("owner_id", sa.Integer(), nullable=True))
        batch.create_foreign_key("fk_hero_owner_id_user", "user", ["owner_id"], ["id"])


def downgrade() -> None:
    with op.batch_alter_table("hero") as batch:
        batch.drop_constraint("fk_hero_owner_id_user", type_="foreignkey")
        batch.drop_column("owner_id")
        batch.drop_column("created_at")
        batch.alter_column(
            "status",
            existing_type=sa.Enum("active", "retired", name="herostatus"),
            nullable=True,
        )
    op.drop_index("ix_user_username", table_name="user")
    op.drop_table("user")
    if op.get_bind().dialect.name == "postgresql":
        sa.Enum("user", "admin", name="role").drop(op.get_bind(), checkfirst=True)
