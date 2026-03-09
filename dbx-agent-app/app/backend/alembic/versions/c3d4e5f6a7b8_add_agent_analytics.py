"""add agent_analytics table

Revision ID: c3d4e5f6a7b8
Revises: b1e2f3a4c5d6
Create Date: 2026-02-24 23:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c3d4e5f6a7b8'
down_revision: Union[str, Sequence[str], None] = 'b1e2f3a4c5d6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add agent_analytics table for tracking per-invocation agent performance."""
    op.create_table('agent_analytics',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('agent_id', sa.Integer(), nullable=False),
        sa.Column('task_description', sa.Text(), nullable=True),
        sa.Column('success', sa.Integer(), server_default='1', nullable=True),
        sa.Column('latency_ms', sa.Integer(), nullable=True),
        sa.Column('quality_score', sa.Integer(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['agent_id'], ['agents.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_analytics_agent_id', 'agent_analytics', ['agent_id'], unique=False)
    op.create_index('idx_analytics_created_at', 'agent_analytics', ['created_at'], unique=False)


def downgrade() -> None:
    """Remove agent_analytics table."""
    op.drop_index('idx_analytics_created_at', table_name='agent_analytics')
    op.drop_index('idx_analytics_agent_id', table_name='agent_analytics')
    op.drop_table('agent_analytics')
