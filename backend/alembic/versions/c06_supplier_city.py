"""add city column to suppliers

Revision ID: c06_supplier_city
Revises: c05_chat_messages
Create Date: 2026-03-08
"""

from alembic import op
import sqlalchemy as sa


revision = "c06_supplier_city"
down_revision = "c05_chat_messages"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("suppliers", sa.Column("city", sa.String(length=150), nullable=True))


def downgrade() -> None:
    op.drop_column("suppliers", "city")
