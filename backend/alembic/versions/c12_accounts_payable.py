"""Add supplier_payments table and credit_days to suppliers

Revision ID: c12
Revises: c11_series_is_default
"""
from alembic import op
import sqlalchemy as sa

revision = "c12"
down_revision = "c11_series_is_default"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("suppliers", sa.Column("credit_days", sa.Integer(), server_default="30", nullable=False))

    op.create_table(
        "supplier_payments",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("purchase_order_id", sa.Integer(), sa.ForeignKey("purchase_orders.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("payment_date", sa.Date(), nullable=False),
        sa.Column("payment_method", sa.String(20), nullable=False),
        sa.Column("reference", sa.String(100), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade():
    op.drop_table("supplier_payments")
    op.drop_column("suppliers", "credit_days")
