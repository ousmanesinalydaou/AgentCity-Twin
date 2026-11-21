"use client";

import { useState } from "react";
import { Activity, ArrowRight, BadgeCheck, Check, ClipboardCheck, Download, FileText, GitBranch, Scale, Timer, X } from "lucide-react";
import { api, messageOf } from "@/lib/api";
import type { Run, RunEvent } from "@/lib/types";
import type { Language, Translate } from "@/i18n";
import { PrintReport } from "./print-report";
import { ExecutionPlan } from "./execution-plan";
import { Empty, ErrorText } from "./ui";

const measure = [
  ["congestion","Congestion","/100"],["travelDelay","Road delay"," min"],["transitDelay","Transit delay"," min"],
  ["emissions","Emissions change","%"],["safetyRisk","Safety risk","/100"],["energyLoad","Energy load","/100"],
];
const pipeline = [["goal","Goal"],["plan","Plan"],["agents","Agents"],["tools","Tools"],["simulation","Simulation"],
                  ["verification","Verification"],["decision","Decision"]];

export function Audit({events,t}: {events:RunEvent[];t:Translate}) {
  if (!events.length) return <Empty title={t("No activity to show")} description={t("Launch a simulation to see its execution trace.")}/>;
  return <div className="audit">
    <div className="execution-graph" aria-label={t("Execution graph")}>
      {pipeline.map(([key,label],index)=><span key={key}>{index>0&&<ArrowRight size={13}/>}
        <b className={events.some(item=>item.stage===key)?"reached":""}>{t(label)}</b></span>)}
    </div>
    <ol className="audit-list">{events.map(item=><li key={item.seq}>
      <span className={`trace-dot status-${item.status}`}/>
      <div><strong>{t(item.text)}</strong><small>{t(item.stage)} · {new Date(item.time).toLocaleTimeString()}</small>
        {typeof item.data.evidence==="string"&&<p>{item.data.evidence}</p>}
        {Object.keys(item.data).length>0&&<details><summary>{t("Event data")}</summary><pre>{JSON.stringify(item.data,null,2)}</pre></details>}
      </div>
    </li>)}</ol>
  </div>;
}

