"""Preserve replay context in golden cases."""

import sqlalchemy as sa
from alembic import op

revision = "0002"
down_revision = "0001"


def upgrade():
    columns = {c["name"] for c in sa.inspect(op.get_bind()).get_columns("golden_cases")}
    if "messages" not in columns:
        op.add_column("golden_cases", sa.Column("messages", sa.JSON(), nullable=True))
    if "system_prompt" not in columns:
        op.add_column("golden_cases", sa.Column("system_prompt", sa.Text(), nullable=True))


def downgrade():
    raise RuntimeError("Destructive downgrade is disabled")
