"""Initial migration - patients and cases tables

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
    # Create case_status enum
    case_status = postgresql.ENUM(
        'CREATED', 'READY', 'PROCESSING', 'REVIEW_REQUIRED', 'REVIEWED', 'CLOSED',
        name='case_status'
    )
    case_status.create(op.get_bind())

    # Create patients table
    op.create_table(
        'patients',
        sa.Column('patient_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('external_id', sa.String(255), nullable=True),
        sa.Column('demographics', postgresql.JSONB(), nullable=False, default={}),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('patient_id'),
    )
    op.create_index('ix_patients_external_id', 'patients', ['external_id'])

    # Create cases table
    op.create_table(
        'cases',
        sa.Column('case_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('patient_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('status', postgresql.ENUM('CREATED', 'READY', 'PROCESSING', 'REVIEW_REQUIRED', 'REVIEWED', 'CLOSED', name='case_status', create_type=False), nullable=False, default='CREATED'),
        sa.Column('tags', postgresql.ARRAY(sa.String()), nullable=False, default=[]),
        sa.Column('metadata', postgresql.JSONB(), nullable=False, default={}),
        sa.Column('created_by', sa.String(255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('case_id'),
        sa.ForeignKeyConstraint(['patient_id'], ['patients.patient_id'], ondelete='CASCADE'),
    )
    op.create_index('ix_cases_patient_id', 'cases', ['patient_id'])


def downgrade() -> None:
    op.drop_table('cases')
    op.drop_table('patients')
    op.execute('DROP TYPE case_status')
