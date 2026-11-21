"""Fit bounded correction factors from paired measurements and model results."""

from statistics import mean, quantiles

METRICS = ("congestion", "travelDelay", "transitDelay", "emissions", "safetyRisk", "energyLoad")
SCALED = {"congestion", "safetyRisk", "energyLoad"}


def feasible(metric, value):
    if metric in SCALED:
        return min(100, max(0, value))
    return value if metric == "emissions" else max(0, value)


def fit(rows):
    fitted = {}
    for metric in METRICS:
        pairs = [(row.modeled, row.observed) for row in rows if row.metric == metric]
        if not pairs:
            continue
        if len(pairs) < 10:
            raise ValueError("Each calibration metric needs at least ten paired observations.")
        split = int(len(pairs) * 0.75)
        training, validation = pairs[:split], pairs[split:]
        xbar, ybar = mean(x for x, _ in training), mean(y for _, y in training)
        variance = sum((x - xbar) ** 2 for x, _ in training)
        slope = (
            min(4, max(0.25, sum((x - xbar) * (y - ybar) for x, y in training) / variance)) if variance else 1.0
        )
        offset = ybar - slope * xbar
        errors = [y - feasible(metric, slope * x + offset) for x, y in validation]
        steps = quantiles(errors, n=20, method="inclusive")
        fitted[metric] = {
            "slope": round(slope, 6),
            "offset": round(offset, 6),
            "samples": len(pairs),
            "validation_samples": len(validation),
            "mae": round(mean(abs(e) for e in errors), 3),
            "lower_error": round(steps[0], 3),
            "upper_error": round(steps[-1], 3),
        }
    return fitted


def correct(metrics, calibration):
    values = dict(metrics)
    intervals = {}
    for metric, model in calibration.items():
        estimate = feasible(metric, metrics[metric] * model["slope"] + model["offset"])
        values[metric] = round(estimate, 1)
        intervals[metric] = [
            round(feasible(metric, min(estimate, estimate + model["lower_error"])), 1),
            round(feasible(metric, max(estimate, estimate + model["upper_error"])), 1),
        ]
    return values, intervals
