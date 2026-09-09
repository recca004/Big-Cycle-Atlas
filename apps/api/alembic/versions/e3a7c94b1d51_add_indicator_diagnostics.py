"""add indicator_diagnostics

Revision ID: e3a7c94b1d51
Revises: 38fff2cf97c9
Create Date: 2026-09-09 14:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e3a7c94b1d51'
down_revision: Union[str, Sequence[str], None] = '38fff2cf97c9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema: auxiliary indicator diagnostics (DEC-022).

    No series foreign key and no changes to observations, source_series,
    or indicators.
    """
    op.create_table('indicator_diagnostics',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('country_id', sa.Integer(), nullable=False),
    sa.Column('indicator_id', sa.Integer(), nullable=False),
    sa.Column('data_source_id', sa.Integer(), nullable=False),
    sa.Column('diagnostic_kind', sa.String(length=30), nullable=False),
    sa.Column('provider_source_code', sa.String(length=50), nullable=False),
    sa.Column('provider_series_code', sa.String(length=100), nullable=False),
    sa.Column('period_start', sa.DateTime(timezone=True), nullable=False),
    sa.Column('value', sa.Float(), nullable=False),
    sa.Column('retrieved_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('vintage_number', sa.Integer(), nullable=False),
    sa.Column('raw_payload', sa.JSON(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.ForeignKeyConstraint(['country_id'], ['countries.id'], ),
    sa.ForeignKeyConstraint(['data_source_id'], ['data_sources.id'], ),
    sa.ForeignKeyConstraint(['indicator_id'], ['indicators.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('country_id', 'indicator_id', 'data_source_id', 'provider_source_code', 'provider_series_code', 'diagnostic_kind', 'period_start', 'vintage_number', name='uq_indicator_diagnostics_identity')
    )
    op.create_index(op.f('ix_indicator_diagnostics_country_id'), 'indicator_diagnostics', ['country_id'], unique=False)
    op.create_index(op.f('ix_indicator_diagnostics_data_source_id'), 'indicator_diagnostics', ['data_source_id'], unique=False)
    op.create_index(op.f('ix_indicator_diagnostics_indicator_id'), 'indicator_diagnostics', ['indicator_id'], unique=False)
    op.create_index(op.f('ix_indicator_diagnostics_period_start'), 'indicator_diagnostics', ['period_start'], unique=False)
    op.create_index('ix_indicator_diagnostics_lookup', 'indicator_diagnostics', ['country_id', 'indicator_id', 'diagnostic_kind', 'period_start'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_indicator_diagnostics_lookup', table_name='indicator_diagnostics')
    op.drop_index(op.f('ix_indicator_diagnostics_period_start'), table_name='indicator_diagnostics')
    op.drop_index(op.f('ix_indicator_diagnostics_indicator_id'), table_name='indicator_diagnostics')
    op.drop_index(op.f('ix_indicator_diagnostics_data_source_id'), table_name='indicator_diagnostics')
    op.drop_index(op.f('ix_indicator_diagnostics_country_id'), table_name='indicator_diagnostics')
    op.drop_table('indicator_diagnostics')