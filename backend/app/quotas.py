"""Atomic minute-window limits shared across API replicas."""

from hashlib import sha256

from sqlalchemy.dialects.postgresql import insert as postgres_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session

from .db import RateBucket, engine, now


def limited(identity, group, limit):
    key = sha256(f"{group}:{identity}".encode()).hexdigest()
    window = int(now().timestamp() // 60)
    insert = postgres_insert if engine.dialect.name == "postgresql" else sqlite_insert
    statement = insert(RateBucket).values(key=key, window=window, count=1)
    statement = statement.on_conflict_do_update(
        index_elements=["key", "window"],
        set_={"count": RateBucket.count + 1},
        where=RateBucket.count < limit,
    ).returning(RateBucket.count)
    with Session(engine) as session, session.begin():
        return session.scalar(statement) is None
