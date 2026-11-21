"""Specialist dispatch and the advisory tool boundary for a city simulation."""

import json
from concurrent.futures import ThreadPoolExecutor, as_completed

from .agents import finding
from .ai.gateway import advise

SPECIALIST_TOOLS = {
    "traffic": "traffic-comparison",
    "mobility": "transit-comparison",
    "environment": "emissions-comparison",
    "safety": "risk-comparison",
    "campus": "accessibility-comparison",
    "energy": "energy-comparison",
    "sensor": "sensor-inventory",
    "communication": "advisory-preparation",
}


def observe(summary, *, status="success", **evidence):
    return {"status": status, "summary": summary, **evidence}


def plan_specialists(execution, agents, *, after="simulation-check", prefix="objective"):
    return {
        agent["id"]: execution.add(
            f"{prefix}-{agent['id']}",
            agent["id"],
            SPECIALIST_TOOLS[agent["id"]],
            "Evaluate the specialist objective.",
            [after],
        )
        for agent in agents
    }


def compare_objectives(execution, stages, city, results):
    if not stages:
        return {}
    execution.plan["counts"]["delegations"] += len(stages)
    execution.update(
        "waiting_for_agent",
        "The orchestrator delegated independent comparisons.",
        tasks=[{"agent": agent, "step": step["id"], "tool": step["tool"]} for agent, step in stages.items()],
    )
    opinions = {}
    with ThreadPoolExecutor(max_workers=min(4, len(stages))) as pool:
        pending = {}
        for agent, step in stages.items():
            started = execution.begin(step)
            pending[pool.submit(finding, agent, city, results)] = agent, step, started
        for future in as_completed(pending):
            agent, step, started = pending[future]
            try:
                rule = future.result()
            except Exception:
                execution.observed(
                    step, started, observe("Specialist comparison failed.", status="error"), failed=True
                )
                raise
            execution.observed(
                step,
                started,
                observe("Specialist comparison completed.", finding=rule),
            )
            opinions[agent] = rule
    return opinions


def request_advisory(agent, rule, results, scenario, providers, allow_cloud, routing, emit):
    allowed = agent.get("allowed_data", [])
    shared_scores = "simulation-scores" in allowed
    aggregate = "aggregate-city-data" in allowed
    prompt = json.dumps(
        {
            "task": scenario["kind"] if aggregate else "urban disruption",
            "duration_minutes": scenario["duration"] if aggregate else None,
            "rule_result": rule if shared_scores else None,
            "strategies": [
                {"id": item["id"], "score": item["score"] if shared_scores else None} for item in results
            ],
        }
    )
    eligible_ids = {item["id"] for item in results}
    eligible = [{**provider, "timeout": min(provider["timeout"], agent["timeout"])} for provider in providers]

    def recorder():
        attempted = False

        def log(stage, message, **details):
            nonlocal attempted
            retry = stage == "provider" and attempted
            attempted |= stage == "provider"
            emit(stage, message, agent["id"], provider_retry=retry, **details)

        return log

    advisory, metadata = advise(
        eligible,
        agent,
        prompt,
        allow_cloud,
        scenario.get("provider_id"),
        recorder(),
        allowed_preferences=eligible_ids,
        **routing,
    )
    comparison = None
    if preferred := scenario.get("compare_provider_id"):
        second = [item for item in eligible if item["id"] == preferred]
        response, receipt = advise(
            second,
            agent,
            prompt,
            allow_cloud,
            preferred,
            recorder(),
            allowed_preferences=eligible_ids,
            **routing,
        )
        if response:
            comparison = {"advisory": response, "execution": receipt}
    return {"advisory": advisory, "execution": metadata, "comparison": comparison}
