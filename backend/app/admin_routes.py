import os

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Response
from pydantic import BaseModel, Field
from sqlalchemy.exc import IntegrityError

from .agents import REQUIRED, registry
from .ai.gateway import ProviderError, generate, persist_provider, public_provider
from .auth import create_user, current_user, person, public_user, require_admin
from .auth_routes import mail_token, require_verification_mail
from .db import Store, db
from .domain import DIMENSIONS, Credentials, ProviderInput, Role, RoutingPolicy
from .runs import policy
from .workspace import members, providers_for

router = APIRouter(tags=["Administration"])


class Named(BaseModel):
    name: str = Field(min_length=2, max_length=100)


class Workspace(Named):
    id: str = Field(pattern=r"^[a-z0-9-]{1,48}$")


class Team(Workspace):
    members: list[str] = Field(default_factory=list, max_length=100)


class Membership(Credentials):
    role: Role = "Viewer"


class RoleUpdate(BaseModel):
    role: Role
    disabled: bool = False


class Policy(BaseModel):
    allow_cloud: bool = False
    weights: dict[str, float]
    map_style: str = Field(default="fiord", pattern=r"^(fiord|dark|liberty|local)$")
    model_routing: RoutingPolicy = Field(default_factory=RoutingPolicy)


class AgentConfig(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    description: str = Field(max_length=200)
    instruction: str = Field(min_length=3, max_length=2000)
    enabled: bool = True
    preferred: str = Field(default="", max_length=48)
    fallbacks: list[str] = Field(default_factory=list, max_length=3)
    tools: list[str] = Field(default_factory=list, max_length=8)
    allowed_data: list[str] = Field(default_factory=list, max_length=8)
    temperature: float = Field(default=0.2, ge=0, le=1)
    timeout: int = Field(default=15, ge=2, le=45)
    priority: int = Field(default=10, ge=0, le=1000)
    max_iterations: int = Field(default=1, ge=1, le=3)


@router.get("/organizations")
def organization(store: Store = Depends(db), user=Depends(current_user)):
    return store.get(user["scope"], "organization", "profile")


@router.patch("/organizations")
def update_organization(form: Named, store: Store = Depends(db), user=Depends(require_admin)):
    store.put(user["scope"], "organization", "profile", form.model_dump())
    store.session.commit()
    return form


@router.get("/workspaces")
def workspaces(store: Store = Depends(db), user=Depends(current_user)):
    return store.list(user["scope"], "workspace")


@router.post("/workspaces", status_code=201)
def add_workspace(form: Workspace, store: Store = Depends(db), user=Depends(require_admin)):
    if store.get(user["scope"], "workspace", form.id):
        raise HTTPException(409, "Workspace ID already exists.")
    store.insert(user["scope"], "workspace", form.id, form.model_dump())
    try:
        store.session.commit()
    except IntegrityError as exc:
        raise HTTPException(409, "Workspace ID already exists.") from exc
    return form


@router.patch("/workspaces/{workspace_id}")
def rename_workspace(workspace_id: str, form: Named, store: Store = Depends(db), user=Depends(require_admin)):
    scope = user["scope"]
    row = store.get(scope, "workspace", workspace_id, lock=True)
    if not row:
        raise HTTPException(404, "Workspace not found.")
    row = {**row, "name": form.name}
    store.put(scope, "workspace", workspace_id, row)
    store.session.commit()
    return row


@router.get("/teams")
def teams(store: Store = Depends(db), user=Depends(require_admin)):
    return store.list(user["scope"], "team")


@router.put("/teams")
def add_team(form: Team, store: Store = Depends(db), user=Depends(require_admin)):
    scope = user["scope"]
    eligible = {item["id"] for item in members(store, scope)}
    if not set(form.members) <= eligible:
        raise HTTPException(422, "Team members must belong to this organization.")
    store.get(scope, "organization", "profile", lock=True)
    team = {**form.model_dump(), "members": list(dict.fromkeys(form.members))}
    store.put(scope, "team", form.id, team)
    store.session.commit()
    return team


@router.delete("/teams/{team_id}", status_code=204)
def remove_team(team_id: str, store: Store = Depends(db), user=Depends(require_admin)):
    scope = user["scope"]
    store.get(scope, "organization", "profile", lock=True)
    if not store.remove(scope, "team", team_id):
        raise HTTPException(404, "Team not found.")
    store.session.commit()
    return Response(status_code=204)


@router.get("/users")
def users(store: Store = Depends(db), user=Depends(require_admin)):
    return [public_user(item) for item in members(store, user["scope"])]


@router.post("/users", status_code=201)
def add_member(
    form: Membership, background: BackgroundTasks, store: Store = Depends(db), user=Depends(require_admin)
):
    if form.role == "Super Admin":
        raise HTTPException(403, "This role is provisioned on the server.")
    require_verification_mail()
    item = create_user(store, form.email, form.name, form.password, scope=user["scope"], role=form.role)
    mail_token(store, background, "verify", item)
    store.session.commit()
    return public_user(item)


@router.patch("/users/{user_id}")
def update_member(user_id: str, form: RoleUpdate, store: Store = Depends(db), user=Depends(require_admin)):
    item = person(store, user_id)
    if not item or item["scope"] != user["scope"]:
        raise HTTPException(404, "Member not found.")
    if user_id == user["id"] or item["role"] == "Super Admin" or form.role == "Super Admin":
        raise HTTPException(403, "This member cannot be changed here.")
    item = {**item, **form.model_dump()}
    store.put("system", "user", user_id, item)
    store.session.commit()
    return public_user(item)


@router.get("/settings/policy")
def get_policy(store: Store = Depends(db), user=Depends(current_user)):
    return policy(store, user["scope"])


@router.put("/settings/policy")
def set_policy(form: Policy, store: Store = Depends(db), user=Depends(require_admin)):
    if (
        set(form.weights) != set(DIMENSIONS)
        or any(not 0 <= v <= 100 for v in form.weights.values())
        or not sum(form.weights.values())
    ):
        raise HTTPException(422, "Assign a weight from 0 to 100 to each objective and use a positive total.")
    if form.allow_cloud and os.getenv("ALLOW_CLOUD_MODELS", "false").lower() not in {"1", "true", "yes"}:
        raise HTTPException(403, "Enable cloud models on the server before granting workspace consent.")
    store.put(user["scope"], "settings", "policy", form.model_dump())
    store.session.commit()
    return form


@router.get("/agents")
def agents(store: Store = Depends(db), user=Depends(current_user)):
    return registry(store, user["scope"])


@router.put("/agents/{agent_id}")
def set_agent(agent_id: str, form: AgentConfig, store: Store = Depends(db), user=Depends(require_admin)):
    current = next((item for item in registry(store, user["scope"]) if item["id"] == agent_id), None)
    if not current:
        raise HTTPException(404, "Agent not found.")
    if agent_id in REQUIRED and not form.enabled:
        raise HTTPException(422, "The simulation pipeline requires this agent.")
    config = {**current, **form.model_dump()}
    store.put(user["scope"], "agent", agent_id, config)
    store.session.commit()
    return config


@router.get("/providers")
@router.get("/models")
def providers(store: Store = Depends(db), user=Depends(current_user)):
    return [public_provider(item) for item in providers_for(store, user["scope"], user["demo"])]


@router.put("/providers")
def save_provider(form: ProviderInput, store: Store = Depends(db), user=Depends(require_admin)):
    scope = user["scope"]
    if any(item["id"] == form.id and item.get("environment") for item in providers_for(store, scope)):
        raise HTTPException(409, "This provider is configured through server environment variables.")
    try:
        config = persist_provider(form, store.get(scope, "provider", form.id))
    except ProviderError as exc:
        raise HTTPException(422, str(exc)) from exc
    if config["default"]:
        for row in store.list(scope, "provider"):
            if row["id"] != form.id and row["default"]:
                store.put(scope, "provider", row["id"], {**row, "default": False})
    store.put(scope, "provider", form.id, config)
    store.session.commit()
    return public_provider(config)


@router.post("/providers/{provider_id}/test")
def test_connection(provider_id: str, store: Store = Depends(db), user=Depends(require_admin)):
    config = next((row for row in providers_for(store, user["scope"]) if row["id"] == provider_id), None)
    if not config:
        raise HTTPException(404, "Provider not found.")
    if not config["local"] and not policy(store, user["scope"])["allow_cloud"]:
        raise HTTPException(403, "Allow cloud execution for this organization first.")
    try:
        return generate(config, "Reply briefly.", "Connection check. Reply OK.").metadata
    except ProviderError as exc:
        raise HTTPException(502, str(exc)) from exc
