import csv
import io
import json
import re
import time
from datetime import datetime
from uuid import uuid4
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, Response, StreamingResponse
from pydantic import BaseModel, Field

from .agents import registry
from .auth import ADMIN, current_user, require_runner
from .city_routes import require_city
from .config import ROOT
from .db import RunJob, Store, db
from .domain import ScenarioInput
from .execution import TERMINAL_RUNS, finish_execution
from .operations import require_feature
from .report_document import TEMPLATES, render
from .runs import new_run, read_run, utc
from .workspace import providers_for

router = APIRouter(tags=["Simulations"])
DEMO_SCENARIOS = {
    row["id"]: row for row in json.loads((ROOT / "data" / "demo-scenarios.json").read_text(encoding="utf-8"))
}
KIND_TERMS = (
    ("Road Closure", ("closes", "road closure", "closure", "fermeture")),
    ("Transit Failure", ("tram", "bus failure", "transit failure", "panne")),
    ("Pollution Spike", ("pollution", "air quality")),
    ("Severe Weather", ("weather", "storm", "flood", "tempête")),
    ("Football Match", ("football", "stadium", "match")),
    ("Power Outage", ("power", "energy outage", "électricité")),
    ("Construction", ("construction", "travaux")),
    ("Campus Event", ("campus event", "university event", "événement")),
    ("Public Gathering", ("crowd", "festival", "gathering")),
)


class Analysis(BaseModel):
    prompt: str = Field(min_length=5, max_length=2000)
    city_id: str = "debrecen"
    workspace_id: str = "city-lab"
    coordinates: tuple[float, float] | None = None


class Approval(BaseModel):
    decision: str = Field(pattern=r"^(approved|rejected)$")
    note: str = Field(min_length=3, max_length=500)


class DemoLaunch(BaseModel):
    workspace_id: str = Field(default="city-lab", pattern=r"^[a-z0-9-]{1,48}$")


def require_workspace(store, scope, workspace_id):
    if store.get(scope, "workspace", workspace_id) is None:
        raise HTTPException(404, "Workspace not found.")


def save_scenario(store, scope, form, *, experiment_id=None, commit=True):
    city = require_city(store, scope, form.city_id)
    require_workspace(store, scope, form.workspace_id)
    start = form.starts_at if form.starts_at.tzinfo else form.starts_at.replace(tzinfo=ZoneInfo(city["timezone"]))
    data = {
        **form.model_dump(mode="json"),
        "id": uuid4().hex,
        "created_at": utc(),
        "starts_at": start.isoformat(),
        "coordinates": list(form.coordinates or city["origin"]),
    }
    if experiment_id:
        data["experiment_id"] = experiment_id
    store.insert(scope, "scenario", data["id"], data)
    if commit:
        store.session.commit()
    return data


def load_scenario(store, scope, scenario_id):
    scenario = store.get(scope, "scenario", scenario_id)
    if not scenario:
        raise HTTPException(404, "Scenario not found.")
    return scenario


def launch(store, user, scenario):
    scope = user["scope"]
    if experiment_id := scenario.get("experiment_id"):
        require_feature(store, scope, "research")
        experiment = store.get(scope, "experiment", experiment_id, lock=True)
        if not experiment or experiment["archived"]:
            raise HTTPException(409, "This experiment is archived.")
    city = require_city(store, scope, scenario["city_id"])
    if not city["edges"] or not city["demand"]:
        raise HTTPException(422, "Add a road graph and demand pairs to this city before running a simulation.")
    from sqlalchemy import func, select

    store.get(scope, "organization", "profile", lock=True)
    active = store.session.scalar(select(func.count()).select_from(RunJob).where(RunJob.scope == scope))
    if active >= 3:
        raise HTTPException(429, "Wait for an active run to complete.")
    providers = providers_for(store, scope, user["demo"])
    for key in ("provider_id", "compare_provider_id"):
        if scenario.get(key) and scenario[key] not in {row["id"] for row in providers if row["enabled"]}:
            raise HTTPException(422, "The selected provider is unavailable.")
    return new_run(
        store,
        scope,
        scenario,
        city,
        registry(store, scope),
        providers,
        {"id": user["id"], "demo": user["demo"], "language": user["preferences"]["language"]},
    )


def run_summary(row):
    return {
        key: row[key] for key in ("id", "scenario_id", "workspace_id", "city_id", "title", "status", "created_at")
    } | {
        "winner": row["result"]["recommendation"]["name"] if row["result"] else None,
        "experiment_id": row.get("experiment_id"),
        "execution_state": (row.get("execution") or {}).get("state"),
    }


def require_run(scope, run_id):
    run = read_run(scope, run_id)
    if run is None:
        raise HTTPException(404, "Run not found.")
    return run


