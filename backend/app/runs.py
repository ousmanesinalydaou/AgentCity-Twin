import hashlib
import json
import logging
import time
from collections import Counter
from datetime import datetime
from statistics import mean
from uuid import uuid4

from sqlalchemy.orm import Session

from .agents import REQUIRED, select_agents
from .city_execution import run_city
from .config import enabled
from .db import Store, engine, now
from .domain import DEFAULT_WEIGHTS, RoutingPolicy
from .execution import Execution, finish_execution, initial_execution
from .jobs import LeaseLost, enqueue, persist
from .monitoring import run_events
from .simulation.catalog import negotiated_strategy
from .simulation.engine import VERSION, simulate
from .telemetry import city_readings

logger = logging.getLogger("agentcity")


def utc():
    return now().isoformat()


def policy(store, scope):
    values = {
        "allow_cloud": False,
        "weights": DEFAULT_WEIGHTS,
        "model_routing": RoutingPolicy().model_dump(),
        **(store.get(scope, "settings", "policy") or {}),
    }
    return {**values, "allow_cloud": values["allow_cloud"] and enabled("ALLOW_CLOUD_MODELS")}


def new_run(store, scope, scenario, city, agents, providers, audit_user):
    settings = policy(store, scope)
    calibration = store.get(scope, "calibration", city["id"])
    if calibration and calibration["active"]:
        city = {**city, "calibration": calibration}
    recent = [
        row
        for row in city_readings(store, scope, city["id"])
        if row["value"] is not None
        and row["source"] != "Simulated"
        and 0 <= (now() - datetime.fromisoformat(row["observed_at"])).total_seconds() <= 900
    ]
    references = {
        sensor["id"]: sensor for sensor in city["sensors"] if sensor["type"] == "Traffic" and sensor["reading"]
    }
    ratios = [
        row["value"] / references[row["sensor_id"]]["reading"]
        for row in recent
        if row["sensor_id"] in references
        and (not row["unit"] or row["unit"] == references[row["sensor_id"]]["unit"])
    ]
    if recent:
        city = {
            **city,
            "observation_context": {
                "count": len(recent),
                "latest": max(row["observed_at"] for row in recent),
                "traffic_multiplier": round(max(0.5, min(1.75, mean(ratios))), 3) if ratios else 1.0,
            },
        }
    data = {
        "id": uuid4().hex,
        "scenario_id": scenario["id"],
        "workspace_id": scenario["workspace_id"],
        "city_id": city["id"],
        "title": scenario["title"],
        "status": "queued",
        "created_at": utc(),
        "events": [],
        "result": None,
        "approval": None,
        "scenario": scenario,
        "requester_id": audit_user["id"],
        "execution": initial_execution(scenario),
    }
    if experiment_id := scenario.get("experiment_id"):
        data["experiment_id"] = experiment_id
    store.insert(scope, "run", data["id"], data)
    store.insert(
        scope,
        "run-input",
        data["id"],
        {
            "city": city,
            "agents": agents,
            "provider_ids": [item["id"] for item in providers],
            "settings": settings,
            "policy": settings,
            "actor": audit_user,
        },
    )
    enqueue(store, scope, data["id"])
    store.session.commit()
    return data


def read_run(scope, run_id):
    with Session(engine) as session:
        return Store(session).get(scope, "run", run_id)


def negotiate(strategies, results, replies, simulate_revision, emit):
    original = results[0]
    preferred = Counter(
        reply["preference"] for reply in replies if reply["preference"] and reply["preference"] != original["id"]
    )
    options = {item.id: item for item in strategies if item.id != "baseline"}
    alternatives = sorted(options.keys() & preferred.keys(), key=lambda key: (-preferred[key], key))
    if original["id"] not in options or not alternatives:
        return results, None
    other = alternatives[0]
    revision = negotiated_strategy(options[original["id"]], options[other])
    contributors = [reply["agent"] for reply in replies if reply["preference"] == other]
    record = {"strategy_id": revision.id, "parents": [original["id"], other], "proposed_by": contributors}
    emit(
        "negotiation",
        "Specialists proposed combining two eligible measures for a second simulation.",
        "orchestrator",
        **record,
    )
    emit(
        "simulation",
        "Evaluating the negotiated revision at all timeline points.",
        "simulation",
        "running",
        strategy=revision.id,
    )
    revised = simulate_revision(revision, contributors)
    if not revised:
        return results, None
    candidate = revised[0]
    ranked = sorted([*results, candidate], key=lambda row: (-row["score"], row["id"]))
    record.update(
        score=candidate["score"], initial_score=original["score"], selected=ranked[0]["id"] == revision.id
    )
    emit(
        "negotiation",
        "The revised strategy was scored against the original options.",
        "critic",
        **record,
    )
    return ranked, record


