"""Add expected_delivery_date to purchase_orders

Revision ID: c03_product_availability
Revises: c02_enhancements
Create Date: 2026-03-06 12:00:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = 'c03_product_availability'
down_revision: Union[str, None] = 'c02_enhancements'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('purchase_orders', sa.Column('expected_delivery_date', sa.Date(), nullable=True))


def downgrade() -> None:
    op.drop_column('purchase_orders', 'expected_delivery_date')