@router.get("/scenarios")
def scenarios(
    city_id: str = "debrecen",
    workspace_id: str = "city-lab",
    store: Store = Depends(db),
    user=Depends(current_user),
):
    return store.list(user["scope"], "scenario", city_id=city_id, workspace_id=workspace_id)


@router.post("/scenarios", status_code=201)
def create_scenario(form: ScenarioInput, store: Store = Depends(db), user=Depends(require_runner)):
    return save_scenario(store, user["scope"], form)


@router.get("/scenarios/demo")
def demo_scenarios(store: Store = Depends(db), user=Depends(current_user)):
    city = require_city(store, user["scope"], "debrecen")
    return [
        {**row, "city_id": city["id"], "coordinates": city["nodes"][row["node"]]}
        for row in DEMO_SCENARIOS.values()
    ]


@router.post("/scenarios/demo/{preset_id}/run", status_code=202)
def run_demo(preset_id: str, form: DemoLaunch, store: Store = Depends(db), user=Depends(require_runner)):
    row = DEMO_SCENARIOS.get(preset_id)
    if not row:
        raise HTTPException(404, "Demo scenario not found.")
    scope = user["scope"]
    city = require_city(store, scope, "debrecen")
    local_date = datetime.now(ZoneInfo(city["timezone"])).date()
    scenario = ScenarioInput(
        **row,
        city_id=city["id"],
        workspace_id=form.workspace_id,
        coordinates=city["nodes"][row["node"]],
        description=row["prompt"],
        starts_at=f"{local_date.isoformat()}T{row['time']}",
    )
    return launch(store, user, save_scenario(store, scope, scenario, commit=False))


@router.post("/scenarios/{scenario_id}/run", status_code=202)
def run_scenario(scenario_id: str, store: Store = Depends(db), user=Depends(require_runner)):
    return launch(store, user, load_scenario(store, user["scope"], scenario_id))


@router.post("/agentcity/analyze", status_code=202)
def analyze(form: Analysis, store: Store = Depends(db), user=Depends(require_runner)):
    from pydantic import ValidationError

    city = require_city(store, user["scope"], form.city_id)
    phrase = form.prompt.strip()
    kind = next(
        (name for name, triggers in KIND_TERMS if any(term in phrase.lower() for term in triggers)), "Emergency"
    )
    hour = re.search(r"\b([01]?\d|2[0-3])[:h]([0-5]\d)\b", phrase)
    start = datetime.now(ZoneInfo(city["timezone"])).replace(second=0, microsecond=0)
    if hour:
        start = start.replace(hour=int(hour[1]), minute=int(hour[2]))
    central = any(word in phrase.lower() for word in ("city center", "centre", "downtown", "kossuth"))
    incident = "accident" in phrase.lower() and "university" in phrase.lower()
    title = "University corridor incident" if incident else f"{kind} scenario"
    try:
        parsed = ScenarioInput(
            title=title,
            kind=kind,
            city_id=form.city_id,
            workspace_id=form.workspace_id,
            description=phrase,
            location="University of Debrecen" if incident else city["name"],
            coordinates=form.coordinates or (city["center"] if central else city["origin"]),
            starts_at=start,
        )
    except ValidationError as exc:
        raise HTTPException(422, "The scenario context is invalid.") from exc
    return launch(store, user, save_scenario(store, user["scope"], parsed))


@router.get("/simulations")
@router.get("/reports")
def runs(
    city_id: str = "debrecen",
    workspace_id: str = "city-lab",
    store: Store = Depends(db),
    user=Depends(current_user),
):
    return [
        run_summary(row) for row in store.list(user["scope"], "run", city_id=city_id, workspace_id=workspace_id)
    ]


@router.get("/simulations/{run_id}")
def simulation(run_id: str, user=Depends(current_user)):
    return require_run(user["scope"], run_id)


@router.get("/simulations/{run_id}/results")
def results(run_id: str, user=Depends(current_user)):
    return require_run(user["scope"], run_id)["result"]


@router.get("/simulations/{run_id}/execution")
def run_execution(run_id: str, user=Depends(current_user)):
    return require_run(user["scope"], run_id).get("execution")


@router.post("/simulations/{run_id}/cancel")
def cancel_run(run_id: str, store: Store = Depends(db), user=Depends(require_runner)):
    scope = user["scope"]
    job = store.session.get(RunJob, (scope, run_id), with_for_update=True)
    run = store.get(scope, "run", run_id, lock=True)
    if not run:
        raise HTTPException(404, "Run not found.")
    actor = (store.get(scope, "run-input", run_id) or {}).get("actor", {})
    if actor.get("id") != user["id"] and user["role"] not in ADMIN | {"City Operator"}:
        raise HTTPException(403, "Only the requester or an operator can cancel this run.")
    if run["status"] == "cancelled":
        return run
    if not job or run["status"] in TERMINAL_RUNS:
        raise HTTPException(409, "Only an active run can be cancelled.")
    run = {**run, "status": "cancelled"}
    if run.get("execution"):
        run["execution"] = finish_execution(run["execution"], "cancelled")
    run["events"] = [
        *run["events"],
        {
            "seq": len(run["events"]) + 1,
            "stage": "execution",
            "agent": None,
            "status": "cancelled",
            "text": "The operator cancelled the run.",
            "time": utc(),
            "data": {"actor": user["name"], "execution": {"state": "cancelled", "active_steps": []}},
        },
    ]
    store.put(scope, "run", run_id, run)
    store.session.delete(job)
    store.session.commit()
    return run


