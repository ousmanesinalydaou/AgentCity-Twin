import json
import time
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from .ai import capabilities
from .ai.gateway import ProviderError, generate, route
from .auth import require_runner
from .city_routes import require_city
from .db import Store, db, now
from .domain import Language
from .operations import require_feature
from .runs import policy
from .workspace import providers_for

router = APIRouter(prefix="/model-lab", tags=["Model lab"])


class Task(BaseModel):
    operation: Literal["vision", "tools", "embeddings", "streaming"]
    prompt: str = Field(min_length=2, max_length=4000)
    city_id: str = Field(default="debrecen", pattern=r"^[a-z0-9-]{1,48}$")
    provider_id: str | None = Field(default=None, max_length=48)
    local_only: bool = True
    image: str | None = Field(default=None, max_length=1_650_000)
    language: Language | None = None


def available(store, user, local_only):
    scope = user["scope"]
    options = providers_for(store, scope, user["demo"])
    data = {row["provider"]: row for row in store.list(scope, "benchmark")}
    return [
        {**entry, "benchmark": data.get(entry["id"], {})}
        for entry in options
        if entry["enabled"] and (entry["local"] or (not local_only and policy(store, scope)["allow_cloud"]))
    ]


def identify(provider):
    return {
        "provider": provider["id"],
        "model": provider["model"],
        "execution": "Local" if provider["local"] else "Cloud",
    }


def snapshot(city):
    return {
        "name": city["name"],
        "roads": len(city["edges"]),
        "incidents": len(city["incidents"]),
        "sensors": len(city["sensors"]),
        "indicators": city["kpis"],
        "source": city["source"],
    }


@router.post("/tasks")
def tasks(form: Task, store: Store = Depends(db), user=Depends(require_runner)):
    require_feature(store, user["scope"], "modelLab")
    context = snapshot(require_city(store, user["scope"], form.city_id))
    if (form.operation == "vision") != bool(form.image):
        raise HTTPException(422, "Attach an image only for a vision task.")
    try:
        image_info = capabilities.validate_image(form.image) if form.image else None
    except ProviderError as exc:
        raise HTTPException(422, str(exc)) from exc
    options = available(store, user, form.local_only)
    candidates = route(
        options,
        {},
        True,
        form.provider_id,
        len(form.prompt) // 3 + 200,
        form.operation,
        routing=policy(store, user["scope"])["model_routing"],
        language=form.language or user["preferences"]["language"],
        complexity="advanced" if form.operation in {"vision", "tools"} or len(form.prompt) > 1800 else "standard",
    )
    if form.provider_id:
        candidates = [provider for provider in candidates if provider["id"] == form.provider_id]
        if not candidates:
            raise HTTPException(422, "The selected provider cannot perform this task under the current policy.")
    if form.operation == "streaming":

        def events():
            for provider in candidates:
                delivered = False
                try:
                    for token in capabilities.stream(provider, form.prompt):
                        delivered = True
                        yield "data: " + json.dumps({"text": token}) + "\n\n"
                    if delivered:
                        yield "data: " + json.dumps({"done": True, **identify(provider)}) + "\n\n"
                        return
                except ProviderError:
                    if delivered:
                        yield 'data: {"error":"The model stream ended early."}\n\n'
                        return
            if form.provider_id:
                yield 'data: {"error":"The provider did not produce a stream."}\n\n'
                return
            data = capabilities.demo(form.operation, form.prompt, image_info, context)
            for word in data["text"].split(" "):
                yield "data: " + json.dumps({"text": word + " "}) + "\n\n"
            yield 'data: {"done":true,"provider":"deterministic","model":"City snapshot","execution":"Local demo"}\n\n'

        return StreamingResponse(
            events(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )
    for provider in candidates:
        try:
            return {
                **capabilities.execute(provider, form.operation, form.prompt, form.image, context),
                **identify(provider),
            }
        except (ProviderError, ValueError, KeyError, TypeError):
            pass
    if form.provider_id:
        raise HTTPException(502, "The configured provider did not complete the model task.")
    return {
        **capabilities.demo(form.operation, form.prompt, image_info, context),
        "execution": "Local demo",
        "provider": "deterministic",
        "model": "Local baseline",
    }


@router.get("/benchmarks")
def benchmarks(store: Store = Depends(db), user=Depends(require_runner)):
    require_feature(store, user["scope"], "modelLab")
    return store.list(user["scope"], "benchmark")


@router.post("/benchmarks/{provider_id}")
def benchmark(provider_id: str, store: Store = Depends(db), user=Depends(require_runner)):
    require_feature(store, user["scope"], "modelLab")
    provider = next((entry for entry in available(store, user, False) if entry["id"] == provider_id), None)
    if provider is None:
        raise HTTPException(404, "Provider unavailable under the current workspace policy.")
    prompts = [
        ("Return only the sum of 37 and 58.", "95"),
        ("Return only the recommended strategy ID. baseline=42 and diversion=81.", "diversion"),
    ]
    latencies, correct = [], 0
    for prompt, answer in prompts:
        start = time.perf_counter()
        try:
            if provider["capabilities"] == ["embeddings"]:
                response = capabilities.execute(provider, "embeddings", prompt, None, {})
                correct += response["dimensions"] > 0 and any(response["vector"])
            else:
                response = generate({**provider, "max_tokens": 32}, "Return the answer only.", prompt, 0.0)
                correct += response.text.strip().strip(".").lower() == answer
        except (ProviderError, ValueError, KeyError, TypeError):
            pass
        latencies.append(round((time.perf_counter() - start) * 1000))
    record = {
        **identify(provider),
        "accuracy": correct / len(prompts),
        "latency_ms": sum(latencies) // len(latencies),
        "samples": len(prompts),
        "time": now().isoformat(),
    }
    store.put(user["scope"], "benchmark", provider_id, record)
    store.session.commit()
    return record
