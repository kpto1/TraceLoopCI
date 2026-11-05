"""Adopt the original schema without destroying existing data."""

from alembic import op

revision = "0001"
down_revision = None


def upgrade():
    from migrations.schema_v1 import Base

    Base.metadata.create_all(op.get_bind(), checkfirst=True)


def downgrade():
    raise RuntimeError("Destructive downgrade is disabled; restore a verified database backup")
