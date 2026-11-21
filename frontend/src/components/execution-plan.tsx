"use client";

import type { Translate } from "@/i18n";
import type { ExecutionState, RunExecution } from "@/lib/types";

const states:Record<ExecutionState,string> = {
  created:"Created",planning:"Planning",executing:"Executing",waiting_for_tool:"Waiting for tool",
  observing:"Observing",replanning:"Replanning",waiting_for_agent:"Waiting for agents",verifying:"Verifying",
  waiting_for_human_approval:"Awaiting operator review",completed:"Completed",
  partially_completed:"Partially completed",failed:"Failed",cancelled:"Cancelled",
};
const outcomes = {passed:"Passed",unmet:"Unmet",pending:"Pending"};
const statusLabels = {
  pending:"Pending",running:"Running",completed:"Completed",degraded:"Fallback used",
  failed:"Failed",skipped:"Skipped",cancelled:"Cancelled",
};
const counterLabels = {
  tool_calls:"Tool calls",delegations:"Delegations",retries:"Retries",replans:"Plan revisions",
  provider_attempts:"Model attempts",provider_failures:"Model failures",
};

export function ExecutionPlan({plan,t}: {plan:RunExecution;t:Translate}) {
  const advanced=plan.steps.some(step=>step.attempts>0);
  return <section className="execution-plan" aria-label={t("Execution plan")}>
    <div className="execution-plan-header">
      <div><h3>{t("Execution plan")}</h3><p>{plan.goal}</p></div>
      <strong className="badge quiet" role="status">{t(states[plan.state])}</strong>
    </div>
    {!!plan.constraints.length&&<p><strong>{t("Constraints")}</strong> · {plan.constraints.join(", ")}</p>}
    {advanced&&<dl className="execution-counts">{Object.entries(counterLabels).map(([key,label])=><div key={key}>
      <dt>{t(label)}</dt><dd>{plan.counts[key]??0}</dd>
    </div>)}</dl>}
    {plan.steps.length>0?<ol className="execution-steps">
      {plan.steps.map(step=><li key={step.id} data-status={step.status}>
        <details>
          <summary>
            <span className="execution-step-title"><strong>{t(step.description)}</strong><small>{t(step.agent)} · {t(step.tool)}</small></span>
            <span className="badge quiet">{t(statusLabels[step.status])}</span>
          </summary>
          <div className="execution-observation">
            {step.depends_on.length>0&&<p>{t("Dependencies")} · {step.depends_on.join(", ")}</p>}
            {step.attempts>0&&<p>{t("Attempts")} {step.attempts}{step.elapsed_ms!==null&&<> · {step.elapsed_ms} ms</>}</p>}
            {step.observation&&<>
              <p>{t(step.observation.summary)}</p>
              {Object.keys(step.observation).length>2&&<pre>{JSON.stringify(
                Object.fromEntries(Object.entries(step.observation).filter(([key])=>key!=="summary"&&key!=="status")),null,2
              )}</pre>}
            </>}
          </div>
        </details>
      </li>)}
    </ol>:<p>{t("Waiting for the worker to build the plan.")}</p>}
    <div className="execution-criteria"><h4>{t("Success criteria")}</h4><ul>{plan.success_criteria.map(item=><li key={item.id}>
      <span>{t(item.label)}</span><strong>{t(outcomes[item.status])}</strong>
    </li>)}</ul>
    {plan.verification&&<p>{t("Independent verification")} · {t(plan.verification.status==="passed"?"Passed":"Failed")}
      {!!plan.verification.rejected.length&&<> · {t("Rejected candidates")} {plan.verification.rejected.join(", ")}</>}</p>}
    </div>
  </section>;
}
