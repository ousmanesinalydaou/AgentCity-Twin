"use client";

import { useCallback, useEffect, useState, type FormEvent, type ReactNode } from "react";
import { Activity, Bell, Copy, Gauge, KeyRound, Link2, Radio, RefreshCw, Users } from "lucide-react";
import type { Translate } from "@/i18n";
import { api, messageOf } from "@/lib/api";
import type { City, Features } from "@/lib/types";
import { Empty, ErrorText } from "./ui";

function Surface({ title, icon, children }: {title:string; icon:ReactNode; children:ReactNode}) {
  return <section className="panel settings-section"><div className="operations-heading"><span className="icon-tile">{icon}</span>
    <h2>{title}</h2></div>{children}</section>;
}

function useResource<T>(path:string) {
  const [data,setData]=useState<T|null>(null);
  const [error,setError]=useState("");
  const [busy,setBusy]=useState(false);
  const [feedback,setFeedback]=useState("");
  const refresh=useCallback(()=>api<T>(path).then(setData).catch(value=>setError(messageOf(value))),[path]);
  useEffect(()=>{void refresh();},[refresh]);
  async function act(request:()=>Promise<unknown>, message:string) {
    setBusy(true);setFeedback("");setError("");
    try {await request();await refresh();setFeedback(message);}
    catch(value){setError(messageOf(value));}
    finally{setBusy(false);}
  }
  return {data,error,busy,feedback,act,refresh};
}

type Credential = {id:string;name:string;scopes:string[];expires_at:string};
const accessScopes:Record<string,string> = {
  "city:read":"Read city data", "research:read":"Read experiments and scenarios", "reports:read":"Read simulation reports",
};

export function ApiCredentials({t}: {t:Translate}) {
  const resource=useResource<Credential[]>("/api-credentials");
  const [token,setToken]=useState("");
  const [copied,setCopied]=useState(false);
  const [pending,setPending]=useState<string|null>(null);
  function create(event:FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form=event.currentTarget, fields=new FormData(form);
    const scopes=fields.getAll("scopes");
    setToken("");setCopied(false);
    void resource.act(async()=>{
      if(!scopes.length)throw new Error(t("Select at least one API permission."));
      const created=await api<{token:string}>("/api-credentials","POST",{
        name:fields.get("name"),days:Number(fields.get("days")),scopes,
      });
      setToken(created.token);form.reset();
    },"");
  }
  return <Surface title={t("API credentials")} icon={<KeyRound size={17}/>}>
    <ErrorText message={t(resource.error)}/>
    <form className="form-stack" onSubmit={create}>
      <div className="form-grid">
        <label>{t("Credential name")}<input name="name" minLength={3} maxLength={80} required/></label>
        <label>{t("Expires after days")}<input name="days" type="number" min={1} max={90} defaultValue={30} required/></label>
      </div>
      <fieldset className="check-grid"><legend>{t("API permissions")}</legend>{Object.entries(accessScopes).map(([scope,label])=>
        <label key={scope}><input name="scopes" type="checkbox" value={scope}/>{t(label)}</label>)}</fieldset>
      <button className="button primary fit" disabled={resource.busy}>{t("Create API credential")}</button>
    </form>
    {token&&<div className="form-stack inline-feedback">
      <label>{t("Copy this credential now. It is shown once.")}<input value={token} readOnly onFocus={event=>event.target.select()}/></label>
      <button className="button secondary fit" onClick={()=>void navigator.clipboard?.writeText(token).then(()=>setCopied(true),()=>setCopied(false))}>
        <Copy size={15}/>{t(copied?"Copied":"Copy credential")}</button>
    </div>}
    {!!resource.data?.length&&<ul className="simple-list">{resource.data.map(row=><li key={row.id}>
      <div><strong>{row.name}</strong><p>{row.scopes.map(scope=>t(accessScopes[scope]??scope)).join(" · ")}</p></div>
      <span>{t("Expires")} {new Date(row.expires_at).toLocaleDateString()}</span>
      {pending===row.id?<div className="form-actions">
        <button className="button secondary compact" disabled={resource.busy} onClick={()=>void resource.act(async()=>{
          await api(`/api-credentials/${row.id}`,"DELETE");setToken("");setPending(null);
        },t("Credential revoked."))}>{t("Confirm revocation")}</button>
        <button className="button secondary compact" onClick={()=>setPending(null)}>{t("Cancel")}</button>
      </div>:<button className="button secondary compact" onClick={()=>setPending(row.id)}>{t("Revoke")}</button>}
    </li>)}</ul>}
    {resource.feedback&&<p role="status" className="success-note">{resource.feedback}</p>}
  </Surface>;
}

