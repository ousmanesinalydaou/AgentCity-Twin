"use client";

import { useCallback, useEffect, useState, type FormEvent, type ReactNode } from "react";
import { Activity, Bell, ClipboardList, Database, Gauge, Globe2, KeyRound, Radio, Save, Settings2, Users } from "lucide-react";
import type { Agent, City, Features, Policy, Preferences, Provider, RoutingPolicy, User, Workspace } from "@/lib/types";
import { api, messageOf } from "@/lib/api";
import { languages, type Translate } from "@/i18n";
import { Empty, ErrorText } from "./ui";
import { AdminActivity, ApiCredentials, CalibrationSettings, DeliverySettings, FeedSettings, IdentitySettings, InvitationSettings } from "./operations";

type Props = {user:User;city:City;workspaces:Workspace[];policy:Policy;providers:Provider[];agents:Agent[];
  refresh:()=>Promise<void>;updateUser:(user:User)=>void;t:Translate;layers:string[];features:Features};
const roles = ["Organization Admin","City Operator","Analyst","Researcher","Developer","Viewer"];
const providerKinds = ["openai","azure","foundry","gemini","anthropic","lmstudio","ollama","compatible","custom"];
const defaultProvider:Provider = {id:"",name:"",kind:"ollama",url:"",model:"",deployment:"",version:"",organization:"",
  enabled:true,local:true,default:false,priority:10,timeout:15,max_tokens:512,context_window:8192,temperature:.2,capabilities:["structured"],secret:""};

function useAction(t:Translate) {
  const [feedback,setFeedback] = useState<{error:boolean;text:string}|null>(null);
  const [busy,setBusy] = useState(false);
  async function perform(action:()=>Promise<unknown>, success="Changes saved.") {
    setBusy(true);setFeedback(null);
    try { await action();setFeedback({error:false,text:t(success)}); }
    catch(error){setFeedback({error:true,text:messageOf(error)});}
    finally{setBusy(false);}
  }
  const status = feedback ? feedback.error?<ErrorText message={feedback.text}/>:<p className="success-note" role="status">{feedback.text}</p> : null;
  return {perform,busy,status};
}

function Section({title,children}: {title:string;children:ReactNode}) {
  return <section className="panel settings-section"><h2>{title}</h2>{children}</section>;
}
function Fields({children,action,t,busy,label="Save"}: {children:ReactNode;action:(event:FormEvent<HTMLFormElement>)=>void;t:Translate;busy:boolean;label?:string}) {
  return <form className="form-stack" onSubmit={event=>{event.preventDefault();action(event);}}>{children}
    <button className="button primary fit" disabled={busy}><Save size={16}/>{t(busy?"Working…":label)}</button>
  </form>;
}

function General({user,updateUser,t}:Props) {
  const [values,setValues] = useState<Preferences>(user.preferences);
  const {perform,busy,status} = useAction(t);
  return <><Section title={t("Account profile")}>
    <Fields action={event=>{
      const values=new FormData(event.currentTarget);
      void perform(async()=>updateUser(await api<User>("/auth/profile","PATCH",{name:values.get("name")})));
    }} t={t} busy={busy}><div className="form-grid"><label>{t("Name")}<input name="name" defaultValue={user.name} minLength={2} maxLength={100} required/></label>
      {!user.demo&&<label>{t("Email address")}<input type="email" value={user.email} readOnly/></label>}</div></Fields>
    {!user.demo&&<IdentitySettings t={t}/>}
  </Section><Section title={t("Preferences")}>
    <Fields action={()=>void perform(async()=>updateUser(await api<User>("/auth/preferences","PATCH",values)))} t={t} busy={busy}>
      <div className="form-grid">
        <label>{t("Language")}<select value={values.language} onChange={e=>setValues({...values,language:e.target.value as Preferences["language"]})}>
          {Object.entries(languages).map(([id,name])=><option key={id} value={id}>{name}</option>)}</select></label>
        <label>{t("Theme")}<select value={values.theme} onChange={e=>setValues({...values,theme:e.target.value as Preferences["theme"]})}>
          {["dark","light","system"].map(item=><option key={item} value={item}>{t(item[0].toUpperCase()+item.slice(1))}</option>)}</select></label>
      </div>
      <label className="check-label"><input type="checkbox" checked={values.notifications} onChange={e=>setValues({...values,notifications:e.target.checked})}/>{t("Show in-app notifications")}</label>
    </Fields>{status}
  </Section></>;
}

