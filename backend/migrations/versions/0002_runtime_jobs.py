"""Persist worker leases and shared quotas."""

import sqlalchemy as sa
from alembic import op

revision = "0002_runtime"
down_revision = "0001_records"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "run_jobs",
        sa.Column("scope", sa.String(64), primary_key=True),
        sa.Column("run_id", sa.String(32), primary_key=True),
        sa.Column("available_at", sa.Float(), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("token", sa.String(32)),
    )
    op.create_index("ix_run_jobs_available", "run_jobs", ["available_at"])
    op.create_table(
        "rate_buckets",
        sa.Column("key", sa.String(64), primary_key=True),
        sa.Column("window", sa.Integer(), primary_key=True),
        sa.Column("count", sa.Integer(), nullable=False),
    )
    status = (
        "payload->>'status'"
        if op.get_context().dialect.name == "postgresql"
        else "json_extract(payload, '$.status')"
    )
    op.execute(
        "INSERT INTO run_jobs (scope, run_id, available_at, attempts) SELECT scope, key, 0, 0 "
        f"FROM records WHERE kind = 'run' AND ({status}) IN ('queued', 'running')"
    )


def downgrade():
    op.drop_table("rate_buckets")
    op.drop_table("run_jobs")
