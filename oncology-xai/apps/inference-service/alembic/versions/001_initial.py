"""Initial migration for inference service

Revision ID: 001
Revises:
Create Date: 2025-01-01 00:00:00.000000

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
    """Upgrade schema."""
    # Create ml_jobs table
    op.create_table(
        'ml_jobs',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('image_id', sa.String(length=36), nullable=False),
        sa.Column('celery_task_id', sa.String(length=255), nullable=True),
        sa.Column(
            'status',
            sa.Enum(
                'PENDING',
                'PROCESSING',
                'COMPLETED',
                'FAILED',
                'CANCELLED',
                name='jobstatus',
            ),
            nullable=False,
        ),
        sa.Column('result_bundle_id', sa.String(length=36), nullable=True),
        sa.Column('priority', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('retry_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('max_retries', sa.Integer(), nullable=False, server_default='3'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('error_details', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('metadata', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_ml_jobs_image_id', 'ml_jobs', ['image_id'])
    op.create_index('ix_ml_jobs_celery_task_id', 'ml_jobs', ['celery_task_id'])
    op.create_index('ix_ml_jobs_status', 'ml_jobs', ['status'])
    op.create_index('ix_ml_jobs_result_bundle_id', 'ml_jobs', ['result_bundle_id'])

    # Create result_bundles table
    op.create_table(
        'result_bundles',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('ml_job_id', sa.String(length=36), nullable=False),
        sa.Column('image_id', sa.String(length=36), nullable=False),
        sa.Column('overall_confidence', sa.Float(), nullable=False),
        sa.Column('summary', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('metadata', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.ForeignKeyConstraint(['ml_job_id'], ['ml_jobs.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_result_bundles_ml_job_id', 'result_bundles', ['ml_job_id'])
    op.create_index('ix_result_bundles_image_id', 'result_bundles', ['image_id'])

    # Create pattern_results table
    op.create_table(
        'pattern_results',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('result_bundle_id', sa.String(length=36), nullable=False),
        sa.Column('pattern_type', sa.String(length=100), nullable=False),
        sa.Column('pattern_name', sa.String(length=255), nullable=False),
        sa.Column('confidence', sa.Float(), nullable=False),
        sa.Column('location', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('bounding_box', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('severity', sa.String(length=50), nullable=True),
        sa.Column('clinical_significance', sa.Text(), nullable=True),
        sa.Column('metadata', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['result_bundle_id'], ['result_bundles.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_pattern_results_result_bundle_id', 'pattern_results', ['result_bundle_id'])

    # Create genetic_results table
    op.create_table(
        'genetic_results',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('result_bundle_id', sa.String(length=36), nullable=False),
        sa.Column('marker_name', sa.String(length=255), nullable=False),
        sa.Column('marker_type', sa.String(length=100), nullable=False),
        sa.Column('presence_probability', sa.Float(), nullable=False),
        sa.Column('clinical_relevance', sa.Text(), nullable=True),
        sa.Column('therapeutic_implications', sa.Text(), nullable=True),
        sa.Column('evidence', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('metadata', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['result_bundle_id'], ['result_bundles.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_genetic_results_result_bundle_id', 'genetic_results', ['result_bundle_id'])

    # Create xai_artifacts table
    op.create_table(
        'xai_artifacts',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('result_bundle_id', sa.String(length=36), nullable=False),
        sa.Column('artifact_type', sa.String(length=100), nullable=False),
        sa.Column('artifact_name', sa.String(length=255), nullable=False),
        sa.Column('artifact_url', sa.Text(), nullable=True),
        sa.Column('artifact_data', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('interpretation', sa.Text(), nullable=True),
        sa.Column('metadata', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['result_bundle_id'], ['result_bundles.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_xai_artifacts_result_bundle_id', 'xai_artifacts', ['result_bundle_id'])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_xai_artifacts_result_bundle_id', table_name='xai_artifacts')
    op.drop_table('xai_artifacts')

    op.drop_index('ix_genetic_results_result_bundle_id', table_name='genetic_results')
    op.drop_table('genetic_results')

    op.drop_index('ix_pattern_results_result_bundle_id', table_name='pattern_results')
    op.drop_table('pattern_results')

    op.drop_index('ix_result_bundles_image_id', table_name='result_bundles')
    op.drop_index('ix_result_bundles_ml_job_id', table_name='result_bundles')
    op.drop_table('result_bundles')

    op.drop_index('ix_ml_jobs_result_bundle_id', table_name='ml_jobs')
    op.drop_index('ix_ml_jobs_status', table_name='ml_jobs')
    op.drop_index('ix_ml_jobs_celery_task_id', table_name='ml_jobs')
    op.drop_index('ix_ml_jobs_image_id', table_name='ml_jobs')
    op.drop_table('ml_jobs')

    sa.Enum(name='jobstatus').drop(op.get_bind(), checkfirst=True)