function PolicyForm({policy,refresh,t}:Props) {
  const [values,setValues]=useState(policy);
  const {perform,busy,status}=useAction(t);
  const routing=values.model_routing??{max_cost_per_million:null,prefer_low_cost:false,require_language_match:false,prefer_advanced:true};
  const changeRouting=<K extends keyof RoutingPolicy>(key:K,value:RoutingPolicy[K])=>
    setValues(previous=>({...previous,model_routing:{...routing,[key]:value}}));
  return <Section title={t("Simulation policy")}>
    <Fields action={()=>void perform(async()=>{await api("/settings/policy","PUT",values);await refresh();})} t={t} busy={busy}>
      <label className="check-label"><input type="checkbox" checked={values.allow_cloud} onChange={e=>setValues({...values,allow_cloud:e.target.checked})}/>{t("Allow cloud model execution")}</label>
      <label>{t("Basemap style")}<select value={values.map_style??"local"} onChange={e=>setValues({...values,map_style:e.target.value})}>
        {["local","fiord","dark","liberty"].map(style=><option key={style}>{style}</option>)}
      </select></label>
      <h3>{t("Scoring weights")}</h3><div className="form-grid">
        {Object.entries(values.weights).map(([key,value])=><label key={key}>{t(key)}<input type="number" min={0} max={100} value={value}
          onChange={e=>setValues({...values,weights:{...values.weights,[key]:+e.target.value}})}/></label>)}</div>
      <h3>{t("Model routing policy")}</h3>
      <label>{t("Maximum estimated USD per million tokens")}
        <input type="number" min={0} max={1000000} step="any" value={routing.max_cost_per_million??""}
          onChange={event=>changeRouting("max_cost_per_million",event.target.value===""?null:Number(event.target.value))}/></label>
      <div className="check-grid">{([
        ["prefer_low_cost","Prefer lower estimated model cost"],["require_language_match","Require a declared language match"],
        ["prefer_advanced","Match model reasoning tier to task complexity"],
      ] as const).map(([key,label])=><label key={key}><input type="checkbox" checked={routing[key]}
        onChange={event=>changeRouting(key,event.target.checked)}/>{t(label)}</label>)}</div>
    </Fields>{status}
  </Section>;
}

