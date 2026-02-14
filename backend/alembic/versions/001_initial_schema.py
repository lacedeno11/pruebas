"""Initial schema creation for PEI Agentic Platform.

Revision ID: 001
Revises: 
Create Date: 2024-02-13 15:30:45.000000

This migration creates the initial database schema with four main tables:
1. cuadrillas - Technical crews that execute OTs
2. ots - Orders of Work with coordinates and status
3. logs_agentes - Agent operation logs with tracing
4. assignments - OT-Cuadrilla assignment history

All tables use UUID primary keys, include timestamps, and have proper
foreign key relationships with cascade delete strategies.
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
    """Create initial schema."""

    # ========================================================================
    # CUADRILLAS TABLE (Crews)
    # ========================================================================

    op.create_table(
        'cuadrillas',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('type', sa.Enum('PRINCIPAL', 'RESERVA', name='cuadrillatype'), nullable=False),
        sa.Column('last_centroid_lat', sa.Float(), nullable=True),
        sa.Column('last_centroid_long', sa.Float(), nullable=True),
        sa.Column('daily_capacity', sa.Integer(), nullable=False),
        sa.Column('current_load', sa.Integer(), nullable=False),
        sa.Column('active', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name'),
    )

    # Create indexes for cuadrillas table
    op.create_index('ix_cuadrilla_active_load', 'cuadrillas', ['active', 'current_load'])
    op.create_index('ix_cuadrilla_type_active', 'cuadrillas', ['type', 'active'])
    op.create_index('ix_cuadrilla_created_at', 'cuadrillas', ['created_at'])
    op.create_index('ix_cuadrillas_name', 'cuadrillas', ['name'])
    op.create_index('ix_cuadrillas_active', 'cuadrillas', ['active'])

    # ========================================================================
    # OTS TABLE (Orders of Work)
    # ========================================================================

    op.create_table(
        'ots',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('external_id', sa.String(50), nullable=False),
        sa.Column('status', sa.Enum(
            'PREPLANIFICADA', 'PLANIFICADA', 'ASIGNADO_TAREA', 
            'DETENIDA', 'ANULADA', 'FINALIZADA',
            name='otstatus'
        ), nullable=False),
        sa.Column('project_type', sa.Enum('PUBLICO', 'PRIVADO', 'TERCERIZADO', name='projecttype'), nullable=False),
        sa.Column('cliente_id', sa.String(50), nullable=False),
        sa.Column('login_id', sa.String(50), nullable=False),
        sa.Column('lat', sa.Float(), nullable=True),
        sa.Column('long', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('cuadrilla_id', sa.UUID(), nullable=True),
        sa.Column('geo_error', sa.Boolean(), nullable=False),
        sa.Column('detention_reason', sa.String(200), nullable=True),
        sa.ForeignKeyConstraint(['cuadrilla_id'], ['cuadrillas.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('external_id'),
    )

    # Create indexes for ots table
    op.create_index('ix_ot_external_id', 'ots', ['external_id'])
    op.create_index('ix_ot_status_cuadrilla', 'ots', ['status', 'cuadrilla_id'])
    op.create_index('ix_ot_project_status', 'ots', ['project_type', 'status'])
    op.create_index('ix_ot_geo_error', 'ots', ['geo_error'])
    op.create_index('ix_ot_created_at', 'ots', ['created_at'])
    op.create_index('ix_ot_cliente_status', 'ots', ['cliente_id', 'status'])
    op.create_index('ix_ot_cuadrilla_id', 'ots', ['cuadrilla_id'])
    op.create_index('ix_ot_status', 'ots', ['status'])
    op.create_index('ix_ot_project_type', 'ots', ['project_type'])

    # ========================================================================
    # LOGS_AGENTES TABLE (Agent Logs)
    # ========================================================================

    op.create_table(
        'logs_agentes',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('ot_id', sa.UUID(), nullable=True),
        sa.Column('agente_name', sa.String(50), nullable=False),
        sa.Column('accion', sa.String(100), nullable=False),
        sa.Column('resultado', sa.String(50), nullable=False),
        sa.Column('raw_llm_response', sa.Text(), nullable=True),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.Column('correlation_id', sa.String(36), nullable=False),
        sa.Column('metadata', sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(['ot_id'], ['ots.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )

    # Create indexes for logs_agentes table
    op.create_index('ix_log_agente_ot', 'logs_agentes', ['agente_name', 'ot_id'])
    op.create_index('ix_log_correlation_timestamp', 'logs_agentes', ['correlation_id', 'timestamp'])
    op.create_index('ix_log_agente_resultado', 'logs_agentes', ['agente_name', 'resultado'])
    op.create_index('ix_log_timestamp', 'logs_agentes', ['timestamp'])
    op.create_index('ix_log_agente_name', 'logs_agentes', ['agente_name'])
    op.create_index('ix_log_ot_id', 'logs_agentes', ['ot_id'])
    op.create_index('ix_log_correlation_id', 'logs_agentes', ['correlation_id'])
    op.create_index('ix_log_resultado', 'logs_agentes', ['resultado'])

    # ========================================================================
    # ASSIGNMENTS TABLE (OT-Cuadrilla Assignments)
    # ========================================================================

    op.create_table(
        'assignments',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('ot_id', sa.UUID(), nullable=False),
        sa.Column('cuadrilla_id', sa.UUID(), nullable=False),
        sa.Column('assigned_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('assigned_by', sa.String(100), nullable=False),
        sa.Column('distance_from_centroid', sa.Float(), nullable=True),
        sa.Column('phase', sa.Enum(
            'INITIAL_BALANCE', 'PROXIMITY', 'NIGHTLY_NORMALIZATION',
            name='assignmentphase'
        ), nullable=False),
        sa.Column('status', sa.Enum('ACTIVE', 'COMPLETED', 'REASSIGNED', 'CANCELLED', name='assignmentstatus'), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('notes', sa.String(500), nullable=True),
        sa.ForeignKeyConstraint(['ot_id'], ['ots.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['cuadrilla_id'], ['cuadrillas.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )

    # Create indexes for assignments table
    op.create_index('ix_assignment_ot_cuadrilla', 'assignments', ['ot_id', 'cuadrilla_id'])
    op.create_index('ix_assignment_cuadrilla_status', 'assignments', ['cuadrilla_id', 'status'])
    op.create_index('ix_assignment_phase_assigned_at', 'assignments', ['phase', 'assigned_at'])
    op.create_index('ix_assignment_assigned_by', 'assignments', ['assigned_by'])
    op.create_index('ix_assignment_ot_id', 'assignments', ['ot_id'])
    op.create_index('ix_assignment_cuadrilla_id', 'assignments', ['cuadrilla_id'])
    op.create_index('ix_assignment_status', 'assignments', ['status'])
    op.create_index('ix_assignment_phase', 'assignments', ['phase'])
    op.create_index('ix_assignment_assigned_at', 'assignments', ['assigned_at'])


def downgrade() -> None:
    """Drop initial schema."""

    # Drop indexes (indexes are automatically dropped with tables, but explicit for clarity)
    op.drop_index('ix_assignment_assigned_at', table_name='assignments')
    op.drop_index('ix_assignment_phase', table_name='assignments')
    op.drop_index('ix_assignment_status', table_name='assignments')
    op.drop_index('ix_assignment_cuadrilla_id', table_name='assignments')
    op.drop_index('ix_assignment_ot_id', table_name='assignments')
    op.drop_index('ix_assignment_assigned_by', table_name='assignments')
    op.drop_index('ix_assignment_phase_assigned_at', table_name='assignments')
    op.drop_index('ix_assignment_cuadrilla_status', table_name='assignments')
    op.drop_index('ix_assignment_ot_cuadrilla', table_name='assignments')

    op.drop_index('ix_log_resultado', table_name='logs_agentes')
    op.drop_index('ix_log_correlation_id', table_name='logs_agentes')
    op.drop_index('ix_log_ot_id', table_name='logs_agentes')
    op.drop_index('ix_log_agente_name', table_name='logs_agentes')
    op.drop_index('ix_log_timestamp', table_name='logs_agentes')
    op.drop_index('ix_log_agente_resultado', table_name='logs_agentes')
    op.drop_index('ix_log_correlation_timestamp', table_name='logs_agentes')
    op.drop_index('ix_log_agente_ot', table_name='logs_agentes')

    op.drop_index('ix_ot_project_type', table_name='ots')
    op.drop_index('ix_ot_status', table_name='ots')
    op.drop_index('ix_ot_cuadrilla_id', table_name='ots')
    op.drop_index('ix_ot_cliente_status', table_name='ots')
    op.drop_index('ix_ot_created_at', table_name='ots')
    op.drop_index('ix_ot_geo_error', table_name='ots')
    op.drop_index('ix_ot_project_status', table_name='ots')
    op.drop_index('ix_ot_status_cuadrilla', table_name='ots')
    op.drop_index('ix_ot_external_id', table_name='ots')

    op.drop_index('ix_cuadrillas_active', table_name='cuadrillas')
    op.drop_index('ix_cuadrillas_name', table_name='cuadrillas')
    op.drop_index('ix_cuadrilla_created_at', table_name='cuadrillas')
    op.drop_index('ix_cuadrilla_type_active', table_name='cuadrillas')
    op.drop_index('ix_cuadrilla_active_load', table_name='cuadrillas')

    # Drop tables
    op.drop_table('assignments')
    op.drop_table('logs_agentes')
    op.drop_table('ots')
    op.drop_table('cuadrillas')

    # Drop enums
    op.execute('DROP TYPE IF EXISTS assignmentstatus')
    op.execute('DROP TYPE IF EXISTS assignmentphase')
    op.execute('DROP TYPE IF EXISTS projecttype')
    op.execute('DROP TYPE IF EXISTS otstatus')
    op.execute('DROP TYPE IF EXISTS cuadrillatype')