type Feed = {id:string;name:string;city_id:string;kind:string;url:string;topic:string;username:string;interval:number;
  enabled:boolean;status:string;error:string;readings:number;vehicles:number;last_success:string|null};
const formats=["rest","websocket","mqtt","gtfs-realtime"];
const feedTypes:Record<string,string>={rest:"REST JSON",websocket:"WebSocket",mqtt:"MQTT","gtfs-realtime":"GTFS-Realtime"};

export function FeedSettings({city,t}: {city:City;t:Translate}) {
  const resource=useResource<Feed[]>("/telemetry/feeds");
  const [selected,setSelected]=useState<Feed|null>(null);
  const [kind,setKind]=useState("rest");
  function submit(event:FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form=new FormData(event.currentTarget);
    void resource.act(async()=>{
      await api(selected?`/telemetry/feeds/${selected.id}`:"/telemetry/feeds",selected?"PUT":"POST",
        {city_id:city.id,kind,name:form.get("name"),url:form.get("url"),topic:form.get("topic")??"",
          username:form.get("username")??"",secret:form.get("secret")??"",interval:Number(form.get("interval")),
          enabled:form.has("enabled")});
      setSelected(null);setKind("rest");event.currentTarget?.reset();
    },t("Feed saved."));
  }
  return <Surface title={t("Live data feeds")} icon={<Radio size={19}/>}>
    <p className="settings-context">{city.name} · {t("Connect approved telemetry endpoints to the city workspace.")}</p>
    <ErrorText message={t(resource.error)}/>{resource.feedback&&<p className="success-note" role="status">{resource.feedback}</p>}
    <ul className="simple-list">{resource.data?.filter(row=>row.city_id===city.id).map(row=><li key={row.id}>
      <div className="record-text"><strong>{t(row.name)}</strong><small>{feedTypes[row.kind]??t("Simulated data")} · {t(row.status)} · {row.readings} {t("Readings")} · {row.vehicles} {t("Vehicles")}</small>
        {row.error&&<small>{t(row.error)}</small>}{row.last_success&&<small>{new Date(row.last_success).toLocaleString()}</small>}</div>
      {row.kind!=="simulated"&&<button className="button secondary compact" onClick={()=>{setSelected(row);setKind(row.kind);}}>{t("Edit")}</button>}
      {row.enabled&&<button className="button secondary compact" onClick={()=>void resource.act(
        ()=>api(`/telemetry/feeds/${row.id}`,"DELETE"),t("Feed paused."))}>{t("Disable")}</button>}
      <button className="button secondary compact" disabled={!row.enabled||resource.busy}
        onClick={()=>void resource.act(()=>api(`/telemetry/feeds/${row.id}/refresh`,"POST"),t("Refresh queued."))}>{t("Refresh feed")}</button>
    </li>)}</ul>
    <div className="form-actions"><button className="button secondary fit" onClick={()=>void resource.refresh()}><RefreshCw size={15}/>{t("Refresh status")}</button>
      {city.id==="debrecen"&&!resource.data?.some(row=>row.kind==="simulated"&&row.enabled)&&
        <button className="button secondary fit" disabled={resource.busy} onClick={()=>void resource.act(
          ()=>api("/telemetry/demo-feed","POST"),t("Feed saved."))}>{t("Start simulated feed")}</button>}
    </div>
    <form className="form-stack operations-form" key={selected?.id??"new"} onSubmit={submit}>
      <h3>{t(selected?"Edit feed":"Add feed")}</h3>
      <div className="form-grid">
        <label>{t("Name")}<input name="name" defaultValue={selected?.name} required minLength={2} maxLength={100}/></label>
        <label>{t("Adapter")}<select value={kind} onChange={event=>setKind(event.target.value)}>
          {formats.map(value=><option value={value} key={value}>{feedTypes[value]}</option>)}
        </select></label>
        <label>{t("Endpoint URL")}<input name="url" type="url" defaultValue={selected?.url} required maxLength={500}/></label>
        <label>{t("Poll interval (s)")}<input name="interval" type="number" min={10} max={3600} defaultValue={selected?.interval??60} required/></label>
        {kind==="mqtt"&&<><label>{t("MQTT topic")}<input name="topic" defaultValue={selected?.topic} required maxLength={180}/></label>
          <label>{t("Username")}<input name="username" defaultValue={selected?.username} maxLength={100}/></label></>}
        <label>{t("API credential")}<input name="secret" type="password" autoComplete="off" maxLength={2048}/></label>
        <label className="check-label"><input name="enabled" type="checkbox" defaultChecked={selected?.enabled??true}/>{t("Enabled")}</label>
      </div>
      <div className="form-actions"><button className="button primary" disabled={resource.busy}>{t("Save feed")}</button>
        {selected&&<button type="button" className="button secondary" onClick={()=>{setSelected(null);setKind("rest");}}>{t("Cancel")}</button>}</div>
    </form>
  </Surface>;
}

