"""Initial database schema creation

Revision ID: 001_initial
Revises: 
Create Date: 2024-02-13 23:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import sqlite

# revision identifiers, used by Alembic.
revision = "001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create all initial database tables."""
    # Create clientes table
    op.create_table(
        "clientes",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("external_id", sa.String(255), nullable=False),
        sa.Column("nombre", sa.String(255), nullable=False),
        sa.Column("tipo_persona", sa.Enum("NATURAL", "JURIDICA", name="tipo_persona_enum"), nullable=False),
        sa.Column("bss_id", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("external_id"),
        sa.UniqueConstraint("bss_id"),
    )
    op.create_index("ix_clientes_external_id", "clientes", ["external_id"])

    # Create logins table
    op.create_table(
        "logins",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("external_id", sa.String(255), nullable=False),
        sa.Column("cliente_id", sa.UUID(), nullable=False),
        sa.Column("direccion", sa.Text(), nullable=False),
        sa.Column("lat", sa.Float(), nullable=True),
        sa.Column("long", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["cliente_id"], ["clientes.id"], ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("external_id"),
    )
    op.create_index("ix_logins_external_id", "logins", ["external_id"])

    # Create proyectos table
    op.create_table(
        "proyectos",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("nombre", sa.String(255), nullable=False),
        sa.Column("tipo", sa.Enum("PUBLICO", "PRIVADO", "TERCERIZADO", name="proyecto_tipo_enum"), nullable=False),
        sa.Column("descripcion", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create ordenes_trabajo table
    op.create_table(
        "ordenes_trabajo",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("external_id", sa.String(255), nullable=False),
        sa.Column("cliente_id", sa.UUID(), nullable=False),
        sa.Column("login_id", sa.UUID(), nullable=False),
        sa.Column("proyecto_id", sa.UUID(), nullable=True),
        sa.Column("status", sa.Enum("PREPLANIFICADA", "PLANIFICADA", "ASIGNADO_TAREA", "DETENIDA", "ANULADA", "FINALIZADA", name="ot_status_enum"), nullable=False),
        sa.Column("lat", sa.Float(), nullable=True),
        sa.Column("long", sa.Float(), nullable=True),
        sa.Column("geo_error", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("detenida_at", sa.DateTime(), nullable=True),
        sa.Column("finalizada_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["cliente_id"], ["clientes.id"], ),
        sa.ForeignKeyConstraint(["login_id"], ["logins.id"], ),
        sa.ForeignKeyConstraint(["proyecto_id"], ["proyectos.id"], ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("external_id"),
    )
    op.create_index("ix_ordenes_trabajo_external_id", "ordenes_trabajo", ["external_id"])

    # Create cuadrillas table
    op.create_table(
        "cuadrillas",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("nombre", sa.String(255), nullable=False),
        sa.Column("tipo", sa.Enum("PRINCIPAL", "RESERVA", name="cuadrilla_tipo_enum"), nullable=False),
        sa.Column("capacidad_diaria", sa.Integer(), nullable=False),
        sa.Column("last_centroid_lat", sa.Float(), nullable=True),
        sa.Column("last_centroid_long", sa.Float(), nullable=True),
        sa.Column("activa", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("nombre"),
    )

    # Create tareas table
    op.create_table(
        "tareas",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("ot_id", sa.UUID(), nullable=False),
        sa.Column("nombre", sa.String(255), nullable=False),
        sa.Column("descripcion", sa.Text(), nullable=True),
        sa.Column("completada", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["ot_id"], ["ordenes_trabajo.id"], ),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create asignaciones table
    op.create_table(
        "asignaciones",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("ot_id", sa.UUID(), nullable=False),
        sa.Column("cuadrilla_id", sa.UUID(), nullable=False),
        sa.Column("assigned_by_agent", sa.String(255), nullable=False),
        sa.Column("distancia_centroide_km", sa.Float(), nullable=True),
        sa.Column("assigned_at", sa.DateTime(), nullable=False),
        sa.Column("unassigned_at", sa.DateTime(), nullable=True),
        sa.Column("activa", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["cuadrilla_id"], ["cuadrillas.id"], ),
        sa.ForeignKeyConstraint(["ot_id"], ["ordenes_trabajo.id"], ),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create logs_agentes table
    op.create_table(
        "logs_agentes",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("ot_id", sa.UUID(), nullable=True),
        sa.Column("agente_name", sa.String(255), nullable=False),
        sa.Column("accion", sa.String(255), nullable=False),
        sa.Column("resultado", sa.String(255), nullable=False),
        sa.Column("raw_llm_response", sa.JSON(), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["ot_id"], ["ordenes_trabajo.id"], ),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    """Drop all tables."""
    op.drop_table("logs_agentes")
    op.drop_table("asignaciones")
    op.drop_table("tareas")
    op.drop_table("cuadrillas")
    op.drop_table("ordenes_trabajo")
    op.drop_table("proyectos")
    op.drop_table("logins")
    op.drop_table("clientes")

