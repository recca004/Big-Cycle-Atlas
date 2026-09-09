"""widen source_series transform_notes to 2000 chars

Revision ID: 1389fa4e7ce0
Revises: 1724f2da4f3f
Create Date: 2026-09-08 20:05:38.070165

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1389fa4e7ce0'
down_revision: Union[str, Sequence[str], None] = '1724f2da4f3f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.alter_column(
        "source_series",
        "transform_notes",
        existing_type=sa.String(length=500),
        type_=sa.String(length=2000),
        existing_nullable=True,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.alter_column(
        "source_series",
        "transform_notes",
        existing_type=sa.String(length=2000),
        type_=sa.String(length=500),
        existing_nullable=True,
    )