type Calibration = {source:string;trained_at:string;active:boolean;metrics:Record<string,{samples:number;mae:number;validation_samples:number}>};
export function CalibrationSettings({city,t}:{city:City;t:Translate}) {
  const resource=useResource<Calibration>(`/calibration/${city.id}`);
  return <Surface title={t("Simulation calibration")} icon={<Gauge size={19}/>}>
    <p className="settings-context">{t("Fit corrections and estimate intervals from held-out measurements.")}</p>
    <ErrorText message={t(resource.error)}/>{resource.feedback&&<p className="success-note" role="status">{resource.feedback}</p>}
    {resource.data&&<><p>{resource.data.source} · {new Date(resource.data.trained_at).toLocaleString()} · {t(resource.data.active?"Enabled":"Disabled")}</p>
      <ul className="simple-list">{Object.entries(resource.data.metrics).map(([name,value])=><li key={name}><strong>{t(name)}</strong>
        <span>{value.samples} {t("Paired observations")} · {t("Mean absolute error")} {value.mae}</span></li>)}</ul>
      <button className="button secondary" disabled={resource.busy} onClick={()=>void resource.act(
        ()=>api(`/calibration/${city.id}`,"PATCH",{active:!resource.data?.active}),t("Calibration updated."))}>{t(resource.data.active?"Disable":"Enable")}</button></>}
    <form className="form-stack operations-form" onSubmit={event=>{
      event.preventDefault();const fields=new FormData(event.currentTarget);
      void resource.act(async()=>{
        const upload=fields.get("file");
        if(!(upload instanceof File)||upload.size>1_500_000){throw new Error(t("Choose a file under 1.5 MB."));}
        await api(`/calibration/${city.id}`,"PUT",{source:fields.get("source"),observations:JSON.parse(await upload.text()),active:true});
      },t("Calibration fitted."));
    }}>
      <div className="form-grid"><label>{t("Data source")}<input name="source" minLength={2} maxLength={120} required/></label>
        <label>{t("Paired observations (JSON)")}<input name="file" type="file" accept=".json,application/json" required/></label></div>
      <button className="button primary fit" disabled={resource.busy}>{t("Fit calibration")}</button>
    </form>
  </Surface>;
}

type DeliveryInfo={channels:{id:string;name:string;kind:string;enabled:boolean}[];events:string[];
  history:{id:string;state:string;type:string;attempts:number}[]};
export function DeliverySettings({t}:{t:Translate}) {
  const resource=useResource<DeliveryInfo>("/notification-settings/channels");
  return <Surface title={t("Notification delivery")} icon={<Bell size={19}/>}>
    <ErrorText message={t(resource.error)}/>{resource.feedback&&<p className="success-note" role="status">{resource.feedback}</p>}
    <ul className="simple-list">{resource.data?.channels.map(row=><li key={row.id}><strong>{row.name}</strong><span>{t(row.kind)} · {t(row.enabled?"Enabled":"Disabled")}</span>
      {row.enabled&&<button className="button secondary compact" onClick={()=>void resource.act(
        ()=>api(`/notification-settings/channels/${row.id}`,"DELETE"),t("Channel disabled."))}>{t("Disable")}</button>}</li>)}</ul>
    <form className="form-stack" onSubmit={event=>{
      event.preventDefault();const fields=new FormData(event.currentTarget);
      void resource.act(()=>api("/notification-settings/channels","POST",{...Object.fromEntries(fields),events:fields.getAll("events")}),t("Channel saved."));
    }}>
      <div className="form-grid">
        <label>{t("Name")}<input name="name" required minLength={2} maxLength={100}/></label>
        <label>{t("Channel type")}<select name="kind">{["email","webhook","slack","teams","sms","push"].map(name=><option key={name} value={name}>{t(name)}</option>)}</select></label>
      </div>
      <label>{t("Destination")}<input type="password" autoComplete="off" name="destination" maxLength={1000} required/></label>
      <fieldset className="check-grid"><legend>{t("Events")}</legend>
        {resource.data?.events.map(name=><label key={name}><input type="checkbox" name="events" value={name}/>{t(name)}</label>)}
      </fieldset><button className="button primary fit" disabled={resource.busy}>{t("Add channel")}</button>
    </form>
    <details className="operations-form"><summary>{t("Delivery history")}</summary>
      <ul className="simple-list">{resource.data?.history.map(row=><li key={row.id}><strong>{t(row.type)}</strong><span>{t(row.state)} · {row.attempts}</span></li>)}</ul>
      <button className="button secondary compact" onClick={()=>void resource.refresh()}>{t("Refresh status")}</button>
    </details>
  </Surface>;
}

