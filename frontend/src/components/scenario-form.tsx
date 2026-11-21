"use client";

import { useState, type ReactNode } from "react";
import { Crosshair, Play, Save } from "lucide-react";
import type { Agent, City, Coordinates, Provider, ScenarioInput } from "@/lib/types";
import type { Translate } from "@/i18n";
import { messageOf } from "@/lib/api";
import { ErrorText } from "./ui";

const kinds = ["Emergency","Road Closure","Campus Event","Football Match","Pollution Spike","Severe Weather",
  "Transit Failure","Construction","Power Outage","Public Gathering"];
const examples:Record<string,string> = {"Emergency":"University corridor accident","Road Closure":"Planned corridor closure",
  "Campus Event":"Campus open day","Football Match":"Stadium departure peak","Pollution Spike":"Air quality alert",
  "Severe Weather":"Severe weather disruption","Transit Failure":"Transit interruption","Construction":"City center works",
  "Power Outage":"Essential services power loss","Public Gathering":"Public gathering departure"};
function cityDate(timezone:string) {
  const date = new Intl.DateTimeFormat("en-CA",{timeZone:timezone,year:"numeric",month:"2-digit",day:"2-digit"}).format(new Date());
  return date+"T17:00";
}

export function ScenarioForm({t,city,coordinates,initial,research,providers,agents,onSubmit,renderMap}: {
  t:Translate;city:City;coordinates:Coordinates|null;initial?:ScenarioInput;research?:boolean;
  providers:Provider[];agents:Agent[];onSubmit:(data:ScenarioInput,run:boolean)=>Promise<void>;renderMap?:(point:Coordinates,pick:(value:Coordinates)=>void)=>ReactNode;
}) {
  const [form,setForm] = useState<ScenarioInput>(initial ?? {
    title:"", kind:"Emergency", location:city.id==="debrecen"?"University of Debrecen":city.name,
    starts_at:cityDate(city.timezone),duration:60,severity:4,population:1200,radius:850,description:"",constraints:"",seed:42,
  });
  const [point,setPoint] = useState<Coordinates>(coordinates ?? initial?.coordinates ?? city.origin);
  const [mapOpen,setMapOpen] = useState(false);
  const [busy,setBusy] = useState(false);
  const [error,setError] = useState("");
  const change = <K extends keyof ScenarioInput>(key:K,value:ScenarioInput[K])=>setForm(values=>({...values,[key]:value}));
  async function submit(run:boolean) {
    setBusy(true);setError("");
    try { await onSubmit({...form,coordinates:point},run); }
    catch(error){setError(messageOf(error));}
    finally{setBusy(false);}
  }
  const number = (name:"duration"|"severity"|"population"|"radius"|"seed",label:string,min:number,max:number) => <label>
    {t(label)}<input type="number" value={form[name]} onChange={event=>change(name,+event.target.value)} min={min} max={max} required/>
  </label>;

  return <form className="form-stack" onSubmit={event=>{
    event.preventDefault();
    void submit((event.nativeEvent as SubmitEvent).submitter?.getAttribute("value") !== "save");
  }}>
    <ErrorText message={error}/>
    <div className="preset-picker">{kinds.slice(0,8).map(kind=><button key={kind} type="button" className="chip"
      onClick={()=>setForm(values=>({...values,kind,title:examples[kind]}))} aria-pressed={form.kind===kind}>{t(kind)}</button>)}</div>
    <div className="form-grid">
      <label>{t("Title")}<input value={form.title} onChange={event=>change("title",event.target.value)} minLength={3} maxLength={120} required placeholder={t("University corridor accident")}/></label>
      <label>{t("Scenario type")}<select value={form.kind} onChange={event=>change("kind",event.target.value)}>{kinds.map(kind=><option key={kind} value={kind}>{t(kind)}</option>)}</select></label>
      <label>{t("Location")}<input value={form.location} onChange={event=>change("location",event.target.value)} maxLength={120} required/></label>
      <label>{t("Start time")}<input type="datetime-local" value={form.starts_at.slice(0,16)} onChange={event=>change("starts_at",event.target.value)} required/></label>
      {number("duration","Duration (min)",15,720)}{number("severity","Severity",1,5)}
      {number("population","Population affected",0,5000000)}{number("radius","Radius (m)",50,10000)}
      <label>{t("Latitude")}<input type="number" step="any" value={point[1]} min={-85} max={85}
        onChange={event=>setPoint([point[0],+event.target.value])} required/></label>
      <label>{t("Longitude")}<input type="number" step="any" value={point[0]} min={-180} max={180}
        onChange={event=>setPoint([+event.target.value,point[1]])} required/></label>
    </div>
    {renderMap&&<button type="button" className="button secondary fit" aria-expanded={mapOpen} onClick={()=>setMapOpen(!mapOpen)}><Crosshair size={15}/>{t("Choose on the map")}</button>}
    {mapOpen&&renderMap?.(point,setPoint)}
    <label>{t("Description")}<textarea value={form.description} onChange={event=>change("description",event.target.value)} maxLength={2000} rows={2}/></label>
    <label>{t("Constraints")}<input value={form.constraints} onChange={event=>change("constraints",event.target.value)}
      placeholder={t("Examples: no reroute, no closure, no additional transit")} maxLength={500}/></label>
    {research && <><div className="form-grid">{number("seed","Simulation seed",0,2147483647)}
      {[["provider_id","Preferred model"],["compare_provider_id","Comparison model"]].map(([key,label])=>
        <label key={key}>{t(label)}<select value={form[key as "provider_id"|"compare_provider_id"]??""} onChange={event=>change(key as "provider_id"|"compare_provider_id",event.target.value||null)}>
          <option value="">{t("Use workspace routing")}</option>{providers.filter(p=>p.enabled).map(p=><option value={p.id} key={p.id}>{p.name} · {p.model}</option>)}
        </select></label>)}</div>
      <fieldset className="check-grid"><legend>{t("Specialist agents")}</legend>
        <label><input type="checkbox" checked={form.agent_ids==null} onChange={event=>change("agent_ids",event.target.checked?null:[])}/>
          {t("Use the scenario’s default specialists")}</label>
        {form.agent_ids!=null&&agents.filter(agent=>!["orchestrator","data","simulation","critic","decision"].includes(agent.id)).map(agent=><label key={agent.id}>
          <input type="checkbox" disabled={!agent.enabled} checked={form.agent_ids?.includes(agent.id)??false}
            onChange={event=>change("agent_ids",event.target.checked?[...(form.agent_ids??[]),agent.id]:(form.agent_ids??[]).filter(id=>id!==agent.id))}/>
          {agent.name}
        </label>)}
      </fieldset></>}
    <div className="form-actions">
      <button type="submit" value="save" className="button secondary" disabled={busy}><Save size={16}/>{t("Save scenario")}</button>
      <button type="submit" value="run" className="button primary" disabled={busy}><Play size={16}/>{t(busy?"Working…":"Run simulation")}</button>
    </div>
  </form>;
}

