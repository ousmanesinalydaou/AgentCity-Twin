"""Tenant feature settings, administration history, and shared worker status."""

from datetime import timedelta
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .auth import current_user, person, read_token, require_admin
from .db import Record, RunJob, Store, db, engine, now

router = APIRouter(prefix="/operations", tags=["Operations"])
DEFAULT_FEATURES = {"research": True, "telemetry": True, "modelLab": True, "notifications": True}


class Features(BaseModel):
    research: bool = True
    telemetry: bool = True
    modelLab: bool = True
    notifications: bool = True


def settings(store, scope):
    return {**DEFAULT_FEATURES, **(store.get(scope, "settings", "features") or {})}


def require_feature(store, scope, key):
    if not settings(store, scope)[key]:
        raise HTTPException(403, "This feature is disabled for the organization.")


def audit_action(token, method, path, request_id):
    with Session(engine) as session, session.begin():
        store = Store(session)
        access = read_token(store, "access", token)
        user = person(store, access["user_id"]) if access else None
        if not user or user["demo"]:
            return
        key = uuid4().hex
        store.insert(
            user["scope"],
            "admin-audit",
            key,
            {
                "id": key,
                "actor": user["name"],
                "action": method,
                "resource": path,
                "time": now().isoformat(),
                "request_id": request_id,
            },
        )


@router.get("/features")
def features(store: Store = Depends(db), user=Depends(current_user)):
    return settings(store, user["scope"])


@router.put("/features")
def set_features(form: Features, store: Store = Depends(db), user=Depends(require_admin)):
    payload = form.model_dump()
    store.put(user["scope"], "settings", "features", payload)
    store.session.commit()
    return payload


@router.get("/admin")
def admin_status(store: Store = Depends(db), user=Depends(require_admin)):
    scope = user["scope"]
    heartbeat = store.session.scalar(
        select(func.count())
        .select_from(Record)
        .where(
            Record.scope == "system",
            Record.kind == "worker",
            Record.updated_at > now() - timedelta(seconds=45),
        )
    )
    jobs = store.session.scalar(select(func.count()).select_from(RunJob).where(RunJob.scope == scope))
    return {"workers": heartbeat, "active_jobs": jobs, "events": store.list(scope, "admin-audit", 100)}
