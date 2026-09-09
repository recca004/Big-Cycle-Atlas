"""add observation identity unique constraint

Revision ID: a1c7e9b04d55
Revises: 937030256f0d
Create Date: 2026-09-08

Concurrent ingestion runs raced and inserted exact-duplicate vintage-1
observations (same country / source series / period). The duplicate rows
were removed; this constraint makes that failure mode impossible.
"""
from alembic import op
import sqlalchemy as sa


revision = "a1c7e9b04d55"
down_revision = "937030256f0d"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_unique_constraint(
        "uq_observations_identity",
        "observations",
        ["country_id", "source_series_id", "period_start", "vintage_number"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_observations_identity", "observations", type_="unique")