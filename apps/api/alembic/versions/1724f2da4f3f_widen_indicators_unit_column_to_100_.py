"""widen indicators unit column to 100 chars

Revision ID: 1724f2da4f3f
Revises: a1c7e9b04d55
Create Date: 2026-09-08 20:04:37.537301

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1724f2da4f3f'
down_revision: Union[str, Sequence[str], None] = 'a1c7e9b04d55'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.alter_column(
        "indicators",
        "unit",
        existing_type=sa.String(length=20),
        type_=sa.String(length=100),
        existing_nullable=True,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.alter_column(
        "indicators",
        "unit",
        existing_type=sa.String(length=100),
        type_=sa.String(length=20),
        existing_nullable=True,
    )
