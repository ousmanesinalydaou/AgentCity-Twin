"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { api, messageOf } from "./api";
import type { Agent, City, DemoScenario, ExecutionDelta, Features, Incident, Layers, Notice, Policy, Provider, Run, RunEvent, RunSummary, Scenario,
  Sensor, Transit, User, Vehicle, Workspace } from "./types";

type Core = {user:User;cities:City[];workspaces:Workspace[];agents:Agent[];policy:Policy;providers:Provider[];features:Features;demoScenarios:DemoScenario[]};
type Context = {layers:Layers;incidents:Incident[];sensors:Sensor[];transit:Transit[];notices:Notice[];runs:RunSummary[];scenarios:Scenario[];vehicles:Vehicle[]};
let session:Promise<User>|null = null;

function getSession() {
  session ??= api<User>("/auth/bootstrap","POST",undefined,false).finally(()=>{session=null;});
  return session;
}

export function useWorkspace(cityId:string, workspace:string) {
  const [core,setCore] = useState<Core|null>(null);
  const [context,setContext] = useState<(Context & {key:string})|null>(null);
  const [error,setError] = useState<string|null>(null);
  const [noticesVersion,setNoticesVersion] = useState(0);

  const refresh = useCallback(() => getSession().then(async user => {

      const [cities,workspaces,agents,policy,providers,features,demoScenarios] = await Promise.all([
        api<City[]>("/cities"),api<Workspace[]>("/workspaces"),api<Agent[]>("/agents"),
        api<Policy>("/settings/policy"),api<Provider[]>("/providers"),api<Features>("/operations/features"),
        api<DemoScenario[]>("/scenarios/demo"),
      ]);
      setError(null);
      setCore({user,cities,workspaces,agents,policy,providers,features,demoScenarios});
      setNoticesVersion(version=>version+1);
  }).catch(error=>setError(messageOf(error))),[]);
  useEffect(()=>{void refresh();},[refresh]);

  const loadContext = useCallback(async () => {
    const query = `?city_id=${encodeURIComponent(cityId)}&workspace_id=${encodeURIComponent(workspace)}`;
    const [layers,incidents,sensors,transit,notices,runs,scenarios,vehicles] = await Promise.all([
      api<Layers>(`/cities/${encodeURIComponent(cityId)}/layers`),api<Incident[]>("/incidents"+query),
      api<Sensor[]>("/sensors"+query),api<Transit[]>("/mobility"+query),api<Notice[]>("/notifications"+query),
      api<RunSummary[]>("/simulations"+query),api<Scenario[]>("/scenarios"+query),api<Vehicle[]>("/telemetry/vehicles"+query),
    ]);
    return {key:query,layers,incidents,sensors,transit,notices,runs,scenarios,vehicles};
  },[cityId,workspace]);

  useEffect(()=>{
    if (!noticesVersion) return;
    let current = true;
    loadContext().then(value=>{if(current)setContext(value);}).catch(error=>{if(current)setError(messageOf(error));});
    return ()=>{current=false;};
  },[noticesVersion,loadContext]);
  const reloadContext=useCallback(()=>setNoticesVersion(value=>value+1),[]);
  useEffect(()=>{
    if(!core?.features.telemetry)return;
    const source=new EventSource("/api/v1/telemetry/events?city_id="+encodeURIComponent(cityId));
    source.onmessage=reloadContext;
    return ()=>source.close();
  },[cityId,core?.features.telemetry,reloadContext]);
  const contextKey = "?city_id="+encodeURIComponent(cityId)+"&workspace_id="+encodeURIComponent(workspace);
  const reloadNotices=useCallback(()=>{
    void api<Notice[]>("/notifications"+contextKey).then(notices=>
      setContext(previous=>previous?.key===contextKey?{...previous,notices}:previous)).catch(()=>undefined);
  },[contextKey]);
  return {core,context:context?.key===contextKey?context:null,error,refresh,reloadContext,reloadNotices,
    updateUser:(user:User)=>setCore(existing=>existing?{...existing,user}:existing)};
}

function terminal(run:Run) {return ["completed","failed","cancelled"].includes(run.status);}

export function useRun(refreshContext:()=>void, refreshNotices:()=>void) {
  const [run,setRun] = useState<Run|null>(null);
  const [events,setEvents] = useState<RunEvent[]>([]);
  const [streamError,setStreamError] = useState<string|null>(null);
  const [attempt,setAttempt] = useState(0);
  const cursor=useRef(0);
  const complete=run?terminal(run):false;
  const id = run?.id;

  useEffect(()=>{
    if (!id||complete) return;
    const source = new EventSource(`/api/v1/simulations/${id}/events`);
    let stopped = false;
    let timer:ReturnType<typeof setTimeout>|undefined;
    let noticeTimer:ReturnType<typeof setTimeout>|undefined;
    async function retrieve(poll=false) {
      if (stopped) return;
      try {
        const updated = await api<Run>(`/simulations/${id}`);
        if(stopped)return;
        setRun(updated);
        setEvents(updated.events);
        cursor.current=updated.events.at(-1)?.seq??0;
        setStreamError(null);
        if (terminal(updated)) { source.close(); refreshContext(); return; }
      } catch(error) { if(!stopped)setStreamError(messageOf(error)); }
      if(poll&&!stopped)timer=setTimeout(()=>void retrieve(true),1200);
    }
    source.onopen = ()=>setStreamError(null);
    source.onmessage = (packet)=>{
      const value = JSON.parse(packet.data) as RunEvent;
      if(value.seq<=cursor.current)return;
      cursor.current=value.seq;
      setRun(current=>{
        if(!current)return current;
        const delta=value.data.execution as ExecutionDelta|undefined;
        const next=current.status==="queued"?{...current,status:"running" as const}:current;
        if(!current.execution||!delta)return next;
        const {step,...updates}=delta;
        const steps=updates.steps??current.execution.steps;
        const merged=step?(steps.some(item=>item.id===step.id)?steps.map(item=>item.id===step.id?step:item):[...steps,step]):steps;
        return {...next,execution:{...current.execution,...updates,steps:merged}};
      });
      setEvents(items=>items.some(item=>item.seq===value.seq)?items:[...items,value]);
      if(value.stage==="agents"&&["completed","failed"].includes(value.status)&&!noticeTimer){
        noticeTimer=setTimeout(()=>{noticeTimer=undefined;refreshNotices();},300);
      }
    };
    source.addEventListener("done",()=>{source.close();void retrieve(true);});
    source.onerror = ()=>{source.close();void retrieve(true);};
    return ()=>{ stopped=true;source.close();if(timer)clearTimeout(timer);if(noticeTimer)clearTimeout(noticeTimer); };
  },[id,complete,attempt,refreshContext,refreshNotices]);

  const open = (value:Run|null) => {
    cursor.current=value?.events.at(-1)?.seq??0;setRun(value);setEvents(value?.events??[]);setStreamError(null);
  };
  return {run,events,open,streamError,retry:()=>setAttempt(number=>number+1)};
}

