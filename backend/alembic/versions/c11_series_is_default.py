"""Add is_default column to document_series

Revision ID: c11_series_is_default
Revises: c10_online_store
"""
from alembic import op
import sqlalchemy as sa

revision = "c11_series_is_default"
down_revision = "c10_online_store"


def upgrade():
    op.add_column(
        "document_series",
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default="false"),
    )


def downgrade():
    op.drop_column("document_series", "is_default")
