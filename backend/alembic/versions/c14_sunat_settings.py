"""Add sunat_settings table for toggle controls

Revision ID: c14
Revises: c13
"""
from alembic import op
import sqlalchemy as sa

revision = "c14"
down_revision = "c13"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "sunat_settings",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("auto_send_enabled", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("block_before_10pm", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_by", sa.Integer, sa.ForeignKey("users.id"), nullable=True),
    )
    # Insert default row
    op.execute("INSERT INTO sunat_settings (id, auto_send_enabled, block_before_10pm) VALUES (1, true, true)")


def downgrade() -> None:
    op.drop_table("sunat_settings")
