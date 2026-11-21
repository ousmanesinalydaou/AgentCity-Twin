import base64
import json
import threading
import time
from datetime import UTC, datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit
from uuid import uuid4

import jwt
import pytest
from app.oidc import validate_id_token
from app.telemetry import decode
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient
from google.transit import gtfs_realtime_pb2
from jwt.algorithms import RSAAlgorithm


def admin(client):
    client.cookies.clear()
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": uuid4().hex + "@example.test",
            "name": "Extension QA",
            "password": "extensions-password-test",
        },
    )
    assert response.status_code == 201
    return response.json()


def test_oidc_checks_nonce_issuer_and_signature():
    private = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public = json.loads(RSAAlgorithm.to_jwk(private.public_key()))
    stamp = int(time.time())
    claims = {
        "iss": "https://issuer.example",
        "aud": "agentcity",
        "sub": "tester",
        "nonce": "test",
        "iat": stamp,
        "exp": stamp + 120,
        "email_verified": True,
        "email": "tester@example.test",
    }
    jwt_value = jwt.encode(claims, private, algorithm="RS256", headers={"kid": "testing"})
    keys = {"keys": [{**public, "kid": "testing", "use": "sig"}]}
    assert validate_id_token(jwt_value, keys, claims["iss"], claims["aud"], "test")["sub"] == "tester"
    with pytest.raises(ValueError):
        validate_id_token(jwt_value, keys, claims["iss"], claims["aud"], "another-nonce")
    with pytest.raises(jwt.InvalidAudienceError):
        validate_id_token(jwt_value, keys, claims["iss"], "wrong-client", "test")


def test_admin_invitation_is_scoped_single_use(client):
    owner = admin(client)
    invited = client.post(
        "/api/v1/invitations", json={"email": uuid4().hex + "@example.test", "role": "Researcher"}
    )
    assert invited.status_code == 201
    token = parse_qs(urlsplit(invited.json()["accept_url"]).query)["token"][0]
    with TestClient(client.app) as visitor:
        form = {"token": token, "name": "Research invitee", "password": "a-valid-test-passphrase"}
        assert visitor.post("/api/v1/auth/invite", json=form).status_code == 200
        member = visitor.get("/api/v1/auth/me").json()
        assert member["role"] == "Researcher" and member["scope"] == owner["scope"]
        assert visitor.post("/api/v1/auth/invite", json=form).status_code == 400
        assert visitor.get("/api/v1/invitations").status_code == 403
    assert client.get("/api/v1/invitations").json()[0]["status"] == "accepted"
    audit = client.get("/api/v1/operations/admin").json()
    assert any(row["resource"] == "/api/v1/invitations" for row in audit["events"])


def test_real_rest_telemetry_and_transit_parser(client, monkeypatch):
    class Feed(BaseHTTPRequestHandler):
        def do_GET(self):
            data = json.dumps(
                {
                    "readings": [
                        {
                            "sensor_id": "TR-02",
                            "value": 560,
                            "observed_at": datetime.now(UTC).isoformat(),
                            "type": "Traffic",
                            "unit": "veh/hr",
                        }
                    ]
                }
            ).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def log_message(self, *_args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Feed)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        admin(client)
        origin = f"http://127.0.0.1:{server.server_port}"
        monkeypatch.setenv("TELEMETRY_ORIGINS", origin)
        result = client.post(
            "/api/v1/telemetry/feeds",
            json={
                "name": "Test corridor",
                "city_id": "debrecen",
                "kind": "rest",
                "url": origin + "/live",
                "interval": 10,
            },
        )
        assert result.status_code == 201, result.text
        for _ in range(15):
            data = client.get("/api/v1/sensors").json()
            traffic = next(row for row in data if row["id"] == "TR-02")
            if traffic["source"] == "Test corridor":
                break
            time.sleep(0.3)
        assert traffic["reading"] == 560 and traffic["online"]
        response = client.get("/api/v1/telemetry/coverage?count=3").json()
        assert 1 <= len(response["candidates"]) <= 3
    finally:
        server.shutdown()
        server.server_close()
        thread.join(2)

    feed = gtfs_realtime_pb2.FeedMessage()
    feed.header.gtfs_realtime_version = "2.0"
    bus = feed.entity.add(id="bus")
    bus.vehicle.trip.trip_id = "trip-5"
    bus.vehicle.position.latitude = 47.53
    bus.vehicle.position.longitude = 21.62
    item = feed.entity.add(id="delay")
    item.trip_update.trip.trip_id = "trip-5"
    item.trip_update.delay = 240
    _, results = decode("gtfs-realtime", feed.SerializeToString())
    assert len(results) == 1 and results[0]["delay"] == 240


def test_calibration_intervals_and_versioned_report(client):
    admin(client)
    profile = client.put(
        "/api/v1/calibration/debrecen",
        json={
            "source": "Test observations",
            "observations": [
                {"metric": "transitDelay", "modeled": index + 1, "observed": 2 + index * 1.15}
                for index in range(14)
            ],
        },
    )
    assert profile.status_code == 200 and profile.json()["metrics"]["transitDelay"]["validation_samples"] > 0
    run = client.post(
        "/api/v1/agentcity/analyze", json={"prompt": "Road closure near the university at 17:00."}
    ).json()
    received = client.get(f"/api/v1/simulations/{run['id']}/events")
    assert "event: done" in received.text
    report = client.get(f"/api/v1/reports/{run['id']}").json()
    result = report["result"]
    assert result["calibration"]["source"] == "Test observations"
    interval = result["recommendation"]["timeline"][2]["intervals"]["transitDelay"]
    assert interval[0] <= interval[1]
    document = client.get(f"/api/v1/reports/{run['id']}/document?template=research&minute=30")
    assert document.status_code == 200 and "<svg" in document.text and "research-1.0" in document.text


