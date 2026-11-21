from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from .auth import require_admin
from .city_routes import require_city
from .db import Store, db, now
from .simulation.calibration import fit

router = APIRouter(prefix="/calibration", tags=["Simulation calibration"])


class Pair(BaseModel):
    metric: Literal["congestion", "travelDelay", "transitDelay", "emissions", "safetyRisk", "energyLoad"]
    modeled: float = Field(ge=-100_000, le=100_000, allow_inf_nan=False)
    observed: float = Field(ge=-100_000, le=100_000, allow_inf_nan=False)


class FitForm(BaseModel):
    source: str = Field(min_length=2, max_length=120)
    observations: list[Pair] = Field(min_length=10, max_length=5000)
    active: bool = True


class CalibrationState(BaseModel):
    active: bool


@router.get("/{city_id}")
def read(city_id: str, store: Store = Depends(db), user=Depends(require_admin)):
    scope = user["scope"]
    require_city(store, scope, city_id)
    return store.get(scope, "calibration", city_id)


@router.put("/{city_id}")
def train(city_id: str, form: FitForm, store: Store = Depends(db), user=Depends(require_admin)):
    scope = user["scope"]
    require_city(store, scope, city_id)
    try:
        models = fit(form.observations)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    output = {
        "city_id": city_id,
        "source": form.source,
        "trained_at": now().isoformat(),
        "metrics": models,
        "active": form.active,
    }
    store.put(scope, "calibration", city_id, output)
    store.session.commit()
    return output


@router.patch("/{city_id}")
def change(city_id: str, state: CalibrationState, store: Store = Depends(db), user=Depends(require_admin)):
    scope = user["scope"]
    require_city(store, scope, city_id)
    profile = store.get(scope, "calibration", city_id, lock=True)
    if not profile:
        raise HTTPException(404, "No calibration has been fitted for this city.")
    profile = {**profile, "active": state.active}
    store.put(scope, "calibration", city_id, profile)
    store.session.commit()
    return profile
