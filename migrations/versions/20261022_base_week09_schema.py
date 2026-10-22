"""Baseline Week 9 schema, before the power and status columns.

Revision ID: 20261022_base
Revises:
"""

from alembic import op
import sqlalchemy as sa

revision = "20261022_base"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "team",
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("headquarters", sa.String(), nullable=False),
        sa.Column("id", sa.Integer(), primary_key=True),
    )
    op.create_index("ix_team_name", "team", ["name"], unique=True)
    op.create_table(
        "mission",
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("id", sa.Integer(), primary_key=True),
    )
    op.create_table(
        "hero",
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("age", sa.Integer(), nullable=True),
        sa.Column("team_id", sa.Integer(), sa.ForeignKey("team.id"), nullable=True),
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("secret_name", sa.String(), nullable=False),
    )
    op.create_index("ix_hero_name", "hero", ["name"])
    op.create_table(
        "heromissionlink",
        sa.Column("hero_id", sa.Integer(), sa.ForeignKey("hero.id"), primary_key=True),
        sa.Column("mission_id", sa.Integer(), sa.ForeignKey("mission.id"), primary_key=True),
    )


def downgrade() -> None:
    op.drop_table("heromissionlink")
    op.drop_index("ix_hero_name", table_name="hero")
    op.drop_table("hero")
    op.drop_table("mission")
    op.drop_index("ix_team_name", table_name="team")
    op.drop_table("team")
