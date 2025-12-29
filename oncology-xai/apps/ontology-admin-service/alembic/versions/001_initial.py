"""Initial migration for ontology admin service.

Revision ID: 001
Revises:
Create Date: 2025-01-15 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create proposal_status enum
    op.execute("""
        CREATE TYPE proposal_status AS ENUM (
            'DRAFT',
            'VALIDATING',
            'VALIDATED',
            'REQUIRES_FIX',
            'PENDING_APPROVAL',
            'APPROVED',
            'PUBLISHED',
            'REJECTED',
            'ROLLBACK_REQUESTED',
            'ROLLED_BACK'
        )
    """)

    # Create ontology_versions table
    op.create_table(
        'ontology_versions',
        sa.Column('version_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('ontology_source', sa.String(length=100), nullable=False),
        sa.Column('version_tag', sa.String(length=50), nullable=False),
        sa.Column('content_hash', sa.String(length=64), nullable=False),
        sa.Column('ontology_data', sa.Text(), nullable=False),
        sa.Column('statistics', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('published_by', sa.String(length=255), nullable=True),
        sa.Column('published_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('replaced_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.PrimaryKeyConstraint('version_id'),
        sa.UniqueConstraint('content_hash')
    )
    op.create_index(op.f('ix_ontology_versions_is_active'), 'ontology_versions', ['is_active'], unique=False)
    op.create_index(op.f('ix_ontology_versions_ontology_source'), 'ontology_versions', ['ontology_source'], unique=False)
    op.create_index(op.f('ix_ontology_versions_version_tag'), 'ontology_versions', ['version_tag'], unique=False)

    # Create ontology_update_proposals table
    op.create_table(
        'ontology_update_proposals',
        sa.Column('proposal_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('ontology_sources', postgresql.ARRAY(sa.String()), nullable=False),
        sa.Column('mode', sa.String(length=20), nullable=False),
        sa.Column('status', sa.Enum('DRAFT', 'VALIDATING', 'VALIDATED', 'REQUIRES_FIX', 'PENDING_APPROVAL', 'APPROVED', 'PUBLISHED', 'REJECTED', 'ROLLBACK_REQUESTED', 'ROLLED_BACK', name='proposal_status'), nullable=False),
        sa.Column('workflow_execution_id', sa.String(length=255), nullable=True),
        sa.Column('diff_summary', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('impact_analysis', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('reasoner_results', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('validation_errors', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('uploaded_files', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('approval_notes', sa.Text(), nullable=True),
        sa.Column('rejection_reason', sa.Text(), nullable=True),
        sa.Column('created_version_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('rollback_from_version_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('rollback_to_version_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('created_by', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('approved_by', sa.String(length=255), nullable=True),
        sa.Column('approved_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['created_version_id'], ['ontology_versions.version_id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['rollback_from_version_id'], ['ontology_versions.version_id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['rollback_to_version_id'], ['ontology_versions.version_id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('proposal_id')
    )
    op.create_index(op.f('ix_ontology_update_proposals_status'), 'ontology_update_proposals', ['status'], unique=False)
    op.create_index(op.f('ix_ontology_update_proposals_workflow_execution_id'), 'ontology_update_proposals', ['workflow_execution_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_ontology_update_proposals_workflow_execution_id'), table_name='ontology_update_proposals')
    op.drop_index(op.f('ix_ontology_update_proposals_status'), table_name='ontology_update_proposals')
    op.drop_table('ontology_update_proposals')
    op.drop_index(op.f('ix_ontology_versions_version_tag'), table_name='ontology_versions')
    op.drop_index(op.f('ix_ontology_versions_ontology_source'), table_name='ontology_versions')
    op.drop_index(op.f('ix_ontology_versions_is_active'), table_name='ontology_versions')
    op.drop_table('ontology_versions')
    op.execute("DROP TYPE proposal_status")
