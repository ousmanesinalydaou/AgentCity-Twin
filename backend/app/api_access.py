"""Expiring organization credentials for explicitly permitted API reads."""

import re
import secrets
from datetime import timedelta
from hmac import compare_digest
from typing import Literal
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field

from .auth import ADMIN, digest, person, require_admin
from .db import Store, db, now
from .quotas import limited

router = APIRouter(prefix="/api-credentials", tags=["API credentials"])
TokenScope = Literal["city:read", "research:read", "reports:read"]
URL_SAFE = r"[A-Za-z0-9_-]+"
TOKEN = re.compile(r"act_([a-f0-9]{32})\.([a-f0-9]{32})\.[A-Za-z0-9_-]{43}")
READS = {
    "city:read": re.compile(
        rf"/api/v1/(cities(?:/{URL_SAFE}(?:/layers)?)?|sensors|incidents|mobility|telemetry/vehicles)"
    ),
    "research:read": re.compile(rf"/api/v1/(experiments(?:/{URL_SAFE}(?:/export)?)?|scenarios)"),
    "reports:read": re.compile(
        rf"/api/v1/(simulations(?:/{URL_SAFE}(?:/results|/execution)?)?|reports(?:/{URL_SAFE}(?:/document)?)?)"
    ),
}


class AccessInput(BaseModel):
    name: str = Field(min_length=3, max_length=80)
    scopes: list[TokenScope] = Field(min_length=1, max_length=3)
    days: int = Field(default=30, ge=1, le=90)


def public(row):
    return {key: value for key, value in row.items() if key != "digest"}


def authenticate(store, request: Request):
    scheme, _, raw = request.headers["authorization"].partition(" ")
    match = TOKEN.fullmatch(raw) if scheme.lower() == "bearer" else None
    if not match:
        raise HTTPException(
            401, "The API credential is invalid or expired.", headers={"WWW-Authenticate": "Bearer"}
        )
    scope, key = match.groups()
    row = store.get(scope, "api-key", key)
    if not row or row["expires_at"] <= now().isoformat() or not compare_digest(row["digest"], digest(raw)):
        raise HTTPException(
            401, "The API credential is invalid or expired.", headers={"WWW-Authenticate": "Bearer"}
        )
    user = person(store, row["created_by"])
    if not user or user.get("disabled") or user["scope"] != scope or user["role"] not in ADMIN:
        raise HTTPException(
            401, "The API credential is invalid or expired.", headers={"WWW-Authenticate": "Bearer"}
        )
    if request.method != "GET" or not any(READS[item].fullmatch(request.url.path) for item in row["scopes"]):
        raise HTTPException(403, "This API credential cannot access the requested operation.")
    if limited(f"api-key:{key}", "read", 120):
        raise HTTPException(429, "Too many requests. Retry in a minute.", headers={"Retry-After": "60"})
    return {**user, "role": "Viewer"}


@router.get("")
def credentials(store: Store = Depends(db), user=Depends(require_admin)):
    return [public(row) for row in store.list(user["scope"], "api-key")]


@router.post("", status_code=201)
def issue(form: AccessInput, store: Store = Depends(db), user=Depends(require_admin)):
    scope = user["scope"]
    key = uuid4().hex
    token = f"act_{scope}.{key}.{secrets.token_urlsafe(32)}"
    stamp = now()
    row = {
        "id": key,
        "name": form.name.strip(),
        "scopes": sorted(set(form.scopes)),
        "created_at": stamp.isoformat(),
        "created_by": user["id"],
        "expires_at": (stamp + timedelta(days=form.days)).isoformat(),
        "digest": digest(token),
    }
    if len(row["name"]) < 3:
        raise HTTPException(422, "Enter a name with at least three characters.")
    store.insert(scope, "api-key", key, row)
    store.session.commit()
    return {**public(row), "token": token}


@router.delete("/{key_id}", status_code=204)
def revoke(key_id: str, store: Store = Depends(db), user=Depends(require_admin)):
    if not store.remove(user["scope"], "api-key", key_id):
        raise HTTPException(404, "API credential not found.")
    store.session.commit()
    return Response(status_code=204)
