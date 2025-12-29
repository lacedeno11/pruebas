"""Initial migration for EHR service.

Revision ID: 001
Revises:
Create Date: 2024-01-01 00:00:00.000000

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
    # Create enum types
    op.execute("""
        CREATE TYPE ehr_document_status AS ENUM (
            'INGESTED', 'PROCESSING', 'ENTITIES_EXTRACTED', 'MAPPED', 'FAILED'
        )
    """)

    # Create ehr_documents table
    op.create_table(
        'ehr_documents',
        sa.Column('ehr_id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('case_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('version', sa.Integer(), nullable=False, default=1),
        sa.Column('raw_text', sa.Text(), nullable=False),
        sa.Column('normalized_text', sa.Text(), nullable=True),
        sa.Column('status', sa.Enum('INGESTED', 'PROCESSING', 'ENTITIES_EXTRACTED', 'MAPPED', 'FAILED', name='ehr_document_status'), nullable=False, server_default='INGESTED'),
        sa.Column('processing_metadata', postgresql.JSONB(), nullable=False, server_default='{}'),
        sa.Column('task_id', sa.String(255), nullable=True),
        sa.Column('created_by', sa.String(255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    )

    # Create ehr_entities table
    op.create_table(
        'ehr_entities',
        sa.Column('entity_id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('ehr_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('entity_type', sa.String(100), nullable=False, index=True),
        sa.Column('text', sa.String(500), nullable=False),
        sa.Column('start_position', sa.Integer(), nullable=True),
        sa.Column('end_position', sa.Integer(), nullable=True),
        sa.Column('confidence', sa.Float(), nullable=False, default=1.0),
        sa.Column('section', sa.String(255), nullable=True),
        sa.Column('metadata', postgresql.JSONB(), nullable=False, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['ehr_id'], ['ehr_documents.ehr_id'], ondelete='CASCADE'),
    )

    # Create ehr_mappings table
    op.create_table(
        'ehr_mappings',
        sa.Column('mapping_id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('ehr_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('entity_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('ontology', sa.String(100), nullable=False, index=True),
        sa.Column('iri', sa.String(500), nullable=False),
        sa.Column('label', sa.String(500), nullable=False),
        sa.Column('confidence', sa.Float(), nullable=False, default=1.0),
        sa.Column('mapping_method', sa.String(100), nullable=False, default='automatic'),
        sa.Column('evidence', postgresql.JSONB(), nullable=False, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['ehr_id'], ['ehr_documents.ehr_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['entity_id'], ['ehr_entities.entity_id'], ondelete='CASCADE'),
    )

    # Create indexes for better query performance
    op.create_index('idx_ehr_documents_case_version', 'ehr_documents', ['case_id', 'version'], unique=True)
    op.create_index('idx_ehr_entities_ehr_type', 'ehr_entities', ['ehr_id', 'entity_type'])
    op.create_index('idx_ehr_mappings_ehr_ontology', 'ehr_mappings', ['ehr_id', 'ontology'])


def downgrade() -> None:
    op.drop_index('idx_ehr_mappings_ehr_ontology', table_name='ehr_mappings')
    op.drop_index('idx_ehr_entities_ehr_type', table_name='ehr_entities')
    op.drop_index('idx_ehr_documents_case_version', table_name='ehr_documents')

    op.drop_table('ehr_mappings')
    op.drop_table('ehr_entities')
    op.drop_table('ehr_documents')

    op.execute('DROP TYPE ehr_document_status')
