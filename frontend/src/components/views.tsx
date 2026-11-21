"use client";

import { useState } from "react";
import { Activity, ArrowRight, Bot, CircleDot, FileDown, FlaskConical, MapPin, Play, Radio, Route, Wind } from "lucide-react";
import type { Agent, Coordinates, RunSummary, Scenario, Sensor, Transit, Vehicle } from "@/lib/types";
import type { Translate } from "@/i18n";
import { Empty } from "./ui";

export function RunList({runs,t,open,report=false}: {runs:RunSummary[];t:Translate;open:(id:string)=>void;report?:boolean}) {
  if (!runs.length) return <Empty title={t("No simulations yet")} description={t("Analyze a scenario to generate a simulation and decision report.")}/>;
  return <div className="record-list">{runs.map(item=><article key={item.id}>
    <span className="icon-tile"><Activity size={18}/></span><div className="record-text"><strong>{item.title}</strong>
      <small>{item.winner ?? new Date(item.created_at).toLocaleString()}</small></div>
    <span className={`badge run-state status-${item.status}`}><i/>{item.execution_state==="partially_completed"?t("Partially completed"):
      item.execution_state==="waiting_for_human_approval"?t("Awaiting operator review"):t(item.status[0].toUpperCase()+item.status.slice(1))}</span>
    {report&&<a href={`/api/v1/reports/${item.id}`} className="icon-button" aria-label={t("Export JSON")}><FileDown size={17}/></a>}
    <button className="button secondary compact" onClick={()=>open(item.id)}>{t("Open")}<ArrowRight size={15}/></button>
  </article>)}</div>;
}

export function ScenarioList({rows,t,start,reuse}: {rows:Scenario[];t:Translate;start:(id:string)=>void;reuse:(scenario:Scenario)=>void}) {
  if (!rows.length) return <Empty title={t("No scenarios saved")} description={t("Build a scenario using a preset, a map location, or a natural-language prompt.")}/>;
  return <div className="record-list">{rows.map(item=><article key={item.id}>
    <span className="icon-tile"><Route size={19}/></span><div className="record-text"><strong>{item.title}</strong>
      <small>{t(item.kind)} · {item.location} · {item.duration} min</small></div>
    <button className="button secondary compact" onClick={()=>reuse(item)}><FlaskConical size={15}/>{t("Repeat")}</button>
    <button className="button primary compact" onClick={()=>start(item.id)}><Play size={15}/>{t("Run")}</button>
  </article>)}</div>;
}

export function AgentList({agents,t,open}: {agents:Agent[];t:Translate;open:(id:string)=>void}) {
  return <div className="detail-grid">{agents.map(agent=><article key={agent.id} className="panel detail-tile">
    <header><span className="icon-tile"><Bot size={18}/></span><span className="badge quiet">{t(agent.enabled?"Available":"Disabled")}</span></header>
    <h3>{agent.name}</h3><p>{t(agent.description)}</p>
    <button className="plain-action" onClick={()=>open(agent.id)}>{t("View activity")} <ArrowRight size={15}/></button>
  </article>)}</div>;
}

