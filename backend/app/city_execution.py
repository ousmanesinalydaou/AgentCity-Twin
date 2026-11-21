"""Execute the dependency-ordered city analysis with bounded verification repairs."""

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from .agent_tasks import compare_objectives, observe, plan_specialists, request_advisory
from .db import Store, engine, now
from .geospatial import supports_network
from .simulation.engine import scenario_strategies
from .simulation.verification import constraint_clauses, inspect_candidates, inspect_findings
from .telemetry import city_readings


def city_inventory(city):
    if not city["edges"] or not city["demand"] or not supports_network(city["edges"], city["demand"]):
        raise ValueError("The road graph cannot connect the scenario demand pairs.")
    return {"roads": len(city["edges"]), "sensors": len(city["sensors"]), "routes": len(city["transit"])}


def read_freshness(scope, city_id):
    from datetime import datetime

    with Session(engine) as session:
        readings = city_readings(Store(session), scope, city_id)
    stamp = now()
    observations = [row for row in readings if row["source"] != "Simulated" and row["value"] is not None]
    fresh = [
        row["observed_at"]
        for row in observations
        if 0 <= (stamp - datetime.fromisoformat(row["observed_at"])).total_seconds() <= 900
    ]
    return {"fresh": len(fresh), "stale": len(observations) - len(fresh), "latest": max(fresh, default=None)}


def prepare(plan, scope, city, scenario, steps):
    plan.update("executing", "Checking the scoped network and observation sources.")
    plan.call(
        steps["graph"],
        lambda: city_inventory(city),
        lambda inventory: observe("Road graph connectivity and the city inventory were checked.", **inventory),
    )
    limits = plan.call(
        steps["constraints"],
        lambda: constraint_clauses(scenario["constraints"]),
        lambda unknown: observe(
            "Unrecognized constraints require a baseline-only comparison."
            if unknown
            else "Scenario constraints were checked.",
            status="warning" if unknown else "success",
            unsupported=len(unknown),
        ),
    )
    feed_step = steps["observations"]
    plan.update("executing", "Reading telemetry freshness for this city.")
    for attempt in range(2):
        try:
            freshness = plan.call(
                feed_step,
                lambda: read_freshness(scope, city["id"]),
                lambda info: observe(
                    "Telemetry freshness was checked.",
                    status="warning" if info["stale"] and not info["fresh"] else "success",
                    **info,
                ),
            )
            if not freshness["fresh"] and not freshness["stale"]:
                plan.update(
                    "observing",
                    "The simulation uses the recorded demonstration inputs.",
                    source=city["source"],
                )
            return limits, bool(freshness["stale"] and not freshness["fresh"])
        except SQLAlchemyError:
            if not attempt:
                plan.update("replanning", "The telemetry query failed. Retrying once.")
    snapshot = plan.add(
        "cached-observations",
        "data",
        "pinned-city-snapshot",
        "Recover with the city inputs saved at queue time.",
        ["graph"],
    )
    plan.publish("The live query failed. The plan switched to the pinned city snapshot.", replan=True)
    plan.call(
        snapshot,
        lambda: city.get("observation_context"),
        lambda info: observe(
            "The analysis retained its pinned inputs.",
            status="warning",
            latest=info["latest"] if info else None,
            source=city["source"],
        ),
    )
    return limits, True


