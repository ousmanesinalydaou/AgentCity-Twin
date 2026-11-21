"""Independent checks of simulator output before it can influence a decision."""

import math
import re
from collections import Counter

from ..domain import DIMENSIONS
from .engine import TIMES

METRICS = {
    "congestion",
    "travelDelay",
    "transitDelay",
    "emissions",
    "safetyRisk",
    "energyLoad",
    "trips",
    "sensorCoverage",
}


def number(value, low=-math.inf, high=math.inf):
    return type(value) in {float, int} and math.isfinite(value) and low <= value <= high


def constraint_clauses(text):
    supported = {
        "no reroute",
        "no diversion",
        "no closure",
        "no restriction",
        "no additional transit",
        "no transit expansion",
        "no advisory",
    }
    clauses = [item.strip() for item in re.split(r"[,;.!?\n]|\band\b", text.lower()) if item.strip()]
    return [item for item in clauses if item not in supported]


def inspect_candidates(city, candidates, expected_ids, weights):
    routes = Counter(
        (f"{start}-{end}", tuple(tuple(point) for point in [city["nodes"][start], *shape, city["nodes"][end]]))
        for start, end, _, _, shape in city["edges"]
    )
    accepted = set()
    issues = {}
    for candidate in candidates:
        if not isinstance(candidate, dict) or not isinstance(candidate.get("id"), str):
            issues["unknown"] = "Invalid candidate schema"
            continue
        key = candidate["id"]
        if key in accepted or key in issues:
            issues[key] = "Duplicate candidate"
        elif key not in expected_ids:
            issues[key] = "Candidate is outside the permitted strategy set"
        else:
            try:
                check_candidate(candidate, routes, weights)
            except (KeyError, TypeError, ValueError, AttributeError) as error:
                issues[key] = str(error) if isinstance(error, ValueError) else "Incomplete simulation evidence"
            else:
                accepted.add(key)
    for key in expected_ids - accepted - issues.keys():
        issues[key] = "Missing simulation result"
    return issues


def check_candidate(candidate, routes, weights):
    frames = candidate["timeline"]
    if tuple(frame["minute"] for frame in frames) != TIMES:
        raise ValueError("Timeline points do not match the simulation contract")
    if not candidate["name"] or not candidate["summary"]:
        raise ValueError("Missing strategy description")
    for frame in frames:
        if not METRICS <= frame["metrics"].keys() or not all(number(val) for val in frame["metrics"].values()):
            raise ValueError("Missing or nonnumeric outcome metrics")
        axes = frame["axes"]
        if set(axes) != set(DIMENSIONS) or not all(number(value, 0, 100) for value in axes.values()):
            raise ValueError("Invalid decision objectives")
        weighted = round(sum(axes[key] * weights[key] for key in DIMENSIONS) / sum(weights.values()), 2)
        if not number(frame["score"], 0, 100) or frame["score"] != weighted:
            raise ValueError("The frame score does not reconcile with the objectives")
        seen = Counter()
        for flow in frame["flows"]:
            route = (flow["id"], tuple(tuple(point) for point in flow["coordinates"]))
            seen[route] += 1
            if (
                seen[route] > routes[route]
                or not number(flow["pressure"], 0, 100)
                or type(flow["affected"]) is not bool
            ):
                raise ValueError("A simulated route is invalid or absent from the road graph")
        if seen != routes:
            raise ValueError("The simulated road graph is incomplete")
    score = round(sum(frames[index]["score"] * weight for index, weight in ((1, 0.25), (2, 0.45), (3, 0.30))), 2)
    if not number(candidate["score"], 0, 100) or candidate["score"] != score:
        raise ValueError("The strategy score does not reconcile with its timeline")


def inspect_findings(findings, selected, candidates):
    if {item["agent"] for item in findings} != set(selected) or len(findings) != len(selected):
        return False
    index = {item["id"]: item for item in candidates}
    for item in findings:
        preference = item["preference"]
        if (
            (preference and preference not in index)
            or not item["evidence"]
            or not number(item["confidence"], 0, 1)
        ):
            return False
        if measurement := item.get("measurement"):
            try:
                frame = next(
                    row for row in index[preference]["timeline"] if row["minute"] == measurement["minute"]
                )
                if frame[measurement["source"]][measurement["metric"]] != measurement["value"]:
                    return False
            except (KeyError, StopIteration):
                return False
    return True
