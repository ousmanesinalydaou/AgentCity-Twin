"""Single-use, role-scoped organization invitations."""

import os
import secrets
from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Response
from pydantic import BaseModel, Field

from .auth import create_user, deliver_email, digest, require_admin, set_auth
from .auth_routes import mail_token, require_verification_mail
from .config import enabled, public_origin
from .db import Store, db, now
from .domain import Role

router = APIRouter(tags=["Membership"])


class InviteForm(BaseModel):
    email: str = Field(pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$", max_length=128)
    role: Role = "Viewer"
    send_email: bool = False


class AcceptForm(BaseModel):
    token: str = Field(min_length=32, max_length=100)
    name: str = Field(min_length=2, max_length=100)
    password: str = Field(min_length=10, max_length=128)


@router.get("/invitations")
def invitations(store: Store = Depends(db), user=Depends(require_admin)):
    stamp = now().timestamp()
    return [
        {**row, "status": "Expired" if row["status"] == "pending" and row["expires"] < stamp else row["status"]}
        for row in store.list(user["scope"], "invite")
    ]


@router.post("/invitations", status_code=201)
def invite(form: InviteForm, background: BackgroundTasks, store: Store = Depends(db), user=Depends(require_admin)):
    if form.role == "Super Admin":
        raise HTTPException(422, "Choose an organization role.")
    if form.send_email and not os.getenv("SMTP_HOST"):
        raise HTTPException(422, "Configure SMTP before sending the invitation by email.")
    scope, token, key = user["scope"], secrets.token_urlsafe(40), uuid4().hex
    email = form.email.lower()
    if store.get("system", "email", email):
        raise HTTPException(409, "This email already belongs to an account.")
    row = {
        "id": key,
        "email": email,
        "role": form.role,
        "status": "pending",
        "created_at": now().isoformat(),
        "expires": now().timestamp() + 7 * 86400,
    }
    store.insert(scope, "invite", key, row)
    store.insert("system", "invite-token", digest(token), {"scope": scope, "id": key, "expires": row["expires"]})
    store.session.commit()
    url = f"{public_origin()}/account?mode=invite&token={token}"
    if form.send_email:
        background.add_task(
            deliver_email, email, "AgentCity Twin workspace invitation", f"Accept your invitation at {url}"
        )
    return {**row, "accept_url": url}


@router.delete("/invitations/{invite_id}")
def revoke(invite_id: str, store: Store = Depends(db), user=Depends(require_admin)):
    scope = user["scope"]
    row = store.get(scope, "invite", invite_id, lock=True)
    if not row or row["status"] != "pending":
        raise HTTPException(404, "Pending invitation not found.")
    store.put(scope, "invite", invite_id, {**row, "status": "revoked"})
    store.session.commit()
    return {"status": "revoked"}


@router.post("/auth/invite")
def accept(form: AcceptForm, response: Response, background: BackgroundTasks, store: Store = Depends(db)):
    token = store.get("system", "invite-token", digest(form.token), lock=True)
    if not token or token["expires"] < now().timestamp():
        raise HTTPException(400, "This invitation has expired.")
    scope, key = token["scope"], token["id"]
    entry = store.get(scope, "invite", key, lock=True)
    if not entry or entry["status"] != "pending":
        raise HTTPException(400, "This invitation is no longer available.")
    verification = enabled("REQUIRE_EMAIL_VERIFICATION")
    require_verification_mail()
    user = create_user(store, entry["email"], form.name, form.password, scope=scope, role=entry["role"])
    store.put(scope, "invite", key, {**entry, "status": "accepted", "accepted_at": now().isoformat()})
    store.remove("system", "invite-token", digest(form.token))
    if verification:
        mail_token(store, background, "verify", user)
    else:
        set_auth(response, store, user)
    store.session.commit()
    return {"success": True, "requires_verification": verification}
