import os
from typing import Literal
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from .ai.gateway import ProviderError, cipher
from .auth import current_user, require_admin
from .db import Store, db, now
from .delivery import EVENTS
from .outbound import resolve

router = APIRouter(prefix="/notification-settings", tags=["Notifications"])


class Channel(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    kind: Literal["email", "webhook", "slack", "teams", "sms", "push"]
    destination: str = Field(default="", max_length=1000)
    events: list[str] = Field(min_length=1, max_length=12)
    enabled: bool = True


def public(row):
    return {key: val for key, val in row.items() if key not in {"credential"}}


@router.get("/channels")
def channels(store: Store = Depends(db), user=Depends(require_admin)):
    return {
        "channels": [public(entry) for entry in store.list(user["scope"], "delivery-channel")],
        "events": sorted(EVENTS),
        "history": [
            {
                "id": row["id"],
                "channel_id": row["channel_id"],
                "state": row["state"],
                "attempts": row["attempts"],
                "type": row["event"]["type"],
            }
            for row in store.list(user["scope"], "delivery", 25)
        ],
    }


@router.post("/channels", status_code=201)
def add_channel(form: Channel, store: Store = Depends(db), user=Depends(require_admin)):
    if set(form.events) - EVENTS:
        raise HTTPException(422, "Select supported notification events.")
    try:
        if form.kind == "email":
            if (
                not os.getenv("SMTP_HOST")
                or "@" not in form.destination
                or any(c in form.destination for c in "\r\n")
            ):
                raise ValueError("Configure SMTP and enter an email address.")
            credential = ""
        else:
            resolve(form.destination, "NOTIFICATION_ORIGINS", {"https", "http"})
            credential = cipher().encrypt(form.destination.encode()).decode()
    except (ValueError, ProviderError) as exc:
        raise HTTPException(422, str(exc)) from exc
    key = uuid4().hex
    value = {
        **form.model_dump(),
        "id": key,
        "destination": form.destination if form.kind == "email" else "",
        "credential": credential,
    }
    store.insert(user["scope"], "delivery-channel", key, value)
    store.session.commit()
    return public(value)


@router.delete("/channels/{channel_id}")
def disable(channel_id: str, store: Store = Depends(db), user=Depends(require_admin)):
    entry = store.get(user["scope"], "delivery-channel", channel_id, lock=True)
    if not entry:
        raise HTTPException(404, "Notification channel not found.")
    store.put(user["scope"], "delivery-channel", channel_id, {**entry, "enabled": False})
    store.session.commit()
    return {"status": "disabled"}


@router.post("/read")
def mark_read(store: Store = Depends(db), user=Depends(current_user)):
    store.put(user["scope"], "notice-read", user["id"], {"read_at": now().isoformat()})
    store.session.commit()
    return {"ok": True}
