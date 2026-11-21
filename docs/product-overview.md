# Product overview

AgentCity Twin helps city and campus teams test how a decision may affect traffic, public transport, safety, or the environment before acting. A road closure, for example, may reduce risk at one junction while shifting congestion to other streets. The workspace lets teams compare options and review the trade-offs.

## What the digital twin represents

The digital twin combines a map of the city with a model of its roads and travel demand. Map layers add context such as transit routes, incidents, and sensor readings. An operator can explore **Current** inputs, switch to **Predicted** to see the forecast without a new intervention, or use **Recommended** to see the forecast with the top-ranked intervention. Both forecasts start from the same scenario.

Debrecen, Hungary, is the demonstration city. The OpenStreetMap basemap represents real geography. The demo scenarios and network estimates are simulated and uncalibrated. A deployment can connect approved feeds and use timestamped observations to calibrate its forecasts. [Simulation assumptions](simulation.md) · [Data and deployment options](operations.md)

## From scenario to recommendation

1. **Describe what happens.** Use **Ask AgentCity**, select a Debrecen preset, or fill in a scenario form. Set the location, time, expected duration, and supported constraints.
2. **Follow the work.** The orchestrator builds an execution plan, checks the city inputs, and delegates relevant comparisons to specialists. Traffic, mobility, environment, safety, and other specialists assess the same scenario from their own objectives.
3. **Compare the options.** The network simulation calculates outcomes at five time points. The workspace's scoring weights combine objectives such as safety, accessibility, travel conditions, and cost. If specialists disagree, the worker can test a combined response in a second simulation.
4. **Verify before recommending.** The Critic checks routes, scores, and supporting evidence. A rejection can trigger corrective work. A verified baseline can still be useful when the constraints or network leave an intervention unresolved.
5. **Review the evidence.** Use **Execution plan**, **Explanation**, and **Audit trace** to see which tools ran, what assumptions shaped the result, and what needed correction. An authorized operator records the review of high-impact recommendations. Field actions follow the organization's procedures.

The simulation produces the numerical estimates. AI models provide structured specialist advisories under the workspace's privacy rules. Local inference is available through LM Studio, and configured deployments can use approved cloud providers. The worker can retain rule-based specialist findings when an advisory fails. [Agent execution](agents.md) · [Model routing](model-router.md)

## Where to start

| Your task | Open |
| --- | --- |
| Run a guided exercise | **Overview → Ask AgentCity → Debrecen demo scenarios** |
| Inspect a corridor, sensor, or route | **Digital Twin**, **Sensors**, or **Mobility** |
| Review a previous decision or export evidence | **Simulations** or **Reports** |
| Change scenario assumptions, seeds, or provider settings and compare results | **Research** |
| Manage data feeds, agents, model access, scoring, or members | **Settings** with organization administrator access |

The public introduction is at `/welcome`. Use `/account` to sign in or create a workspace. Use the language menu to switch the interface between English, French, and Bambara. The demo creates an isolated session and lets you explore the review flow. For a presentation without a running server, open the [offline Debrecen walkthrough](../presentation/index.html).

