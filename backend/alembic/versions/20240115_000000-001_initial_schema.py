"""initial_schema

Revision ID: 001_initial_schema
Revises: 
Create Date: 2024-01-15 00:00:00.000000

Create initial database schema for DERCAS PEI backend with four core tables:
- ots: Work orders with status lifecycle and crew assignment
- cuadrillas: Work crews with capacity and centroid tracking
- logs_agentes: Agent action logs for audit trail
- asignaciones: Assignment history with distance tracking
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic
revision = '001_initial_schema'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create initial database schema."""
    
    # Create ENUM types for OT status
    ot_status_enum = sa.Enum(
        'PREPLANIFICADA',
        'PLANIFICADA',
        'ASIGNADO_TAREA',
        'DETENIDA',
        'ANULADA',
        'FINALIZADA',
        'ERROR_GEO',
        name='ot_status'
    )
    ot_status_enum.create(op.get_bind())

    # Create ENUM types for project type
    project_type_enum = sa.Enum(
        'PUBLICO',
        'PRIVADO',
        'TERCERIZADO',
        name='project_type'
    )
    project_type_enum.create(op.get_bind())

    # Create ENUM types for cuadrilla type
    cuadrilla_type_enum = sa.Enum(
        'PRINCIPAL',
        'RESERVA',
        name='cuadrilla_type'
    )
    cuadrilla_type_enum.create(op.get_bind())

    # Create ENUM types for agent type
    agente_type_enum = sa.Enum(
        'ROUTER',
        'OTS',
        'PLANIFICACION',
        'GOBERNANZA',
        'COMUNICACION',
        name='agente_type'
    )
    agente_type_enum.create(op.get_bind())

    # Create ENUM types for log resultado
    log_resultado_enum = sa.Enum(
        'SUCCESS',
        'FAILURE',
        'PENDING',
        name='log_resultado'
    )
    log_resultado_enum.create(op.get_bind())

    # Create ENUM types for assignment phase
    assignment_phase_enum = sa.Enum(
        'BALANCE',
        'PROXIMITY',
        'RESERVA',
        name='assignment_phase'
    )
    assignment_phase_enum.create(op.get_bind())

    # Create cuadrillas table first (referenced by ots)
    op.create_table(
        'cuadrillas',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('type', cuadrilla_type_enum, nullable=False, server_default='PRINCIPAL'),
        sa.Column('last_centroid_lat', sa.Float(), nullable=True),
        sa.Column('last_centroid_long', sa.Float(), nullable=True),
        sa.Column('max_capacity', sa.Integer(), nullable=False, server_default='10'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name', name='uq_cuadrilla_name'),
    )
    
    # Create indexes for cuadrillas
    op.create_index('idx_cuadrilla_type', 'cuadrillas', ['type'])
    op.create_index('idx_cuadrilla_created_at', 'cuadrillas', ['created_at'])

    # Create ots table
    op.create_table(
        'ots',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('external_id', sa.String(length=100), nullable=False),
        sa.Column('client_id', sa.String(length=100), nullable=False),
        sa.Column('login', sa.String(length=100), nullable=False),
        sa.Column('lat', sa.Float(), nullable=True),
        sa.Column('long', sa.Float(), nullable=True),
        sa.Column('status', ot_status_enum, nullable=False, server_default='PREPLANIFICADA'),
        sa.Column('project_type', project_type_enum, nullable=False, server_default='PUBLICO'),
        sa.Column('cuadrilla_id', sa.Integer(), nullable=True),
        sa.Column('detention_reason', sa.Text(), nullable=True),
        sa.Column('detention_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['cuadrilla_id'], ['cuadrillas.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('external_id', name='uq_ot_external_id'),
    )
    
    # Create indexes for ots
    op.create_index('idx_ot_external_id', 'ots', ['external_id'])
    op.create_index('idx_ot_status', 'ots', ['status'])
    op.create_index('idx_ot_cuadrilla_id', 'ots', ['cuadrilla_id'])
    op.create_index('idx_ot_created_at', 'ots', ['created_at'])
    op.create_index('idx_ot_status_project', 'ots', ['status', 'project_type'])
    op.create_index('idx_ot_cuadrilla_status', 'ots', ['cuadrilla_id', 'status'])
    op.create_index('idx_ot_lat_long', 'ots', ['lat', 'long'])
    op.create_index('idx_ot_detention_date', 'ots', ['detention_date'])
    op.create_index('idx_ot_client_id', 'ots', ['client_id'])

    # Create logs_agentes table
    op.create_table(
        'logs_agentes',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('ot_id', sa.Integer(), nullable=True),
        sa.Column('agente_name', agente_type_enum, nullable=False),
        sa.Column('accion', sa.Text(), nullable=False),
        sa.Column('resultado', log_resultado_enum, nullable=False, server_default='PENDING'),
        sa.Column('raw_llm_response', sa.JSON(), nullable=True),
        sa.Column('error_details', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['ot_id'], ['ots.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    
    # Create indexes for logs_agentes
    op.create_index('idx_log_ot_id', 'logs_agentes', ['ot_id'])
    op.create_index('idx_log_agente_name', 'logs_agentes', ['agente_name'])
    op.create_index('idx_log_resultado', 'logs_agentes', ['resultado'])
    op.create_index('idx_log_created_at', 'logs_agentes', ['created_at'])
    op.create_index('idx_log_agente_name_resultado', 'logs_agentes', ['agente_name', 'resultado'])
    op.create_index('idx_log_ot_created_at', 'logs_agentes', ['ot_id', 'created_at'])

    # Create asignaciones table
    op.create_table(
        'asignaciones',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('ot_id', sa.Integer(), nullable=False),
        sa.Column('cuadrilla_id', sa.Integer(), nullable=False),
        sa.Column('assigned_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('assigned_by_agent', sa.String(length=100), nullable=False),
        sa.Column('distance_from_centroid', sa.Float(), nullable=True),
        sa.Column('phase', assignment_phase_enum, nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['ot_id'], ['ots.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['cuadrilla_id'], ['cuadrillas.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    
    # Create indexes for asignaciones
    op.create_index('idx_asignacion_ot_id', 'asignaciones', ['ot_id'])
    op.create_index('idx_asignacion_cuadrilla_id', 'asignaciones', ['cuadrilla_id'])
    op.create_index('idx_asignacion_ot_assigned_at', 'asignaciones', ['ot_id', 'assigned_at'])
    op.create_index('idx_asignacion_cuadrilla_assigned_at', 'asignaciones', ['cuadrilla_id', 'assigned_at'])
    op.create_index('idx_asignacion_phase', 'asignaciones', ['phase'])
    op.create_index('idx_asignacion_created_at', 'asignaciones', ['created_at'])


def downgrade() -> None:
    """Drop all tables and enums created in upgrade."""
    
    # Drop tables in reverse order (respecting foreign keys)
    op.drop_table('asignaciones')
    op.drop_table('logs_agentes')
    op.drop_table('ots')
    op.drop_table('cuadrillas')
    
    # Drop ENUM types
    enum_types = [
        'assignment_phase',
        'log_resultado',
        'agente_type',
        'cuadrilla_type',
        'project_type',
        'ot_status',
    ]
    
    for enum_type in enum_types:
        op.execute(f"DROP TYPE IF EXISTS {enum_type}")

