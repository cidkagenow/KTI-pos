"""Add ubigeo fields to clients table (departamento, provincia, distrito, ubigeo code)."""

revision = "c16_client_ubigeo"
down_revision = "c15_cat_sales"

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column("clients", sa.Column("departamento", sa.String(50), nullable=True))
    op.add_column("clients", sa.Column("provincia", sa.String(50), nullable=True))
    op.add_column("clients", sa.Column("distrito", sa.String(50), nullable=True))
    op.add_column("clients", sa.Column("ubigeo", sa.String(6), nullable=True))


def downgrade():
    op.drop_column("clients", "ubigeo")
    op.drop_column("clients", "distrito")
    op.drop_column("clients", "provincia")
    op.drop_column("clients", "departamento")