type Invitation={id:string;email:string;role:string;status:string;expires:number};
export function InvitationSettings({t}:{t:Translate}) {
  const resource=useResource<Invitation[]>("/invitations");
  const [url,setUrl]=useState("");
  const [copied,setCopied]=useState(false);
  return <Surface title={t("Organization invitations")} icon={<Users size={19}/>}>
    <ErrorText message={t(resource.error)}/>{resource.feedback&&<p className="success-note" role="status">{resource.feedback}</p>}
    <form className="form-stack" onSubmit={event=>{
      event.preventDefault();const fields=new FormData(event.currentTarget);setUrl("");setCopied(false);
      void resource.act(async()=>{
        const invitation=await api<{accept_url:string}>("/invitations","POST",{email:fields.get("email"),role:fields.get("role"),send_email:fields.has("emailDelivery")});
        setUrl(invitation.accept_url);
      },t("Invitation created."));
    }}>
      <div className="form-grid"><label>{t("Email address")}<input name="email" type="email" required maxLength={128}/></label>
        <label>{t("Role")}<select name="role" defaultValue="Viewer">
          {["Organization Admin","City Operator","Analyst","Researcher","Developer","Viewer"].map(role=><option value={role} key={role}>{t(role)}</option>)}
        </select></label></div>
      <label className="check-label"><input type="checkbox" name="emailDelivery"/>{t("Send invitation by email")}</label>
      <button className="button primary fit" disabled={resource.busy}>{t("Create invitation")}</button>
    </form>
    {url&&<div className="search-input operations-form"><input aria-label={t("Invitation link")} readOnly value={url}/>
      <button className="button secondary" onClick={()=>{void navigator.clipboard.writeText(url).then(()=>setCopied(true)).catch(()=>setCopied(false));}}>
        <Copy size={15}/>{t(copied?"Copied":"Copy link")}</button></div>}
    <ul className="simple-list">{resource.data?.map(row=><li key={row.id}><div className="record-text"><strong>{row.email}</strong>
      <small>{t(row.role)} · {t(row.status)}</small></div>
      {row.status==="pending"&&<button className="button secondary compact" onClick={()=>void resource.act(
        ()=>api(`/invitations/${row.id}`,"DELETE"),t("Invitation revoked."))}>{t("Revoke")}</button>}</li>)}</ul>
  </Surface>;
}

type AdminStatus={workers:number;active_jobs:number;events:{id:string;actor:string;action:string;resource:string;time:string}[]};
export function AdminActivity({features,onChange,t}:{features:Features;onChange:()=>void;t:Translate}) {
  const resource=useResource<AdminStatus>("/operations/admin");
  const [fields,setFields]=useState(features);
  return <Surface title={t("Workspace operations")} icon={<Activity size={19}/>}>
    <ErrorText message={t(resource.error)}/>{resource.feedback&&<p className="success-note" role="status">{resource.feedback}</p>}
    {!!resource.data&&<dl className="fact-grid"><div><dt>{t("Active workers")}</dt><dd>{resource.data.workers}</dd></div>
      <div><dt>{t("Active jobs")}</dt><dd>{resource.data.active_jobs}</dd></div></dl>}
    <form className="form-stack" onSubmit={event=>{
      event.preventDefault();void resource.act(async()=>{await api("/operations/features","PUT",fields);onChange();},t("Changes saved."));
    }}>
      <fieldset className="check-grid"><legend>{t("Workspace features")}</legend>
        {Object.entries(fields).map(([key,value])=><label key={key}><input type="checkbox" checked={value} onChange={event=>
          setFields(current=>({...current,[key]:event.target.checked}))}/>{t(key)}</label>)}
      </fieldset>
      <button className="button primary fit" disabled={resource.busy}>{t("Save")}</button>
    </form>
    <h3 className="operations-form">{t("Administration audit")}</h3>
    {!resource.data?.events.length&&<Empty title={t("No recorded changes")}/>}
    <ul className="simple-list">{resource.data?.events.map(event=><li key={event.id}>
      <div className="record-text"><strong>{event.actor} · {event.action}</strong><small>{event.resource}</small></div>
      <time>{new Date(event.time).toLocaleString()}</time></li>)}</ul>
    <button className="button secondary" onClick={()=>void resource.refresh()}><RefreshCw size={15}/>{t("Refresh status")}</button>
  </Surface>;
}

export function IdentitySettings({t}:{t:Translate}) {
  const {data}=useResource<{enabled:boolean}>("/auth/oidc/status");
  return data?.enabled?<a className="button secondary fit" href="/api/v1/auth/oidc/start?link=true"><Link2 size={16}/>{t("Link single sign-on")}</a>:null;
}

