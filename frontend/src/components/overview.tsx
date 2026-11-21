"use client";

import { Activity, ArrowDownRight, ArrowUpRight, Bot, CalendarClock, ChevronDown, ChevronRight, CircleDot, Clock3,
  MapPin, Play, ShieldCheck, Sparkles, TrafficCone, TramFront, TriangleAlert, Wind } from "lucide-react";
import { useState } from "react";
import type { Agent, City, DemoScenario, Incident, Run, RunEvent } from "@/lib/types";
import type { Translate } from "@/i18n";
import { sideIcons } from "./navigation";
import { Empty } from "./ui";

const indicators = [
  {key:"traffic",name:"Traffic flow",unit:"/100",color:"mint",icon:Activity,label:"Network efficiency"},
  {key:"environment",name:"Air quality",unit:"/100",color:"cyan",icon:Wind,label:"Environmental health"},
  {key:"mobility",name:"Transit reliability",unit:"%",color:"violet",icon:TramFront,label:"On-time service"},
  {key:"safety",name:"City safety",unit:"/100",color:"amber",icon:ShieldCheck,label:"Safety index"},
];
const patterns = [
  [10,15,12,22,19,23,18,33,29,39,35,49],
  [7,12,11,23,19,23,29,28,37,36,44,47],
  [12,8,18,15,26,22,29,32,36,31,40,48],
  [17,14,23,19,23,28,25,31,36,33,39,44],
];

function Sparkline({values,id}: {values:number[];id:string}) {
  const points = values.map((value,index) => [index * 8, 50 - value]);
  const path = points.map(([x,y],index)=>`${index===0?"M":"L"} ${x},${y}`).join(" ");
  return <svg className="sparkline" viewBox="0 0 92 52" fill="none" aria-hidden="true">
    <defs><linearGradient id={id} x1="0" y1="0" x2="0" y2="1"><stop stopColor="currentColor" stopOpacity=".28"/><stop offset="1" stopColor="currentColor" stopOpacity="0"/></linearGradient></defs>
    <path d={path+` L ${points.at(-1)?.[0]},52 L 0,52 Z`} fill={`url(#${id})`}/>
    <path d={path} stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round"/>
    <circle cx={points.at(-1)?.[0]} cy={points.at(-1)?.[1]} r="2" fill="currentColor"/>
  </svg>;
}

export function Indicators({ city, run, tick, mode, t }: { city:City;run:Run|null;tick:number;mode:string;t:Translate }) {
  const result = run?.result;
  const frame = mode==="Current"?null:mode==="Predicted"?result?.baseline.timeline[tick]:result?.recommendation.timeline[tick];
  return <section className="kpi-grid" aria-label={t("City overview")}>
    {indicators.map(({key,name,unit,color,icon:Icon,label},index)=>{
      const logical = frame?.axes[key] ?? city.kpis[key];
      const value = logical === undefined ? "–" : Math.round(logical);
      const baseline = result?.baseline.timeline[tick].axes[key] ?? city.kpis[key];
      const change = frame && baseline !== undefined ? Math.round((frame.axes[key] - baseline)*10)/10 : null;
      const graph = result ? (mode==="Recommended"?result.recommendation:result.baseline).timeline.map(point=>point.axes[key]/2) : patterns[index];
      return <article key={key} className={`kpi-card accent-${color}`}>
        <div className="kpi-title"><span className="icon-tile"><Icon size={17} strokeWidth={1.8}/></span>{t(name)}</div>
        <div className="kpi-value">{value}<span>{value === "–" ? "" : unit}</span></div>
        <div className="kpi-meta">{change !== null && change !== 0 ? <span className={change>0?"positive":"caution"}>
          {change>0?<ArrowUpRight size={13}/>:<ArrowDownRight size={13}/>} {change>0?"+":""}{change} {t("vs baseline")}</span> : t(label)}</div>
        {logical!==undefined && <Sparkline id={`spark-${key}`} values={graph}/>}
      </article>;
    })}
  </section>;
}

export const modes = ["Current","Predicted","Recommended"];
export const ticks = ["Now","+15 min","+30 min","+60 min","+2h"];

export function Timeline({tick,change,mode,modeChange,t,run,playing,togglePlay}: {
  tick:number;change:(value:number)=>void;mode:string;modeChange:(value:string)=>void;t:Translate;run:Run|null;playing:boolean;togglePlay:()=>void;
}) {
  return <section className="timeline-panel" aria-label={t("Simulation timeline")}>
    <div className="timeline-top">
      <div className="timeline-heading"><Clock3 size={16}/><strong>{t("Simulation timeline")}</strong></div>
      <div className="mode-switch" role="group" aria-label={t("Map state")}>{modes.map(item=><button key={item}
        onClick={()=>modeChange(item)} aria-pressed={item===mode} className={item===mode?"selected":""}>{t(item)}</button>)}</div>
    </div>
    <div className="timeline-controls">
      <button className="play-timeline icon-button" onClick={togglePlay} aria-label={t(playing?"Pause timeline":"Play timeline")} disabled={!run?.result}>
        {playing?<span className="pause-icon"/>:<Play size={15} fill="currentColor"/>}</button>
      <div className="timeline-points">
        <div className="timeline-rail"><span style={{width:`${tick * 25}%`}}/></div>
        {ticks.map((point,index)=><button key={point} onClick={()=>change(index)} aria-pressed={index===tick}
          disabled={!run?.result && index!==0} className={index===tick?"current-tick":""}><i/><span>{t(point)}</span></button>)}
      </div>
    </div>
  </section>;
}

const activeDefaults = ["traffic","mobility","environment","safety"];
const agentIcons: typeof sideIcons = {...sideIcons, safety:ShieldCheck};
const colorMap:Record<string,string> = {blue:"cyan",violet:"violet",green:"mint",orange:"amber",cyan:"cyan",indigo:"violet",yellow:"amber"};

