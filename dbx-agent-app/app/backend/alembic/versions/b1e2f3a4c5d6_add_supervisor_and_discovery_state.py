"""add supervisor and discovery_state tables

Revision ID: b1e2f3a4c5d6
Revises: 423f4a48143d
Create Date: 2026-02-18 10:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b1e2f3a4c5d6'
down_revision: Union[str, Sequence[str], None] = '423f4a48143d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add supervisors and discovery_state tables."""
    op.create_table('supervisors',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('collection_id', sa.Integer(), nullable=False),
        sa.Column('app_name', sa.String(length=255), nullable=False),
        sa.Column('generated_at', sa.DateTime(), nullable=False),
        sa.Column('deployed_url', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['collection_id'], ['collections.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_supervisor_collection_id', 'supervisors', ['collection_id'], unique=False)
    op.create_index('idx_supervisor_app_name', 'supervisors', ['app_name'], unique=False)
    op.create_index(op.f('ix_supervisors_id'), 'supervisors', ['id'], unique=False)

    op.create_table('discovery_state',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('is_running', sa.Boolean(), nullable=False),
        sa.Column('last_run_timestamp', sa.String(length=64), nullable=True),
        sa.Column('last_run_status', sa.String(length=32), nullable=True),
        sa.Column('last_run_message', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )


def downgrade() -> None:
    """Remove supervisors and discovery_state tables."""
    op.drop_table('discovery_state')
    op.drop_index(op.f('ix_supervisors_id'), table_name='supervisors')
    op.drop_index('idx_supervisor_app_name', table_name='supervisors')
    op.drop_index('idx_supervisor_collection_id', table_name='supervisors')
    op.drop_table('supervisors')