export function Decision({run,events,t,tick,change,review,canCancel,openMap,language}: {
  run:Run;events:RunEvent[];t:Translate;tick:number;change:(value:Run)=>void;review:boolean;canCancel:boolean;openMap:()=>void;language:Language;
}) {
  const [tab,setTab] = useState("Compare");
  const [notice,setNotice] = useState("");
  const [busy,setBusy] = useState(false);
  const [note,setNote] = useState("");
  const result = run.result;
  async function approve(decision:string) {
    if (note.trim().length<3) {setNotice(t("Enter a review note."));return;}
    setBusy(true);setNotice("");
    try { change(await api<Run>(`/simulations/${run.id}/approval`,"POST",{decision,note})); }
    catch(error){setNotice(messageOf(error));}
    finally{setBusy(false);}
  }
  async function cancel() {
    setBusy(true);setNotice("");
    try {change(await api<Run>(`/simulations/${run.id}/cancel`,"POST"));}
    catch(error){setNotice(messageOf(error));}
    finally{setBusy(false);}
  }

  if (!result) return <section className="panel decision-panel" aria-live="polite">
    <div className="decision-head"><span className="icon-tile decision-icon"><Activity size={22}/></span><div>
      <div className="eyebrow">{t("Scenario analysis")}</div><h2>{run.title}</h2>
      <p>{t(run.status==="cancelled"?"The operator cancelled the run.":(run.error ?? "Gathering city data and evaluating candidate strategies."))}</p>
    </div><span className={`badge run-state status-${run.status}`}><i/>{t(run.status)}</span></div>
    {canCancel&&["queued","running"].includes(run.status)&&<div className="execution-actions">
      <button type="button" className="button secondary compact" disabled={busy} onClick={()=>void cancel()}>{t("Cancel run")}</button>
    </div>}
    <ErrorText message={t(notice)}/>
    {run.execution&&<ExecutionPlan plan={run.execution} t={t}/>}
    <Audit events={events} t={t}/>
  </section>;

  const winner = result.recommendation;
  const before = result.baseline.timeline[tick].metrics;
  const after = winner.timeline[tick].metrics;
  return <section className="panel decision-panel" aria-label={t("Simulation results")}>
    <div className="decision-head"><span className="icon-tile decision-icon"><BadgeCheck size={24}/></span><div>
      <div className="eyebrow">{t(run.execution?.state==="partially_completed"?"Verified baseline":"Recommended strategy")}</div>
      <h2>{t(winner.name)}</h2><p>{t(winner.summary)}</p>
    </div><div className="decision-score"><strong>{winner.score.toFixed(1)}</strong><small>/100 {t("decision score")}</small></div></div>
    <div className="decision-meta"><span className="badge quiet">{t("Simulated data")}</span><span><Check size={14}/>{Math.round(result.confidence*100)}% {t("confidence")}</span>
      <span><Timer size={14}/>{result.elapsed_ms} ms</span><button className="plain-action" onClick={openMap}>{t("View on map")}</button></div>
    {run.execution?.state==="partially_completed"&&<p className="execution-actions">{t("The run verified a baseline, but could not recommend an intervention.")}</p>}
    <div className="tabbar" role="group" aria-label={t("Result sections")}>
      {([["Compare",Scale],["Explanation",FileText],["Audit trace",GitBranch],["Execution plan",Activity]] as const)
        .filter(([name])=>name!=="Execution plan"||run.execution).map(([name,Icon])=><button key={name} aria-pressed={tab===name}
        className={tab===name?"selected":""} onClick={()=>setTab(name)}><Icon size={16}/>{t(name)}</button>)}
    </div>
    {tab==="Compare"&&<div className="decision-body">
      <div className="result-grid">
        <div><h3>{t("Strategy ranking")}</h3><div className="strategy-list">{result.strategies.map((strategy,index)=><div key={strategy.id}>
          <div><span>{index+1}. {t(strategy.name)}</span><strong>{strategy.score.toFixed(1)}</strong></div>
          <div className="score-meter"><span className={strategy.id===winner.id?"winner":""} style={{width:strategy.score+"%"}}/></div>
        </div>)}</div></div>
        <div><h3>{t("Outcome comparison")} · +{winner.timeline[tick].minute}m</h3><table className="comparison-table">
          <thead><tr><th>{t("Metric")}</th><th>{t("Do nothing")}</th><th>{t("Recommended")}</th></tr></thead><tbody>
          {measure.map(([key,label,unit])=><tr key={key}><th>{t(label)}</th><td>{before[key]}{unit}</td><td>{after[key]}{unit}
            {winner.timeline[tick].intervals?.[key]&&
              <small className="interval-label">{t("Validation interval")} {winner.timeline[tick].intervals?.[key].join("–")}{unit}</small>}
          </td></tr>)}</tbody>
        </table></div>
      </div>
      <button className="button secondary fit" onClick={()=>setTab("Explanation")}><FileText size={15}/>{t("Why did AgentCity choose this?")}</button>
    </div>}
    {tab==="Explanation"&&<div className="decision-body">
      <h3>{t("Why did AgentCity choose this?")}</h3>
      <p>{t(winner.name)} {t("ranked first under the workspace scoring policy with a weighted score of")} {winner.score.toFixed(1)}/100. {t("The baseline scored")} {result.baseline.score.toFixed(1)}/100.</p>
      <p><strong>{t("Scenario")}</strong> · {run.scenario.kind}, {run.scenario.location} · {run.scenario.duration} min · {t("Severity")} {run.scenario.severity}/5</p>
      {run.scenario.constraints&&<p><strong>{t("Constraints")}</strong> · {run.scenario.constraints}</p>}
      <p><strong>{t("Data source")}</strong> · {result.source} · {t(result.freshness)}</p>
      <details open><summary>{t("Agent consensus and disagreements")}</summary><div className="findings">
        {result.messages.map(item=><div key={item.agent}><strong>{item.name}</strong><p>{t(item.summary)}</p><small>{item.evidence} · {Math.round(item.confidence*100)}% · {item.execution.execution}</small>
          {item.task&&<p>{t("Tool calls")} · {item.task.tools_used.map(tool=>t(tool)).join(", ")}</p>}
          {item.advisory&&<p>{t("Model advisory")} · {item.execution.model} · {item.advisory.summary} · {item.advisory.evidence}</p>}
          {item.comparison&&<p>{t("Comparison model")} · {item.comparison.execution.model} · {item.comparison.advisory.summary}</p>}</div>)}
      </div></details>
      {result.negotiation&&<details open><summary>{t("Negotiated revision")}</summary>
        <p>{result.negotiation.parents.map(id=>t(result.strategies.find(row=>row.id===id)?.name??id)).join(" + ")}</p>
        <p>{t(result.negotiation.selected?"The revision ranked first after a second simulation.":"The original strategy ranked higher after a second simulation.")}</p>
        <p>{t("Revised score")} {result.negotiation.score.toFixed(1)}/100 · {t("Initial leading score")} {result.negotiation.initial_score.toFixed(1)}/100</p>
        <p>{t("Proposed by")} {result.negotiation.proposed_by.map(id=>result.messages.find(row=>row.agent===id)?.name??id).join(", ")}</p>
      </details>}
      <details><summary>{t("Rejected alternatives and assumptions")}</summary>
        <ul>{result.strategies.filter(item=>item.id!==winner.id).map(item=><li key={item.id}>{t(item.name)} · {item.score.toFixed(1)}/100 · {t(item.summary)}</li>)}
          {[...result.assumptions,...result.limitations].map(item=><li key={item}>{t(item)}</li>)}</ul>
      </details>
      <details><summary>{t("Reproducibility")}</summary><p>{t("Simulation seed")} {result.seed} · {result.model_version}</p><code>{result.input_hash}</code>
        <dl className="fact-grid">{Object.entries(result.weights).map(([key,value])=><div key={key}><dt>{t(key)}</dt><dd>{value}</dd></div>)}</dl></details>
    </div>}
    {tab==="Audit trace"&&<Audit events={run.events} t={t}/>}
    {tab==="Execution plan"&&run.execution&&<ExecutionPlan plan={run.execution} t={t}/>}
    {result.requires_approval&&<div className="review-box"><ClipboardCheck size={18}/><div>
      <strong>{t(run.approval?"Recorded operator review":"Operator review required")}</strong>
      {run.approval?<p>{t(run.approval.decision)} · {run.approval.actor} · {run.approval.note}</p>:<>
        <p>{t("This simulation recommends a high-impact intervention. Record a human decision for the audit trail.")}</p>
        {review&&<form className="review-form" onSubmit={event=>event.preventDefault()}><input aria-label={t("Review note")} value={note} maxLength={500}
          onChange={event=>setNote(event.target.value)} placeholder={t("Review note")}/>
          <button type="button" className="button secondary" onClick={()=>void approve("approved")} disabled={busy}><Check size={15}/>{t("Approve")}</button>
          <button type="button" className="button secondary" onClick={()=>void approve("rejected")} disabled={busy}><X size={15}/>{t("Reject")}</button></form>}
      </>}<ErrorText message={notice}/></div></div>}
    <PrintReport run={run} t={t}/>
    <footer className="decision-exports">
      <a className="button secondary" href={`/api/v1/reports/${run.id}/document?template=decision&minute=${winner.timeline[tick].minute}&language=${language}`}
        target="_blank" rel="noreferrer"><FileText size={15}/>{t("Decision document")}</a>
      <a className="button secondary" href={`/api/v1/reports/${run.id}/document?template=research&minute=${winner.timeline[tick].minute}&language=${language}`}
        target="_blank" rel="noreferrer"><FileText size={15}/>{t("Research document")}</a>
      <a href={`/api/v1/reports/${run.id}`} className="button secondary"><Download size={15}/>{t("Export JSON")}</a>
      <a href={`/api/v1/reports/${run.id}?format=csv`} className="button secondary"><Download size={15}/>{t("Export CSV")}</a>
      <button className="button secondary" onClick={()=>window.print()}><FileText size={15}/>{t("Print report")}</button>
    </footer>
  </section>;
}