def checked_simulation(plan, city, scenario, strategies, weights, simulate, step):
    expected = {item.id for item in strategies}

    def run_model():
        return simulate(city, scenario, strategies, weights)

    rows = plan.call(
        step,
        run_model,
        lambda result: observe("The network model returned candidates.", candidates=len(result)),
    )
    check = plan.add(
        step["id"] + "-check",
        "critic",
        "simulation-verifier",
        "Independently verify routes, scores, and timeline.",
        [step["id"]],
    )

    def review(review_step, candidates, identifiers):
        plan.update("verifying", "The Critic is checking the simulator evidence.")
        return plan.call(
            review_step,
            lambda: inspect_candidates(city, candidates, identifiers, weights),
            lambda faults: observe(
                "The Critic rejected invalid or missing candidates."
                if faults
                else "The candidate evidence passed verification.",
                status="warning" if faults else "success",
                faults=faults,
            ),
        )

    issues = review(check, rows, expected)
    if not issues:
        return rows, []
    plan.update(
        "replanning",
        "The Critic rejected a candidate. The simulator will recompute the valid strategy set.",
        agent="critic",
        rejected=issues,
    )
    repair = plan.add(
        step["id"] + "-repair",
        "simulation",
        "network-simulator",
        "Recompute the strategy set after independent rejection.",
        [check["id"]],
    )
    verify = plan.add(
        step["id"] + "-recheck",
        "critic",
        "simulation-verifier",
        "Verify the corrected simulation.",
        [repair["id"]],
    )
    plan.publish("The orchestrator added a corrective simulation and verification.", replan=True)
    rows = plan.call(
        repair,
        run_model,
        lambda result: observe("The corrected simulation returned.", candidates=len(result)),
    )
    bad = review(verify, rows, expected)
    if "baseline" in bad:
        plan.plan["verification"] = {"status": "failed", "checked_by": "critic", "rejected": sorted(bad)}
        raise ValueError("Independent verification could not confirm the baseline.")
    safe = [
        row for row in rows if isinstance(row, dict) and isinstance(row.get("id"), str) and row["id"] not in bad
    ]
    return safe, sorted(issues.keys() | bad.keys())


