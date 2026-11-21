import hashlib
import os
import secrets
import smtplib
from email.message import EmailMessage
from uuid import uuid4

from fastapi import Cookie, Depends, HTTPException, Request, Response
from pwdlib import PasswordHash
from sqlalchemy.exc import IntegrityError

from .config import demo_enabled, enabled
from .db import Store, db, now
from .domain import Preferences

ADMIN = {"Super Admin", "Organization Admin"}
RUNNERS = ADMIN | {"City Operator", "Analyst", "Researcher", "Developer"}
ACCESS_SECONDS = 30 * 60
REFRESH_SECONDS = 7 * 24 * 3600
HASHER = PasswordHash.recommended()
DUMMY_HASH = HASHER.hash(secrets.token_hex(16))


def digest(token: str):
    return hashlib.sha256(token.encode()).hexdigest()


def remember(store, purpose, user_id, seconds):
    token = secrets.token_urlsafe(32)
    store.insert("system", purpose, digest(token), {"user_id": user_id, "expires": now().timestamp() + seconds})
    return token


def read_token(store, purpose, token, lock=False):
    if not token:
        return None
    value = store.get("system", purpose, digest(token), lock)
    return value if value and value["expires"] > now().timestamp() else None


def person(store, user_id):
    return store.get("system", "user", user_id)


def public_user(user):
    return {key: val for key, val in user.items() if key != "password"}


def set_auth(response: Response, store, user):
    access_token = remember(store, "access", user["id"], ACCESS_SECONDS)
    refresh_token = remember(store, "refresh", user["id"], REFRESH_SECONDS)
    options = {"httponly": True, "secure": enabled("COOKIE_SECURE"), "samesite": "lax"}
    response.set_cookie("agentcity_access", access_token, max_age=ACCESS_SECONDS, **options)
    response.set_cookie("agentcity_refresh", refresh_token, max_age=REFRESH_SECONDS, **options)


def current_user(request: Request, store: Store = Depends(db), agentcity_access: str | None = Cookie(default=None)):
    if "authorization" in request.headers:
        from .api_access import authenticate

        return authenticate(store, request)
    token = read_token(store, "access", agentcity_access)
    user = person(store, token["user_id"]) if token else None
    if not user or user.get("disabled"):
        raise HTTPException(401, "Sign in to access the workspace.")
    return user


def require_admin(user=Depends(current_user)):
    if user["role"] not in ADMIN or user["demo"]:
        raise HTTPException(403, "An organization administrator is required.")
    return user


def require_runner(user=Depends(current_user)):
    if user["role"] not in RUNNERS:
        raise HTTPException(403, "This role cannot create simulations.")
    return user


def create_user(store, email, name, password, *, scope=None, role="Organization Admin", demo=False):
    email = email.strip().lower()
    user = {
        "id": uuid4().hex,
        "scope": scope or uuid4().hex,
        "email": email,
        "name": name.strip(),
        "role": role,
        "verified": demo,
        "demo": demo,
        "preferences": Preferences().model_dump(),
        "password": HASHER.hash(password) if password else DUMMY_HASH,
    }
    store.insert("system", "email", email, {"id": user["id"]})
    store.insert("system", "user", user["id"], user)
    store.insert(user["scope"], "member", user["id"], {"id": user["id"]})
    if scope is None:
        store.insert(user["scope"], "organization", "profile", {"name": f"{user['name'] or 'New'} organization"})
        store.insert(user["scope"], "workspace", "city-lab", {"id": "city-lab", "name": "City Operations"})
    try:
        store.session.flush()
    except IntegrityError as exc:
        raise HTTPException(409, "This email address is already registered.") from exc
    return user


def signin(store, email, password):
    key = store.get("system", "email", email.strip().lower())
    user = person(store, key["id"]) if key else None
    valid = HASHER.verify(password, user["password"] if user else DUMMY_HASH)
    if not valid or not user or user.get("disabled") or user["demo"]:
        raise HTTPException(401, "Email or password is incorrect.")
    if enabled("REQUIRE_EMAIL_VERIFICATION") and not user["verified"]:
        raise HTTPException(403, "Verify your email address before signing in.")
    return user


def create_demo(store):
    if not demo_enabled():
        raise HTTPException(404, "The demo is disabled.")
    return create_user(store, f"{uuid4().hex}@demo.invalid", "Demo Operator", "", role="City Operator", demo=True)


def rotate(store, request: Request, response: Response):
    old = request.cookies.get("agentcity_refresh")
    record = read_token(store, "refresh", old, lock=True)
    user = person(store, record["user_id"]) if record else None
    if not user or user.get("disabled") or not store.remove("system", "refresh", digest(old)):
        raise HTTPException(401, "The session expired.")
    access = request.cookies.get("agentcity_access")
    if access:
        store.remove("system", "access", digest(access))
    set_auth(response, store, user)
    store.session.commit()
    return public_user(user)


def logout(store, request, response):
    for key in ("access", "refresh"):
        name = f"agentcity_{key}"
        token = request.cookies.get(name)
        if token:
            store.remove("system", key, digest(token))
        response.delete_cookie(name)
    store.session.commit()


def deliver_email(destination, subject, body):
    host = os.getenv("SMTP_HOST")
    if not host:
        return
    message = EmailMessage()
    message["From"] = os.getenv("SMTP_FROM", "agentcity@localhost")
    message["To"] = destination
    message["Subject"] = subject
    message.set_content(body)
    with smtplib.SMTP(host, int(os.getenv("SMTP_PORT", "587")), timeout=10) as mail:
        if enabled("SMTP_STARTTLS", "true"):
            mail.starttls()
        if os.getenv("SMTP_USERNAME"):
            mail.login(os.getenv("SMTP_USERNAME"), os.environ["SMTP_PASSWORD"])
        mail.send_message(message)
