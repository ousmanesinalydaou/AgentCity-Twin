"""Manage saved research experiments and their scenario and run variants."""

from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from .auth import current_user, require_runner
from .city_routes import require_city
from .db import Store, db
from .domain import ScenarioInput
from .operations import require_feature
from .run_routes import launch, require_workspace, run_summary, save_scenario
from .runs import utc

router = APIRouter(prefix="/experiments", tags=["Research"])


class ExperimentMetadata(BaseModel):
    name: str = Field(min_length=3, max_length=120)
    notes: str = Field(default="", max_length=2000)


class ExperimentInput(ExperimentMetadata):
    city_id: str = Field(pattern=r"^[a-z0-9-]{1,48}$")
    workspace_id: str = Field(pattern=r"^[a-z0-9-]{1,48}$")


class ExperimentUpdate(ExperimentMetadata):
    archived: bool


def get_experiment(store, scope, experiment_id, *, lock=False):
    require_feature(store, scope, "research")
    row = store.get(scope, "experiment", experiment_id, lock=lock)
    if not row:
        raise HTTPException(404, "Experiment not found.")
    return row


def records(store, scope, row, limit=250):
    variants = store.list(scope, "scenario", limit, experiment_id=row["id"])
    runs = store.list(scope, "run", limit, experiment_id=row["id"])
    return variants, runs


@router.get("")
def list_experiments(
    city_id: str = "debrecen",
    workspace_id: str = "city-lab",
    store: Store = Depends(db),
    user=Depends(current_user),
):
    scope = user["scope"]
    require_feature(store, scope, "research")
    return store.list(scope, "experiment", city_id=city_id, workspace_id=workspace_id)


def create_experiment(store, scope, form):
    require_feature(store, scope, "research")
    require_city(store, scope, form.city_id)
    require_workspace(store, scope, form.workspace_id)
    row = {**form.model_dump(), "id": uuid4().hex, "created_at": utc(), "archived": False}
    store.insert(scope, "experiment", row["id"], row)
    return row


@router.post("", status_code=201)
def add_experiment(form: ExperimentInput, store: Store = Depends(db), user=Depends(require_runner)):
    row = create_experiment(store, user["scope"], form)
    store.session.commit()
    return row


@router.get("/{experiment_id}")
def detail(experiment_id: str, store: Store = Depends(db), user=Depends(current_user)):
    scope = user["scope"]
    row = get_experiment(store, scope, experiment_id)
    variants, runs = records(store, scope, row)
    return {**row, "variants": variants, "runs": [outcome(run) for run in runs]}


def outcome(run):
    result = run["result"]
    frame = (
        next((frame for frame in result["recommendation"]["timeline"] if frame["minute"] == 30), None)
        if result
        else None
    )
    return {
        **run_summary(run),
        "seed": run["scenario"]["seed"],
        "input_hash": result["input_hash"] if result else None,
        "score": result["recommendation"]["score"] if result else None,
        "congestion": frame["metrics"]["congestion"] if frame else None,
        "transit_delay": frame["metrics"]["transitDelay"] if frame else None,
    }


@router.put("/{experiment_id}")
def update(experiment_id: str, form: ExperimentUpdate, store: Store = Depends(db), user=Depends(require_runner)):
    scope = user["scope"]
    row = {**get_experiment(store, scope, experiment_id, lock=True), **form.model_dump()}
    store.put(scope, "experiment", experiment_id, row)
    store.session.commit()
    return row


@router.post("/{experiment_id}/variants", status_code=201)
def add_variant(
    experiment_id: str,
    form: ScenarioInput,
    start: bool = False,
    store: Store = Depends(db),
    user=Depends(require_runner),
):
    scope = user["scope"]
    row = get_experiment(store, scope, experiment_id, lock=True)
    if row["archived"]:
        raise HTTPException(409, "This experiment is archived.")
    if (form.city_id, form.workspace_id) != (row["city_id"], row["workspace_id"]):
        raise HTTPException(422, "Use the experiment’s city and workspace.")
    variant = save_scenario(store, scope, form, experiment_id=experiment_id, commit=False)
    run = launch(store, user, variant) if start else None
    if not start:
        store.session.commit()
    return {"variant": variant, "run": run}


@router.get("/{experiment_id}/export")
def export(experiment_id: str, store: Store = Depends(db), user=Depends(current_user)):
    scope = user["scope"]
    row = get_experiment(store, scope, experiment_id)
    variants, runs = records(store, scope, row, limit=None)
    return JSONResponse(
        {"schema_version": 1, "experiment": row, "variants": variants, "runs": runs},
        headers={"Content-Disposition": f'attachment; filename="agentcity-experiment-{row["id"]}.json"'},
    )
