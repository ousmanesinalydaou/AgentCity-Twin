import heapq
import math
import random
from collections import Counter
from datetime import datetime
from itertools import pairwise

from ..domain import DIMENSIONS
from .calibration import correct
from .catalog import BASELINE, PROFILES, STRATEGIES

TIMES = (0, 15, 30, 60, 120)
VERSION = "network-1.1"


def clamp(number):
    return min(100, max(0, number))


def distance(a, b):
    return 111_195 * math.hypot((a[0] - b[0]) * math.cos(math.radians((a[1] + b[1]) / 2)), a[1] - b[1])


def shortest(graph, origin, destination, times):
    queue = [(0, origin, ())]
    visited = set()
    while queue:
        time, node, path = heapq.heappop(queue)
        if node in visited:
            continue
        if node == destination:
            return path
        visited.add(node)
        for neighbor, index in graph.get(node, []):
            if neighbor not in visited:
                heapq.heappush(queue, (time + times[index], neighbor, (*path, index)))
    return ()


def scenario_strategies(scenario):
    choices = [STRATEGIES[key] for key in PROFILES[scenario["kind"]]]
    constraints = scenario["constraints"].lower()
    restrictions = {
        "routing": ("no reroute", "no diversion"),
        "restriction": ("no closure", "no restriction"),
        "transit": ("no additional transit", "no transit expansion"),
        "demand": ("no advisory",),
    }
    allowed = [
        option
        for option in choices
        if not any(term in constraints for term in restrictions.get(option.measure, ()))
    ]
    return [BASELINE, *allowed]


def demand_level(scenario, minute):
    start = scenario.get("starts_at")
    if not start:
        hour = 17
    else:
        parsed = datetime.fromisoformat(start)
        hour = parsed.hour + parsed.minute / 60
    hour = (hour + minute / 60) % 24
    factor = 1.08 if 7 <= hour < 9.5 or 16 <= hour < 18.5 else 0.85 if 6 <= hour < 22 else 0.53
    return factor * (1 - min(0.28, minute / 430))


def frame(city, scenario, option, minute, weights):
    nodes, edges = city["nodes"], city["edges"]
    if not edges or not city["demand"]:
        raise ValueError("This city needs a connected road graph and demand pairs before it can be simulated.")
    rng = random.Random(scenario["seed"])
    jitter = [rng.uniform(0.95, 1.05) for _ in city["demand"]]
    point = scenario["coordinates"]
    radius = scenario["radius"]
    graph = {}
    free, capacity, influence = [], [], []
    active = 1.0 if minute <= scenario["duration"] else 0.34
    criticality = scenario["severity"] / 5 * active
    rollout = min(1, 0.27 + minute / 34) if option.id != "baseline" else 0
    peak = demand_level(scenario, minute) * city.get("observation_context", {}).get("traffic_multiplier", 1.0)
    for index, (a, b, minutes, cap, shape) in enumerate(edges):
        graph.setdefault(a, []).append((b, index))
        graph.setdefault(b, []).append((a, index))
        points = [nodes[a], *shape, nodes[b]]
        midpoints = [[(p[0] + q[0]) / 2, (p[1] + q[1]) / 2] for p, q in pairwise(points)]
        impact = max(0.0, 1 - min(distance(point, spot) for spot in [*points, *midpoints]) / radius)
        influence.append(impact)
        free.append(minutes)
        capacity.append(max(cap * 0.18, cap * (1 - impact * criticality * (0.96 - rollout * option.recovery))))
    flows = Counter()
    trips = total_minutes = undelayed = 0.0
    for iteration in range(3):
        times = [free[i] * (1 + min(8, 0.37 * (flows[i] / capacity[i]) ** 3)) for i in range(len(edges))]
        added = Counter()
        trips = total_minutes = undelayed = 0.0
        for i, (a, b, demand) in enumerate(city["demand"]):
            route = shortest(graph, a, b, times)
            if not route:
                continue
            population_factor = min(0.45, math.log1p(scenario["population"]) / 25) if scenario["population"] else 0
            group = demand * jitter[i] * peak * (1 + population_factor - option.demand * rollout)
            trips += group
            total_minutes += group * sum(times[i] for i in route)
            undelayed += group * sum(free[i] for i in route)
            for index in route:
                added[index] += group
        flows = Counter({i: (flows[i] * iteration + added[i]) / (iteration + 1) for i in range(len(edges))})
    loading = sum(min(3, flows[i] / capacity[i]) for i in range(len(edges))) / len(edges)
    delay = max(0, total_minutes - undelayed) / max(1, trips)
    transit_delay = max(0, delay * 0.62 + criticality * 5 - option.transit * rollout * 11)
    emissions = delay * 1.9 + criticality * 13 - option.demand * rollout * 34
    risk = clamp(24 + criticality * 67 + loading * 9 - option.protection * rollout * 75)
    metrics = dict(
        congestion=round(clamp(loading * 70 + delay * 1.65), 1),
        travelDelay=round(delay, 1),
        transitDelay=round(transit_delay, 1),
        emissions=round(emissions, 1),
        safetyRisk=round(risk, 1),
        energyLoad=round(clamp(65 + criticality * 25 - option.energy_relief * rollout * 25), 1),
        trips=round(trips),
        sensorCoverage=round(min(100, len(city["sensors"]) * 11.5)),
    )
    models = city.get("calibration", {}).get("metrics", {})
    if models:
        metrics, intervals = correct(metrics, models)
        delay, transit_delay, emissions, risk = (
            metrics[key] for key in ("travelDelay", "transitDelay", "emissions", "safetyRisk")
        )
    else:
        intervals = {}
    city_scores = [
        100 - metrics["congestion"],
        100 - transit_delay * 4,
        86 - emissions * 1.35,
        100 - risk,
        100 - option.cost,
        100 - option.complexity,
        50 + option.protection * 65 + option.recovery * 40,
        72 + option.transit * 30 - transit_delay * 2,
        92 - delay * 1.7 - risk * 0.28,
        86 - emissions * 1.15 + option.demand * 12,
    ]
    axes = {dimension: round(clamp(score), 1) for dimension, score in zip(DIMENSIONS, city_scores, strict=True)}
    score = sum(axes[key] * weights[key] for key in DIMENSIONS) / sum(weights.values())
    flows_data = [
        {
            "id": f"{a}-{b}",
            "coordinates": [nodes[a], *shape, nodes[b]],
            "pressure": round(clamp(flows[i] / capacity[i] * 65), 1),
            "affected": influence[i] > 0.2,
        }
        for i, (a, b, _, _, shape) in enumerate(edges)
    ]
    return {
        "minute": minute,
        "metrics": metrics,
        "intervals": intervals,
        "axes": axes,
        "score": round(score, 2),
        "flows": flows_data,
        "interventionActive": bool(rollout),
        "incidentPhase": "Active" if minute <= scenario["duration"] else "Recovery",
        "incidentIntensity": round(active * scenario["severity"] / 5, 3),
    }


def simulate(city, scenario, strategies, weights):
    candidates = []
    for strategy in strategies:
        frames = [frame(city, scenario, strategy, minute, weights) for minute in TIMES]
        # Compare capacity through the peak and immediate recovery period.
        score = round(sum(frames[i]["score"] * share for i, share in ((1, 0.25), (2, 0.45), (3, 0.3))), 2)
        candidates.append(
            {
                "id": strategy.id,
                "name": strategy.name,
                "summary": strategy.summary,
                "score": score,
                "timeline": frames,
            }
        )
    return sorted(candidates, key=lambda row: (-row["score"], row["id"]))
