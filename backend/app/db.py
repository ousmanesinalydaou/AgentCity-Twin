from datetime import UTC, datetime
from typing import Any

from sqlalchemy import JSON, DateTime, Float, Index, Integer, String, create_engine, delete, event, select, text
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

from .config import database_url


def now() -> datetime:
    return datetime.now(UTC)


class Base(DeclarativeBase):
    pass


class Record(Base):
    __tablename__ = "records"
    scope: Mapped[str] = mapped_column(String(64), primary_key=True)
    kind: Mapped[str] = mapped_column(String(32), primary_key=True)
    key: Mapped[str] = mapped_column(String(254), primary_key=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)
    __table_args__ = (Index("ix_records_listing", "scope", "kind", "updated_at"),)


class RunJob(Base):
    __tablename__ = "run_jobs"
    scope: Mapped[str] = mapped_column(String(64), primary_key=True)
    run_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    available_at: Mapped[float] = mapped_column(Float, default=0)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    token: Mapped[str | None] = mapped_column(String(32), default=None)
    __table_args__ = (Index("ix_run_jobs_available", "available_at"),)


class RateBucket(Base):
    __tablename__ = "rate_buckets"
    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    window: Mapped[int] = mapped_column(Integer, primary_key=True)
    count: Mapped[int] = mapped_column(Integer, default=0)


def make_engine(url: str):
    engine = create_engine(url, pool_pre_ping=True)
    if engine.dialect.name == "sqlite":

        @event.listens_for(engine, "connect")
        def configure(connection, _):
            connection.execute("PRAGMA busy_timeout=5000")
            connection.execute("PRAGMA journal_mode=WAL")

    return engine


engine = make_engine(database_url())


class Store:
    """Persist workspace entities and tenant-scoped run archives."""

    def __init__(self, session: Session):
        self.session = session

    def get(self, scope: str, kind: str, key: str, lock=False):
        row = self.session.get(Record, (scope, kind, key), with_for_update=lock)
        return row.payload if row else None

    def list(self, scope: str, kind: str, limit: int | None = 250, **fields: str):
        rows = self.session.scalars(
            select(Record)
            .where(
                Record.scope == scope,
                Record.kind == kind,
                *(Record.payload[key].as_string() == value for key, value in fields.items()),
            )
            .order_by(Record.updated_at.desc(), Record.key)
            .limit(limit)
        )
        return [row.payload for row in rows]

    def put(self, scope: str, kind: str, key: str, payload: dict):
        self.session.merge(Record(scope=scope, kind=kind, key=key, payload=payload))

    def insert(self, scope: str, kind: str, key: str, payload: dict):
        self.session.add(Record(scope=scope, kind=kind, key=key, payload=payload))

    def remove(self, scope: str, kind: str, key: str) -> bool:
        result = self.session.execute(
            delete(Record).where(Record.scope == scope, Record.kind == kind, Record.key == key)
        )
        return result.rowcount == 1

    def spatial(self, scope: str, city_id: str, source: str, geometry: dict):
        if self.session.bind.dialect.name != "postgresql":
            return
        import json

        self.session.execute(
            text(
                "INSERT INTO city_geometries (scope, city_id, source, geometry) "
                "VALUES (:scope, :city, :source, ST_SetSRID(ST_GeomFromGeoJSON(:geometry), 4326))"
            ),
            {"scope": scope, "city": city_id, "source": source, "geometry": json.dumps(geometry)},
        )

    def remove_spatial(self, scope: str, source: str):
        if self.session.bind.dialect.name == "postgresql":
            self.session.execute(
                text("DELETE FROM city_geometries WHERE scope = :scope AND source = :source"),
                {"scope": scope, "source": source},
            )


def db():
    with Session(engine) as session:
        yield Store(session)
