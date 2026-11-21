# Simulation

Each scenario has location, influence radius, duration, severity, start time, affected population, and a reproducible seed. A small weighted road graph assigns trips from origin–destination demand pairs to low-cost paths. Capacity drops near the event, and demand varies by city-local hour. Three assignment passes account for the effect of capacity on travel cost. Different intervention profiles vary demand, recovery, access, transit capacity, and response cost.

The engine evaluates 0, 15, 30, 60, and 120 minutes. It computes congestion, road and transit delay, emissions change, safety risk, energy load, trip counts, and coverage estimates. Normalized objectives use configurable 0–100 weights. The ranking uses a weighted aggregate of the 15-, 30-, and 60-minute scores. The baseline is always included, and supported constraint phrases can remove incompatible candidates.

The demo coefficients are illustrative and its confidence is a heuristic. Calibrate and validate the model against appropriate observations before using it to inform operational decisions.

