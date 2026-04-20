"""Add cat_sales table for CAT/AFOCAT certificate tracking.

Revision ID: c15_cat_sales
"""

from alembic import op
import sqlalchemy as sa

revision = "c15_cat_sales"
down_revision = "c14"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "cat_sales",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("certificate_number", sa.String(50), nullable=True),
        sa.Column("serie", sa.String(20), nullable=True),
        sa.Column("placa", sa.String(20), nullable=False),
        sa.Column("marca", sa.String(100), nullable=True),
        sa.Column("modelo", sa.String(100), nullable=True),
        sa.Column("año", sa.Integer(), nullable=True),
        sa.Column("serie_vehiculo", sa.String(100), nullable=True),
        sa.Column("asientos", sa.Integer(), nullable=True),
        sa.Column("categoria", sa.String(20), nullable=True),
        sa.Column("clase", sa.String(50), nullable=True),
        sa.Column("uso", sa.String(100), nullable=True),
        sa.Column("customer_name", sa.String(200), nullable=False),
        sa.Column("customer_dni", sa.String(20), nullable=True),
        sa.Column("customer_phone", sa.String(50), nullable=True),
        sa.Column("customer_address", sa.String(300), nullable=True),
        sa.Column("fecha_desde", sa.String(20), nullable=True),
        sa.Column("fecha_hasta", sa.String(20), nullable=True),
        sa.Column("precio", sa.Numeric(10, 2), nullable=True),
        sa.Column("ap_extra", sa.Numeric(10, 2), nullable=True),
        sa.Column("total", sa.Numeric(10, 2), nullable=True),
        sa.Column("status", sa.String(20), server_default="VENDIDO"),
        sa.Column("pdf_cat_path", sa.String(300), nullable=True),
        sa.Column("pdf_boleta_path", sa.String(300), nullable=True),
        sa.Column("sold_by", sa.Integer(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade():
    op.drop_table("cat_sales")
