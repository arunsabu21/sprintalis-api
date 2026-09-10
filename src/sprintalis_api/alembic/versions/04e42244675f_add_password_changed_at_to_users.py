"""add password_changed_at to users

Revision ID: 04e42244675f
Revises: 922d4ae065de
Create Date: 2026-09-10 20:29:41.368689

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "04e42244675f"
down_revision: Union[str, Sequence[str], None] = "922d4ae065de"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("password_changed_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("users", "password_changed_at")