function Providers({providers,refresh,t}:Props) {
  const [form,setForm]=useState<Provider>(defaultProvider);
  const {perform,busy,status}=useAction(t);
  const change = <K extends keyof Provider>(key:K,value:Provider[K])=>setForm(fields=>({...fields,[key]:value}));
  return <Section title={t("Model providers")}>
    <div className="provider-list">{providers.map(row=><article key={row.id}><div><strong>{row.name}</strong><small>{row.model} · {t(row.local?"Local":"Cloud")} · {t(row.enabled?"Enabled":"Disabled")}</small></div>
      {!row.environment&&<button className="button secondary compact" onClick={()=>setForm({...row,secret:""})}>{t("Edit")}</button>}
      <button className="button secondary compact" disabled={busy} onClick={()=>void perform(async()=>{await api(`/providers/${row.id}/test`,"POST");},"Connection verified.")}>{t("Test")}</button></article>)}</div>
    <Fields action={()=>void perform(async()=>{await api("/providers","PUT",form);setForm(defaultProvider);await refresh();})} t={t} busy={busy}>
      <h3>{t("Add or edit provider")}</h3>
      <div className="form-grid">
        {(["id","name","model","url","deployment","version","organization"] as const).map(key=><label key={key}>{t(({id:"Provider ID",name:"Name",model:"Model",url:"Base URL",deployment:"Deployment",version:"API version",organization:"Organization"})[key])}
          <input value={form[key]} onChange={e=>change(key,e.target.value)} required={["id","name","model"].includes(key)} maxLength={key==="url"?512:160}/></label>)}
        <label>{t("Provider type")}<select value={form.kind} onChange={e=>change("kind",e.target.value)}>{providerKinds.map(value=><option key={value}>{value}</option>)}</select></label>
        <label>{t("API credential")}<input type="password" autoComplete="new-password" value={form.secret??""} onChange={e=>change("secret",e.target.value)} maxLength={2048}/></label>
        <label>{t("Estimated USD per million tokens")}<input type="number" min={0} max={1000000} step="any" value={form.cost_per_million??""}
          onChange={event=>change("cost_per_million",event.target.value===""?null:Number(event.target.value))}/></label>
        <label>{t("Reasoning tier")}<select value={form.reasoning_tier??"standard"} onChange={event=>change("reasoning_tier",event.target.value as Provider["reasoning_tier"])}>
          <option value="standard">{t("Standard")}</option><option value="advanced">{t("Advanced")}</option>
        </select></label>
        {([["priority","Priority",0,1000,1],["timeout","Timeout (s)",2,45,1],["max_tokens","Maximum tokens",64,8192,1],
           ["context_window","Context window",512,2000000,1],["temperature","Temperature",0,1,.1]] as const).map(([key,label,min,max,step])=><label key={key}>
          {t(label)}<input type="number" value={form[key]} min={min} max={max} step={step} onChange={e=>change(key,+e.target.value)}/></label>)}
      </div>
      <fieldset className="check-grid"><legend>{t("Declared model languages")}</legend>
        {(Object.keys(languages) as Preferences["language"][]).map(code=><label key={code}>
          <input type="checkbox" checked={form.languages?.includes(code)??false} onChange={event=>change("languages",
            event.target.checked?[...(form.languages??[]),code]:(form.languages??[]).filter(item=>item!==code))}/>{languages[code]}</label>)}
      </fieldset>
      <fieldset className="check-grid"><legend>{t("Capabilities")}</legend>{["structured","vision","tools","embeddings","streaming"].map(capability=>
        <label key={capability}><input type="checkbox" checked={form.capabilities.includes(capability)} onChange={e=>change("capabilities",
          e.target.checked?[...form.capabilities,capability]:form.capabilities.filter(item=>item!==capability))}/>{t(capability)}</label>)}</fieldset>
      <div className="check-grid">{(["enabled","local","default"] as const).map(key=><label key={key}><input type="checkbox" checked={form[key]} onChange={e=>change(key,e.target.checked)}/>{t(({enabled:"Enabled",local:"Local execution",default:"Default provider"})[key])}</label>)}</div>
    </Fields>{status}
  </Section>;
}

function AgentConfiguration({agents,providers,refresh,t}:Props) {
  const [form,setForm]=useState<Agent>(agents[0]);
  const {perform,busy,status}=useAction(t);
  if(!form)return <Empty title={t("No agents available")}/>;
  const change = <K extends keyof Agent>(key:K,value:Agent[K])=>setForm(fields=>({...fields,[key]:value}));
  return <Section title={t("Agent configuration")}>
    <Fields action={()=>void perform(async()=>{await api(`/agents/${form.id}`,"PUT",form);await refresh();})} t={t} busy={busy}>
      <label>{t("Agent")}<select value={form.id} onChange={e=>setForm(agents.find(row=>row.id===e.target.value)!)}>{agents.map(row=><option key={row.id} value={row.id}>{row.name}</option>)}</select></label>
      <div className="form-grid">
        <label>{t("Name")}<input value={form.name} onChange={e=>change("name",e.target.value)} required/></label>
        <label>{t("Preferred model")}<select value={form.preferred} onChange={e=>change("preferred",e.target.value)}><option value="">{t("Use workspace routing")}</option>{providers.map(p=><option key={p.id} value={p.id}>{p.name} · {p.model}</option>)}</select></label>
        <label>{t("Description")}<input value={form.description} onChange={e=>change("description",e.target.value)} maxLength={200}/></label>
        <label>{t("Fallback provider IDs")}<input value={form.fallbacks.join(",")} onChange={e=>change("fallbacks",e.target.value.split(",").slice(0,3))}/></label>
        <label>{t("Tools")}<input value={form.tools.join(",")} onChange={e=>change("tools",e.target.value.split(","))}/></label>
        <label>{t("Allowed data")}<input value={form.allowed_data.join(",")} onChange={e=>change("allowed_data",e.target.value.split(","))}/></label>
        {([["priority","Priority",0,1000,1],["timeout","Timeout (s)",2,45,1],["temperature","Temperature",0,1,.1],["max_iterations","Maximum iterations",1,3,1]] as const).map(([key,label,min,max,step])=>
          <label key={key}>{t(label)}<input type="number" value={form[key]} min={min} max={max} step={step} onChange={e=>change(key,+e.target.value)}/></label>)}
      </div>
      <label>{t("System instruction")}<textarea rows={4} value={form.instruction} onChange={e=>change("instruction",e.target.value)} required maxLength={2000}/></label>
      <label className="check-label"><input type="checkbox" checked={form.enabled} onChange={e=>change("enabled",e.target.checked)}/>{t("Enabled")}</label>
    </Fields>{status}
  </Section>;
}