export function SensorList({items,t,locate,environment=false}: {items:Sensor[];t:Translate;locate:(value:Coordinates)=>void;environment?:boolean}) {
  const [expanded,setExpanded] = useState<string|null>(null);
  const shown = environment?items.filter(row=>["Air quality","Weather","Noise"].includes(row.type)):items;
  if(!shown.length)return <Empty title={t("No sensors in this city")}/>;
  return <div className="detail-grid">{shown.map(sensor=><article className="panel detail-tile" key={sensor.id}>
    <header><span className="icon-tile">{environment?<Wind size={18}/>:<Radio size={18}/>}</span>
      <span className={`badge ${sensor.online?"quiet":"warning"}`}><i/>{t(sensor.online?"Online":"Offline")}</span></header>
    <h3>{sensor.name}</h3><p>{t(sensor.type)} · {sensor.id} · {sensor.source==="Simulated"?t("Simulated data"):sensor.source}
      {sensor.observed_at&&<> · {new Date(sensor.observed_at).toLocaleString()}</>}</p>
    <div className="sensor-reading">{sensor.reading??"–"} <small>{sensor.unit}</small></div>
    <div className="sensor-actions">{sensor.coordinates&&<button className="plain-action" onClick={()=>locate(sensor.coordinates!)}><MapPin size={15}/>{t("View on map")}</button>}
      <button className="plain-action" aria-expanded={expanded===sensor.id} onClick={()=>setExpanded(expanded===sensor.id?null:sensor.id)}>{t("History")}</button></div>
    {expanded===sensor.id&&<div className="sensor-details">
      <p>{sensor.uptime!==null&&<>{t("Uptime")} {sensor.uptime}% · </>}{t("Coverage")} {sensor.radius} m
        {sensor.confidence!==null&&<> · {t("Confidence")} {Math.round(sensor.confidence*100)}%</>}</p>
      {sensor.history.length>0?<SensorHistory sensor={sensor} t={t}/>:<p>{t("No readings are available.")}</p>}
    </div>}
  </article>)}</div>;
}

function SensorHistory({sensor,t}: {sensor:Sensor;t:Translate}) {
  const readings=sensor.history.map(item=>item.value);
  const low=Math.min(0,...readings), high=Math.max(0,...readings);
  const range=Math.max(0.001,high-low);
  const label=(item:Sensor["history"][number])=>`${item.observed_at?new Date(item.observed_at).toLocaleString():item.hour} · ${item.value} ${sensor.unit}`;
  return <><div className="history-chart" role="img" aria-label={t(sensor.source==="Simulated"?"Hourly simulated readings":"Observed sensor readings")}>
    {sensor.history.map(item=><div className="history-bar" key={item.observed_at??item.hour} title={label(item)}><span style={{
      bottom:Math.min(item.value-low,-low)/range*100+"%",
      height:Math.max(1,Math.abs(item.value)/range*100)+"%",
    }}/></div>)}
  </div><details><summary>{t("Readings table")}</summary><ul className="simple-list">{sensor.history.map(item=>
    <li key={item.observed_at??item.hour}>{label(item)}</li>)}</ul></details></>;
}

export function MobilityView({routes,t,open,vehicles,locate}: {
  routes:Transit[];t:Translate;open:(route:Transit)=>void;vehicles:Vehicle[];locate:(point:Coordinates)=>void;
}) {
  if(!routes.length&&!vehicles.length)return <Empty title={t("No transit routes in this city")}/>;
  return <><div className="detail-grid">{routes.map(item=><article className="panel detail-tile" key={item.id}>
    <header><span className="icon-tile" style={{color:item.color}}><Route size={18}/></span><span className="badge quiet">{item.source??t("Simulated data")}</span></header>
    <h3>{item.name}</h3><p><CircleDot size={12}/> {t(item.mode)} {item.frequency? `· ${t("Every")} ${item.frequency} min`:""}</p>
    {item.stop_count!==undefined&&<p>{t("Stops served")} {item.stop_count}</p>}
    <button className="plain-action" onClick={()=>open(item)}>{t("View transit on map")}<ArrowRight size={15}/></button>
  </article>)}</div>
    {!!vehicles.length&&<section className="panel settings-section operations-form"><h2>{t("Reported transit positions and delays")}</h2>
    <ul className="simple-list">{vehicles.map((item,index)=><li key={item.id+index}>
      <strong>{routes.find(route=>route.route_id===item.route)?.name||item.route||item.trip||item.id}</strong><span>{new Date(item.observed_at).toLocaleString()}
        {item.stale&&<> · {t("Stale observation")}</>}
        {item.delay!==null&&<> · {t("Transit delay")} {Math.round(item.delay/60)} min</>}</span>
      {item.coordinates&&<button className="button secondary compact" onClick={()=>locate(item.coordinates!)}>{t("View on map")}</button>}
    </li>)}</ul></section>}</>;
}

