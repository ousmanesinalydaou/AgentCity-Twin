"use client";

import dynamic from "next/dynamic";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Activity, ArrowRight, Bot, ChevronRight, CircleHelp, Globe2, LayoutGrid, LogIn, LogOut, MapPin,
  Plus, Search, Sparkles } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { translate, type Language } from "@/i18n";
import { persistLanguage } from "@/i18n/preference";
import { api, messageOf } from "@/lib/api";
import type { Coordinates, DemoScenario, Incident, Run, RunEvent, ScenarioInput, User } from "@/lib/types";
import { useRun, useWorkspace } from "@/lib/workspace";
import { Audit, Decision } from "./decision";
import { ExecutionPlan } from "./execution-plan";
import { SensorCoverage } from "./coverage-plan";
import { ModelLab } from "./model-lab";
import { LanguageOptions, navigation, SideNav, Topbar, type Popup } from "./navigation";
import { ActivityPanel, AskPanel, IncidentPanel, Indicators, Timeline } from "./overview";
import { ResearchExperiments } from "./research";
import { ScenarioForm } from "./scenario-form";
import { SettingsView } from "./settings";
import { Dialog, Empty, ErrorText } from "./ui";
import { AgentList, MobilityView, RunList, ScenarioList, SensorList } from "./views";

const CityMap = dynamic(()=>import("./map/city-map"), {ssr:false,loading:()=> <div className="map-area debrecen-fallback"/>});
const flatNav = navigation.flat();
const pages = Object.fromEntries(flatNav.map(item=>[item.id,item.name]));
const descriptions:Record<string,string> = {
  twin:"Explore city layers and modeled interventions.",scenarios:"Create and repeat urban disruption scenarios.",
  simulations:"Review active and completed scenario runs.",agents:"Inspect the specialist team and its execution history.",
  sensors:"Inspect sensor readings, coverage, and availability.",mobility:"Explore routes, stops, and vehicle positions.",
  environment:"Monitor modeled air quality and environmental readings.",reports:"Review and export documented recommendations.",
  research:"Run repeatable experiments with controlled inputs.",settings:"Manage workspace preferences, data, and policies.",
};

