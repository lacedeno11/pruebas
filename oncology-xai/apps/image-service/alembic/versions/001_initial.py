"""Initial migration - images table

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
    image_format = postgresql.ENUM('png', 'biff', name='image_format')
    image_format.create(op.get_bind())

    op.create_table(
        'images',
        sa.Column('image_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('case_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('format', postgresql.ENUM('png', 'biff', name='image_format', create_type=False), nullable=False),
        sa.Column('storage_uri', sa.String(1024), nullable=False),
        sa.Column('checksum', sa.String(128), nullable=False),
        sa.Column('size_bytes', sa.BigInteger(), nullable=False),
        sa.Column('stain', sa.String(255), nullable=True),
        sa.Column('magnification', sa.String(50), nullable=True),
        sa.Column('notes', sa.String(2000), nullable=True),
        sa.Column('uploaded_by', sa.String(255), nullable=True),
        sa.Column('uploaded_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('image_id'),
    )
    op.create_index('ix_images_case_id', 'images', ['case_id'])

def downgrade() -> None:
    op.drop_table('images')
    op.execute('DROP TYPE image_format')
