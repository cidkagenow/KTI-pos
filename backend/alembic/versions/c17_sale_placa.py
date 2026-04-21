"""Add placa field to sales table for vehicle plate number."""

revision = "c17_sale_placa"
down_revision = "c16_client_ubigeo"

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column("sales", sa.Column("placa", sa.String(20), nullable=True))


def downgrade():
    op.drop_column("sales", "placa")
