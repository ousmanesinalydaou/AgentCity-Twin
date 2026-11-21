"""Poll the shared database and dispatch leased work to bounded executors."""

import logging
import os
import signal
import socket
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from threading import Event, Thread

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from .db import RateBucket, Record, Store, engine, now
from .delivery import process_delivery
from .execution import TERMINAL_RUNS
from .jobs import claim
from .monitoring import initialize, tracer

logger = logging.getLogger("agentcity.worker")


def sweep():
    with Session(engine) as session, session.begin():
        stamp = now().timestamp()
        session.execute(
            delete(Record).where(
                Record.scope == "system",
                Record.kind.in_(("access", "refresh", "reset", "verify", "oidc-state", "invite-token")),
                Record.payload["expires"].as_float() < stamp,
            )
        )
        session.execute(delete(RateBucket).where(RateBucket.window < int(stamp // 60) - 2))
        session.execute(
            delete(Record).where(Record.kind == "telemetry-event", Record.updated_at < now() - timedelta(days=7))
        )
        days = int(os.getenv("RUN_RETENTION_DAYS", "0"))
        if days > 0:
            archive = session.scalars(
                select(Record)
                .where(
                    Record.kind == "run",
                    Record.updated_at < now() - timedelta(days=days),
                    Record.payload["status"].as_string().in_(TERMINAL_RUNS),
                )
                .limit(500)
                .with_for_update(skip_locked=True)
            )
            for row in archive:
                Store(session).remove(row.scope, "run-input", row.key)
                session.delete(row)


def heartbeat():
    with Session(engine) as session, session.begin():
        Store(session).put("system", "worker", socket.gethostname()[:120], {"seen_at": now().isoformat()})


def healthy():
    with Session(engine) as session:
        row = session.get(Record, ("system", "worker", socket.gethostname()[:120]))
        if row is None:
            return False
        updated = row.updated_at if row.updated_at.tzinfo else row.updated_at.replace(tzinfo=now().tzinfo)
        return updated > now() - timedelta(seconds=45)


def perform(scope, run_id, token):
    from .runs import execute

    with tracer.start_as_current_span("simulation.execute", attributes={"agentcity.run_id": run_id}):
        execute(scope, run_id, token)


def serve(stop):
    from .telemetry import scheduled_refresh

    slots = max(1, min(16, int(os.getenv("WORKER_CONCURRENCY", "4"))))
    active = set()
    next_sweep = 0.0
    next_heartbeat = 0.0
    with ThreadPoolExecutor(max_workers=slots) as analyses, ThreadPoolExecutor(max_workers=2) as operations:
        periodic = {}
        while not stop.is_set():
            for future in {task for task in active if task.done()}:
                active.remove(future)
                if future.exception():
                    logger.error("An analysis task stopped unexpectedly", exc_info=future.exception())
            try:
                while len(active) < slots and (job := claim()):
                    active.add(analyses.submit(perform, *job))
                for task in (scheduled_refresh, process_delivery):
                    future = periodic.get(task)
                    if not future or future.done():
                        if future and future.exception():
                            logger.error("A periodic task stopped unexpectedly", exc_info=future.exception())
                        periodic[task] = operations.submit(task)
                if time.monotonic() >= next_sweep:
                    sweep()
                    next_sweep = time.monotonic() + 1800
                if time.monotonic() >= next_heartbeat:
                    heartbeat()
                    next_heartbeat = time.monotonic() + 15
            except Exception:
                logger.exception("Worker iteration failed")
            stop.wait(0.5)


def embedded():
    stop = Event()
    thread = Thread(target=serve, args=(stop,), name="agentcity-worker", daemon=True)
    thread.start()
    return stop, thread


def main():
    logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
    initialize("worker")
    stop = Event()
    signal.signal(signal.SIGTERM, lambda *_: stop.set())
    signal.signal(signal.SIGINT, lambda *_: stop.set())
    serve(stop)


if __name__ == "__main__":
    if "--health" in sys.argv:
        sys.exit(0 if healthy() else 1)
    main()