def test_model_lab_local_fallbacks_and_validation(client):
    client.cookies.clear()
    assert client.post("/api/v1/auth/demo").is_success
    form = {"prompt": "Traffic snapshot", "operation": "embeddings"}
    vector = client.post("/api/v1/model-lab/tasks", json=form).json()
    assert vector["execution"] == "Local demo" and len(vector["vector"]) == 128
    tools = client.post("/api/v1/model-lab/tasks", json={**form, "operation": "tools"}).json()
    assert tools["tools"] == ["city_snapshot"]
    assert "data:" in client.post("/api/v1/model-lab/tasks", json={**form, "operation": "streaming"}).text
    assert (
        client.post(
            "/api/v1/model-lab/tasks",
            json={
                **form,
                "operation": "vision",
                "image": "data:image/png;base64," + base64.b64encode(b"not an image").decode(),
            },
        ).status_code
        == 422
    )


def test_oidc_authorization_callback_and_local_session(client, monkeypatch):
    issuer = "https://identity.example"
    client_id = "agentcity-qa"
    monkeypatch.setenv("OIDC_ISSUER", issuer)
    monkeypatch.setenv("OIDC_CLIENT_ID", client_id)
    monkeypatch.setenv("OIDC_CLIENT_SECRET", "unit-test-secret")
    private = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    key = {**json.loads(RSAAlgorithm.to_jwk(private.public_key())), "kid": "test-key", "use": "sig"}
    expected = {}

    class Reply:
        def __init__(self, item):
            self.item = item

        def raise_for_status(self):
            return self

        def json(self):
            return self.item

    class IdentityProvider:
        def __init__(self, **_kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            pass

        def get(self, url):
            if url.endswith("openid-configuration"):
                return Reply(
                    {
                        "issuer": issuer,
                        "authorization_endpoint": issuer + "/authorize",
                        "token_endpoint": issuer + "/token",
                        "jwks_uri": issuer + "/keys",
                    }
                )
            assert url == issuer + "/keys"
            return Reply({"keys": [key]})

        def post(self, url, data, auth):
            assert url == issuer + "/token" and auth[0] == client_id
            import hashlib

            verified = base64.urlsafe_b64encode(hashlib.sha256(data["code_verifier"].encode()).digest())
            assert verified.rstrip(b"=").decode() == expected["code_challenge"]
            stamp = int(time.time())
            token = jwt.encode(
                {
                    "iss": issuer,
                    "aud": client_id,
                    "sub": "new-user",
                    "nonce": expected["nonce"],
                    "iat": stamp,
                    "exp": stamp + 120,
                    "email_verified": True,
                    "email": "oidc-" + uuid4().hex + "@example.test",
                    "name": "OIDC QA",
                },
                private,
                algorithm="RS256",
                headers={"kid": "test-key"},
            )
            return Reply({"id_token": token})

    monkeypatch.setattr("app.oidc.httpx.Client", IdentityProvider)
    with TestClient(client.app) as visitor:
        start = visitor.get("/api/v1/auth/oidc/start", follow_redirects=False)
        assert start.status_code == 307
        expected.update(
            {key: values[0] for key, values in parse_qs(urlsplit(start.headers["location"]).query).items()}
        )
        assert expected["code_challenge_method"] == "S256"
        callback = visitor.get(
            "/api/v1/auth/oidc/callback",
            params={"state": expected["state"], "code": "identity-code"},
            follow_redirects=False,
        )
        assert callback.status_code == 303, callback.text
        assert visitor.get("/api/v1/auth/me").json()["verified"] is True
        replay = visitor.get(
            "/api/v1/auth/oidc/callback",
            params={"state": expected["state"], "code": "identity-code"},
            follow_redirects=False,
        )
        assert replay.status_code == 400


def test_notification_outbox_delivers_private_metadata_only(client, monkeypatch):
    from app.db import Store, engine
    from app.delivery import publish
    from cryptography.fernet import Fernet
    from sqlalchemy.orm import Session

    received = []

    class Delivery(BaseHTTPRequestHandler):
        def do_POST(self):
            received.append(json.loads(self.rfile.read(int(self.headers["Content-Length"]))))
            self.send_response(204)
            self.end_headers()

        def log_message(self, *_args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Delivery)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        user = admin(client)
        origin = f"http://127.0.0.1:{server.server_port}"
        monkeypatch.setenv("NOTIFICATION_ORIGINS", origin)
        monkeypatch.setenv("PROVIDER_ENCRYPTION_KEY", Fernet.generate_key().decode())
        config = client.post(
            "/api/v1/notification-settings/channels",
            json={
                "name": "Test webhook",
                "kind": "webhook",
                "destination": origin + "/delivery",
                "events": ["simulation.completed"],
            },
        )
        assert config.status_code == 201 and "credential" not in config.json()
        with Session(engine) as session, session.begin():
            publish(
                Store(session),
                user["scope"],
                event="simulation.completed",
                city_id="debrecen",
                title="Private scenario title",
            )
        for _ in range(20):
            if received:
                break
            time.sleep(0.25)
        assert received[0]["type"] == "simulation.completed"
        assert "Private scenario title" not in json.dumps(received)
    finally:
        server.shutdown()
        server.server_close()
        thread.join(2)
