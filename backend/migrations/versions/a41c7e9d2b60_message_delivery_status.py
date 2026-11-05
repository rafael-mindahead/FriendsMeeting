"""Add delivery and read timestamps to messages."""

from alembic import op
import sqlalchemy as sa


revision = "a41c7e9d2b60"
down_revision = "9d2c4f6a1b83"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "messages",
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "messages",
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("messages", "read_at")
    op.drop_column("messages", "delivered_at")