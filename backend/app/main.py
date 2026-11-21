import logging
import os
import time
from contextlib import asynccontextmanager
from uuid import uuid4

from anyio.to_thread import run_sync
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from . import (
    admin_routes,
    api_access,
    auth_routes,
    calibration_routes,
    city_routes,
    delivery_routes,
    experiments,
    invitations,
    model_routes,
    oidc,
    operations,
    public_routes,
    run_routes,
    telemetry_routes,
)
from .config import demo_enabled, enabled, public_origin
from .db import Base, engine
from .monitoring import http_latency, http_requests, initialize, tracer
from .quotas import limited
from .worker import embedded

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger("agentcity.http")
initialize("api")


@asynccontextmanager
async def lifespan(_app):
    if engine.dialect.name == "sqlite" and enabled("SQLITE_AUTO_SCHEMA", "true"):
        Base.metadata.create_all(engine)
    worker = embedded() if not enabled("EXTERNAL_WORKER") else None
    try:
        yield
    finally:
        if worker:
            stop, thread = worker
            stop.set()
            await run_sync(thread.join, 15)


app = FastAPI(title="AgentCity Twin API", version="1.0.0", lifespan=lifespan)
MAX_BODY = 2_000_000


@app.middleware("http")
async def protect(request: Request, call_next):
    started = time.perf_counter()
    request_id = uuid4().hex
    path = request.url.path
    response = None
    if request.method in {"POST", "PATCH", "PUT", "DELETE"}:
        origin = request.headers.get("origin")
        fetch_site = request.headers.get("sec-fetch-site")
        if (origin and origin != public_origin()) or fetch_site == "cross-site":
            response = JSONResponse({"detail": "This request origin is not allowed."}, status_code=403)
        sizes = request.headers.get("content-length")
        if sizes and (len(sizes) > 10 or not sizes.isdecimal() or int(sizes) > MAX_BODY):
            response = JSONResponse({"detail": "The request is too large."}, status_code=413)
        identity = request.client.host if request.client else "unknown"
        group = "auth" if path.startswith("/api/v1/auth/") and "/preferences" not in path else "write"
        if response is None and await run_sync(limited, identity, group, 24 if group == "auth" else 120):
            response = JSONResponse(
                {"detail": "Too many requests. Retry in a minute."}, status_code=429, headers={"Retry-After": "60"}
            )
        if response is None and request.headers.get("content-type", "").startswith("application/json"):
            chunks = bytearray()
            async for chunk in request.stream():
                chunks.extend(chunk)
                if len(chunks) > MAX_BODY:
                    response = JSONResponse({"detail": "The request is too large."}, status_code=413)
                    break
            request._body = bytes(chunks)
    with tracer.start_as_current_span("api.request", attributes={"http.request.method": request.method}) as span:
        if response is None:
            response = await call_next(request)
        span.set_attribute("http.response.status_code", response.status_code)
        span_context = span.get_span_context()
        if span_context.is_valid:
            response.headers["X-Trace-ID"] = format(span_context.trace_id, "032x")
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Content-Type-Options"] = "nosniff"
    if "cache-control" not in response.headers:
        response.headers["Cache-Control"] = "no-store"
    attributes = {"method": request.method, "status": str(response.status_code)}
    http_requests.add(1, attributes)
    http_latency.record((time.perf_counter() - started) * 1000, attributes)
    if (
        response.status_code < 400
        and request.method in {"POST", "PUT", "PATCH", "DELETE"}
        and path.split("/")[3:4]
        and path.split("/")[3]
        in {
            "users",
            "teams",
            "workspaces",
            "organizations",
            "providers",
            "data-sources",
            "settings",
            "operations",
            "invitations",
            "telemetry",
            "calibration",
            "experiments",
            "notification-settings",
            "agents",
            "api-credentials",
        }
    ):
        try:
            await run_sync(
                operations.audit_action, request.cookies.get("agentcity_access"), request.method, path, request_id
            )
        except SQLAlchemyError:
            logger.exception("Could not persist administration event request=%s", request_id)
    logger.info(
        "request=%s method=%s status=%s latency_ms=%d",
        request_id,
        request.method,
        response.status_code,
        (time.perf_counter() - started) * 1000,
    )
    return response


@app.get("/api/v1/health", tags=["System"])
def health():
    try:
        with Session(engine) as session:
            session.execute(text("SELECT 1"))
        return {"status": "ok", "database": engine.dialect.name, "demo": demo_enabled()}
    except SQLAlchemyError:
        return JSONResponse({"status": "degraded", "database": "unavailable"}, status_code=503)


for router in (
    auth_routes.router,
    city_routes.router,
    run_routes.router,
    experiments.router,
    admin_routes.router,
    api_access.router,
    public_routes.router,
    calibration_routes.router,
    telemetry_routes.router,
    invitations.router,
    oidc.router,
    model_routes.router,
    delivery_routes.router,
    operations.router,
):
    app.include_router(router, prefix="/api/v1")
