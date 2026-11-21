"use client";

import { useEffect, useState, type FormEvent } from "react";
import { FileDown, Plus } from "lucide-react";
import type { Translate } from "@/i18n";
import { api, messageOf } from "@/lib/api";
import type { Experiment, ExperimentDetail, Scenario } from "@/lib/types";
import { Empty, ErrorText } from "./ui";

type Props = {
  city:string;workspace:string;selected:string|null;select:(id:string|null)=>void;canEdit:boolean;
  revision:unknown;t:Translate;addVariant:(id:string,initial?:Scenario)=>void;
  start:(id:string)=>void;open:(id:string)=>void;
};

export function ResearchExperiments({city,workspace,selected,select,canEdit,revision,t,addVariant,start,open}:Props) {
  const [rows,setRows] = useState<Experiment[]>([]);
  const [detail,setDetail] = useState<ExperimentDetail|null>(null);
  const [error,setError] = useState("");
  const [busy,setBusy] = useState(false);
  const [version,setVersion] = useState(0);

  useEffect(()=>{
    let current=true;
    const search=new URLSearchParams({city_id:city,workspace_id:workspace});
    api<Experiment[]>("/experiments?"+search).then(value=>{if(current)setRows(value);})
      .catch(value=>{if(current)setError(messageOf(value));});
    return ()=>{current=false;};
  },[city,workspace,version]);

  useEffect(()=>{
    if(!selected)return;
    let current=true;
    api<ExperimentDetail>("/experiments/"+selected).then(value=>{if(current)setDetail(value);})
      .catch(value=>{if(current)setError(messageOf(value));});
    return ()=>{current=false;};
  },[selected,version,revision]);

  async function save(event:FormEvent<HTMLFormElement>, existing?:Experiment) {
    event.preventDefault();
    const form=event.currentTarget;
    const fields=new FormData(form);
    const name=String(fields.get("name")).trim(), notes=String(fields.get("notes")).trim();
    setBusy(true);setError("");
    try {
      if(existing) {
        const toggle=(event.nativeEvent as SubmitEvent).submitter?.getAttribute("value")==="archive";
        await api("/experiments/"+existing.id,"PUT",{name,notes,archived:toggle?!existing.archived:existing.archived});
      } else {
        const created=await api<Experiment>("/experiments","POST",{name,notes,city_id:city,workspace_id:workspace});
        form.reset();select(created.id);
      }
      setVersion(value=>value+1);
    } catch(value) { setError(messageOf(value)); }
    finally { setBusy(false); }
  }

  const record=detail?.id===selected?detail:null;
  const fields=(existing?:Experiment)=><>
    <label>{t("Experiment name")}<input name="name" required minLength={3} maxLength={120} defaultValue={existing?.name}/></label>
    <label>{t("Research notes")}<textarea name="notes" rows={2} maxLength={2000} defaultValue={existing?.notes}/></label>
  </>;
  return <section className="panel settings-section operations-form">
    <h2>{t("Experiments")}</h2>
    <ErrorText message={error}/>
    <label>{t("Open experiment")}<select value={selected??""} onChange={event=>{setError("");select(event.target.value||null);}}>
      <option value="">{t("Select an experiment")}</option>
      {rows.map(row=><option key={row.id} value={row.id}>{row.name}{row.archived?" · "+t("Archived"):""}</option>)}
    </select></label>
    {!selected&&canEdit&&<form className="form-stack" onSubmit={event=>void save(event)}>
      {fields()}<button className="button primary fit" disabled={busy}><Plus size={16}/>{t("Create experiment")}</button>
    </form>}
    {record&&<>
      {canEdit?<form key={record.id} className="form-stack" onSubmit={event=>void save(event,record)}>
        {fields(record)}
        <div className="form-actions">
          <button className="button primary compact" disabled={busy}>{t("Save experiment")}</button>
          <button className="button secondary compact" disabled={busy} value="archive">{t(record.archived?"Restore experiment":"Archive experiment")}</button>
        </div>
      </form>:<p>{record.notes}</p>}
      <div className="form-actions">
        {!record.archived&&canEdit&&<button className="button primary" onClick={()=>addVariant(record.id)}>
          <Plus size={16}/>{t("Add scenario variant")}
        </button>}
        <a className="button secondary" href={"/api/v1/experiments/"+record.id+"/export"}><FileDown size={16}/>{t("Export experiment")}</a>
      </div>
      <h3>{t("Scenario variants")}</h3>
      {record.variants.length?<ul className="simple-list">{record.variants.map(row=><li key={row.id}>
        <strong>{row.title}</strong><span>{t("Simulation seed")} {row.seed}</span>
        {!record.archived&&canEdit&&<>
          <button className="button secondary compact" onClick={()=>addVariant(record.id,row)}>{t("Duplicate variant")}</button>
          <button className="button secondary compact" onClick={()=>start(row.id)}>{t("Run")}</button>
        </>}
      </li>)}</ul>:<Empty title={t("No variants yet")}/>}
      {!!record.runs.length&&<div className="table-scroll"><table className="result-table">
        <caption>{t("Experiment outcomes at +30 minutes")}</caption>
        <thead><tr>{["Run","Status","Simulation seed","Score","Congestion","Transit delay"].map(label=><th scope="col" key={label}>{t(label)}</th>)}</tr></thead>
        <tbody>{record.runs.map(row=><tr key={row.id}>
          <th scope="row"><button className="plain-action" onClick={()=>open(row.id)}>{row.title}</button></th>
          <td>{t(row.status[0].toUpperCase()+row.status.slice(1))}</td><td>{row.seed}</td><td>{row.score??"–"}</td>
          <td>{row.congestion??"–"}</td><td>{row.transit_delay===null?"–":row.transit_delay+" min"}</td>
        </tr>)}</tbody>
      </table></div>}
    </>}
  </section>;
}
