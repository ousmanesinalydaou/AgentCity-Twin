"""An opt-in OpenID Connect authorization-code integration with PKCE."""

import base64
import hashlib
import os
import secrets
from urllib.parse import urlencode, urlsplit

import httpx
import jwt
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.exc import IntegrityError

from .auth import create_user, digest, person, read_token, set_auth
from .config import enabled, public_origin
from .db import Store, db, now

router = APIRouter(prefix="/auth/oidc", tags=["Authentication"])
ALGORITHMS = {"RS256", "RS384", "RS512", "ES256", "ES384", "ES512", "PS256"}


def configuration():
    keys = ("OIDC_ISSUER", "OIDC_CLIENT_ID", "OIDC_CLIENT_SECRET")
    values = tuple(os.getenv(key, "") for key in keys)
    return values if all(values) else None


def secure_url(value):
    url = urlsplit(value)
    if (
        url.scheme != "https"
        or not url.hostname
        or url.username
        or url.password
        or url.fragment
        or any(char.isspace() for char in value)
    ):
        raise ValueError("The identity provider must use HTTPS.")
    return value


def discovery(http, issuer):
    config = (
        http.get(secure_url(issuer.rstrip("/") + "/.well-known/openid-configuration")).raise_for_status().json()
    )
    if config["issuer"] != issuer:
        raise ValueError("Identity provider issuer mismatch.")
    for key in ("authorization_endpoint", "token_endpoint", "jwks_uri"):
        secure_url(config[key])
    return config


def validate_id_token(token, keys, issuer, client_id, nonce):
    header = jwt.get_unverified_header(token)
    algorithm = header.get("alg")
    if algorithm not in ALGORITHMS or not header.get("kid"):
        raise ValueError("Unexpected identity token signing method.")
    row = next(key for key in keys["keys"] if key.get("kid") == header["kid"] and key.get("use", "sig") == "sig")
    claims = jwt.decode(
        token,
        jwt.PyJWK.from_dict(row, algorithm).key,
        algorithms=[algorithm],
        issuer=issuer,
        audience=client_id,
        options={"require": ["sub", "iss", "aud", "exp", "iat", "nonce"]},
        leeway=10,
    )
    if claims["nonce"] != nonce or (
        isinstance(claims["aud"], list) and len(claims["aud"]) > 1 and claims.get("azp") != client_id
    ):
        raise ValueError("Identity token correlation failed.")
    return claims


def current_id(store, request):
    token = read_token(store, "access", request.cookies.get("agentcity_access"))
    user = person(store, token["user_id"]) if token else None
    return user["id"] if user and not user["demo"] and not user.get("disabled") else None


@router.get("/status")
def status():
    return {"enabled": configuration() is not None}


@router.get("/start")
def start(request: Request, link: bool = False, store: Store = Depends(db)):
    configured = configuration()
    if not configured:
        raise HTTPException(404, "Single sign-on is disabled.")
    issuer, client_id, _ = configured
    linked_user = current_id(store, request) if link else None
    if link and not linked_user:
        raise HTTPException(401, "Sign in before linking an identity provider.")
    state, nonce, verifier = (secrets.token_urlsafe(48) for _ in range(3))
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    try:
        with httpx.Client(timeout=8, follow_redirects=False) as http:
            config = discovery(http, issuer)
    except (httpx.HTTPError, ValueError, KeyError) as exc:
        raise HTTPException(502, "The identity provider could not be discovered.") from exc
    redirect_uri = public_origin() + "/api/v1/auth/oidc/callback"
    store.insert(
        "system",
        "oidc-state",
        digest(state),
        {
            "nonce": nonce,
            "verifier": verifier,
            "expires": now().timestamp() + 600,
            "redirect_uri": redirect_uri,
            "link": linked_user,
        },
    )
    store.session.commit()
    query = urlencode(
        {
            "client_id": client_id,
            "response_type": "code",
            "scope": "openid email profile",
            "redirect_uri": redirect_uri,
            "nonce": nonce,
            "state": state,
            "code_challenge": challenge,
            "code_challenge_method": "S256",
        }
    )
    endpoint = config["authorization_endpoint"]
    response = RedirectResponse(endpoint + ("&" if "?" in endpoint else "?") + query)
    response.set_cookie(
        "agentcity_oidc", state, max_age=600, httponly=True, samesite="lax", secure=enabled("COOKIE_SECURE")
    )
    return response


