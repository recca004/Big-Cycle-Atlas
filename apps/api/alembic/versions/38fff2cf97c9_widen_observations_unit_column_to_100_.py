"""widen observations unit column to 100 chars

Revision ID: 38fff2cf97c9
Revises: 1389fa4e7ce0
Create Date: 2026-09-08 20:07:59.907322

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '38fff2cf97c9'
down_revision: Union[str, Sequence[str], None] = '1389fa4e7ce0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.alter_column(
        "observations",
        "unit",
        existing_type=sa.String(length=20),
        type_=sa.String(length=100),
        existing_nullable=True,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.alter_column(
        "observations",
        "unit",
        existing_type=sa.String(length=100),
        type_=sa.String(length=20),
        existing_nullable=True,
    )
