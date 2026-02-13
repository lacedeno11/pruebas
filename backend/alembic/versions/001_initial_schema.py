"""Initial schema with OTs, Cuadrillas, LogAgentes, and Asignaciones

Revision ID: 001
Revises: 
Create Date: 2024-01-01 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create OT status enum
    ot_status = sa.Enum(
        'PREPLANIFICADA',
        'PLANIFICADA',
        'ASIGNADO_TAREA',
        'DETENIDA',
        'ANULADA',
        'FINALIZADA',
        name='ot_status'
    )
    ot_status.create(op.get_bind(), checkfirst=True)

    # Create project_type enum
    project_type = sa.Enum(
        'PUBLICO',
        'PRIVADO',
        'TERCERIZADO',
        name='project_type'
    )
    project_type.create(op.get_bind(), checkfirst=True)

    # Create cuadrilla_type enum
    cuadrilla_type = sa.Enum(
        'Principal',
        'Reserva',
        name='cuadrilla_type'
    )
    cuadrilla_type.create(op.get_bind(), checkfirst=True)

    # Create ots table
    op.create_table(
        'ots',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('external_id', sa.String(), nullable=False),
        sa.Column('status', ot_status, nullable=False),
        sa.Column('project_type', project_type, nullable=False),
        sa.Column('lat', sa.Float(), nullable=True),
        sa.Column('long', sa.Float(), nullable=True),
        sa.Column('cliente_id', sa.String(), nullable=False),
        sa.Column('login_id', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('geo_error', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('detention_reason', sa.String(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('external_id'),
    )
    op.create_index(op.f('ix_ots_external_id'), 'ots', ['external_id'], unique=True)

    # Create cuadrillas table
    op.create_table(
        'cuadrillas',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('type', cuadrilla_type, nullable=False),
        sa.Column('last_centroid_lat', sa.Float(), nullable=True),
        sa.Column('last_centroid_long', sa.Float(), nullable=True),
        sa.Column('capacity', sa.Integer(), nullable=False, server_default='10'),
        sa.Column('current_load', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name'),
    )
    op.create_index(op.f('ix_cuadrillas_name'), 'cuadrillas', ['name'], unique=True)

    # Create logs_agentes table
    op.create_table(
        'logs_agentes',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('ot_id', sa.Integer(), nullable=True),
        sa.Column('cuadrilla_id', sa.Integer(), nullable=True),
        sa.Column('agente_name', sa.String(), nullable=False),
        sa.Column('accion', sa.String(), nullable=False),
        sa.Column('resultado', sa.String(), nullable=False),
        sa.Column('raw_llm_response', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['ot_id'], ['ots.id'], ),
        sa.ForeignKeyConstraint(['cuadrilla_id'], ['cuadrillas.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_logs_agentes_agente_name'), 'logs_agentes', ['agente_name'], unique=False)
    op.create_index(op.f('ix_logs_agentes_ot_id'), 'logs_agentes', ['ot_id'], unique=False)

    # Create asignaciones table
    op.create_table(
        'asignaciones',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('ot_id', sa.Integer(), nullable=False),
        sa.Column('cuadrilla_id', sa.Integer(), nullable=False),
        sa.Column('assigned_at', sa.DateTime(), nullable=False),
        sa.Column('assigned_by_agent', sa.String(), nullable=True),
        sa.Column('distance_to_centroid', sa.Float(), nullable=True),
        sa.Column('priority', sa.Integer(), nullable=False, server_default='0'),
        sa.ForeignKeyConstraint(['cuadrilla_id'], ['cuadrillas.id'], ),
        sa.ForeignKeyConstraint(['ot_id'], ['ots.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_asignaciones_cuadrilla_id'), 'asignaciones', ['cuadrilla_id'], unique=False)
    op.create_index(op.f('ix_asignaciones_ot_id'), 'asignaciones', ['ot_id'], unique=False)


def downgrade() -> None:
    # Drop indexes
    op.drop_index(op.f('ix_asignaciones_ot_id'), table_name='asignaciones')
    op.drop_index(op.f('ix_asignaciones_cuadrilla_id'), table_name='asignaciones')
    op.drop_index(op.f('ix_logs_agentes_ot_id'), table_name='logs_agentes')
    op.drop_index(op.f('ix_logs_agentes_agente_name'), table_name='logs_agentes')
    op.drop_index(op.f('ix_cuadrillas_name'), table_name='cuadrillas')
    op.drop_index(op.f('ix_ots_external_id'), table_name='ots')

    # Drop tables
    op.drop_table('asignaciones')
    op.drop_table('logs_agentes')
    op.drop_table('cuadrillas')
    op.drop_table('ots')

    # Drop enums
    sa.Enum(name='cuadrilla_type').drop(op.get_bind(), checkfirst=True)
    sa.Enum(name='project_type').drop(op.get_bind(), checkfirst=True)
    sa.Enum(name='ot_status').drop(op.get_bind(), checkfirst=True)

