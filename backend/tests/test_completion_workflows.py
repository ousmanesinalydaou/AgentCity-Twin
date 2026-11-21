import base64
from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient


def register(client):
    client.cookies.clear()
    response = client.post(
        "/api/v1/auth/register",
        json={
            "name": "Workflow Admin",
            "email": f"{uuid4().hex}@example.test",
            "password": "experiment-test-password",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_experiment_variants_archive_comparison_and_export(client):
    register(client)
    response = client.post(
        "/api/v1/experiments",
        json={
            "name": "Evening transport disruption",
            "notes": "Keep the simulation seed fixed.",
            "city_id": "debrecen",
            "workspace_id": "city-lab",
        },
    )
    assert response.status_code == 201, response.text
    experiment = response.json()
    url = f"/api/v1/experiments/{experiment['id']}"
    variant = {"title": "No extra transit", "agent_ids": [], "starts_at": "2026-11-20T17:00", "seed": 96}
    created = client.post(url + "/variants?start=true", json=variant)
    assert created.status_code == 201, created.text
    run_id = created.json()["run"]["id"]
    assert "event: done" in client.get(f"/api/v1/simulations/{run_id}/events").text
    result = client.get(url).json()
    assert result["variants"][0]["seed"] == 96
    assert result["runs"][0]["status"] == "completed"
    assert result["runs"][0]["score"] is not None and len(result["runs"][0]["input_hash"]) == 64
    assert client.get(url + "/export").json()["runs"][0]["id"] == run_id
    assert client.put(
        url, json={"name": experiment["name"], "notes": "Results reviewed.", "archived": True}
    ).is_success
    assert client.post(url + "/variants", json=variant).status_code == 409
    assert client.post(f"/api/v1/scenarios/{result['variants'][0]['id']}/run").status_code == 409
    assert client.get(url + "/export").is_success
    with TestClient(client.app) as other:
        assert other.post("/api/v1/auth/demo").is_success
        assert other.get(url).status_code == 404


def test_gtfs_transit_and_administration_lifecycle(client):
    user = register(client)
    data = (Path(__file__).resolve().parents[2] / "examples" / "debrecen-transit.zip").read_bytes()
    body = {"city_id": "debrecen", "name": "Transit fixture", "layer": "Transit", "format": "gtfs-zip"}
    assert client.post("/api/v1/data-sources", json={**body, "content": "broken"}).status_code == 422
    created = client.post("/api/v1/data-sources", json={**body, "content": base64.b64encode(data).decode()})
    assert created.status_code == 201, created.text
    source = created.json()
    assert source["route_count"] == 2
    routes = client.get("/api/v1/mobility").json()
    assert {route["name"] for route in routes if route.get("source") == body["name"]} == {"Demo 27", "Demo T7"}
    overlays = client.get("/api/v1/cities/debrecen/layers").json()["features"]
    assert any(row["properties"].get("approximate") is True for row in overlays)
    assert client.delete(f"/api/v1/data-sources/{source['id']}").status_code == 204
    assert not any(row.get("source") == body["name"] for row in client.get("/api/v1/mobility").json())
    assert client.patch("/api/v1/workspaces/city-lab", json={"name": "Research lab"}).is_success
    assert client.get("/api/v1/workspaces").json()[0]["name"] == "Research lab"
    assert client.put(
        "/api/v1/teams", json={"id": "transit", "name": "Transit", "members": [user["id"]]}
    ).is_success
    assert client.put("/api/v1/teams", json={"id": "transit", "name": "Rail", "members": []}).is_success
    assert client.get("/api/v1/teams").json()[0]["name"] == "Rail"
    assert client.delete("/api/v1/teams/transit").status_code == 204
    assert client.get("/api/v1/teams").json() == []


def test_read_credential_permissions_revoke_and_secret_handling(client):
    register(client)
    response = client.post(
        "/api/v1/api-credentials",
        json={
            "name": "Transit feedback dashboard",
            "scopes": ["city:read"],
            "days": 14,
        },
    )
    assert response.status_code == 201, response.text
    row = response.json()
    headers = {"Authorization": f"Bearer {row['token']}"}
    public = client.get("/api/v1/api-credentials").text
    assert row["token"] not in public and "digest" not in public
    with TestClient(client.app) as service:
        assert service.get("/api/v1/mobility", headers=headers).is_success
        assert service.get("/api/v1/simulations", headers=headers).status_code == 403
        assert service.get("/api/v1/users", headers=headers).status_code == 403
        assert service.post("/api/v1/scenarios", headers=headers, json={}).status_code == 403
        assert client.delete(f"/api/v1/api-credentials/{row['id']}").status_code == 204
        assert service.get("/api/v1/mobility", headers=headers).status_code == 401


def test_required_verification_and_resend_without_account_disclosure(client, monkeypatch):
    from app import auth_routes

    monkeypatch.setenv("REQUIRE_EMAIL_VERIFICATION", "true")
    monkeypatch.delenv("SMTP_HOST", raising=False)
    account = {
        "name": "Verification Tester",
        "email": f"{uuid4().hex}@example.test",
        "password": "verification-test-password",
    }
    with TestClient(client.app, client=("verification-test", 50000)) as account_client:
        assert account_client.post("/api/v1/auth/register", json=account).status_code == 503
        received = []
        monkeypatch.setenv("SMTP_HOST", "fixture.invalid")
        monkeypatch.setattr(
            auth_routes, "deliver_email", lambda address, subject, body: received.append((address, body))
        )
        assert account_client.post("/api/v1/auth/register", json=account).status_code == 201
        assert account_client.post("/api/v1/auth/login", json=account).status_code == 403
        endpoint = "/api/v1/auth/resend-verification"
        assert account_client.post(endpoint, json={"email": "unknown@example.test"}).json() == {"ok": True}
        assert account_client.post(endpoint, json={"email": account["email"]}).json() == {"ok": True}
        assert len(received) == 2 and received[-1][0] == account["email"]
        token = received[-1][1].split("token=")[-1]
        assert account_client.post("/api/v1/auth/verify", json={"token": token}).is_success
        assert account_client.post("/api/v1/auth/login", json=account).is_success


def test_agent_outcomes_are_published_and_dissent_is_resimulated(client, monkeypatch):
    from app.ai.gateway import ProviderError

    register(client)
    monkeypatch.setenv("LM_STUDIO_MODEL", "fixture")

    def unavailable(*args, **kwargs):
        raise ProviderError("The fixture provider is unavailable.")

    monkeypatch.setattr("app.ai.gateway.generate", unavailable)
    traffic = next(agent for agent in client.get("/api/v1/agents").json() if agent["id"] == "traffic")
    assert client.put("/api/v1/agents/traffic", json={**traffic, "tools": []}).is_success
    created = client.post(
        "/api/v1/scenarios",
        json={
            "title": "Specialist review",
            "kind": "Emergency",
            "starts_at": "2026-11-20T17:00",
            "agent_ids": ["traffic", "mobility", "environment", "safety", "campus"],
        },
    ).json()
    launched = client.post(f"/api/v1/scenarios/{created['id']}/run")
    assert launched.status_code == 202
    resource = f"/api/v1/simulations/{launched.json()['id']}"
    assert "event: done" in client.get(resource + "/events").text
    run = client.get(resource).json()
    assert run["status"] == "completed", run.get("error")
    negotiation = run["result"]["negotiation"]
    revision = next(row for row in run["result"]["strategies"] if row["id"] == negotiation["strategy_id"])
    assert len(revision["timeline"]) == 5
    assert revision["timeline"][0]["incidentPhase"] == "Active"
    assert revision["timeline"][-1]["incidentPhase"] == "Recovery"
    assert any(
        item["stage"] == "simulation" and item["data"].get("strategy") == revision["id"] for item in run["events"]
    )
    notices = client.get("/api/v1/notifications").json()
    outcomes = [item for item in notices if item["type"] in ("agent.completed", "agent.failed")]
    assert sum(item["type"] == "agent.completed" for item in outcomes) == 1
    assert sum(item["type"] == "agent.failed" for item in outcomes) == 4


def test_demo_library_uses_curated_parameters_and_launches_real_runs(client, monkeypatch):
    monkeypatch.setenv("DEMO_LOCAL_PROVIDER", "")
    with TestClient(client.app, client=("demo-library-test", 50001)) as demo:
        assert demo.post("/api/v1/auth/demo").is_success
        library = demo.get("/api/v1/scenarios/demo").json()
        assert len(library) == 5
        assert len({tuple(row["coordinates"]) for row in library}) == 5
        assert len({row["focus"] for row in library}) == 5
        for preset in library:
            response = demo.post(f"/api/v1/scenarios/demo/{preset['id']}/run", json={"workspace_id": "city-lab"})
            assert response.status_code == 202, response.text
            started = response.json()
            scenario = started["scenario"]
            for field in ("kind", "coordinates", "location", "duration", "severity", "population", "constraints", "radius"):
                assert scenario[field] == preset[field]
            assert scenario["starts_at"][11:16] == preset["time"]
            resource = f"/api/v1/simulations/{started['id']}"
            assert "event: done" in demo.get(resource + "/events").text
            completed = demo.get(resource).json()
            assert completed["status"] == "completed"
            assert preset["focus"] in completed["result"]["recommendation"]["timeline"][2]["metrics"]
        assert demo.post("/api/v1/scenarios/demo/missing/run", json={}).status_code == 404
