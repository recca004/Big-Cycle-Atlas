"""initial

Revision ID: 2bf93faf72ce
Revises: 
Create Date: 2026-09-07 20:35:26.885920

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2bf93faf72ce'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'countries',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('iso3', sa.String(length=3), nullable=False),
        sa.Column('iso2', sa.String(length=2), nullable=False),
        sa.Column('name', sa.String(length=120), nullable=False),
        sa.Column('region', sa.String(length=60), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True),
                  server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_countries_iso3'), 'countries', ['iso3'], unique=True)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_countries_iso3'), table_name='countries')
    op.drop_table('countries')
