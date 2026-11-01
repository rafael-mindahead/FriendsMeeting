"""Store sanitized avatars in PostgreSQL, independently of user records."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "f7b2c31d904e"
down_revision = "e82a4c51d902"
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.create_table(
        "user_avatars",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("image", sa.LargeBinary(), nullable=False),
        sa.Column("media_type", sa.String(length=32), nullable=False),
        sa.Column("revision", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

def downgrade() -> None:
    op.drop_table("user_avatars")