export function WorkspaceApp() {
  const router=useRouter();
  const [cityId,setCityId]=useState("debrecen");
  const [workspace,setWorkspace]=useState("city-lab");
  const [view,setView]=useState("overview");
  const [languageOverride,setLanguageOverride]=useState<Language|null>(null);
  const [menu,setMenu]=useState(false);
  const [popup,setPopup]=useState<Popup>(null);
  const [query,setQuery]=useState("");
  const [form,setForm]=useState<{initial?:ScenarioInput;research?:boolean;experimentId?:string}|null>(null);
  const [experiment,setExperiment]=useState<string|null>(null);
  const [point,setPoint]=useState<Coordinates|null>(null);
  const [promptPoint,setPromptPoint]=useState<Coordinates|null>(null);
  const [prompt,setPrompt]=useState("");
  const [demoPreset,setDemoPreset]=useState<DemoScenario|null>(null);
  const [submitting,setSubmitting]=useState(false);
  const [actionError,setActionError]=useState("");
  const [mode,setMode]=useState("Current");
  const [tick,setTick]=useState(0);
  const [playing,setPlaying]=useState(false);
  const [activity,setActivity]=useState<{id:string;events:RunEvent[];name:string}|null>(null);

  const {core,context,error,refresh,reloadContext,reloadNotices,updateUser}=useWorkspace(cityId,workspace);
  const {run,events,open:openRun,streamError,retry}=useRun(reloadContext,reloadNotices);
  const user=core?.user??null;
  const language=languageOverride??user?.preferences.language??"en";
  const t=translate(language);
  const city=core?.cities.find(candidate=>candidate.id===cityId)??null;
  const agents=core?.agents??[];
  const providers=core?.providers??[];
  const incidents=context?.incidents??[];
  const mapOn=view==="overview"||view==="twin";
  const permitted=!!user&&user.role!=="Viewer";
  const approval=!!user&&["City Operator","Organization Admin","Super Admin"].includes(user.role);

  useEffect(()=>{
    function restore() {
      const selected=new URLSearchParams(window.location.search).get("view");
      setView(selected && pages[selected] ? selected : "overview");
    }
    restore();
    window.addEventListener("popstate",restore);
    function shortcut(event:KeyboardEvent) {
      if ((event.ctrlKey||event.metaKey)&&event.key.toLowerCase()==="k") {
        event.preventDefault();setPopup("search");
      }
    }
    window.addEventListener("keydown",shortcut);
    return ()=>{window.removeEventListener("popstate",restore);window.removeEventListener("keydown",shortcut);};
  },[]);

  useEffect(()=>{
    document.documentElement.lang=language;
    if(user)persistLanguage(language);
    const selected=user?.preferences.theme??"dark";
    const media=window.matchMedia("(prefers-color-scheme: light)");
    const apply=()=>{document.documentElement.dataset.theme=selected==="system"?(media.matches?"light":"dark"):selected;};
    apply();media.addEventListener("change",apply);
    return ()=>media.removeEventListener("change",apply);
  },[language,user]);

  useEffect(()=>{
    if (!playing) return;
    const interval=setInterval(()=>setTick(old=>(old+1)%5),1100);
    return ()=>clearInterval(interval);
  },[playing]);

  function navigate(value:string) {
    const url=new URL(window.location.href);
    if (value==="overview") url.searchParams.delete("view"); else url.searchParams.set("view",value);
    if(url.href!==window.location.href) window.history.pushState({}, "", url);
    setView(value);setPopup(null);
  }
  function changeContext(id:string, type:string) {
    if (type==="city") setCityId(id);else setWorkspace(id);
    openRun(null);setPoint(null);setPromptPoint(null);setMode("Current");setTick(0);setPlaying(false);setActionError("");setExperiment(null);
    setDemoPreset(null);setPrompt("");
  }
  function mapSelect(value:Coordinates) {setPoint(value);setPromptPoint(value);setDemoPreset(null);}
  function chooseDemo(preset:DemoScenario) {
    setDemoPreset(preset);setPrompt(t(preset.prompt));setPoint(preset.coordinates);setPromptPoint(preset.coordinates);
    openRun(null);setMode("Current");setTick(0);setPlaying(false);setActionError("");
  }
  function locate(value:Coordinates) {setPoint([...value]);navigate("twin");}
  function selectIncident(incident:Incident) {
    mapSelect(incident.coordinates);
    setPrompt(`Evaluate an emergency near ${incident.location} at 17:00. ${incident.name}.`);
  }
  function runReady(value:Run) {
    openRun(value);
    setPoint(value.scenario.coordinates);
    setTick(2);setMode("Recommended");setPlaying(false);
  }
  async function launchPrompt() {
    if (!point&&!city) return;
    if (prompt.trim().length<5 || submitting)return;
    setSubmitting(true);setActionError("");
    try {
      const value=demoPreset
        ? await api<Run>(`/scenarios/demo/${demoPreset.id}/run`,"POST",{workspace_id:workspace})
        : await api<Run>("/agentcity/analyze","POST",{prompt:prompt.trim(),city_id:cityId,workspace_id:workspace,coordinates:promptPoint});
      runReady(value);reloadContext();
    } catch(error){setActionError(messageOf(error));}
    finally{setSubmitting(false);}
  }
  async function submitScenario(values:ScenarioInput, shouldRun:boolean) {
    const payload={...values,city_id:cityId,workspace_id:workspace};
    if(form?.experimentId) {
      const created=await api<{run:Run|null}>(`/experiments/${form.experimentId}/variants?start=${shouldRun}`,"POST",payload);
      if(created.run)runReady(created.run);
      setForm(null);reloadContext();
      return;
    }
    const created=await api<{id:string}>("/scenarios","POST",payload);
    reloadContext();
    if(shouldRun) {
      try {
        runReady(await api<Run>(`/scenarios/${created.id}/run`,"POST"));
        navigate("overview");
      } catch (error) {
        setActionError(messageOf(error));
        navigate("scenarios");
      }
    } else navigate("scenarios");
    setForm(null);
  }
  async function startSaved(id:string, inResearch=false) {
    setActionError("");
    try {runReady(await api<Run>(`/scenarios/${id}/run`,"POST"));if(!inResearch)navigate("overview");reloadContext();}
    catch(error){setActionError(messageOf(error));}
  }
  async function loadRun(id:string) {
    setActionError("");setPopup(null);
    try {runReady(await api<Run>(`/simulations/${id}`));if(mapOn)navigate("simulations");}
    catch(error){setActionError(messageOf(error));}
  }
  async function loadAgent(id:string) {
    setActionError("");
    try {
      const history=await api<{id:string;title:string;events:RunEvent[]}[]>(`/agents/${id}/runs`);
      setActivity({id,events:history[0]?.events??[],name:agents.find(item=>item.id===id)?.name??"Agent"});
    } catch(error){setActionError(messageOf(error));}
  }
  async function switchLanguage(value:Language) {
    setLanguageOverride(value);setPopup(null);
    if (user) {
      try {updateUser(await api<User>("/auth/preferences","PATCH",{...user.preferences,language:value}));}
      catch(error){setLanguageOverride(null);setActionError(messageOf(error));}
    }
  }
  async function signOut() {
    try {await api("/auth/logout","POST");router.replace("/account");}
    catch(error){setActionError(messageOf(error));}
  }
  const closePopup=useCallback(()=>setPopup(null),[]);
  const frame=mode==="Current"?undefined:mode==="Predicted"?run?.result?.baseline.timeline[tick]:run?.result?.recommendation.timeline[tick];
  const decision=run&&<Decision key={run.id} run={run} events={events} t={t} tick={tick} change={value=>{openRun(value);reloadContext();}} language={language}
    review={approval} canCancel={approval||!!user&&permitted&&run.requester_id===user.id}
    openMap={()=>{setMode("Recommended");navigate("twin");window.scrollTo({top:0,behavior:"instant"});}}/>;
  const searchTerms=[
    ...flatNav.map(item=>({key:item.id,label:t(item.name),detail:t("Workspace view"),act:()=>navigate(item.id)})),
    ...(core?.cities??[]).map(item=>({key:item.id,label:item.name,detail:item.country,act:()=>{changeContext(item.id,"city");navigate("overview");}})),
    ...(context?.runs??[]).map(item=>({key:item.id,label:item.title,detail:t("Simulation"),act:()=>void loadRun(item.id)})),
    ...(context?.sensors??[]).flatMap(item=>item.coordinates?[{
      key:item.id,label:item.name,detail:t(item.type),act:()=>locate(item.coordinates!),
    }]:[]),
  ].filter(item=>`${item.label} ${item.detail}`.toLowerCase().includes(query.trim().toLowerCase())).slice(0,12);

  return <div className="app-shell">
    <a href="#main-content" className="skip-link">{t("Skip to content")}</a>
    <Topbar t={t} user={user} city={city} cities={core?.cities??[]} workspace={workspace} workspaces={core?.workspaces??[]}
      cityChange={id=>changeContext(id,"city")} workspaceChange={id=>changeContext(id,"workspace")}
      onPopup={setPopup} notices={user?.preferences.notifications&&core?.features.notifications?context?.notices??[]:[]} toggleNav={()=>setMenu(!menu)}/>
    <SideNav active={view} change={navigate} t={t} isOpen={menu} close={()=>setMenu(false)} demo={user?.demo??false}
      showResearch={core?.features.research??true}/>
    <main className="main-content" id="main-content">
      <div className="page-heading"><div>
        <div className="page-breadcrumb"><LayoutGrid size={13}/>{t("Workspace")}<ChevronRight size={12}/><span>{t(pages[view])}</span></div>
        <h1>{view==="overview"?(city?t("{city} Digital Twin").replace("{city}", city.name):t("City Digital Twin")):t(pages[view])}</h1>
        <p>{view==="overview"?<><MapPin size={14}/>{city?.name??"Debrecen"}, {city?.country??"Hungary"}<i/>{t("Urban intelligence workspace")}</>
          :t(descriptions[view])}</p>
      </div><div className="page-actions">
        {mapOn&&<span className="badge demo-badge"><i/>{t("Simulated data")}</span>}
        {permitted&&view!=="research"&&<button className="button primary" onClick={()=>setForm({})}><Plus size={18}/>{t("New scenario")}</button>}
      </div></div>

      <ErrorText message={actionError}/>
      {streamError&&<div className="inline-feedback"><ErrorText message={streamError}/><button className="button secondary" onClick={retry}>{t("Retry")}</button></div>}
      {error&&<div className="inline-feedback"><ErrorText message={error}/><button className="button secondary" onClick={()=>void refresh()}>{t("Retry")}</button>
        {!user&&<Link className="button secondary" href="/account">{t("Sign in")}</Link>}</div>}
      {!city&&!error&&<section className="skeleton-workspace" aria-live="polite"><p>{t("Loading workspace…")}</p><div/><div/></section>}

      {city&&mapOn&&<>
        {view==="overview"&&<Indicators city={city} run={run} tick={tick} mode={mode} t={t}/>}
        <div className="workspace-flow">
        <div className={`city-grid ${view==="twin"?"full-map-view":""}`}>
          <section className="panel map-panel">
            <header className="map-panel-header"><span className="panel-heading-icon"><MapPin size={18}/></span>
              <div><h2>{t("City Digital Twin")}</h2><p>{t("Urban network and incident overlays")}</p></div>
              <span className="badge quiet view-badge"><i/>{t(mode==="Current"?"City state":mode)}</span></header>
            <CityMap key={city.id} city={city} data={context?.layers??null} incidents={incidents} selected={point}
              select={mapSelect} frame={frame} mode={mode} radius={run?.scenario.radius} style={core?.policy.map_style} t={t}
              expanded={view==="twin"} forecastOrigin={run?.scenario.coordinates} duration={run?.scenario.duration}/>
            <Timeline tick={tick} change={value=>{setTick(value);if(mode==="Current"&&value>0)setMode("Predicted");}} mode={mode}
              modeChange={value=>setMode(value)} playing={playing} togglePlay={()=>{if(mode==="Current")setMode("Predicted");setPlaying(!playing);}}
              t={t} run={run}/>
          </section>
          <aside className="city-side">
            <ActivityPanel agents={agents} events={events} t={t} open={()=>setPopup("activity")}/>
            <IncidentPanel incidents={incidents} t={t} choose={selectIncident}/>
          </aside>
        </div>
        {permitted&&<AskPanel value={prompt} change={value=>{setPrompt(value);setDemoPreset(null);}} submit={()=>void launchPrompt()} busy={submitting} t={t}
          demos={core?.demoScenarios.filter(row=>row.city_id===cityId)??[]} selected={demoPreset} choose={chooseDemo}
          coordinate={promptPoint?`${t("Map context")} · ${promptPoint[1].toFixed(4)}, ${promptPoint[0].toFixed(4)}`:undefined}/>}
        </div>
        {decision}
        <footer className="workspace-footer"><span><Activity size={13}/>{city.source}</span><Link href="/welcome">{t("About AgentCity")}<ArrowRight size={13}/></Link></footer>
      </>}

      {city&&view==="scenarios"&&<ScenarioList rows={context?.scenarios??[]} t={t} start={id=>{if(permitted)void startSaved(id);}}
        reuse={initial=>{if(permitted)setForm({initial,research:true});}}/>}
      {city&&view==="research"&&core&&!core.features.research&&<Empty title={t("Research is disabled in this workspace")}/>}
      {city&&["simulations","reports"].includes(view)&&<>
        {decision}<RunList runs={context?.runs??[]} t={t} open={id=>void loadRun(id)} report={view==="reports"}/>
      </>}
      {city&&view==="research"&&core?.features.research&&<>
        <ResearchExperiments key={`${city.id}:${workspace}`} city={city.id} workspace={workspace} selected={experiment}
          select={setExperiment} canEdit={permitted} revision={context} t={t}
          addVariant={(experimentId,initial)=>setForm({experimentId,initial,research:true})}
          start={id=>void startSaved(id,true)} open={id=>void loadRun(id)}/>
        {decision}
        {core.features.modelLab&&<ModelLab key={city.id} city={city.id} providers={providers} t={t} canUse={permitted}/>}
      </>}
      {city&&view==="agents"&&<AgentList agents={agents} t={t} open={id=>void loadAgent(id)}/>}
      {city&&view==="sensors"&&core?.features.telemetry&&<SensorCoverage key={city.id} city={city.id} locate={locate} t={t}/>}
      {city&&["sensors","environment"].includes(view)&&<SensorList key={view} items={context?.sensors??[]} locate={locate} t={t} environment={view==="environment"}/>}
      {city&&view==="mobility"&&<MobilityView routes={context?.transit??[]} vehicles={context?.vehicles??[]} locate={locate}
        t={t} open={route=>{
          const feature=context?.layers.features.find(item=>item.geometry.type==="LineString"&&
            item.properties?.route_id===route.route_id&&item.properties?.source_id===route.id.split(":")[0]);
          if(route.route_id&&feature?.geometry.type==="LineString") {
            const coordinates=feature.geometry.coordinates[Math.floor(feature.geometry.coordinates.length/2)];
            locate([coordinates[0],coordinates[1]]);
          } else navigate("twin");
        }}/>}
      {city&&core&&user&&view==="settings"&&<SettingsView user={user} city={city} workspaces={core.workspaces} policy={core.policy}
        providers={providers} agents={agents} refresh={refresh} updateUser={value=>{setLanguageOverride(null);updateUser(value);reloadContext();}}
        t={t} features={core.features} layers={context?.layers.layers??[]}/>}

      {city&&form&&<Dialog open title={t(form.experimentId?"Add scenario variant":"Create scenario")} close={()=>setForm(null)} wide>
        <ScenarioForm t={t} city={city} coordinates={form.initial?null:promptPoint} initial={form.initial} research={form.research} providers={providers}
          agents={agents} onSubmit={submitScenario} renderMap={(value,pick)=><CityMap city={city} data={context?.layers??null}
            incidents={incidents} selected={value} select={pick} mode="Current" t={t} startPicking/>}/></Dialog>}
      {activity&&<Dialog open title={activity.name} close={()=>setActivity(null)} wide><Audit events={activity.events} t={t}/></Dialog>}
      <Dialog open={popup==="activity"} title={t("Agent Activity")} close={closePopup} wide>
        {run?.execution&&<ExecutionPlan plan={run.execution} t={t}/>}
        {events.length>0?<Audit events={events} t={t}/>:<><Empty title={t("No active run")} description={t("Analyze a scenario to watch specialist agents collaborate.")}/>
          <button className="button secondary" onClick={()=>navigate("agents")}><Bot size={16}/>{t("Browse agents")}</button></>}
      </Dialog>
      <Dialog open={popup==="search"} title={t("Search")} close={closePopup}>
        <div className="search-input"><Search size={19}/><input autoFocus value={query} onChange={event=>setQuery(event.target.value)}
          placeholder={t("Search cities, views, and data")} aria-label={t("Search cities, views, and data")}/></div>
        <div className="search-results">{searchTerms.map(item=><button key={item.key} onClick={item.act}>
          <span>{item.label}<small>{item.detail}</small></span><ChevronRight size={16}/></button>)}
          {!searchTerms.length&&<Empty title={t("No matches")}/>}</div>
      </Dialog>
      <Dialog open={popup==="language"} title={t("Language")} close={closePopup}>
        <LanguageOptions language={language} change={value=>void switchLanguage(value)}/>
      </Dialog>
      <Dialog open={popup==="notifications"} title={t("Notifications")} close={closePopup}>
        {!core?.features.notifications||!user?.preferences.notifications||!context?.notices.length?<Empty title={t("No notifications")}/>:<div className="search-results">
          {context.notices.some(row=>row.unread)&&<button className="button secondary fit" onClick={()=>{
            void api("/notification-settings/read","POST").then(reloadContext).catch(value=>setActionError(messageOf(value)));
          }}>{t("Mark all as read")}</button>}
          {context.notices.map(item=><div key={item.id}><span className="icon-tile"><Sparkles size={16}/></span><span>{t(item.text)}
            <small>{t(item.type)}{item.time&&` · ${item.time.includes("T")?new Date(item.time).toLocaleString():item.time}`}</small></span></div>)}</div>}
      </Dialog>
      <Dialog open={popup==="user"} title={t("My account")} close={closePopup}>
        <div className="account-menu"><p><strong>{user?.name}</strong><span>{t(user?.role??"Viewer")}</span></p>
          <label className="mobile-workspace-choice">{t("Workspace")}<select value={workspace} onChange={event=>changeContext(event.target.value,"workspace")}>
            {(core?.workspaces??[]).map(item=><option key={item.id} value={item.id}>{t(item.name)}</option>)}</select></label>
          {user?.demo?<Link className="button primary" href="/account"><LogIn size={16}/>{t("Sign in")}</Link>
            :<button className="button secondary" onClick={()=>void signOut()}><LogOut size={16}/>{t("Sign out")}</button>}
          <button className="button secondary" onClick={()=>navigate("settings")}><Globe2 size={16}/>{t("Preferences")}</button>
          <Link className="button secondary" href="/welcome"><CircleHelp size={16}/>{t("About AgentCity")}</Link></div>
      </Dialog>
    </main>
  </div>;
}

