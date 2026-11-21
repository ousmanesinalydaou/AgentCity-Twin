"""Accept the complete validated length of an email identity key."""

import sqlalchemy as sa
from alembic import op

revision = "0003_record_keys"
down_revision = "0002_runtime"
branch_labels = None
depends_on = None


def upgrade():
    if op.get_context().dialect.name == "postgresql":
        op.alter_column("records", "key", existing_type=sa.String(128), type_=sa.String(254))


def downgrade():
    if op.get_context().dialect.name == "postgresql":
        op.alter_column("records", "key", existing_type=sa.String(254), type_=sa.String(128))
