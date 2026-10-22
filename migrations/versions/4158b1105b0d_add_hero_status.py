"""add hero status

Revision ID: 4158b1105b0d
Revises: 59b9ed58da4a
Create Date: 2026-10-08 16:52:14.581525

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4158b1105b0d'
down_revision: Union[str, Sequence[str], None] = '59b9ed58da4a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    hero_status = sa.Enum(
        "active",
        "retired",
        name="herostatus",
    )

    if op.get_bind().dialect.name == "postgresql":
        hero_status.create(op.get_bind(), checkfirst=True)

    op.add_column(
        "hero",
        sa.Column(
            "status",
            hero_status,
            nullable=True
        )
    )


def downgrade() -> None:
    op.drop_column("hero", "status")

    hero_status = sa.Enum(
        "active",
        "retired",
        name="herostatus",
    )

    if op.get_bind().dialect.name == "postgresql":
        hero_status.drop(op.get_bind(), checkfirst=True)
