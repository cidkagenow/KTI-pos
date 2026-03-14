"""increase decimal precision on purchase_order_items unit_cost and line_total

Revision ID: c09_po_decimal_precision
Revises: c08_trabajadores
Create Date: 2026-03-15
"""

from alembic import op
import sqlalchemy as sa


revision = "c09_po_decimal_precision"
down_revision = "c08_trabajadores"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "purchase_order_items",
        "unit_cost",
        existing_type=sa.Numeric(12, 2),
        type_=sa.Numeric(12, 6),
    )
    op.alter_column(
        "purchase_order_items",
        "line_total",
        existing_type=sa.Numeric(12, 2),
        type_=sa.Numeric(12, 6),
    )
    op.alter_column(
        "purchase_order_items",
        "flete_unit",
        existing_type=sa.Numeric(12, 2),
        type_=sa.Numeric(12, 6),
    )


def downgrade() -> None:
    op.alter_column(
        "purchase_order_items",
        "flete_unit",
        existing_type=sa.Numeric(12, 6),
        type_=sa.Numeric(12, 2),
    )
    op.alter_column(
        "purchase_order_items",
        "unit_cost",
        existing_type=sa.Numeric(12, 6),
        type_=sa.Numeric(12, 2),
    )
    op.alter_column(
        "purchase_order_items",
        "line_total",
        existing_type=sa.Numeric(12, 6),
        type_=sa.Numeric(12, 2),
    )
