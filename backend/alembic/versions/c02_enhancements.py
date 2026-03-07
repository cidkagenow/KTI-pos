"""KTI2 feature enhancements

Revision ID: c02_enhancements
Revises: b05505109857
Create Date: 2026-03-06 01:00:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = 'c02_enhancements'
down_revision: Union[str, None] = 'b05505109857'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Product enhancements
    op.add_column('products', sa.Column('wholesale_price', sa.Numeric(12, 2), nullable=True))
    op.add_column('products', sa.Column('comentario', sa.String(500), nullable=True))

    # Client enhancements
    op.add_column('clients', sa.Column('ref_comercial', sa.String(200), nullable=True))
    op.add_column('clients', sa.Column('zona', sa.String(100), nullable=True))
    op.add_column('clients', sa.Column('comentario', sa.String(500), nullable=True))
    op.add_column('clients', sa.Column('credit_limit', sa.Numeric(12, 2), nullable=True))
    op.add_column('clients', sa.Column('credit_days', sa.Integer(), nullable=True))

    # Purchase order enhancements
    op.add_column('purchase_orders', sa.Column('doc_type', sa.String(20), nullable=True))
    op.add_column('purchase_orders', sa.Column('doc_number', sa.String(50), nullable=True))
    op.add_column('purchase_orders', sa.Column('condicion', sa.String(20), server_default='CONTADO', nullable=True))
    op.add_column('purchase_orders', sa.Column('moneda', sa.String(10), server_default='SOLES', nullable=True))
    op.add_column('purchase_orders', sa.Column('tipo_cambio', sa.Numeric(8, 4), nullable=True))
    op.add_column('purchase_orders', sa.Column('igv_included', sa.Boolean(), server_default='true', nullable=True))
    op.add_column('purchase_orders', sa.Column('subtotal', sa.Numeric(12, 2), nullable=True))
    op.add_column('purchase_orders', sa.Column('igv_amount', sa.Numeric(12, 2), nullable=True))
    op.add_column('purchase_orders', sa.Column('flete', sa.Numeric(12, 2), server_default='0', nullable=True))
    op.add_column('purchase_orders', sa.Column('grr_number', sa.String(50), nullable=True))
    op.add_column('purchase_orders', sa.Column('supplier_doc', sa.String(50), nullable=True))
    op.add_column('purchase_orders', sa.Column('issue_date', sa.DateTime(timezone=True), nullable=True))

    # Purchase order item enhancements
    op.add_column('purchase_order_items', sa.Column('discount_pct1', sa.Numeric(5, 2), server_default='0', nullable=True))
    op.add_column('purchase_order_items', sa.Column('discount_pct2', sa.Numeric(5, 2), server_default='0', nullable=True))
    op.add_column('purchase_order_items', sa.Column('discount_pct3', sa.Numeric(5, 2), server_default='0', nullable=True))
    op.add_column('purchase_order_items', sa.Column('flete_unit', sa.Numeric(12, 2), server_default='0', nullable=True))
    op.add_column('purchase_order_items', sa.Column('product_code', sa.String(50), nullable=True))
    op.add_column('purchase_order_items', sa.Column('product_name', sa.String(200), nullable=True))

    # Sale enhancements
    op.add_column('sales', sa.Column('cash_received', sa.Numeric(12, 2), nullable=True))
    op.add_column('sales', sa.Column('cash_change', sa.Numeric(12, 2), nullable=True))
    op.add_column('sales', sa.Column('payment_method', sa.String(20), server_default='EFECTIVO', nullable=True))
    op.add_column('sales', sa.Column('max_discount_pct', sa.Numeric(5, 2), server_default='0', nullable=True))

    # Supplier enhancements
    op.add_column('suppliers', sa.Column('address', sa.String(300), nullable=True))


def downgrade() -> None:
    op.drop_column('suppliers', 'address')
    op.drop_column('sales', 'max_discount_pct')
    op.drop_column('sales', 'payment_method')
    op.drop_column('sales', 'cash_change')
    op.drop_column('sales', 'cash_received')
    op.drop_column('purchase_order_items', 'product_name')
    op.drop_column('purchase_order_items', 'product_code')
    op.drop_column('purchase_order_items', 'flete_unit')
    op.drop_column('purchase_order_items', 'discount_pct3')
    op.drop_column('purchase_order_items', 'discount_pct2')
    op.drop_column('purchase_order_items', 'discount_pct1')
    op.drop_column('purchase_orders', 'issue_date')
    op.drop_column('purchase_orders', 'supplier_doc')
    op.drop_column('purchase_orders', 'grr_number')
    op.drop_column('purchase_orders', 'flete')
    op.drop_column('purchase_orders', 'igv_amount')
    op.drop_column('purchase_orders', 'subtotal')
    op.drop_column('purchase_orders', 'igv_included')
    op.drop_column('purchase_orders', 'tipo_cambio')
    op.drop_column('purchase_orders', 'moneda')
    op.drop_column('purchase_orders', 'condicion')
    op.drop_column('purchase_orders', 'doc_number')
    op.drop_column('purchase_orders', 'doc_type')
    op.drop_column('clients', 'credit_days')
    op.drop_column('clients', 'credit_limit')
    op.drop_column('clients', 'comentario')
    op.drop_column('clients', 'zona')
    op.drop_column('clients', 'ref_comercial')
    op.drop_column('products', 'comentario')
    op.drop_column('products', 'wholesale_price')
