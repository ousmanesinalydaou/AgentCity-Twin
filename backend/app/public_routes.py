import json
import os
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from .auth import require_admin
from .city import DEBRECEN, LAYERS, city_layers
from .city_routes import public_city
from .config import demo_enabled
from .db import Store, db
from .runs import utc

router = APIRouter(prefix="/public", tags=["Public"])


class ContactForm(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    email: str = Field(min_length=3, max_length=254, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    message: str = Field(min_length=10, max_length=2000)


class Plan(BaseModel):
    name: str = Field(min_length=2, max_length=65)
    description: str = Field(min_length=2, max_length=200)
    price: str = Field(default="", max_length=60)


@router.get("/plans", response_model=list[Plan])
def plans():
    try:
        items = json.loads(os.getenv("PUBLIC_PLANS", "[]"))
        return [Plan.model_validate(value) for value in items[:6]] if isinstance(items, list) else []
    except ValueError:
        return []


@router.get("/demo")
def preview(store: Store = Depends(db)):
    if not demo_enabled():
        raise HTTPException(404, "The demo is disabled.")
    return {
        "city": public_city(DEBRECEN),
        "incidents": DEBRECEN["incidents"],
        "layers": {**city_layers(DEBRECEN, store, "public"), "layers": LAYERS},
    }


@router.post("/contact", status_code=201)
def contact(form: ContactForm, store: Store = Depends(db)):
    ticket = uuid4().hex
    store.insert("system", "contact", ticket, {**form.model_dump(), "id": ticket, "created_at": utc()})
    store.session.commit()
    return {"id": ticket}


@router.get("/contact")
def inbox(store: Store = Depends(db), user=Depends(require_admin)):
    if user["role"] != "Super Admin":
        raise HTTPException(403, "A platform administrator is required.")
    return store.list("system", "contact")
