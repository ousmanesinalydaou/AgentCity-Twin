"use client";

import { Crosshair, MapPin } from "lucide-react";
import { useState } from "react";
import type { Translate } from "@/i18n";
import { api, messageOf } from "@/lib/api";
import type { Coordinates } from "@/lib/types";
import { Empty, ErrorText } from "./ui";

type Plan={candidates:{id:string;coordinates:Coordinates;radius:number;covered_nodes:number;demand_weight:number}[];
  uncovered_nodes:number;mode:string};

export function SensorCoverage({t,city,locate}:{t:Translate;city:string;locate:(point:Coordinates)=>void}) {
  const [visible,setVisible]=useState(false);
  const [count,setCount]=useState(5);
  const [value,setValue]=useState<Plan|null>(null);
  const [error,setError]=useState("");
  const [loading,setLoading]=useState(false);
  return <section className="panel settings-section coverage-panel">
    <button aria-expanded={visible} className="plain-action" onClick={()=>setVisible(!visible)}>
      <Crosshair size={17}/>{t("Plan sensor coverage")}
    </button>
    {visible&&<><p className="settings-context">{t("Find gaps using coverage radius, road demand, and the current sensor inventory.")}</p>
      <form className="form-actions" onSubmit={event=>{
        event.preventDefault();setLoading(true);setError("");
        void api<Plan>(`/telemetry/coverage?city_id=${encodeURIComponent(city)}&count=${count}`).then(setValue)
          .catch(value=>setError(messageOf(value))).finally(()=>setLoading(false));
      }}><label>{t("Number of sites")}<input type="number" min={1} max={12} required value={count}
        onChange={event=>setCount(+event.target.value)}/></label>
        <button className="button primary" disabled={loading}>{t(loading?"Working…":"Calculate coverage")}</button>
      </form>
      <ErrorText message={t(error)}/>
      {value&&<div><p>{t(value.mode)} · {value.uncovered_nodes} {t("Uncovered nodes")}</p>
        {!value.candidates.length&&<Empty title={t("No additional locations found")}/>}
        <ul className="simple-list">{value.candidates.map(row=><li key={row.id}><strong>{row.coordinates[1].toFixed(4)}, {row.coordinates[0].toFixed(4)}</strong>
          <span>{row.covered_nodes} {t("Covered nodes")} · {row.radius} m · {row.demand_weight} {t("Demand weight")}</span>
          <button className="button secondary compact" onClick={()=>locate(row.coordinates)}><MapPin size={15}/>{t("View on map")}</button></li>)}</ul>
      </div>}</>}
  </section>;
}

