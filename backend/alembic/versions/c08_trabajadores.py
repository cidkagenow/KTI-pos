"""add trabajadores and asistencias tables, add trabajador_id to sales

Revision ID: c08_trabajadores
Revises: c07_nota_credito
Create Date: 2026-03-12
"""

from alembic import op
import sqlalchemy as sa


revision = "c08_trabajadores"
down_revision = "c07_nota_credito"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── Trabajadores table ───────────────────────────────────────────
    op.create_table(
        "trabajadores",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("full_name", sa.String(100), nullable=False),
        sa.Column("dni", sa.String(20), nullable=True, unique=True),
        sa.Column("phone", sa.String(20), nullable=True),
        sa.Column("cargo", sa.String(30), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )

    # ── Asistencias table ────────────────────────────────────────────
    op.create_table(
        "asistencias",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "trabajador_id",
            sa.Integer(),
            sa.ForeignKey("trabajadores.id"),
            nullable=False,
        ),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("check_in_time", sa.String(5), nullable=True),
        sa.Column("check_out_time", sa.String(5), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="PRESENTE"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint(
            "trabajador_id", "date", name="uq_asistencia_trabajador_date"
        ),
    )
    op.create_index(
        "ix_asistencias_date", "asistencias", ["date"]
    )

    # ── Add trabajador_id to sales ───────────────────────────────────
    op.add_column(
        "sales",
        sa.Column(
            "trabajador_id",
            sa.Integer(),
            sa.ForeignKey("trabajadores.id"),
            nullable=True,
        ),
    )
    op.create_index("ix_sales_trabajador_id", "sales", ["trabajador_id"])

    # Make seller_id nullable for new sales that use trabajador_id instead
    op.alter_column("sales", "seller_id", existing_type=sa.Integer(), nullable=True)


def downgrade() -> None:
    op.alter_column("sales", "seller_id", existing_type=sa.Integer(), nullable=False)
    op.drop_index("ix_sales_trabajador_id", table_name="sales")
    op.drop_column("sales", "trabajador_id")
    op.drop_index("ix_asistencias_date", table_name="asistencias")
    op.drop_table("asistencias")
    op.drop_table("trabajadores")
