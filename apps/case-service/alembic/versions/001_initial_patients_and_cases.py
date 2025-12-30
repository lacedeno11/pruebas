"""Initial patients and cases tables

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
    # Create case_status enum
    case_status_enum = postgresql.ENUM(
        'CREATED', 'READY', 'PROCESSING', 'REVIEW_REQUIRED', 'CLOSED',
        name='case_status'
    )
    case_status_enum.create(op.get_bind())

    # Create patients table
    op.create_table(
        'patients',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('patient_id', sa.String(100), nullable=False, unique=True, index=True,
                  comment='External patient identifier'),
        sa.Column('age', sa.Integer(), nullable=True, comment='Patient age'),
        sa.Column('gender', sa.String(20), nullable=True, comment='Patient gender'),
        sa.Column('medical_record_number', sa.String(100), nullable=True, index=True,
                  comment='Medical record number'),
        sa.Column('diagnosis_date', sa.DateTime(timezone=True), nullable=True,
                  comment='Initial diagnosis date'),
        sa.Column('primary_site', sa.String(200), nullable=True, comment='Primary tumor site'),
        sa.Column('histology', sa.String(200), nullable=True, comment='Histological type'),
        sa.Column('stage', sa.String(50), nullable=True, comment='Cancer stage'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(),
                  nullable=False, comment='Creation timestamp'),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True,
                  comment='Last update timestamp'),
        sa.PrimaryKeyConstraint('id', name='pk_patients'),
        sa.UniqueConstraint('patient_id', name='uq_patients_patient_id'),
        comment='Patient information table'
    )

    # Create index on patient_id for faster lookups
    op.create_index('ix_patients_patient_id', 'patients', ['patient_id'])
    op.create_index('ix_patients_medical_record_number', 'patients', ['medical_record_number'])

    # Create cases table
    op.create_table(
        'cases',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('case_id', sa.String(100), nullable=False, unique=True, index=True,
                  comment='External case identifier'),
        sa.Column('patient_id', postgresql.UUID(as_uuid=True), nullable=False, index=True,
                  comment='Associated patient ID'),
        sa.Column('status', case_status_enum, nullable=False, default='CREATED', index=True,
                  comment='Case processing status'),
        sa.Column('title', sa.String(200), nullable=True, comment='Case title'),
        sa.Column('description', sa.Text(), nullable=True, comment='Case description'),
        sa.Column('priority', sa.Integer(), nullable=False, default=1,
                  comment='Case priority (1-5)'),
        sa.Column('clinical_context', postgresql.JSON(), nullable=True,
                  comment='Additional clinical context'),
        sa.Column('assigned_to', sa.String(100), nullable=True, index=True,
                  comment='Assigned clinician'),
        sa.Column('processing_started_at', sa.DateTime(timezone=True), nullable=True,
                  comment='Processing start time'),
        sa.Column('processing_completed_at', sa.DateTime(timezone=True), nullable=True,
                  comment='Processing completion time'),
        sa.Column('review_required_reason', sa.String(500), nullable=True,
                  comment='Reason for review requirement'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(),
                  nullable=False, comment='Creation timestamp'),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True,
                  comment='Last update timestamp'),
        sa.ForeignKeyConstraint(['patient_id'], ['patients.id'], 
                               name='fk_cases_patient_id_patients', ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name='pk_cases'),
        sa.UniqueConstraint('case_id', name='uq_cases_case_id'),
        comment='Case information table'
    )

    # Create indexes on cases table for faster lookups
    op.create_index('ix_cases_case_id', 'cases', ['case_id'])
    op.create_index('ix_cases_patient_id', 'cases', ['patient_id'])
    op.create_index('ix_cases_status', 'cases', ['status'])
    op.create_index('ix_cases_assigned_to', 'cases', ['assigned_to'])
    op.create_index('ix_cases_created_at', 'cases', ['created_at'])
    
    # Create composite index for common queries
    op.create_index('ix_cases_status_created_at', 'cases', ['status', 'created_at'])
    op.create_index('ix_cases_patient_status', 'cases', ['patient_id', 'status'])


def downgrade() -> None:
    # Drop indexes first
    op.drop_index('ix_cases_patient_status', 'cases')
    op.drop_index('ix_cases_status_created_at', 'cases')
    op.drop_index('ix_cases_created_at', 'cases')
    op.drop_index('ix_cases_assigned_to', 'cases')
    op.drop_index('ix_cases_status', 'cases')
    op.drop_index('ix_cases_patient_id', 'cases')
    op.drop_index('ix_cases_case_id', 'cases')
    
    # Drop cases table
    op.drop_table('cases')
    
    # Drop patient indexes
    op.drop_index('ix_patients_medical_record_number', 'patients')
    op.drop_index('ix_patients_patient_id', 'patients')
    
    # Drop patients table
    op.drop_table('patients')
    
    # Drop enum
    case_status_enum = postgresql.ENUM(name='case_status')
    case_status_enum.drop(op.get_bind())
