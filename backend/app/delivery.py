"""Persist explicit tenant delivery channels and process a retrying outbox."""

import logging
import os
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from .ai.gateway import cipher
from .auth import deliver_email
from .db import Record, Store, engine, now
from .outbound import request_bytes

logger = logging.getLogger("agentcity.delivery")
EVENTS = {
    "agent.completed",
    "agent.failed",
    "simulation.completed",
    "simulation.failed",
    "recommendation.available",
    "risk.severe",
    "provider.unavailable",
    "sensor.offline",
    "feed.unavailable",
}


def publish(store, scope, *, event, city_id, title, key=None):
    identifier = key or uuid4().hex
    if store.get(scope, "notice", identifier):
        return
    data = {"id": identifier, "type": event, "text": title, "time": now().isoformat(), "city_id": city_id}
    store.insert(scope, "notice", identifier, data)
    for channel in store.list(scope, "delivery-channel"):
        if channel["enabled"] and event in channel["events"]:
            outbox_id = uuid4().hex
            store.insert(
                scope,
                "delivery",
                outbox_id,
                {
                    "id": outbox_id,
                    "channel_id": channel["id"],
                    "event": data,
                    "state": "queued",
                    "attempts": 0,
                    "available": 0.0,
                },
            )


def dispatch(channel, event):
    # External channels receive event metadata without scenario descriptions or sensor coordinates.
    message = f"AgentCity Twin · {event['type']} · {event['city_id']}"
    if channel["kind"] == "email":
        if not os.getenv("SMTP_HOST"):
            raise ValueError("SMTP is unavailable.")
        deliver_email(channel["destination"], "AgentCity Twin notification", message)
        return
    destination = cipher().decrypt(channel["credential"].encode()).decode()
    if channel["kind"] == "slack":
        payload = {"text": message}
    elif channel["kind"] == "teams":
        payload = {
            "type": "message",
            "attachments": [
                {
                    "contentType": "application/vnd.microsoft.card.adaptive",
                    "content": {
                        "type": "AdaptiveCard",
                        "$schema": "https://adaptivecards.io/schemas/adaptive-card.json",
                        "version": "1.4",
                        "body": [{"type": "TextBlock", "text": message}],
                    },
                }
            ],
        }
    else:
        payload = {
            "type": event["type"],
            "id": event["id"],
            "city_id": event["city_id"],
            "time": event["time"],
            "channel": channel["kind"],
            "message": message,
        }
    request_bytes("POST", destination, "NOTIFICATION_ORIGINS", body=payload, limit=50_000)


def process_delivery():
    sent_at = now().timestamp()
    with Session(engine) as session, session.begin():
        job = session.scalar(
            select(Record)
            .where(
                Record.kind == "delivery",
                Record.payload["state"].as_string() == "queued",
                Record.payload["available"].as_float() <= sent_at,
            )
            .order_by(Record.updated_at)
            .limit(1)
            .with_for_update(skip_locked=True)
        )
        if not job:
            return
        if job.payload["attempts"] >= 3:
            job.payload = {**job.payload, "state": "failed"}
            return
        scope, key = job.scope, job.key
        data = {**job.payload, "available": sent_at + 30, "attempts": job.payload["attempts"] + 1}
        job.payload = data
        channel = Store(session).get(scope, "delivery-channel", data["channel_id"])
    state = "cancelled"
    if channel and channel["enabled"]:
        try:
            dispatch(channel, data["event"])
            state = "sent"
        except Exception as error:
            logger.warning("Notification delivery failed job=%s error=%s", key, type(error).__name__)
            state = "queued" if data["attempts"] < 3 else "failed"
    with Session(engine) as session, session.begin():
        store = Store(session)
        current = store.get(scope, "delivery", key, lock=True)
        if current and current["attempts"] == data["attempts"]:
            store.put(
                scope, "delivery", key, {**data, "state": state, "available": sent_at + 10 * 2 ** data["attempts"]}
            )
