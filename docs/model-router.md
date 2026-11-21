# Model router

The router filters enabled providers by capability, context window, cloud consent, and the workspace’s optional cost ceiling and required language match. It orders eligible providers by explicit selection or agent preference, declared language, task complexity and reasoning tier, estimated cost when enabled, default provider, priority, benchmark accuracy, and latency. The advisory path tries up to three eligible providers before using rule-based findings.

Set the workspace routing policy in **Settings → Simulation policy**. Configure each provider’s supported languages, estimated USD per million tokens, and reasoning tier in **Settings → Model providers**. An environment-managed provider reads the same metadata from `<PREFIX>_LANGUAGES`, `<PREFIX>_COST_PER_MILLION`, and `<PREFIX>_REASONING_TIER`. Language is taken from the account preference unless an API caller supplies it for a Model Lab task. Declared languages are operator-supplied. Unpriced cloud models are excluded when a ceiling is set. Local models without an entered rate count as zero provider cost. The ceiling filters declared rates and does not represent a spending quota.

Scenario advisories use advanced routing for severity 4 or higher or at least 10,000 affected people. The Model Lab uses it for vision, tool calls, or prompts over 1,800 characters.

Benchmarks use a fixed prompt set, report exact-match accuracy and mean request latency, and persist results in the workspace. Use the **Model lab** to run a benchmark and inspect the measured values. Keep the benchmark version and model ID when comparing results.