def run_city(
    plan, scope, city, scenario, specialists, providers, allow_cloud, routing, weights, simulate, negotiate
):
    steps = {
        "graph": plan.add("graph", "data", "road-network", "Check the road graph and city inventory."),
        "observations": plan.add(
            "observations",
            "data",
            "city-readings",
            "Inspect current sensor freshness.",
            ["graph"],
        ),
        "constraints": plan.add(
            "constraints", "orchestrator", "constraint-check", "Check the scenario constraints."
        ),
        "simulation": plan.add(
            "simulation",
            "simulation",
            "network-simulator",
            "Simulate permitted strategies.",
            ["graph", "constraints"],
        ),
    }
    objectives = plan_specialists(plan, specialists)
    advisory_steps = {
        agent["id"]: plan.add(
            "advisory-" + agent["id"],
            agent["id"],
            "model-gateway",
            "Request a structured specialist advisory.",
            [objectives[agent["id"]]["id"]],
        )
        for agent in specialists
        if providers and "model-gateway" in agent.get("tools", [])
    }
    verification = plan.add(
        "verify-findings",
        "critic",
        "evidence-verifier",
        "Verify the delegated findings.",
        [advisory_steps.get(key, step)["id"] for key, step in objectives.items()] or ["simulation"],
    )
    decision = plan.add(
        "rank", "decision", "weighted-ranking", "Rank the verified strategies.", ["verify-findings"]
    )
    plan.publish("The orchestrator created a dependency-ordered task plan.")
    unsupported, degraded = prepare(plan, scope, city, scenario, steps)
    strategies = scenario_strategies(scenario)
    if unsupported:
        strategies = strategies[:1]
        plan.publish("The plan limited the run to the baseline for human review.", replan=True)
    plan.emit(
        "simulation",
        f"Evaluating {len(strategies)} strategies across five time points.",
        "simulation",
        "running",
        strategies=[item.id for item in strategies],
        seed=scenario["seed"],
    )
    results, rejected = checked_simulation(
        plan, city, scenario, strategies, weights, simulate, steps["simulation"]
    )
    if not any(
        flow["affected"]
        for flow in next(row for row in results if row["id"] == "baseline")["timeline"][0]["flows"]
    ):
        plan.emit("warning", "The selected area does not overlap a modeled corridor.", "critic")
        results = [row for row in results if row["id"] == "baseline"]
        plan.publish(
            "The plan retained only the baseline because the incident is outside the network.", replan=True
        )
    plan.emit("simulation", "Network simulation complete.", "simulation", results=len(results))
    opinions = compare_objectives(plan, objectives, city, results)
    findings = []
    for agent in specialists:
        actor = agent["id"]
        rule = opinions[actor]
        empty = {
            "advisory": None,
            "comparison": None,
            "execution": {
                "provider": "deterministic",
                "model": "City rules",
                "execution": "Local",
                "advisory_status": "not_requested",
            },
        }
        model = empty
        if actor in advisory_steps:
            model = plan.call(
                advisory_steps[actor],
                lambda agent=agent, rule=rule: request_advisory(
                    agent, rule, results, scenario, providers, allow_cloud, routing, plan.emit
                ),
                lambda outcome: observe(
                    "Model execution receipt recorded.",
                    status="warning" if outcome["execution"].get("advisory_status") == "failed" else "success",
                    execution=outcome["execution"],
                ),
            )
        findings.append({"agent": actor, "name": agent["name"], **rule, **model})
        failed = model["execution"].get("advisory_status") == "failed"
        plan.emit(
            "agents",
            "The model advisory failed. The rule-based finding was retained." if failed else rule["summary"],
            actor,
            "failed" if failed else "completed",
            agent_name=agent["name"],
            evidence=rule["evidence"],
            preference=rule["preference"],
            confidence=rule["confidence"],
            execution=model["execution"],
        )

    def simulate_revision(revision, contributors):
        step = plan.add(
            "revision-simulation",
            "simulation",
            "network-simulator",
            "Test the negotiated revision.",
            [item["id"] for item in objectives.values()],
        )
        plan.plan["counts"]["delegations"] += 1
        plan.update(
            "waiting_for_agent",
            "Specialists delegated the combined strategy to the simulation agent.",
            agent=contributors[0],
            delegated_to="simulation",
            requested_by=contributors,
            step_id=step["id"],
        )
        plan.publish("The plan added a second simulation for specialist dissent.", replan=True)
        revised, dropped = checked_simulation(plan, city, scenario, [revision], weights, simulate, step)
        rejected.extend(dropped)
        return revised

    results, negotiation = negotiate(strategies, results, findings, simulate_revision, plan.emit)
    passed = plan.call(
        verification,
        lambda: inspect_findings(findings, opinions, results),
        lambda result: observe(
            "The Critic checked the source, confidence, and candidate references of specialist findings.",
            status="success" if result else "warning",
            passed=result,
        ),
    )
    if not passed:
        repair_steps = plan_specialists(plan, specialists, prefix="recheck")
        plan.publish("The Critic requested a fresh comparison of the verified strategies.", replan=True)
        corrected = compare_objectives(plan, repair_steps, city, results)
        findings = [
            {**item, **corrected[item["agent"]], "advisory": None, "comparison": None} for item in findings
        ]
        passed = plan.call(
            verification,
            lambda: inspect_findings(findings, corrected, results),
            lambda result: observe(
                "The Critic checked the corrected specialist evidence.",
                status="success" if result else "warning",
                passed=result,
            ),
        )
    if not passed:
        plan.plan["verification"] = {"status": "failed", "checked_by": "critic", "rejected": sorted(set(rejected))}
        raise ValueError("Independent verification could not confirm the specialist evidence.")
    ranked = plan.call(
        decision,
        lambda: sorted(results, key=lambda item: (-item["score"], item["id"])),
        lambda options: observe(
            "The decision agent ranked verified outcomes.", ranking=[item["id"] for item in options]
        ),
    )
    plan.plan["verification"] = {"status": "passed", "checked_by": "critic", "rejected": sorted(set(rejected))}
    criteria = {"alternatives": len(ranked) > 1, "constraints": not unsupported}
    for criterion in plan.plan["success_criteria"]:
        criterion["status"] = "passed" if criteria.get(criterion["id"], True) else "unmet"
    for item in findings:
        steps = [step for step in plan.plan["steps"] if step["agent"] == item["agent"]]
        item["task"] = {
            "state": "partially_completed"
            if item["execution"].get("advisory_status") == "failed"
            else "completed",
            "goal": next(agent["description"] for agent in specialists if agent["id"] == item["agent"]),
            "actions_taken": [step["id"] for step in steps if step["attempts"]],
            "tools_used": sorted({step["tool"] for step in steps if step["attempts"]}),
            "observations": [
                {
                    "step": step["id"],
                    "status": step["observation"]["status"],
                    "summary": step["observation"]["summary"],
                }
                for step in steps
                if step["observation"]
            ],
            "verification": {"status": "passed", "checked_by": "critic"},
        }
    return ranked, findings, negotiation, degraded