def resolve_user(store, claims, link):
    subject = digest(claims["iss"] + "\n" + claims["sub"])
    identity = store.get("system", "oidc-identity", subject)
    if identity:
        if link and link != identity["user_id"]:
            raise ValueError("This identity is linked to a different account.")
        return person(store, identity["user_id"])
    email = claims.get("email")
    if (
        claims.get("email_verified") is not True
        or not isinstance(email, str)
        or len(email) > 128
        or "@" not in email
    ):
        raise ValueError("A verified identity email is required.")
    existing = store.get("system", "email", email.strip().lower())
    if link and (not existing or link != existing["id"]):
        raise ValueError("Link using the email on your account.")
    if not link and existing:
        raise ValueError("Sign in with your password and link single sign-on from account settings.")
    if link:
        user = person(store, link)
    elif enabled("ENABLE_REGISTRATION", "true"):
        name = str(claims.get("name", email.split("@")[0]))[:100]
        user = {**create_user(store, email, name, ""), "verified": True}
        store.put("system", "user", user["id"], user)
    else:
        raise ValueError("Account registration is closed.")
    store.insert("system", "oidc-identity", subject, {"user_id": user["id"]})
    return user


@router.get("/callback")
def callback(request: Request, state: str = "", code: str = "", store: Store = Depends(db)):
    config = configuration()
    cookie = request.cookies.get("agentcity_oidc", "")
    if (
        not config
        or not code
        or len(code) > 2048
        or len(state) > 128
        or not cookie.isascii()
        or not state.isascii()
        or not secrets.compare_digest(cookie, state)
    ):
        raise HTTPException(400, "The single sign-on request is invalid or expired.")
    state_id = digest(state)
    transaction = store.get("system", "oidc-state", state_id, lock=True)
    if (
        not transaction
        or transaction["expires"] < now().timestamp()
        or not store.remove("system", "oidc-state", state_id)
    ):
        raise HTTPException(400, "The single sign-on request has expired.")
    store.session.commit()
    if transaction["link"] and transaction["link"] != current_id(store, request):
        raise HTTPException(401, "The linking session has expired.")
    issuer, client_id, secret = config
    try:
        with httpx.Client(timeout=10, follow_redirects=False) as http:
            metadata = discovery(http, issuer)
            methods = metadata.get("token_endpoint_auth_methods_supported", ["client_secret_basic"])
            payload = {
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": transaction["redirect_uri"],
                "code_verifier": transaction["verifier"],
            }
            auth = None
            if "client_secret_basic" in methods:
                auth = (client_id, secret)
            else:
                payload.update(client_id=client_id, client_secret=secret)
            token = (
                http.post(metadata["token_endpoint"], data=payload, auth=auth)
                .raise_for_status()
                .json()["id_token"]
            )
            keys = http.get(metadata["jwks_uri"]).raise_for_status().json()
        claims = validate_id_token(token, keys, issuer, client_id, transaction["nonce"])
    except (ValueError, KeyError, StopIteration, httpx.HTTPError, jwt.PyJWTError) as exc:
        raise HTTPException(401, "Single sign-on verification failed.") from exc
    try:
        user = resolve_user(store, claims, transaction["link"])
        if not user or user.get("disabled"):
            raise ValueError("The account is disabled.")
        response = RedirectResponse("/?view=settings" if transaction["link"] else "/", status_code=303)
        set_auth(response, store, user)
        response.delete_cookie("agentcity_oidc")
        store.session.commit()
        return response
    except (ValueError, IntegrityError) as exc:
        detail = str(exc) if isinstance(exc, ValueError) else "The identity could not be linked."
        raise HTTPException(409, detail) from exc
