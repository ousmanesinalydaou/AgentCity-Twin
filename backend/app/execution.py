"""Durable plan transitions for the worker's bounded city-analysis loop."""

from time import perf_counter

TERMINAL_RUNS = {"completed", "failed", "cancelled"}


def initial_execution(scenario):
    return {
        "goal": scenario["title"],
        "state": "created",
        "revision": 0,
        "steps": [],
        "constraints": [scenario["constraints"]] if scenario["constraints"] else [],
        "success_criteria": [
            {"id": key, "label": label, "status": "pending"}
            for key, label in (
                ("baseline", "Simulate the baseline at every time point"),
                ("alternatives", "Evaluate a feasible intervention"),
                ("evidence", "Verify the specialist findings"),
                ("constraints", "Check the scenario constraints"),
                ("verification", "Pass independent verification"),
                ("decision", "Publish ranked outcomes and limitations"),
            )
        ],
        "counts": {
            "tool_calls": 0,
            "delegations": 0,
            "retries": 0,
            "replans": 0,
            "provider_attempts": 0,
            "provider_failures": 0,
        },
        "verification": None,
        "active_steps": [],
    }


def finish_execution(execution, state):
    return {
        **execution,
        "state": state,
        "active_steps": [],
        "steps": [
            {**step, "status": "cancelled" if state == "cancelled" else "skipped"}
            if step["status"] in {"pending", "running"}
            else step
            for step in execution["steps"]
        ],
    }


class Execution:
    def __init__(self, data, emit):
        self.record = data
        self.emit = emit
        previous = data.get("execution") or {}
        data["execution"] = initial_execution(data["scenario"])
        self.plan = data["execution"]
        self.plan["revision"] = previous.get("revision", 0)
        if previous.get("steps"):
            self.plan["revision"] += 1
            self.plan["counts"].update(previous.get("counts", {}))
            self.plan["counts"]["retries"] += 1
            self.plan["counts"]["replans"] += 1

    def update(self, state, message, *, agent="orchestrator", step=None, status="completed", **details):
        self.plan["state"] = state
        delta = {
            "state": state,
            "revision": self.plan["revision"],
            "counts": self.plan["counts"].copy(),
            "active_steps": list(self.plan["active_steps"]),
        }
        if step:
            delta["step"] = step.copy()
        if "plan" in details:
            delta["steps"] = [item.copy() for item in self.plan["steps"]]
        if self.plan["verification"] is not None:
            delta["verification"] = self.plan["verification"]
        self.emit("execution", message, agent, status, execution=delta, **details)

    def add(self, key, agent, tool, description, after=()):
        step = {
            "id": key,
            "agent": agent,
            "tool": tool,
            "description": description,
            "depends_on": list(after),
            "status": "pending",
            "attempts": 0,
            "observation": None,
            "elapsed_ms": None,
        }
        self.plan["steps"].append(step)
        return step

    def publish(self, message, *, replan=False):
        if replan:
            self.plan["revision"] += 1
            self.plan["counts"]["replans"] += 1
        self.update("replanning" if replan else "planning", message, plan=True)

    def begin(self, step):
        finished = {item["id"] for item in self.plan["steps"] if item["status"] in {"completed", "degraded"}}
        if not set(step["depends_on"]) <= finished:
            raise RuntimeError("The tool dependencies were not met.")
        if step["attempts"]:
            self.plan["counts"]["retries"] += 1
        self.plan["counts"]["tool_calls"] += 1
        step["attempts"] += 1
        step["status"] = "running"
        self.plan["active_steps"].append(step["id"])
        self.update(
            "waiting_for_tool",
            step["description"],
            agent=step["agent"],
            step=step,
            status="running",
        )
        return perf_counter()

    def observed(self, step, started, observation, *, failed=False, degraded=False):
        self.plan["active_steps"].remove(step["id"])
        step.update(
            status="failed" if failed else "degraded" if degraded else "completed",
            elapsed_ms=round((perf_counter() - started) * 1000),
            observation=observation,
        )
        self.update(
            "observing",
            "Tool observation recorded.",
            agent=step["agent"],
            step=step,
            status="failed" if failed else "completed",
        )

    def call(self, step, action, observe):
        started = self.begin(step)
        try:
            value = action()
            observation = observe(value)
        except Exception:
            self.observed(step, started, {"status": "error", "summary": "Tool execution failed."}, failed=True)
            raise
        self.observed(step, started, observation, degraded=observation["status"] == "warning")
        return value
