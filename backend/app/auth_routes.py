import os

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field

from .auth import (
    HASHER,
    create_demo,
    create_user,
    current_user,
    deliver_email,
    digest,
    logout,
    person,
    public_user,
    read_token,
    remember,
    rotate,
    set_auth,
    signin,
)
from .config import enabled, public_origin
from .db import Store, db
from .domain import Credentials, Preferences

router = APIRouter(prefix="/auth", tags=["Authentication"])


class EmailInput(BaseModel):
    email: str = Field(min_length=3, max_length=254, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class TokenInput(BaseModel):
    token: str = Field(min_length=20, max_length=80)


class ResetInput(TokenInput):
    password: str = Field(min_length=10, max_length=128)


def mail_token(store, background, purpose, user):
    if os.getenv("SMTP_HOST"):
        token = remember(store, purpose, user["id"], 3600)
        label = "Verify your email" if purpose == "verify" else "Reset your password"
        background.add_task(
            deliver_email,
            user["email"],
            f"AgentCity Twin · {label}",
            f"{label} at {public_origin()}/account?mode={purpose}&token={token}",
        )


def require_verification_mail():
    if enabled("REQUIRE_EMAIL_VERIFICATION") and not os.getenv("SMTP_HOST"):
        raise HTTPException(503, "Email verification requires an active mail service.")


@router.post("/register", status_code=201)
def register(form: Credentials, response: Response, background: BackgroundTasks, store: Store = Depends(db)):
    if not enabled("ENABLE_REGISTRATION", "true"):
        raise HTTPException(403, "Account registration is closed.")
    require_verification_mail()
    user = create_user(store, form.email, form.name or form.email.split("@")[0], form.password)
    mail_token(store, background, "verify", user)
    if not enabled("REQUIRE_EMAIL_VERIFICATION"):
        set_auth(response, store, user)
    store.session.commit()
    return public_user(user)


@router.post("/login")
def login(form: Credentials, response: Response, store: Store = Depends(db)):
    user = signin(store, form.email, form.password)
    set_auth(response, store, user)
    store.session.commit()
    return public_user(user)


@router.post("/demo")
def demo(response: Response, store: Store = Depends(db)):
    user = create_demo(store)
    set_auth(response, store, user)
    store.session.commit()
    return public_user(user)


@router.post("/bootstrap")
def bootstrap(request: Request, response: Response, store: Store = Depends(db)):
    token = read_token(store, "access", request.cookies.get("agentcity_access"))
    user = person(store, token["user_id"]) if token else None
    if user and not user.get("disabled"):
        return public_user(user)
    if request.cookies.get("agentcity_refresh"):
        try:
            return rotate(store, request, response)
        except HTTPException as exc:
            if exc.status_code != 401:
                raise
    return demo(response, store)


@router.post("/refresh")
def refresh(request: Request, response: Response, store: Store = Depends(db)):
    return rotate(store, request, response)


@router.post("/logout")
def sign_out(request: Request, response: Response, store: Store = Depends(db)):
    logout(store, request, response)
    return {"ok": True}


@router.get("/me")
def me(user=Depends(current_user)):
    return public_user(user)


class Profile(BaseModel):
    name: str = Field(min_length=2, max_length=100)


@router.patch("/profile")
def update_profile(form: Profile, store: Store = Depends(db), user=Depends(current_user)):
    name = form.name.strip()
    if len(name) < 2:
        raise HTTPException(422, "Enter a name with at least two characters.")
    user = {**user, "name": name}
    store.put("system", "user", user["id"], user)
    store.session.commit()
    return public_user(user)


@router.patch("/preferences")
def preferences(form: Preferences, store: Store = Depends(db), user=Depends(current_user)):
    user = {**user, "preferences": form.model_dump()}
    store.put("system", "user", user["id"], user)
    store.session.commit()
    return public_user(user)


@router.post("/forgot")
def forgot(form: EmailInput, background: BackgroundTasks, store: Store = Depends(db)):
    entry = store.get("system", "email", form.email.lower().strip())
    user = person(store, entry["id"]) if entry else None
    if user and not user["demo"] and not user.get("disabled"):
        mail_token(store, background, "reset", user)
        store.session.commit()
    return {"ok": True}


@router.post("/resend-verification")
def resend_verification(form: EmailInput, background: BackgroundTasks, store: Store = Depends(db)):
    entry = store.get("system", "email", form.email.lower().strip())
    user = person(store, entry["id"]) if entry else None
    if user and not (user["demo"] or user["verified"] or user.get("disabled")):
        mail_token(store, background, "verify", user)
        store.session.commit()
    return {"ok": True}


def redeem(store, token, purpose):
    record = read_token(store, purpose, token, lock=True)
    if not record or not store.remove("system", purpose, digest(token)):
        raise HTTPException(400, "This link is invalid or expired.")
    return person(store, record["user_id"])


@router.post("/reset")
def reset(form: ResetInput, store: Store = Depends(db)):
    from sqlalchemy import delete

    from .db import Record

    user = {**redeem(store, form.token, "reset"), "password": HASHER.hash(form.password)}
    store.put("system", "user", user["id"], user)
    store.session.execute(
        delete(Record).where(
            Record.scope == "system",
            Record.kind.in_(("access", "refresh", "reset")),
            Record.payload["user_id"].as_string() == user["id"],
        )
    )
    store.session.commit()
    return {"ok": True}


@router.post("/verify")
def verify(form: TokenInput, store: Store = Depends(db)):
    user = {**redeem(store, form.token, "verify"), "verified": True}
    store.put("system", "user", user["id"], user)
    store.session.commit()
    return {"ok": True}
