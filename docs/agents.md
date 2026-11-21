# Agents

The orchestrator selects the specialist team using scenario type and enabled registry entries. The default registry covers traffic, mobility, environment, safety, campus, energy, sensor coverage, and communication. The data, simulation, verification, and ranking stages are required. Each specialist returns a finding, evidence, an objective-specific recommendation, and a confidence indicator.

Specialists review the first simulation. When they prefer a different permitted intervention to the leading intervention, the orchestrator proposes a revision pairing the leading measure with the most-supported alternative. The model allocates 60% of implementation effort to the first measure and 40% to the second and includes an added coordination cost. The engine evaluates this revision in a bounded second pass across all five time points. The original alternatives remain eligible. The critic records contributing specialists, both scores, and which strategy ranked first. The decision view and JSON export retain that evidence and the dissent.

Where a provider is configured, agents can request an advisory using approved aggregate fields. The deterministic specialist findings drive the revision and the numerical ranking. Agents retain their rule-based finding after a provider failure and publish an explicit failure alert. Agent instructions, preferred providers, fallback IDs, timeout, priority, tools, and data permissions are editable by administrators.

## Autonomous execution

Each new run stores a goal, scenario constraints, dependency-ordered steps, and explicit success criteria. The worker exposes plan changes and step observations through the existing event stream. Open **Execution plan** while a run is active or from the result after it finishes. The JSON report retains tool receipts, elapsed time, attempts, delegated steps, rejected candidates, and the Critic's outcome.

The orchestrator selects specialists from the scenario type and an optional agent selection. It checks the city graph, reads workspace telemetry freshness, simulates the allowable strategies, and delegates independent comparisons to a bounded local pool. Each specialist reads evidence for its own objective. Its optional model call uses the configured capabilities and permitted aggregate inputs. When specialists favor a different measure, their delegation to the simulator adds a new step to the plan.

The Critic independently verifies the strategy set, graph geometry, timeline, metric schema, weighted scores, and specialist references. A rejected simulation triggers one corrective simulation per strategy batch. A rejected specialist finding triggers one fresh comparison. Candidates that fail both checks are excluded. A baseline or specialist evidence failure ends the run without a recommendation.

The telemetry query retries once and falls back to the inputs pinned when the run was queued. A stale feed or a fallback lowers confidence and appears in the report. Unsupported constraints and scenarios outside the modeled network can produce a verified baseline with a **Partially completed** execution state. The worker stops with **Awaiting operator review** when a verified recommendation requires review. The operator can record an approval or rejection. The workflow models and records a decision within the workspace.

The requester or an authorized operator can cancel a queued or active run. Cancellation removes the job lease and fences subsequent writes from the worker. The stored **Cancelled** plan remains available for review. Older reports created before execution plans were introduced keep their original trace.

