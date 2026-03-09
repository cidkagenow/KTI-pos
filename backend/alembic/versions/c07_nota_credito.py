"""add nota de credito fields to sales

Revision ID: c07_nota_credito
Revises: c06_supplier_city
Create Date: 2026-03-09
"""

from alembic import op
import sqlalchemy as sa


revision = "c07_nota_credito"
down_revision = "c06_supplier_city"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "sales",
        sa.Column("ref_sale_id", sa.Integer(), sa.ForeignKey("sales.id"), nullable=True),
    )
    op.add_column(
        "sales",
        sa.Column("nc_motivo_code", sa.String(length=5), nullable=True),
    )
    op.add_column(
        "sales",
        sa.Column("nc_motivo_text", sa.String(length=200), nullable=True),
    )
    op.create_index("ix_sales_ref_sale_id", "sales", ["ref_sale_id"])


def downgrade() -> None:
    op.drop_index("ix_sales_ref_sale_id", table_name="sales")
    op.drop_column("sales", "nc_motivo_text")
    op.drop_column("sales", "nc_motivo_code")
    op.drop_column("sales", "ref_sale_id")
