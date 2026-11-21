from copy import deepcopy

AGENTS = [
    ("orchestrator", "City Orchestrator", "Assign work and sequence the analysis.", "cyan"),
    ("traffic", "Traffic Agent", "Minimize modeled congestion and road delay.", "blue"),
    ("mobility", "Mobility Agent", "Maintain accessible, reliable public transport.", "violet"),
    ("environment", "Environment Agent", "Reduce exposure and modeled emissions.", "green"),
    ("safety", "Safety Agent", "Protect essential access and reduce modeled risk.", "orange"),
    ("campus", "Campus Agent", "Evaluate campus access and pedestrian demand.", "indigo"),
    ("energy", "Energy Agent", "Preserve capacity for essential facilities.", "yellow"),
    ("data", "Data Retrieval Agent", "Identify the inputs available for this city.", "cyan"),
    ("sensor", "Sensor Agent", "Assess telemetry coverage and uncertainty.", "green"),
    ("communication", "Communication Agent", "Summarize impacts for operators and the public.", "blue"),
    ("simulation", "Simulation Agent", "Evaluate strategies on the network.", "violet"),
    ("critic", "Critic / Verifier", "Check scores, coverage, and assumptions.", "orange"),
    ("decision", "Decision Agent", "Rank verified strategies using workspace weights.", "cyan"),
]
REGISTRY = [
    {
        "id": key,
        "name": name,
        "description": description,
        "color": color,
        "enabled": True,
        "preferred": "",
        "fallbacks": [],
        "temperature": 0.2,
        "timeout": 20,
        "tools": ["city-model", "simulation-metrics", "model-gateway"],
        "allowed_data": ["simulation-scores", "aggregate-city-data"],
        "priority": i,
        "max_iterations": 1,
        "instruction": f"You are the {name}. {description}",
    }
    for i, (key, name, description, color) in enumerate(AGENTS)
]
REQUIRED = {"orchestrator", "data", "simulation", "critic", "decision"}
PROFILE = {
    "Emergency": {"traffic", "mobility", "environment", "safety", "campus"},
    "Road Closure": {"traffic", "mobility", "safety"},
    "Campus Event": {"traffic", "mobility", "campus", "safety", "communication"},
    "Football Match": {"traffic", "mobility", "safety", "communication"},
    "Pollution Spike": {"environment", "sensor", "safety"},
    "Severe Weather": {"traffic", "safety", "environment", "sensor"},
    "Transit Failure": {"traffic", "mobility", "communication"},
    "Construction": {"traffic", "mobility", "environment", "safety"},
    "Power Outage": {"energy", "sensor", "safety", "communication"},
    "Public Gathering": {"traffic", "mobility", "safety", "communication"},
}


def registry(store, scope):
    overrides = {item["id"]: item for item in store.list(scope, "agent")}
    return [{**deepcopy(agent), **overrides.get(agent["id"], {})} for agent in REGISTRY]


def select_agents(agents, scenario):
    candidates = set(scenario["agent_ids"]) if scenario.get("agent_ids") is not None else PROFILE[scenario["kind"]]
    return sorted(
        (item for item in agents if item["id"] in REQUIRED or (item["id"] in candidates and item["enabled"])),
        key=lambda item: item["priority"],
    )


OBJECTIVES = {
    "traffic": ("congestion", "min", "lowest modeled congestion"),
    "mobility": ("transitDelay", "min", "least transit delay"),
    "environment": ("emissions", "min", "lowest estimated change in emissions"),
    "safety": ("safetyRisk", "min", "lowest modeled safety risk"),
    "campus": ("accessibility", "max", "best accessibility score"),
    "energy": ("energyLoad", "min", "lowest modeled energy load"),
}


def finding(agent, city, candidates):
    ranked = [item for item in candidates if item["id"] != "baseline"] or candidates
    if agent in OBJECTIVES:
        latest = [(item, item["timeline"][2]) for item in ranked]
        metric, direction, reason = OBJECTIVES[agent]
        selector = min if direction == "min" else max
        key = "axes" if metric == "accessibility" else "metrics"
        candidate, time = selector(latest, key=lambda pair: pair[1][key][metric])
        return {
            "preference": candidate["id"],
            "summary": f"{candidate['name']} has the {reason}.",
            "evidence": f"{metric} at +30 min: {time[key][metric]}",
            "measurement": {"metric": metric, "value": time[key][metric], "minute": time["minute"], "source": key},
            "confidence": 0.78,
        }
    if agent == "sensor":
        offline = sum(not item["online"] for item in city["sensors"])
        return {
            "preference": "",
            "summary": f"{offline} of {len(city['sensors'])} sensors are offline.",
            "evidence": "Sensor inventory in the run snapshot",
            "confidence": 0.7,
        }
    return {
        "preference": ranked[0]["id"],
        "summary": "Draft a disruption advisory for operator review.",
        "evidence": "Simulation scope and response timeline",
        "confidence": 0.75,
    }