export function ActivityPanel({agents,events,t,open}: {agents:Agent[];events:RunEvent[];t:Translate;open:()=>void}) {
  const [collapsed,setCollapsed]=useState(false);
  const keyed = new Map<string,RunEvent>();
  for (const event of events) if (event.agent && !["provider","fallback","negotiation","warning"].includes(event.stage)) keyed.set(event.agent,event);
  const selected = new Set(events.filter(event=>event.stage==="agents"&&event.agent).map(event=>event.agent));
  const featured = agents.filter(agent=>selected.size?selected.has(agent.id):activeDefaults.includes(agent.id))
    .filter(agent=>!["orchestrator","data","simulation","critic","decision"].includes(agent.id));
  return <section className="panel activity-panel">
    <header className="panel-heading"><span className="panel-heading-icon agent-heading-icon"><Bot size={18}/></span><h2>{t("Agent Activity")}</h2>
      <span className="badge quiet"><i/>{featured.filter(item=>item.enabled).length} {t("Available")}</span>
      <button className="panel-collapse" aria-label={t("Toggle agent panel")} aria-expanded={!collapsed} onClick={()=>setCollapsed(!collapsed)}><ChevronDown size={15}/></button></header>
    {!collapsed&&<>
    <div className="activity-list">
      {featured.length===0&&<Empty title={t("Loading agents…")}/>}
      {featured.map(agent=>{
        const event = keyed.get(agent.id);
        const status = event?.status ?? (agent.enabled?"standby":"disabled");
        const Icon = agentIcons[agent.id] ?? Bot;
        const detail = event?.text ?? ({traffic:"Road network analysis",mobility:"Transit network analysis",environment:"Air quality monitoring",safety:"Risk and response modeling"}[agent.id] ?? agent.description);
        return <div className={`agent-row accent-${colorMap[agent.color] ?? "cyan"}`} key={agent.id}>
          <span className="icon-tile"><Icon size={16} strokeWidth={1.8}/></span>
          <span className="row-text"><strong>{t(agent.name)}</strong><small title={detail}>{t(detail)}</small></span>
          <span className={`agent-status status-${status}`} title={t(status)}><i/><span>{t(status[0].toUpperCase()+status.slice(1))}</span></span>
        </div>;
      })}
    </div>
    <button className="panel-footer-button" onClick={open}>{t("All activity")}<ChevronRight size={15}/></button></>}
  </section>;
}

export function IncidentPanel({incidents,t,choose}: {incidents:Incident[];t:Translate;choose:(incident:Incident)=>void}) {
  const [collapsed,setCollapsed]=useState(false);
  return <section className="panel incident-panel">
    <header className="panel-heading"><span className="panel-heading-icon incident-heading-icon"><TriangleAlert size={17}/></span><h2>{t("Incident Feed")}</h2>
      <span className="badge quiet">{incidents.length} {t("Active")}</span>
      <button className="panel-collapse" aria-label={t("Toggle incident panel")} aria-expanded={!collapsed} onClick={()=>setCollapsed(!collapsed)}><ChevronDown size={15}/></button></header>
    {!collapsed&&<>
    <div>{incidents.length===0&&<Empty title={t("No active incidents")}/>}
    {incidents.map((incident,index)=>{
      const Icon = index===0?TriangleAlert:index===1?TrafficCone:CircleDot;
      return <button className="incident-row" key={incident.id} onClick={()=>choose(incident)}>
        <span className={`incident-icon ${incident.severity>=4?"critical":""}`}><Icon size={15}/></span>
        <span className="row-text"><strong>{t(incident.name)}</strong><small><MapPin size={11}/>{incident.location}</small></span>
        <span className="incident-age">{incident.age}</span>
      </button>;
    })}</div>
    <div className="feed-note"><CalendarClock size={13}/>{t("Simulated city events")}</div></>}
  </section>;
}

export function AskPanel({value,change,submit,busy,t,coordinate,demos,selected,choose}: {
  value:string;change:(value:string)=>void;submit:()=>void;busy:boolean;t:Translate;coordinate?:string;
  demos:DemoScenario[];selected:DemoScenario|null;choose:(preset:DemoScenario)=>void;
}) {
  return <section className="ask-panel">
    <div className="ask-heading"><span className="ask-icon"><Sparkles size={17}/></span><div><h2>{t("Ask AgentCity")}</h2>
      <p>{coordinate ?? t("Describe a city event to simulate its impact.")}</p></div></div>
    <form className="ask-form" onSubmit={event=>{event.preventDefault();submit();}}>
      <input aria-label={t("Scenario prompt")} placeholder={t("What happens if a road closes at 17:00?")} value={value}
        onChange={event=>change(event.target.value)} maxLength={2000} required minLength={5}/>
      <button className="button primary analyze-button" type="submit" disabled={busy}><Sparkles size={16}/><span>{t(busy?"Analyzing…":"Analyze scenario")}</span></button>
    </form>
    {demos.length>0&&<div className="demo-scenarios">
      <div className="prompt-chips" role="group" aria-label={t("Debrecen demo scenarios")}>
        <span>{t("Debrecen demo scenarios")}</span>
        {demos.map(preset=><button key={preset.id} type="button" aria-pressed={selected?.id===preset.id}
          disabled={busy} onClick={()=>choose(preset)}>{t(preset.label)}</button>)}
      </div>
      {selected&&<div className="demo-context">
        <p>{t(selected.brief)}</p>
        <p>{selected.location} · {selected.time} · {selected.duration} min · {t("Simulated data")}</p>
      </div>}
    </div>}
  </section>;
}

