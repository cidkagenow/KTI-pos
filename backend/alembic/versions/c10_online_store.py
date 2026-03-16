"""add online store: is_online flag + online_orders tables

Revision ID: c10_online_store
Revises: c09_po_decimal_precision
Create Date: 2026-03-15
"""

from alembic import op
import sqlalchemy as sa

revision = "c10_online_store"
down_revision = "c09_po_decimal_precision"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add is_online flag to products
    op.add_column(
        "products",
        sa.Column("is_online", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )

    # Create online_orders table
    op.create_table(
        "online_orders",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("order_code", sa.String(20), unique=True, nullable=False),
        sa.Column("customer_name", sa.String(200), nullable=False),
        sa.Column("customer_phone", sa.String(20), nullable=False),
        sa.Column("customer_email", sa.String(200), nullable=True),
        sa.Column(
            "payment_method",
            sa.String(20),
            nullable=False,
            server_default="EN_TIENDA",
        ),
        sa.Column("payment_reference", sa.String(200), nullable=True),
        sa.Column("subtotal", sa.Numeric(12, 2), nullable=False),
        sa.Column("igv_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("total", sa.Numeric(12, 2), nullable=False),
        sa.Column(
            "status",
            sa.String(20),
            nullable=False,
            server_default="PENDIENTE",
        ),
        sa.Column("confirmed_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ready_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("picked_up_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancel_reason", sa.String(500), nullable=True),
        sa.Column("sale_id", sa.Integer(), sa.ForeignKey("sales.id"), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )

    # Create online_order_items table
    op.create_table(
        "online_order_items",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "order_id",
            sa.Integer(),
            sa.ForeignKey("online_orders.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "product_id",
            sa.Integer(),
            sa.ForeignKey("products.id"),
            nullable=False,
        ),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("unit_price", sa.Numeric(12, 2), nullable=False),
        sa.Column("line_total", sa.Numeric(12, 2), nullable=False),
        sa.Column("product_code", sa.String(50), nullable=False),
        sa.Column("product_name", sa.String(200), nullable=False),
        sa.Column("brand_name", sa.String(100), nullable=True),
        sa.Column("presentation", sa.String(100), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("online_order_items")
    op.drop_table("online_orders")
    op.drop_column("products", "is_online")
