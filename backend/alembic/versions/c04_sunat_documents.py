"""Create sunat_documents table

Revision ID: c04_sunat_documents
Revises: c03_product_availability
Create Date: 2026-03-07 12:00:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = 'c04_sunat_documents'
down_revision: Union[str, None] = 'c03_product_availability'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'sunat_documents',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('sale_id', sa.Integer(), sa.ForeignKey('sales.id'), nullable=True),
        sa.Column('doc_category', sa.String(20), nullable=False),
        sa.Column('reference_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('ticket', sa.String(100), nullable=True),
        sa.Column('sunat_status', sa.String(20), server_default='PENDIENTE', nullable=False),
        sa.Column('sunat_description', sa.Text(), nullable=True),
        sa.Column('sunat_hash', sa.String(255), nullable=True),
        sa.Column('sunat_cdr_url', sa.Text(), nullable=True),
        sa.Column('sunat_xml_url', sa.Text(), nullable=True),
        sa.Column('sunat_pdf_url', sa.Text(), nullable=True),
        sa.Column('raw_request', sa.Text(), nullable=True),
        sa.Column('raw_response', sa.Text(), nullable=True),
        sa.Column('attempt_count', sa.Integer(), server_default='0', nullable=False),
        sa.Column('last_attempt_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('sent_by', sa.Integer(), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_sunat_documents_sale_id', 'sunat_documents', ['sale_id'])
    op.create_index('ix_sunat_documents_doc_category', 'sunat_documents', ['doc_category'])
    op.create_index('ix_sunat_documents_sunat_status', 'sunat_documents', ['sunat_status'])


def downgrade() -> None:
    op.drop_index('ix_sunat_documents_sunat_status', 'sunat_documents')
    op.drop_index('ix_sunat_documents_doc_category', 'sunat_documents')
    op.drop_index('ix_sunat_documents_sale_id', 'sunat_documents')
    op.drop_table('sunat_documents')
