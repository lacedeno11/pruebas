"""Initial tables for patients and cases

Revision ID: 001
Revises: 
Create Date: 2024-01-01 12:00:00.000000

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
    # Create patients table
    op.create_table('patients',
        sa.Column('id', postgresql.UUID(as_uuid=False), nullable=False, comment='Unique patient identifier'),
        sa.Column('external_id', sa.String(length=255), nullable=True, comment='External patient ID from hospital system'),
        sa.Column('first_name', sa.String(length=255), nullable=False, comment='Patient first name'),
        sa.Column('last_name', sa.String(length=255), nullable=False, comment='Patient last name'),
        sa.Column('date_of_birth', sa.DateTime(timezone=True), nullable=True, comment='Patient date of birth'),
        sa.Column('gender', sa.String(length=10), nullable=True, comment='Patient gender (M/F/O/U)'),
        sa.Column('medical_record_number', sa.String(length=100), nullable=True, comment='Medical record number'),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True, comment='Additional patient metadata'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False, comment='Record creation timestamp'),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False, comment='Record last update timestamp'),
        sa.Column('created_by', sa.String(length=255), nullable=True, comment='User who created the record'),
        sa.Column('updated_by', sa.String(length=255), nullable=True, comment='User who last updated the record'),
        sa.Column('is_active', sa.Boolean(), nullable=False, comment='Whether the patient record is active'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for patients table
    op.create_index('idx_patients_external_id', 'patients', ['external_id'], unique=False)
    op.create_index('idx_patients_mrn', 'patients', ['medical_record_number'], unique=False)
    op.create_index('idx_patients_name', 'patients', ['last_name', 'first_name'], unique=False)
    op.create_index('idx_patients_created_at', 'patients', ['created_at'], unique=False)
    op.create_index('idx_patients_active', 'patients', ['is_active'], unique=False)
    
    # Create unique constraint for external_id
    op.create_unique_constraint('uq_patients_external_id', 'patients', ['external_id'])
    
    # Create cases table
    op.create_table('cases',
        sa.Column('id', postgresql.UUID(as_uuid=False), nullable=False, comment='Unique case identifier'),
        sa.Column('patient_id', postgresql.UUID(as_uuid=False), nullable=False, comment='Reference to patient'),
        sa.Column('external_id', sa.String(length=255), nullable=True, comment='External case ID from hospital system'),
        sa.Column('title', sa.String(length=500), nullable=False, comment='Case title or summary'),
        sa.Column('description', sa.Text(), nullable=True, comment='Detailed case description'),
        sa.Column('status', sa.String(length=50), nullable=False, comment='Case status (draft, active, completed, archived)'),
        sa.Column('priority', sa.String(length=20), nullable=False, comment='Case priority (low, normal, high, urgent)'),
        sa.Column('diagnosis', sa.Text(), nullable=True, comment='Clinical diagnosis or working diagnosis'),
        sa.Column('clinical_notes', sa.Text(), nullable=True, comment='Clinical notes and observations'),
        sa.Column('case_date', sa.DateTime(timezone=True), nullable=True, comment='Date when the case occurred'),
        sa.Column('admission_date', sa.DateTime(timezone=True), nullable=True, comment='Patient admission date'),
        sa.Column('discharge_date', sa.DateTime(timezone=True), nullable=True, comment='Patient discharge date'),
        sa.Column('tags', postgresql.JSONB(astext_type=sa.Text()), nullable=True, comment='Case tags for categorization'),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True, comment='Additional case metadata'),
        sa.Column('processing_status', sa.String(length=50), nullable=False, comment='AI processing status (pending, processing, completed, failed)'),
        sa.Column('processing_progress', sa.Integer(), nullable=False, comment='Processing progress percentage (0-100)'),
        sa.Column('processing_error', sa.Text(), nullable=True, comment='Processing error message if failed'),
        sa.Column('has_images', sa.Boolean(), nullable=False, comment='Whether case has associated images'),
        sa.Column('has_ehr_data', sa.Boolean(), nullable=False, comment='Whether case has EHR data'),
        sa.Column('has_inference_results', sa.Boolean(), nullable=False, comment='Whether case has inference results'),
        sa.Column('has_graph_data', sa.Boolean(), nullable=False, comment='Whether case has knowledge graph data'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False, comment='Record creation timestamp'),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False, comment='Record last update timestamp'),
        sa.Column('created_by', sa.String(length=255), nullable=True, comment='User who created the record'),
        sa.Column('updated_by', sa.String(length=255), nullable=True, comment='User who last updated the record'),
        sa.Column('is_active', sa.Boolean(), nullable=False, comment='Whether the case record is active'),
        sa.ForeignKeyConstraint(['patient_id'], ['patients.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for cases table
    op.create_index('idx_cases_patient_id', 'cases', ['patient_id'], unique=False)
    op.create_index('idx_cases_external_id', 'cases', ['external_id'], unique=False)
    op.create_index('idx_cases_status', 'cases', ['status'], unique=False)
    op.create_index('idx_cases_priority', 'cases', ['priority'], unique=False)
    op.create_index('idx_cases_processing_status', 'cases', ['processing_status'], unique=False)
    op.create_index('idx_cases_case_date', 'cases', ['case_date'], unique=False)
    op.create_index('idx_cases_created_at', 'cases', ['created_at'], unique=False)
    op.create_index('idx_cases_active', 'cases', ['is_active'], unique=False)
    op.create_index('idx_cases_has_images', 'cases', ['has_images'], unique=False)
    op.create_index('idx_cases_has_inference', 'cases', ['has_inference_results'], unique=False)


def downgrade() -> None:
    # Drop cases table
    op.drop_index('idx_cases_has_inference', table_name='cases')
    op.drop_index('idx_cases_has_images', table_name='cases')
    op.drop_index('idx_cases_active', table_name='cases')
    op.drop_index('idx_cases_created_at', table_name='cases')
    op.drop_index('idx_cases_case_date', table_name='cases')
    op.drop_index('idx_cases_processing_status', table_name='cases')
    op.drop_index('idx_cases_priority', table_name='cases')
    op.drop_index('idx_cases_status', table_name='cases')
    op.drop_index('idx_cases_external_id', table_name='cases')
    op.drop_index('idx_cases_patient_id', table_name='cases')
    op.drop_table('cases')
    
    # Drop patients table
    op.drop_constraint('uq_patients_external_id', 'patients', type_='unique')
    op.drop_index('idx_patients_active', table_name='patients')
    op.drop_index('idx_patients_created_at', table_name='patients')
    op.drop_index('idx_patients_name', table_name='patients')
    op.drop_index('idx_patients_mrn', table_name='patients')
    op.drop_index('idx_patients_external_id', table_name='patients')
    op.drop_table('patients')
