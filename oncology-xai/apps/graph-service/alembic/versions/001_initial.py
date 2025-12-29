"""Initial migration - case_graph_snapshots table

Revision ID: 001
Revises:
Create Date: 2024-01-01 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create case_graph_snapshots table
    op.create_table(
        'case_graph_snapshots',
        sa.Column('graph_snapshot_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('case_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('nodes', postgresql.JSONB(), nullable=False),
        sa.Column('edges', postgresql.JSONB(), nullable=False),
        sa.Column('layout', postgresql.JSONB(), nullable=False),
        sa.Column('depth', sa.Integer(), nullable=False),
        sa.Column('include_inferred', sa.Boolean(), nullable=False),
        sa.Column('metadata', postgresql.JSONB(), nullable=False),
        sa.Column('task_id', sa.String(255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('graph_snapshot_id'),
        sa.Comment('Stores complete graph snapshots including nodes, edges, layout, and metadata'),
    )

    # Create indexes
    op.create_index('ix_case_graph_snapshots_case_id', 'case_graph_snapshots', ['case_id'])
    op.create_index(
        'ix_case_graph_snapshots_case_depth_inferred',
        'case_graph_snapshots',
        ['case_id', 'depth', 'include_inferred'],
    )


def downgrade() -> None:
    op.drop_table('case_graph_snapshots')
