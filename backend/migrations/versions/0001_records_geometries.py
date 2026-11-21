import sqlalchemy as sa
from alembic import op

revision = "0001_records"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "records",
        sa.Column("scope", sa.String(64), primary_key=True),
        sa.Column("kind", sa.String(32), primary_key=True),
        sa.Column("key", sa.String(128), primary_key=True),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_records_listing", "records", ["scope", "kind", "updated_at"])
    if op.get_context().dialect.name == "postgresql":
        op.execute("CREATE EXTENSION IF NOT EXISTS postgis")
        op.execute(
            "CREATE TABLE city_geometries (id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY, "
            "scope varchar(64) NOT NULL, city_id varchar(48) NOT NULL, source varchar(32) NOT NULL, "
            "geometry geometry(Geometry, 4326) NOT NULL)"
        )
        op.execute("CREATE INDEX ix_city_geometries_geometry ON city_geometries USING GIST (geometry)")
        op.execute("CREATE INDEX ix_city_geometries_scope ON city_geometries (scope, city_id, source)")


def downgrade():
    if op.get_context().dialect.name == "postgresql":
        op.drop_table("city_geometries")
    op.drop_table("records")
