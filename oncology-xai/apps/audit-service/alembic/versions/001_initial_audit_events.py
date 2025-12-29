"""Initial audit events table

Revision ID: 001
Revises:
Create Date: 2025-01-15 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create audit_events table
    op.create_table(
        'audit_events',
        sa.Column('event_id', postgresql.UUID(), nullable=False, server_default=sa.text("gen_random_uuid()::text")),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('user_id', sa.String(length=255), nullable=True),
        sa.Column('case_id', sa.String(length=255), nullable=True),
        sa.Column('entity_type', sa.String(length=100), nullable=False),
        sa.Column('entity_id', sa.String(length=255), nullable=True),
        sa.Column('action', sa.String(length=100), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('details_json', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('correlation_id', sa.String(length=255), nullable=True),
        sa.Column('source_service', sa.String(length=100), nullable=True),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('user_agent', sa.Text(), nullable=True),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.PrimaryKeyConstraint('event_id')
    )

    # Create indexes
    op.create_index('ix_audit_events_timestamp', 'audit_events', ['timestamp'])
    op.create_index('ix_audit_events_user_id', 'audit_events', ['user_id'])
    op.create_index('ix_audit_events_case_id', 'audit_events', ['case_id'])
    op.create_index('ix_audit_events_entity_type', 'audit_events', ['entity_type'])
    op.create_index('ix_audit_events_action', 'audit_events', ['action'])
    op.create_index('ix_audit_events_status', 'audit_events', ['status'])
    op.create_index('ix_audit_events_correlation_id', 'audit_events', ['correlation_id'])

    # Composite indexes for common query patterns
    op.create_index('ix_audit_case_timestamp', 'audit_events', ['case_id', 'timestamp'])
    op.create_index('ix_audit_user_timestamp', 'audit_events', ['user_id', 'timestamp'])
    op.create_index('ix_audit_type_action', 'audit_events', ['entity_type', 'action'])
    op.create_index('ix_audit_timestamp_desc', 'audit_events', [sa.text('timestamp DESC')])


def downgrade() -> None:
    # Drop indexes
    op.drop_index('ix_audit_timestamp_desc', table_name='audit_events')
    op.drop_index('ix_audit_type_action', table_name='audit_events')
    op.drop_index('ix_audit_user_timestamp', table_name='audit_events')
    op.drop_index('ix_audit_case_timestamp', table_name='audit_events')
    op.drop_index('ix_audit_events_correlation_id', table_name='audit_events')
    op.drop_index('ix_audit_events_status', table_name='audit_events')
    op.drop_index('ix_audit_events_action', table_name='audit_events')
    op.drop_index('ix_audit_events_entity_type', table_name='audit_events')
    op.drop_index('ix_audit_events_case_id', table_name='audit_events')
    op.drop_index('ix_audit_events_user_id', table_name='audit_events')
    op.drop_index('ix_audit_events_timestamp', table_name='audit_events')

    # Drop table
    op.drop_table('audit_events')
