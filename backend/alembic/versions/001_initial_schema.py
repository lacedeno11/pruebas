"""Initial schema with all database tables

Revision ID: 001
Revises: 
Create Date: 2024-02-13 22:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create cuadrillas table
    op.create_table(
        'cuadrillas',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('type', sa.String(length=20), nullable=False),
        sa.Column('capacity', sa.Integer(), nullable=True, server_default='10'),
        sa.Column('last_centroid_lat', sa.Float(), nullable=True),
        sa.Column('last_centroid_long', sa.Float(), nullable=True),
        sa.Column('active', sa.Boolean(), nullable=True, server_default='true'),
        sa.Column('created_at', sa.DateTime(), nullable=True, server_default=sa.func.now()),
        sa.CheckConstraint("type IN ('Principal', 'Reserva')", name='check_cuadrilla_type'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_cuadrillas_type', 'cuadrillas', ['type'])
    op.create_index('idx_cuadrillas_active', 'cuadrillas', ['active'])

    # Create ots table
    op.create_table(
        'ots',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('external_id', sa.String(length=50), nullable=False),
        sa.Column('cliente_id', sa.String(length=50), nullable=True),
        sa.Column('login_id', sa.String(length=50), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('project_type', sa.String(length=20), nullable=False),
        sa.Column('lat', sa.Float(), nullable=True),
        sa.Column('long', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=True, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column('last_status_change', sa.DateTime(), nullable=True, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column('cuadrilla_id', sa.Integer(), nullable=True),
        sa.Column('detalle_detencion', sa.Text(), nullable=True),
        sa.CheckConstraint("status IN ('PREPLANIFICADA', 'PLANIFICADA', 'ASIGNADO_TAREA', 'DETENIDA', 'ANULADA', 'FINALIZADA')", name='check_ot_status'),
        sa.CheckConstraint("project_type IN ('PUBLICO', 'PRIVADO', 'TERCERIZADO')", name='check_ot_project_type'),
        sa.ForeignKeyConstraint(['cuadrilla_id'], ['cuadrillas.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('external_id', name='uq_ot_external_id')
    )
    op.create_index('idx_ots_status', 'ots', ['status'])
    op.create_index('idx_ots_project_type', 'ots', ['project_type'])
    op.create_index('idx_ots_cuadrilla', 'ots', ['cuadrilla_id'])
    op.create_index('idx_ots_created_at', 'ots', ['created_at'])

    # Create logs_agentes table
    op.create_table(
        'logs_agentes',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('ot_id', sa.Integer(), nullable=True),
        sa.Column('agente_name', sa.String(length=50), nullable=False),
        sa.Column('accion', sa.String(length=100), nullable=False),
        sa.Column('resultado', sa.String(length=20), nullable=False),
        sa.Column('raw_llm_response', sa.Text(), nullable=True),
        sa.Column('metadata', sa.String(length=2000), nullable=True),
        sa.Column('timestamp', sa.DateTime(), nullable=True, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['ot_id'], ['ots.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_logs_ot', 'logs_agentes', ['ot_id'])
    op.create_index('idx_logs_timestamp', 'logs_agentes', ['timestamp'])
    op.create_index('idx_logs_agente_name', 'logs_agentes', ['agente_name'])

    # Create asignaciones table
    op.create_table(
        'asignaciones',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('ot_id', sa.Integer(), nullable=False),
        sa.Column('cuadrilla_id', sa.Integer(), nullable=False),
        sa.Column('assigned_at', sa.DateTime(), nullable=True, server_default=sa.func.now()),
        sa.Column('assigned_by_agent', sa.String(length=50), nullable=True),
        sa.Column('distance_to_centroid', sa.Float(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True, server_default='true'),
        sa.ForeignKeyConstraint(['cuadrilla_id'], ['cuadrillas.id'], ),
        sa.ForeignKeyConstraint(['ot_id'], ['ots.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_asignaciones_ot', 'asignaciones', ['ot_id'])
    op.create_index('idx_asignaciones_cuadrilla', 'asignaciones', ['cuadrilla_id'])
    op.create_index('idx_asignaciones_active', 'asignaciones', ['is_active'])
    op.create_index('idx_asignaciones_assigned_at', 'asignaciones', ['assigned_at'])

    # Create alertas table
    op.create_table(
        'alertas',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('ot_id', sa.Integer(), nullable=False),
        sa.Column('tipo', sa.String(length=50), nullable=False),
        sa.Column('mensaje', sa.Text(), nullable=False),
        sa.Column('destinatario', sa.String(length=100), nullable=True),
        sa.Column('canal', sa.String(length=20), nullable=False),
        sa.Column('enviado_at', sa.DateTime(), nullable=True),
        sa.Column('leido', sa.Boolean(), nullable=True, server_default='false'),
        sa.ForeignKeyConstraint(['ot_id'], ['ots.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_alertas_ot', 'alertas', ['ot_id'])
    op.create_index('idx_alertas_tipo', 'alertas', ['tipo'])
    op.create_index('idx_alertas_enviado_at', 'alertas', ['enviado_at'])


def downgrade() -> None:
    # Drop alertas table
    op.drop_index('idx_alertas_enviado_at', table_name='alertas')
    op.drop_index('idx_alertas_tipo', table_name='alertas')
    op.drop_index('idx_alertas_ot', table_name='alertas')
    op.drop_table('alertas')

    # Drop asignaciones table
    op.drop_index('idx_asignaciones_assigned_at', table_name='asignaciones')
    op.drop_index('idx_asignaciones_active', table_name='asignaciones')
    op.drop_index('idx_asignaciones_cuadrilla', table_name='asignaciones')
    op.drop_index('idx_asignaciones_ot', table_name='asignaciones')
    op.drop_table('asignaciones')

    # Drop logs_agentes table
    op.drop_index('idx_logs_agente_name', table_name='logs_agentes')
    op.drop_index('idx_logs_timestamp', table_name='logs_agentes')
    op.drop_index('idx_logs_ot', table_name='logs_agentes')
    op.drop_table('logs_agentes')

    # Drop ots table
    op.drop_index('idx_ots_created_at', table_name='ots')
    op.drop_index('idx_ots_cuadrilla', table_name='ots')
    op.drop_index('idx_ots_project_type', table_name='ots')
    op.drop_index('idx_ots_status', table_name='ots')
    op.drop_table('ots')

    # Drop cuadrillas table
    op.drop_index('idx_cuadrillas_active', table_name='cuadrillas')
    op.drop_index('idx_cuadrillas_type', table_name='cuadrillas')
    op.drop_table('cuadrillas')

