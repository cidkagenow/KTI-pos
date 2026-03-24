"""Add image_path to products

Revision ID: c13
Revises: c12
"""
from alembic import op
import sqlalchemy as sa

revision = "c13"
down_revision = "c12"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("products", sa.Column("image_path", sa.String(300), nullable=True))


def downgrade() -> None:
    op.drop_column("products", "image_path")
