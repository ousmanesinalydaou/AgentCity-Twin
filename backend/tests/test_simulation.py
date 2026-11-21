from app.city import DEBRECEN
from app.domain import DEFAULT_WEIGHTS
from app.simulation.engine import scenario_strategies, simulate

SCENARIO = {
    "kind": "Emergency",
    "constraints": "",
    "seed": 42,
    "coordinates": DEBRECEN["origin"],
    "severity": 4,
    "duration": 60,
    "population": 1200,
    "radius": 850,
}


def test_deterministic_intervention_comparison():
    options = scenario_strategies(SCENARIO)
    result = simulate(DEBRECEN, SCENARIO, options, DEFAULT_WEIGHTS)
    assert result == simulate(DEBRECEN, SCENARIO, options, DEFAULT_WEIGHTS)
    assert len(result) == 4
    assert [row["score"] for row in result] == sorted((row["score"] for row in result), reverse=True)
    baseline = next(row for row in result if row["id"] == "baseline")
    assert result[0]["score"] > baseline["score"]
    assert [frame["minute"] for frame in result[0]["timeline"]] == [0, 15, 30, 60, 120]
    assert result[0]["timeline"][2]["metrics"]["safetyRisk"] < baseline["timeline"][2]["metrics"]["safetyRisk"]


def test_constraints_and_experiment_seed_change_model():
    restriction = {**SCENARIO, "constraints": "No reroute, no closure"}
    assert [option.id for option in scenario_strategies(restriction)] == ["baseline", "notify"]
    options = scenario_strategies(SCENARIO)
    assert simulate(DEBRECEN, SCENARIO, options, DEFAULT_WEIGHTS) != simulate(
        DEBRECEN, {**SCENARIO, "seed": 94}, options, DEFAULT_WEIGHTS
    )
