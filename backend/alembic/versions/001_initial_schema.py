"""Initial schema creation for PEI Platform

Revision ID: 001
Revises: 
Create Date: 2024-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create initial tables: cuadrillas, ots, agent_logs"""
    
    # Create cuadrillas table
    op.create_table(
        "cuadrillas",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column(
            "type",
            sa.Enum("PRINCIPAL", "RESERVA", name="cuadrillatype"),
            nullable=False,
        ),
        sa.Column("last_centroid_lat", sa.Float(), nullable=True),
        sa.Column("last_centroid_long", sa.Float(), nullable=True),
        sa.Column("max_daily_capacity", sa.Integer(), nullable=False, server_default="10"),
        sa.Column("current_load", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name", name="uq_cuadrilla_name"),
        sa.Index("ix_cuadrilla_type", "type"),
    )

    # Create ots table
    op.create_table(
        "ots",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("external_id", sa.String(length=100), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "PREPLANIFICADA",
                "PLANIFICADA",
                "ASIGNADO_TAREA",
                "DETENIDA",
                "ANULADA",
                "FINALIZADA",
                name="otstatus",
            ),
            nullable=False,
            server_default="PREPLANIFICADA",
        ),
        sa.Column(
            "project_type",
            sa.Enum("PUBLICO", "PRIVADO", "TERCERIZADO", name="projecttype"),
            nullable=False,
        ),
        sa.Column("lat", sa.Float(), nullable=True),
        sa.Column("long", sa.Float(), nullable=True),
        sa.Column("cliente_id", sa.String(length=100), nullable=False),
        sa.Column("login_id", sa.String(length=100), nullable=False),
        sa.Column("is_geo_error", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("cuadrilla_id", sa.Integer(), nullable=True),
        sa.Column("assigned_at", sa.DateTime(), nullable=True),
        sa.Column("detention_reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["cuadrilla_id"], ["cuadrillas.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("external_id", name="uq_ot_external_id"),
        sa.Index("ix_ot_external_id", "external_id"),
        sa.Index("ix_ot_status", "status"),
        sa.Index("ix_ot_project_type", "project_type"),
        sa.Index("ix_ot_cliente_id", "cliente_id"),
        sa.Index("ix_ot_login_id", "login_id"),
        sa.Index("ix_ot_is_geo_error", "is_geo_error"),
        sa.Index("ix_ot_cuadrilla_id", "cuadrilla_id"),
        sa.Index("ix_ot_status_created_at", "status", "created_at"),
        sa.Index("ix_ot_cuadrilla_status", "cuadrilla_id", "status"),
    )

    # Create agent_logs table
    op.create_table(
        "agent_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("ot_id", sa.Integer(), nullable=True),
        sa.Column("agent_name", sa.String(length=100), nullable=False),
        sa.Column("accion", sa.Text(), nullable=False),
        sa.Column(
            "resultado",
            sa.Enum("SUCCESS", "FAILURE", "WARNING", name="resultadoenum"),
            nullable=False,
        ),
        sa.Column("raw_llm_response", sa.JSON(), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.Column("timestamp", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["ot_id"], ["ots.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.Index("ix_agent_logs_timestamp", "timestamp"),
        sa.Index("ix_agent_logs_agent_name", "agent_name"),
        sa.Index("ix_agent_logs_ot_id", "ot_id"),
    )


def downgrade() -> None:
    """Drop all tables created in upgrade()"""
    
    # Drop tables in reverse order of creation
    op.drop_table("agent_logs")
    op.drop_table("ots")
    op.drop_table("cuadrillas")