type Source = {id:string;city_id:string;name:string;layer:string;format:string;feature_count:number;route_count:number};
function encodedArchive(file:File) {
  return new Promise<string>((resolve,reject)=>{
    const reader=new FileReader();
    reader.onload=()=>resolve(String(reader.result).split(",")[1]);
    reader.onerror=()=>reject(reader.error);
    reader.readAsDataURL(file);
  });
}

function DataSettings({city,layers,refresh,t}:Props) {
  const [rows,setRows] = useState<Source[]>([]);
  const [error,setError] = useState("");
  const [format,setFormat] = useState("geojson");
  const [pendingRemoval,setPendingRemoval] = useState<string|null>(null);
  const {perform,busy,status}=useAction(t);
  const load=useCallback(()=>api<Source[]>("/data-sources").then(setRows).catch(err=>setError(messageOf(err))),[]);
  useEffect(()=>{void load();},[load]);
  return <>
    <Section title={t("Data sources")}>
      <ErrorText message={error}/>
      {rows.length>0&&<ul className="simple-list">{rows.map(row=><li key={row.id}><strong>{row.name}</strong>
        <span>{row.city_id} · {t(row.layer)} · {row.feature_count} {t("features")}{!!row.route_count&&<> · {row.route_count} {t("routes")}</>}</span>
        {pendingRemoval===row.id?<div className="form-actions">
          <button className="button secondary compact" disabled={busy} onClick={()=>void perform(async()=>{
            await api(`/data-sources/${row.id}`,"DELETE");setPendingRemoval(null);await load();await refresh();
          })}>{t("Confirm removal")}</button>
          <button className="button secondary compact" onClick={()=>setPendingRemoval(null)}>{t("Cancel")}</button>
        </div>:<button className="button secondary compact" onClick={()=>setPendingRemoval(row.id)}>{t("Remove source")}</button>}
      </li>)}</ul>}
      <Fields action={event=>{
        const data = new FormData(event.currentTarget);
        void perform(async()=>{
          const file = data.get("file") as File;
          const zipped=format==="gtfs-zip";
          if (!file.size||file.size>(zipped?1_400_000:1_500_000)) {
            throw new Error(t(zipped?"Choose a GTFS ZIP under 1.4 MB.":"Choose a file under 1.5 MB."));
          }
          const raw=zipped?await encodedArchive(file):await file.text();
          const content=["geojson","json"].includes(format)?JSON.parse(raw):raw;
          await api("/data-sources","POST",{city_id:city.id,name:data.get("name"),layer:zipped?"Transit":data.get("layer"),format,content});
          await load();await refresh();
        },"Data source imported.");
      }} t={t} busy={busy} label="Import">
        <p>{city.name} · {t("Imported features appear on the selected map layer.")}</p>
        <div className="form-grid"><label>{t("Name")}<input name="name" required minLength={2} maxLength={100}/></label>
          <label>{t("Layer")}<select name="layer" disabled={format==="gtfs-zip"} key={format==="gtfs-zip"?"transit":"manual"}
            defaultValue={format==="gtfs-zip"?"Transit":undefined}>{layers.map(row=><option key={row} value={row}>{t(row)}</option>)}</select></label>
          <label>{t("Format")}<select value={format} onChange={event=>setFormat(event.target.value)}>
            <option value="geojson">GeoJSON</option><option value="csv">CSV</option><option value="json">JSON</option>
            <option value="gtfs">{t("GTFS shapes text")}</option><option value="gtfs-zip">{t("GTFS Schedule ZIP")}</option>
          </select></label>
          <label>{t("File")}<input key={format} type="file" name="file" accept={format==="gtfs-zip"?".zip":".geojson,.json,.csv,.txt"} required/></label>
        </div>
      </Fields>{status}
    </Section>
    <Section title={t("Add a city")}><Fields action={event=>{
      const form=new FormData(event.currentTarget);
      void perform(async()=>{const graph=String(form.get("graph")||"");
        await api("/cities","POST",{...(graph?JSON.parse(graph):{}),id:form.get("id"),name:form.get("name"),country:form.get("country"),
          center:[Number(form.get("lng")),Number(form.get("lat"))],timezone:form.get("timezone")});await refresh();},"City added.");
    }} t={t} busy={busy} label="Add city">
      <div className="form-grid">{[["id","City ID"],["name","Name"],["country","Country"],["timezone","Time zone"]].map(([name,label])=><label key={name}>
        {t(label)}<input name={name} defaultValue={name==="timezone"?"UTC":undefined} required/></label>)}
        <label>{t("Latitude")}<input type="number" step="any" min="-85" max="85" name="lat" required/></label>
        <label>{t("Longitude")}<input type="number" step="any" min="-180" max="180" name="lng" required/></label></div>
      <label>{t("Simulation graph JSON (optional)")}<textarea name="graph" placeholder='{"nodes":{},"edges":[],"demand":[]}' rows={3}/></label>
    </Fields>{status}</Section>
  </>;
}

