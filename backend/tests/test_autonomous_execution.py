from threading import Event

from app import city_execution, runs
from app.simulation.engine import simulate
from fastapi.testclient import TestClient


def launch(client, **updates):
    response = client.post(
        "/api/v1/scenarios",
        json={
            "title": "Execution contract",
            "starts_at": "2026-11-20T17:00",
            "agent_ids": ["traffic", "mobility", "safety"],
            **updates,
        },
    )
    assert response.status_code == 201, response.text
    response = client.post(f"/api/v1/scenarios/{response.json()['id']}/run")
    assert response.status_code == 202, response.text
    return f"/api/v1/simulations/{response.json()['id']}"


def completed(client, path):
    stream = client.get(path + "/events").text
    assert "event: done" in stream
    return client.get(path).json(), stream


def test_critic_rejects_false_route_and_worker_replans(client, monkeypatch):
    monkeypatch.setenv("DEMO_LOCAL_PROVIDER", "")
    calls = []

    def invalid_first_pass(city, scenario, strategies, weights):
        rows = simulate(city, scenario, strategies, weights)
        calls.append([item.id for item in strategies])
        if len(calls) == 1:
            next(item for item in rows if item["id"] == "reroute")["timeline"][0]["flows"][0]["coordinates"][0] = [
                0,
                0,
            ]
        return rows

    monkeypatch.setattr(runs, "simulate", invalid_first_pass)
    with TestClient(client.app, client=("verify-loop", 50002)) as app:
        assert app.post("/api/v1/auth/demo").is_success
        path = launch(app)
        run, stream = completed(app, path)
        assert run["status"] == "completed", run.get("error")
        assert run["result"]["verified"] is True
        assert calls[0] == calls[1]
        assert "The Critic rejected invalid or missing candidates." in stream
        assert "A simulated route is invalid or absent from the road graph" in stream
        plan = app.get(path + "/execution").json()
        assert plan["verification"]["checked_by"] == "critic"
        assert plan["state"] == "waiting_for_human_approval"
        assert plan["counts"]["replans"] >= 1 and plan["counts"]["delegations"] >= 3
        assert all(criterion["status"] == "passed" for criterion in plan["success_criteria"])
        assert any(step["id"] == "simulation-repair" and step["status"] == "completed" for step in plan["steps"])
        approval = app.post(path + "/approval", json={"decision": "rejected", "note": "Pilot decision reviewed"})
        assert approval.is_success and approval.json()["execution"]["state"] == "completed"


def test_unknown_constraints_preserve_verified_baseline(client, monkeypatch):
    monkeypatch.setenv("DEMO_LOCAL_PROVIDER", "")
    with TestClient(client.app, client=("partial-loop", 50003)) as app:
        assert app.post("/api/v1/auth/demo").is_success
        path = launch(app, constraints="Only vehicles with an approved service permit", agent_ids=[])
        run, _ = completed(app, path)
        assert run["result"]["recommendation"]["id"] == "baseline"
        assert run["execution"]["state"] == "partially_completed"
        outcomes = {item["id"]: item["status"] for item in run["execution"]["success_criteria"]}
        assert outcomes["constraints"] == outcomes["alternatives"] == "unmet"
        assert outcomes["baseline"] == outcomes["verification"] == "passed"


def test_missing_baseline_stops_after_one_correction(client, monkeypatch):
    monkeypatch.setenv("DEMO_LOCAL_PROVIDER", "")
    attempts = []

    def omit_baseline(*args):
        attempts.append(1)
        return [row for row in simulate(*args) if row["id"] != "baseline"]

    monkeypatch.setattr(runs, "simulate", omit_baseline)
    with TestClient(client.app, client=("blocked-loop", 50005)) as app:
        assert app.post("/api/v1/auth/demo").is_success
        run, _ = completed(app, launch(app, agent_ids=[]))
        assert run["status"] == run["execution"]["state"] == "failed"
        assert len(attempts) == 2 and run["result"] is None
        assert not any(event["stage"] == "decision" for event in run["events"])


def test_worker_recovers_from_telemetry_read_error_and_honors_cancel(client, monkeypatch):
    from sqlalchemy.exc import SQLAlchemyError

    monkeypatch.setenv("DEMO_LOCAL_PROVIDER", "")

    def no_telemetry(*_args):
        raise SQLAlchemyError("Fixture telemetry unavailable")

    monkeypatch.setattr(city_execution, "read_freshness", no_telemetry)
    with TestClient(client.app, client=("cancel-loop", 50004)) as app:
        assert app.post("/api/v1/auth/demo").is_success
        path = launch(app, agent_ids=[])
        run, _ = completed(app, path)
        assert run["status"] == "completed", run.get("error")
        assert run["execution"]["counts"]["retries"] >= 1
        assert any(step["id"] == "cached-observations" for step in run["execution"]["steps"])
        assert any("pinned evidence" in item for item in run["result"]["limitations"])
        entered, release = Event(), Event()

        def blocked(*args):
            entered.set()
            if not release.wait(10):
                raise RuntimeError("Fixture wait expired")
            return simulate(*args)

        monkeypatch.setattr(runs, "simulate", blocked)
        try:
            path = launch(app, agent_ids=[])
            assert entered.wait(8)
            result = app.post(path + "/cancel")
            assert result.is_success, result.text
            assert result.json()["execution"]["state"] == "cancelled"
        finally:
            release.set()
        run, stream = completed(app, path)
        assert run["status"] == "cancelled" and run["result"] is None
        assert "The operator cancelled the run." in stream