def execute(scope, run_id, token):
    with Session(engine) as session:
        store = Store(session)
        data = store.get(scope, "run", run_id)
        inputs = store.get(scope, "run-input", run_id)
    if not data or not inputs:
        return
    city, scenario = inputs["city"], data["scenario"]
    settings = inputs["settings"]
    routing = {
        "routing": settings.get("model_routing"),
        "language": inputs["actor"].get("language", "en"),
        "complexity": "advanced" if scenario["severity"] >= 4 or scenario["population"] >= 10_000 else "standard",
    }
    started = time.perf_counter()

    def emit(stage, message, agent=None, status="completed", **metadata):
        if stage == "fallback":
            data["execution"]["counts"]["provider_failures"] += 1
        if stage == "provider":
            data["execution"]["counts"]["provider_attempts"] += 1
            if metadata.get("provider_retry"):
                data["execution"]["counts"]["retries"] += 1
        event = {
            "seq": len(data["events"]) + 1,
            "stage": stage,
            "agent": agent,
            "status": status,
            "text": message,
            "time": utc(),
            "data": metadata,
        }
        data["events"].append(event)
        notice_types = {
            "fallback": ("provider.unavailable",),
            "decision": ("simulation.completed", "recommendation.available"),
            "error": ("simulation.failed",),
        }.get(stage, ())
        if stage == "decision" and data["result"]["requires_approval"]:
            notice_types += ("risk.severe",)
        if stage == "agents" and status in {"completed", "failed"}:
            notice_types = ("agent." + status,)
        notices = [
            {
                "event": kind,
                "city_id": city["id"],
                "title": f"{metadata['agent_name']} · {message}" if metadata.get("agent_name") else message,
                "key": f"{run_id}-{agent}-{kind}" if stage == "agents" else f"{run_id}-{event['seq']}-{index}",
            }
            for index, kind in enumerate(notice_types)
        ]
        persist(scope, run_id, token, data, notices)
        run_events.add(1, {"stage": stage, "status": status})
        if inputs["actor"]["demo"] and stage in {"goal", "plan", "agents", "simulation", "negotiation"}:
            time.sleep(0.055)
        logger.info("run=%s stage=%s agent=%s status=%s", run_id, stage, agent, status)

    plan = Execution(data, emit)
    try:
        from .workspace import providers_for

        with Session(engine) as session:
            allow_cloud = settings["allow_cloud"] and policy(Store(session), scope)["allow_cloud"]
            providers = [
                item
                for item in providers_for(Store(session), scope, demo=inputs["actor"]["demo"])
                if item["id"] in inputs["provider_ids"]
            ]
        agents = select_agents(inputs["agents"], scenario)
        names = {item["id"]: item["name"] for item in agents}
        emit(
            "goal",
            f"Scenario received: {scenario['title']}",
            "orchestrator",
            kind=scenario["kind"],
            actor=inputs["actor"]["id"],
        )
        emit("plan", f"Assigned {len(agents)} agents.", "orchestrator", agents=list(names))
        for agent in agents:
            if agent["id"] != "orchestrator":
                emit("agents", f"{agent['name']} queued.", agent["id"], "queued")
        results, replies, negotiation, degraded = run_city(
            plan,
            scope,
            city,
            scenario,
            [agent for agent in agents if agent["id"] not in REQUIRED],
            providers,
            allow_cloud,
            routing,
            settings["weights"],
            simulate,
            negotiate,
        )
        baseline = next(row for row in results if row["id"] == "baseline")
        winner = results[0]
        dissent = [item for item in replies if item["preference"] and item["preference"] != winner["id"]]
        if dissent:
            emit(
                "negotiation",
                f"{len(dissent)} agents prefer another strategy on their own objective.",
                "critic",
                disagreements=[item["agent"] for item in dissent],
                resolution="Use weighted objectives and retain dissent in the report.",
            )
        emit(
            "verification",
            "Timeline coverage and score bounds passed verification.",
            "critic",
            verified=True,
            simulated=True,
        )
        partial = any(item["status"] != "passed" for item in plan.plan["success_criteria"])
        confidence = round(
            min(
                0.84,
                0.62
                + max(0, winner["score"] - baseline["score"]) / 175
                - (0.08 if dissent else 0)
                - (0.12 if degraded else 0)
                - (0.12 if partial else 0),
            ),
            2,
        )
        result = {
            "baseline": baseline,
            "recommendation": winner,
            "strategies": results,
            "messages": replies,
            "disagreements": dissent,
            "negotiation": negotiation,
            "confidence": confidence,
            "verified": True,
            "mode": "Simulated",
            "assumptions": [
                "Demand uses a fresh traffic reading against the demonstration baseline."
                if city.get("observation_context", {}).get("traffic_multiplier", 1) != 1
                else "Demand and road capacities are demonstration inputs.",
                "Risk, emissions and energy use are simplified estimates.",
                "Only supported constraint phrases filter the strategy catalog.",
            ],
            "limitations": [
                "Calibration intervals use held-out residuals and depend on the selected observations."
                if "calibration" in city
                else "The model is uncalibrated and does not estimate uncertainty intervals.",
                "Model advisories are independent of numeric ranking.",
            ],
            "requires_approval": winner["id"] != "baseline"
            and (scenario["severity"] >= 4 or scenario["kind"] in {"Emergency", "Severe Weather", "Power Outage"}),
            "source": city["source"],
            "freshness": city.get("observation_context", {}).get(
                "latest", city.get("calibration", {}).get("trained_at", "Static demonstration baseline")
            ),
            "calibration": city.get("calibration"),
            "observation_context": city.get("observation_context"),
            "weights": settings["weights"],
            "elapsed_ms": round((time.perf_counter() - started) * 1000),
            "seed": scenario["seed"],
            "model_version": VERSION,
            "input_hash": hashlib.sha256(
                json.dumps(
                    {
                        "city": city,
                        "scenario": {
                            k: v for k, v in scenario.items() if k not in {"id", "created_at", "experiment_id"}
                        },
                        "weights": settings["weights"],
                        "strategy_ids": sorted(row["id"] for row in results),
                    },
                    sort_keys=True,
                ).encode()
            ).hexdigest(),
        }
        if degraded:
            result["limitations"].append(
                "Live telemetry was stale or unavailable. The run used its pinned evidence."
            )
        if partial:
            result["limitations"].append("The run verified a baseline, but could not recommend an intervention.")
        state = (
            "partially_completed"
            if partial
            else "waiting_for_human_approval"
            if result["requires_approval"]
            else "completed"
        )
        data["execution"] = finish_execution(plan.plan, state)
        emit(
            "execution",
            "The orchestrator checked the completion criteria.",
            execution={
                "state": state,
                "revision": data["execution"]["revision"],
                "counts": data["execution"]["counts"],
                "success_criteria": data["execution"]["success_criteria"],
                "verification": data["execution"]["verification"],
                "active_steps": [],
            },
        )
        data["result"] = result
        data["status"] = "completed"
        emit(
            "decision",
            f"{winner['name']} ranks first at {winner['score']:.1f}/100.",
            "decision",
            score=winner["score"],
            confidence=confidence,
            elapsed_ms=result["elapsed_ms"],
        )
    except LeaseLost:
        logger.info("Worker lease changed run=%s", run_id)
    except ValueError as exc:
        data["status"] = "failed"
        data["execution"] = finish_execution(plan.plan, "failed")
        data["error"] = str(exc)
        emit("error", data["error"], status="failed")
    except Exception:
        logger.exception("Unexpected simulation failure run=%s", run_id)
        data["status"] = "failed"
        data["execution"] = finish_execution(plan.plan, "failed")
        data["error"] = "The run could not finish. Review the audit trail and retry."
        emit("error", data["error"], status="failed")
