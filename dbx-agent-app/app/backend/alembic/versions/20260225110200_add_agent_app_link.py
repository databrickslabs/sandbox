"""add agent app link

Revision ID: d1e2f3a4b5c6
Revises: c3d4e5f6a7b8
Create Date: 2026-02-25 11:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd1e2f3a4b5c6'
down_revision: Union[str, None] = 'c3d4e5f6a7b8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add app_id column to agents table
    op.add_column('agents', sa.Column('app_id', sa.Integer(), nullable=True))
    op.create_foreign_key('fk_agent_app', 'agents', 'apps', ['app_id'], ['id'], ondelete='CASCADE')


def downgrade() -> None:
    # Remove the foreign key and column
    op.drop_constraint('fk_agent_app', 'agents', type_='foreignkey')
    op.drop_column('agents', 'app_id')
