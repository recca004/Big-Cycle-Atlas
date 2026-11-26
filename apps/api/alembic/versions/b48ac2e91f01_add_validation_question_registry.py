"""add validation question registry

Revision ID: b48ac2e91f01
Revises: f30725ab4c2d
Create Date: 2026-11-26 00:15:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b48ac2e91f01'
down_revision: Union[str, Sequence[str], None] = 'f30725ab4c2d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'validation_questions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('question_code', sa.String(length=12), nullable=False),
        sa.Column('registry_version', sa.String(length=40), nullable=False),
        sa.Column('category', sa.String(length=60), nullable=False),
        sa.Column('original_question', sa.Text(), nullable=False),
        sa.Column('short_title', sa.String(length=120), nullable=False),
        sa.Column('theory_claims', sa.JSON(), nullable=False),
        sa.Column('related_forces', sa.JSON(), nullable=False),
        sa.Column('related_power_measures', sa.JSON(), nullable=False),
        sa.Column('required_datasets', sa.JSON(), nullable=False),
        sa.Column('available_datasets', sa.JSON(), nullable=False),
        sa.Column('missing_datasets', sa.JSON(), nullable=False),
        sa.Column('historical_coverage', sa.JSON(), nullable=False),
        sa.Column('country_coverage', sa.JSON(), nullable=False),
        sa.Column('existing_research_methods', sa.JSON(), nullable=False),
        sa.Column('supporting_evidence', sa.JSON(), nullable=False),
        sa.Column('contradictory_evidence', sa.JSON(), nullable=False),
        sa.Column('alternative_explanations', sa.JSON(), nullable=False),
        sa.Column('falsification_criteria', sa.Text(), nullable=False),
        sa.Column('scientific_limitations', sa.JSON(), nullable=False),
        sa.Column('source_references', sa.JSON(), nullable=False),
        sa.Column('implementation_status', sa.String(length=80), nullable=False),
        sa.Column('research_validation_status', sa.String(length=100), nullable=False),
        sa.Column('current_answer', sa.Text(), nullable=False),
        sa.Column('related_hypotheses', sa.JSON(), nullable=False),
        sa.Column('chart', sa.JSON(), nullable=True),
        sa.Column('previous_implementation_status', sa.String(length=80), nullable=False),
        sa.Column('last_reviewed_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('methodology_version', sa.String(length=80), nullable=False),
        sa.Column('content_checksum', sa.String(length=64), nullable=False),
        sa.Column('raw_payload', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('question_code', 'registry_version', name='uq_validation_question_version'),
    )
    op.create_index(op.f('ix_validation_questions_category'), 'validation_questions', ['category'], unique=False)
    op.create_index('ix_validation_questions_category_status', 'validation_questions', ['category', 'implementation_status', 'research_validation_status'], unique=False)
    op.create_index(op.f('ix_validation_questions_content_checksum'), 'validation_questions', ['content_checksum'], unique=False)
    op.create_index(op.f('ix_validation_questions_implementation_status'), 'validation_questions', ['implementation_status'], unique=False)
    op.create_index(op.f('ix_validation_questions_last_reviewed_at'), 'validation_questions', ['last_reviewed_at'], unique=False)
    op.create_index(op.f('ix_validation_questions_question_code'), 'validation_questions', ['question_code'], unique=False)
    op.create_index(op.f('ix_validation_questions_registry_version'), 'validation_questions', ['registry_version'], unique=False)
    op.create_index(op.f('ix_validation_questions_research_validation_status'), 'validation_questions', ['research_validation_status'], unique=False)
    op.create_index(op.f('ix_validation_questions_short_title'), 'validation_questions', ['short_title'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_validation_questions_short_title'), table_name='validation_questions')
    op.drop_index(op.f('ix_validation_questions_research_validation_status'), table_name='validation_questions')
    op.drop_index(op.f('ix_validation_questions_registry_version'), table_name='validation_questions')
    op.drop_index(op.f('ix_validation_questions_question_code'), table_name='validation_questions')
    op.drop_index(op.f('ix_validation_questions_last_reviewed_at'), table_name='validation_questions')
    op.drop_index(op.f('ix_validation_questions_implementation_status'), table_name='validation_questions')
    op.drop_index(op.f('ix_validation_questions_content_checksum'), table_name='validation_questions')
    op.drop_index('ix_validation_questions_category_status', table_name='validation_questions')
    op.drop_index(op.f('ix_validation_questions_category'), table_name='validation_questions')
    op.drop_table('validation_questions')