@router.get("/agents/{agent_id}/runs")
def agent_runs(agent_id: str, store: Store = Depends(db), user=Depends(current_user)):
    return [
        {
            "id": row["id"],
            "title": row["title"],
            "events": [item for item in row["events"] if item["agent"] == agent_id],
        }
        for row in store.list(user["scope"], "run", 20)
        if any(item["agent"] == agent_id for item in row["events"])
    ]


@router.get("/simulations/{run_id}/events")
def events(run_id: str, request: Request, user=Depends(current_user)):
    scope = user["scope"]
    require_run(scope, run_id)
    header = request.headers.get("Last-Event-ID", "0")
    last = int(header) if header.isdecimal() and len(header) < 10 else 0

    def stream():
        cursor = last
        wait = 0
        while True:
            run = read_run(scope, run_id)
            if not run:
                return
            for event in run["events"][cursor:]:
                cursor = event["seq"]
                yield f"id: {cursor}\ndata: {json.dumps(event)}\n\n"
            if run["status"] in TERMINAL_RUNS:
                yield f"event: done\ndata: {json.dumps({'status': run['status']})}\n\n"
                return
            if wait % 40 == 0:
                yield ": keepalive\n\n"
            wait += 1
            time.sleep(0.35)

    return StreamingResponse(
        stream(), media_type="text/event-stream", headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}
    )


@router.post("/simulations/{run_id}/approval")
def approve(run_id: str, form: Approval, store: Store = Depends(db), user=Depends(current_user)):
    if user["role"] not in ADMIN | {"City Operator"}:
        raise HTTPException(403, "A city operator or administrator must review this run.")
    scope = user["scope"]
    run = store.get(scope, "run", run_id, lock=True)
    if not run or not run["result"] or not run["result"]["requires_approval"]:
        raise HTTPException(409, "This run does not require an approval decision.")
    if run["approval"]:
        raise HTTPException(409, "This run already has a recorded review.")
    run = {**run, "approval": {"decision": form.decision, "note": form.note, "actor": user["name"], "time": utc()}}
    if (run.get("execution") or {}).get("state") == "waiting_for_human_approval":
        run["execution"] = finish_execution(run["execution"], "completed")
    run["events"] = [
        *run["events"],
        {
            "seq": len(run["events"]) + 1,
            "stage": "approval",
            "agent": None,
            "status": "completed",
            "text": f"Human review: {form.decision}.",
            "time": utc(),
            "data": run["approval"],
        },
    ]
    store.put(scope, "run", run_id, run)
    store.session.commit()
    return run


@router.get("/reports/{run_id}")
def report(run_id: str, format: str = "json", user=Depends(current_user)):
    row = require_run(user["scope"], run_id)
    if format == "csv":
        out = io.StringIO()
        writer = csv.writer(out)
        writer.writerow(
            ("strategy", "score", "minute", "congestion", "transit_delay_min", "emissions_pct", "risk")
        )
        for strategy in (row["result"] or {}).get("strategies", []):
            for item in strategy["timeline"]:
                m = item["metrics"]
                writer.writerow(
                    (
                        strategy["name"],
                        strategy["score"],
                        item["minute"],
                        m["congestion"],
                        m["transitDelay"],
                        m["emissions"],
                        m["safetyRisk"],
                    )
                )
        return Response(
            out.getvalue(),
            media_type="text/csv",
            headers={"Content-Disposition": f'attachment; filename="agentcity-{run_id}.csv"'},
        )
    return Response(
        json.dumps(row, indent=2),
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="agentcity-{run_id}.json"'},
    )


@router.get("/reports/{run_id}/document", response_class=HTMLResponse)
def document(
    run_id: str, template: str = "decision", minute: int = 30, language: str = "en", user=Depends(current_user)
):
    run = require_run(user["scope"], run_id)
    if not run["result"]:
        raise HTTPException(409, "Complete the simulation before opening its report.")
    if template not in TEMPLATES or minute not in {0, 15, 30, 60, 120}:
        raise HTTPException(422, "Choose a supported template and timeline point.")
    return HTMLResponse(render(run, template, minute, language if language in {"en", "fr", "bm"} else "en"))