type Team = {id:string;name:string;members:string[]};
function Organization({user,workspaces,refresh,t}:Props) {
  const [name,setName]=useState("");
  const [members,setMembers]=useState<User[]>([]);
  const [teams,setTeams]=useState<Team[]>([]);
  const [editingTeam,setEditingTeam]=useState<Team|null>(null);
  const [removingTeam,setRemovingTeam]=useState<string|null>(null);
  const [renamingWorkspace,setRenamingWorkspace]=useState<Workspace|null>(null);
  const [issue,setIssue]=useState("");
  const {perform,busy,status}=useAction(t);
  const load=useCallback(async()=>{
    await Promise.all([api<{name:string}>("/organizations"),api<User[]>("/users"),api<Team[]>("/teams")]).then(([profile,people,teamList])=>{
      setName(profile.name);setMembers(people);setTeams(teamList);
    }).catch(error=>setIssue(messageOf(error)));
  },[]);
  useEffect(()=>{void load();},[load]);
  return <>
    <Section title={t("Organization")}><ErrorText message={issue}/>
      <Fields action={()=>void perform(async()=>{await api("/organizations","PATCH",{name});})} t={t} busy={busy}><label>{t("Name")}
        <input value={name} onChange={e=>setName(e.target.value)} required minLength={2}/></label></Fields>{status}
    </Section>
    <Section title={t("Workspaces")}>
      <ul className="simple-list">{workspaces.map(row=><li key={row.id}><strong>{t(row.name)}</strong><span>{row.id}</span>
        <button className="button secondary compact" onClick={()=>setRenamingWorkspace(row)}>{t("Rename")}</button></li>)}</ul>
      {renamingWorkspace&&<Fields key={renamingWorkspace.id} action={event=>{
        const data=new FormData(event.currentTarget);
        void perform(async()=>{await api(`/workspaces/${renamingWorkspace.id}`,"PATCH",{name:data.get("name")});setRenamingWorkspace(null);await refresh();});
      }} t={t} busy={busy} label="Save workspace name">
        <label>{t("Workspace name")}<input name="name" defaultValue={renamingWorkspace.name} required minLength={2} maxLength={100}/></label>
        <button type="button" className="button secondary fit" onClick={()=>setRenamingWorkspace(null)}>{t("Cancel")}</button>
      </Fields>}
      <Fields action={e=>{const data=new FormData(e.currentTarget);void perform(async()=>{await api("/workspaces","POST",Object.fromEntries(data));await refresh();});}} t={t} busy={busy} label="Add workspace">
        <div className="form-grid"><label>{t("Workspace ID")}<input name="id" pattern="[a-z0-9-]+" required/></label><label>{t("Name")}<input name="name" required minLength={2}/></label></div>
      </Fields>{status}
    </Section>
    <Section title={t("Members and roles")}>
      <ul className="simple-list">{members.map(row=><li key={row.id}><strong>{row.name || row.email}</strong>
        {row.id===user.id||row.role==="Super Admin"?<span>{t(row.role)}</span>:<><select aria-label={row.name+" role"} value={row.role} disabled={busy}
          onChange={e=>void perform(async()=>{await api(`/users/${row.id}`,"PATCH",{role:e.target.value,disabled:row.disabled??false});await load();})}>
          {roles.map(role=><option key={role}>{role}</option>)}</select>
          <button className="button secondary compact" disabled={busy} onClick={()=>void perform(async()=>{await api(`/users/${row.id}`,"PATCH",{role:row.role,disabled:!row.disabled});await load();})}>{t(row.disabled?"Enable":"Disable")}</button></>}</li>)}</ul>
      <Fields action={e=>{const data=new FormData(e.currentTarget);void perform(async()=>{await api("/users","POST",Object.fromEntries(data));await load();});}} t={t} busy={busy} label="Add member">
        <div className="form-grid"><label>{t("Name")}<input name="name" required/></label><label>{t("Email address")}<input name="email" type="email" required/></label>
          <label>{t("Temporary password")}<input name="password" type="password" minLength={10} autoComplete="new-password" required/></label>
          <label>{t("Role")}<select name="role" defaultValue="Viewer">{roles.map(role=><option key={role}>{role}</option>)}</select></label></div>
      </Fields>{status}
    </Section>
    <Section title={t("Teams")}>
      <ul className="simple-list">{teams.map(row=><li key={row.id}><strong>{row.name}</strong><span>{row.members.length} {t("members")}</span>
        {removingTeam===row.id?<div className="form-actions">
          <button className="button secondary compact" disabled={busy} onClick={()=>void perform(async()=>{
            await api(`/teams/${row.id}`,"DELETE");setRemovingTeam(null);
            if(editingTeam?.id===row.id)setEditingTeam(null);
            await load();
          })}>{t("Confirm removal")}</button>
          <button className="button secondary compact" onClick={()=>setRemovingTeam(null)}>{t("Cancel")}</button>
        </div>:<div className="form-actions">
          <button className="button secondary compact" onClick={()=>setEditingTeam(row)}>{t("Edit team")}</button>
          <button className="button secondary compact" onClick={()=>setRemovingTeam(row.id)}>{t("Remove team")}</button>
        </div>}
      </li>)}</ul>
      <Fields key={editingTeam?.id??"new"} action={event=>{
        const form=event.currentTarget;
        const data=new FormData(form);
        void perform(async()=>{
          await api("/teams","PUT",{id:data.get("id"),name:data.get("name"),members:data.getAll("members")});
          form.reset();setEditingTeam(null);await load();
        });
      }} t={t} busy={busy} label="Save team">
        <div className="form-grid">
          <label>{t("Team ID")}<input name="id" pattern="[a-z0-9-]+" maxLength={48} readOnly={!!editingTeam} defaultValue={editingTeam?.id} required/></label>
          <label>{t("Name")}<input name="name" required minLength={2} maxLength={100} defaultValue={editingTeam?.name}/></label>
        </div>
        <fieldset className="check-grid"><legend>{t("Members")}</legend>{members.map(row=><label key={row.id}>
          <input type="checkbox" name="members" value={row.id} defaultChecked={editingTeam?.members.includes(row.id)}/>{row.name}
        </label>)}</fieldset>
        {editingTeam&&<button type="button" className="button secondary fit" onClick={()=>setEditingTeam(null)}>{t("Cancel")}</button>}
      </Fields>{status}
    </Section>
  </>;
}

