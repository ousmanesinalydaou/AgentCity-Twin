from uuid import uuid4

from fastapi.testclient import TestClient


def test_scenario_trace_exports_and_tenant_isolation(client):
    client.cookies.clear()
    demo = client.post("/api/v1/auth/demo")
    assert demo.status_code == 200 and demo.json()["demo"]
    data = client.get("/api/v1/cities/debrecen/layers").json()
    assert data["type"] == "FeatureCollection" and len(data["features"]) > 20
    response = client.post(
        "/api/v1/agentcity/analyze",
        json={"prompt": "An accident happens near the University of Debrecen at 17:00 during rush hour."},
    )
    assert response.status_code == 202, response.text
    run_id = response.json()["id"]
    stream = client.get(f"/api/v1/simulations/{run_id}/events")
    assert stream.headers["content-type"].startswith("text/event-stream")
    assert "event: done" in stream.text and "verification" in stream.text
    result = client.get(f"/api/v1/simulations/{run_id}").json()
    assert result["status"] == "completed", result
    assert result["scenario"]["starts_at"][11:16] == "17:00"
    assert result["result"]["verified"] and result["result"]["mode"] == "Simulated"
    assert result["result"]["recommendation"]["score"] > result["result"]["baseline"]["score"]
    permission = client.post(
        f"/api/v1/simulations/{run_id}/approval", json={"decision": "approved", "note": "Demo evidence reviewed"}
    )
    assert permission.status_code == 200 and permission.json()["approval"]["decision"] == "approved"
    assert client.get(f"/api/v1/reports/{run_id}?format=csv").text.startswith("strategy,score,minute")
    assert client.get(f"/api/v1/reports/{run_id}").json()["id"] == run_id
    with TestClient(client.app) as outsider:
        outsider.post("/api/v1/auth/demo")
        assert outsider.get(f"/api/v1/simulations/{run_id}").status_code == 404
    assert client.get("/api/v1/users").status_code == 403


def test_credentials_preferences_and_session_rotation(client):
    client.cookies.clear()
    email = uuid4().hex + "@example.test"
    form = {"email": email, "name": "QA Account", "password": "test-password-2026"}
    assert client.post("/api/v1/auth/register", json=form).status_code == 201
    assert client.get("/api/v1/auth/me").json()["role"] == "Organization Admin"
    assert (
        client.patch(
            "/api/v1/auth/preferences", json={"language": "fr", "theme": "light", "notifications": False}
        ).json()["preferences"]["language"]
        == "fr"
    )
    previous = client.cookies.get("agentcity_refresh")
    assert client.post("/api/v1/auth/refresh").status_code == 200
    assert previous != client.cookies.get("agentcity_refresh")
    assert client.post("/api/v1/auth/logout").status_code == 200
    assert client.get("/api/v1/auth/me").status_code == 401
    assert client.post("/api/v1/auth/login", json={**form, "password": "wrong-password"}).status_code == 401
    assert client.post("/api/v1/auth/login", json=form).status_code == 200
    assert client.post("/api/v1/auth/logout", headers={"Origin": "https://untrusted.example"}).status_code == 403


def test_admin_assets_are_tenant_scoped(client):
    client.cookies.clear()
    client.post(
        "/api/v1/auth/register",
        json={"email": uuid4().hex + "@example.test", "name": "City Admin", "password": "test-password-2026"},
    )
    response = client.post(
        "/api/v1/data-sources",
        json={
            "city_id": "debrecen",
            "name": "Sensor trial",
            "layer": "Sensors",
            "format": "csv",
            "content": "name,longitude,latitude\nAdded sensor,21.63,47.54",
        },
    )
    assert response.status_code == 201 and response.json()["feature_count"] == 1
    layers = client.get("/api/v1/cities/debrecen/layers").json()["features"]
    assert any(item["properties"].get("name") == "Added sensor" for item in layers)
    response = client.post("/api/v1/workspaces", json={"id": "experiment", "name": "Experiment lab"})
    assert response.status_code == 201
    assert any(item["id"] == "experiment" for item in client.get("/api/v1/workspaces").json())
    with TestClient(client.app) as visitor:
        visitor.post("/api/v1/auth/demo")
        assert visitor.get("/api/v1/data-sources").json() == []


def test_public_map_and_contact(client):
    assert client.get("/api/v1/public/demo").json()["city"]["id"] == "debrecen"
    response = client.post(
        "/api/v1/public/contact",
        json={
            "name": "Demo Tester",
            "email": "tester@example.test",
            "message": "I would like details for a new city.",
        },
    )
    assert response.status_code == 201 and len(response.json()["id"]) == 32
