"""widen source_series external_code to 255 chars

Revision ID: a8f3c2d1e5b7
Revises: e3a7c94b1d51
Create Date: 2026-09-10 16:00:00.000000

Sprint 5.20.1: The exact OECD education provider identity
(agency,dataflow,version/key) exceeds the previous varchar(100) limit.
The old limit forced a synthetic abbreviation ("EAG_LSO_NEAC/...") that
discarded the agency and version components. Widening to varchar(255)
allows the full, traceable, provider-native identity to be stored
without truncation. No data semantics change — existing rows are
preserved exactly; only the column capacity changes.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a8f3c2d1e5b7'
down_revision: Union[str, Sequence[str], None] = 'e3a7c94b1d51'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema: widen source_series.external_code varchar(100) → 255."""
    op.alter_column(
        "source_series",
        "external_code",
        existing_type=sa.String(length=100),
        type_=sa.String(length=255),
        existing_nullable=False,
    )


def downgrade() -> None:
    """Downgrade schema: narrow source_series.external_code back to 100.

    CAUTION: rows with external_code longer than 100 chars (e.g. the exact
    OECD education identity) would be truncated or rejected. Downgrade is
    only safe if those rows have first been shortened.
    """
    op.alter_column(
        "source_series",
        "external_code",
        existing_type=sa.String(length=255),
        type_=sa.String(length=100),
        existing_nullable=False,
    )
