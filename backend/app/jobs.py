"""Durable execution leases with fencing when a provider or worker stalls."""

from threading import Lock
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from .db import RunJob, Store, engine, now
from .execution import TERMINAL_RUNS, finish_execution

LEASE_SECONDS = 180
MAX_ATTEMPTS = 3
SQLITE_LOCK = Lock()


class LeaseLost(Exception):
    pass


def enqueue(store: Store, scope: str, run_id: str) -> None:
    store.session.add(RunJob(scope=scope, run_id=run_id))


def _claim():
    with Session(engine) as session, session.begin():
        stamp = now().timestamp()
        job = session.scalar(
            select(RunJob)
            .where(RunJob.available_at <= stamp)
            .order_by(RunJob.available_at, RunJob.run_id)
            .limit(1)
            .with_for_update(skip_locked=True)
        )
        if job is None:
            return None
        store = Store(session)
        run = store.get(job.scope, "run", job.run_id, lock=True)
        if not run or run["status"] in TERMINAL_RUNS:
            session.delete(job)
            return None
        events = run["events"]
        if job.attempts >= MAX_ATTEMPTS:
            message = "The run exceeded the worker retry limit."
            events.append(
                {
                    "seq": len(events) + 1,
                    "stage": "error",
                    "agent": None,
                    "status": "failed",
                    "text": message,
                    "time": now().isoformat(),
                    "data": {},
                }
            )
            run = {**run, "status": "failed", "error": message, "events": events}
            if run.get("execution"):
                run["execution"] = finish_execution(run["execution"], "failed")
            store.put(job.scope, "run", job.run_id, run)
            session.delete(job)
            return None
        if job.attempts:
            events.append(
                {
                    "seq": len(events) + 1,
                    "stage": "worker",
                    "agent": None,
                    "status": "running",
                    "text": "Resuming an interrupted run.",
                    "time": now().isoformat(),
                    "data": {"attempt": job.attempts + 1},
                }
            )
        job.available_at = stamp + LEASE_SECONDS
        job.attempts += 1
        job.token = uuid4().hex
        store.put(job.scope, "run", job.run_id, {**run, "status": "running", "events": events})
        return job.scope, job.run_id, job.token


def claim():
    if engine.dialect.name == "sqlite":
        with SQLITE_LOCK:
            return _claim()
    return _claim()


def persist(scope, run_id, token, run, notifications=()):
    with Session(engine) as session, session.begin():
        job = session.get(RunJob, (scope, run_id), with_for_update=True)
        if not job or job.token != token:
            raise LeaseLost()
        store = Store(session)
        store.put(scope, "run", run_id, {**run})
        if notifications:
            from .delivery import publish

            for notification in notifications:
                publish(store, scope, **notification)
        if run["status"] in TERMINAL_RUNS:
            session.delete(job)
        else:
            job.available_at = now().timestamp() + LEASE_SECONDS