function Health({t}: {t:Translate}) {
  const [result,setResult] = useState<{status:string;database:string;demo:boolean}|null>(null);
  const [error,setError]=useState("");
  const read=useCallback(()=>api<{status:string;database:string;demo:boolean}>("/health").then(setResult).catch(error=>setError(messageOf(error))),[]);
  useEffect(()=>{void read();},[read]);
  return <Section title={t("System health")}><ErrorText message={error}/>
    {result&&<dl className="fact-grid"><div><dt>{t("API")}</dt><dd>{result.status}</dd></div><div><dt>{t("Database")}</dt><dd>{result.database}</dd></div>
      <div><dt>{t("Demo workspace")}</dt><dd>{t(result.demo?"Enabled":"Disabled")}</dd></div></dl>}
    <div className="form-actions"><button className="button secondary" onClick={()=>{setError("");void read();}}><Activity size={16}/>{t("Refresh")}</button>
      <a className="button secondary" href="/api-docs" target="_blank" rel="noreferrer">{t("API documentation")}</a></div>
  </Section>;
}

export function SettingsView(props:Props) {
  const [tab,setTab]=useState("preferences");
  const admin = !props.user.demo&&["Super Admin","Organization Admin"].includes(props.user.role);
  const choices = [{key:"preferences",text:"Preferences",icon:Globe2},{key:"health",text:"System health",icon:Activity},
    ...(admin?[{key:"policy",text:"Simulation policy",icon:Settings2},{key:"providers",text:"Model providers",icon:KeyRound},
      {key:"agents",text:"Agent configuration",icon:ClipboardList},{key:"data",text:"Data sources",icon:Database},
      {key:"organization",text:"Organization",icon:Users},{key:"invitations",text:"Invitations",icon:Users},
      {key:"feeds",text:"Live data feeds",icon:Radio},{key:"calibration",text:"Simulation calibration",icon:Gauge},
      {key:"delivery",text:"Notification delivery",icon:Bell},{key:"credentials",text:"API credentials",icon:KeyRound},
      {key:"operations",text:"Operations",icon:Activity}]:[])];
  return <div className="settings-view"><div className="tabbar">{choices.map(({key,text,icon:Icon})=>
    <button key={key} className={tab===key?"selected":""} aria-pressed={tab===key} onClick={()=>setTab(key)}><Icon size={16}/>{props.t(text)}</button>)}</div>
    {tab==="preferences"&&<General key={props.user.preferences.language+"-"+props.user.preferences.theme} {...props}/>}
    {tab==="health"&&<Health t={props.t}/>}
    {admin&&tab==="policy"&&<PolicyForm {...props}/>}
    {admin&&tab==="providers"&&<Providers {...props}/>}
    {admin&&tab==="agents"&&<AgentConfiguration {...props}/>}
    {admin&&tab==="data"&&<DataSettings {...props}/>}
    {admin&&tab==="organization"&&<Organization {...props}/>}
    {admin&&tab==="invitations"&&<InvitationSettings t={props.t}/>}
    {admin&&tab==="feeds"&&<FeedSettings key={props.city.id} city={props.city} t={props.t}/>}
    {admin&&tab==="calibration"&&<CalibrationSettings key={props.city.id} city={props.city} t={props.t}/>}
    {admin&&tab==="delivery"&&<DeliverySettings t={props.t}/>}
    {admin&&tab==="credentials"&&<ApiCredentials t={props.t}/>}
    {admin&&tab==="operations"&&<AdminActivity features={props.features} onChange={()=>void props.refresh()} t={props.t}/>}
  </div>;
}

