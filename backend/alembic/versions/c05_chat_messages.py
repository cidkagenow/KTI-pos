"""add chat_messages table

Revision ID: c05_chat_messages
Revises: c04_sunat_documents
Create Date: 2026-03-08
"""

from alembic import op
import sqlalchemy as sa


revision = "c05_chat_messages"
down_revision = "c04_sunat_documents"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "chat_messages",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("role", sa.String(length=10), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_chat_messages_user_created",
        "chat_messages",
        ["user_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_chat_messages_user_created", table_name="chat_messages")
    op.drop_table("chat_messages")
