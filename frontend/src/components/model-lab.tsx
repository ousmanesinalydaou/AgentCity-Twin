"use client";

import { Bot, Braces, ImagePlus, Radio, Timer, Wrench } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import type { Translate } from "@/i18n";
import { api, messageOf } from "@/lib/api";
import type { Provider } from "@/lib/types";
import { ErrorText } from "./ui";

type Operation="embeddings"|"vision"|"streaming"|"tools";
type Output={model?:string;provider?:string;execution?:string;text?:string;dimensions?:number;vector?:number[];tools?:string[]};
type Benchmark={provider:string;model:string;accuracy:number;latency_ms:number};
const operations: {key:Operation; label:string; icon:typeof Bot}[]=[
  {key:"streaming",label:"Streaming text",icon:Radio},{key:"vision",label:"Image analysis",icon:ImagePlus},
  {key:"embeddings",label:"Embeddings",icon:Braces},{key:"tools",label:"City tools",icon:Wrench},
];

function encodedImage(file:File) {
  return new Promise<string>((resolve,reject)=>{
    const reader=new FileReader();
    reader.onload=()=>resolve(String(reader.result));
    reader.onerror=()=>reject(new Error("The image could not be read."));
    reader.readAsDataURL(file);
  });
}

async function readStream(data:unknown, signal:AbortSignal, completed:(value:Output)=>void, token:(value:string)=>void) {
  const response=await fetch("/api/v1/model-lab/tasks",{method:"POST",headers:{"Content-Type":"application/json"},
    body:JSON.stringify(data),signal,credentials:"same-origin"});
  if(!response.ok||!response.body){
    const body=await response.json().catch(()=>null);
    throw new Error(typeof body?.detail==="string"?body.detail:"The model stream is unavailable.");
  }
  const reader=response.body.getReader();
  const decode=new TextDecoder();
  let pending="",done=false;
  try {
    while(!done) {
      const next=await reader.read();
      if(next.done)break;
      pending+=decode.decode(next.value,{stream:true});
      const packets=pending.split("\n\n");
      pending=packets.pop()??"";
      for(const packet of packets){
        const line=packet.split("\n").find(value=>value.startsWith("data: "));
        if(!line)continue;
        const payload=JSON.parse(line.slice(6));
        if(payload.error)throw new Error(payload.error);
        if(typeof payload.text==="string")token(payload.text);
        if(payload.done){done=true;completed(payload);break;}
      }
    }
    if(!done)throw new Error("The model stream ended early.");
  } finally {await reader.cancel().catch(()=>undefined);}
}

export function ModelLab({providers,city,t,canUse}: {providers:Provider[];city:string;t:Translate;canUse:boolean}) {
  const [operation,setOperation]=useState<Operation>("streaming");
  const [output,setOutput]=useState<Output|null>(null);
  const [text,setText]=useState("");
  const [error,setError]=useState("");
  const [busy,setBusy]=useState(false);
  const [benchmark,setBenchmark]=useState<Benchmark|null>(null);
  const stream=useRef<AbortController|null>(null);
  useEffect(()=>()=>stream.current?.abort(),[]);
  if(!canUse)return null;
  return <section className="panel settings-section model-lab">
    <div className="operations-heading"><span className="icon-tile"><Bot size={19}/></span><h2>{t("Model lab")}</h2></div>
    <p className="settings-context">{t("Test model capabilities with local fallback and record provider benchmarks.")}</p>
    <ErrorText message={t(error)}/>
    <div className="tabbar" role="group" aria-label={t("Model capabilities")}>
      {operations.map(({key,label,icon:Icon})=><button key={key} disabled={busy} aria-pressed={operation===key}
        className={operation===key?"selected":""} onClick={()=>{setOperation(key);setOutput(null);setText("");}}><Icon size={16}/>{t(label)}</button>)}
    </div>
    <form className="form-stack operations-form" key={operation} onSubmit={event=>{
      event.preventDefault();
      const form=new FormData(event.currentTarget);
      setBusy(true);setError("");setOutput(null);setText("");
      const controller=new AbortController();stream.current=controller;
      void (async()=>{
        const image=form.get("image");
        if(image instanceof File&&image.size>1_200_000)throw new Error(t("Choose an image under 1.2 MB."));
        const payload={operation,city_id:city,prompt:form.get("prompt"),provider_id:form.get("provider")||null,
          local_only:!form.has("cloud"),image:image instanceof File&&image.size?await encodedImage(image):null};
        if (operation==="streaming") {
          await readStream(payload,controller.signal,setOutput,(value)=>setText(current=>current+value));
        } else setOutput(await api<Output>("/model-lab/tasks","POST",payload));
      })().catch(value=>{if(!controller.signal.aborted)setError(messageOf(value));}).finally(()=>{setBusy(false);});
    }}>
      <label>{t("Prompt")}<textarea name="prompt" required minLength={2} maxLength={4000} rows={3}
        placeholder={t("Summarize the current city dataset.")}/></label>
      {operation==="vision"&&<label>{t("Image")}<input type="file" name="image" accept="image/png,image/jpeg,image/webp" required/></label>}
      <label>{t("Provider")}<select name="provider">
        <option value="">{t("Use workspace routing")}</option>
        {providers.filter(row=>row.enabled&&row.capabilities.includes(operation)).map(row=>
          <option key={row.id} value={row.id}>{row.name} · {row.model}</option>)}
      </select></label>
      <label className="check-label"><input type="checkbox" name="cloud"/>{t("Permit approved cloud providers")}</label>
      <div className="form-actions"><button className="button primary" disabled={busy}>{t(busy?"Working…":"Run model task")}</button>
        {busy&&operation==="streaming"&&<button type="button" className="button secondary" onClick={()=>stream.current?.abort()}>{t("Stop stream")}</button>}</div>
    </form>
    {(text||output)&&<div className="model-output" aria-live="polite">
      {output&&<span className="badge quiet">{output.model} · {t(output.execution??"Local")}</span>}
      {(text||output?.text)&&<p>{text||output?.text}</p>}
      {output?.vector&&<details><summary>{output.dimensions} {t("Embedding dimensions")}</summary><pre>{JSON.stringify(output.vector)}</pre></details>}
      {!!output?.tools?.length&&<p><Wrench size={16}/> {output.tools.join(", ")}</p>}
    </div>}
    {!!providers.length&&<form className="form-stack operations-form" onSubmit={event=>{
      event.preventDefault();const provider=new FormData(event.currentTarget).get("candidate");
      if(typeof provider!=="string"||!provider)return;
      setBusy(true);setError("");setBenchmark(null);
      void api<Benchmark>(`/model-lab/benchmarks/${encodeURIComponent(provider)}`,"POST").then(setBenchmark)
        .catch(value=>setError(messageOf(value))).finally(()=>setBusy(false));
    }}>
      <label>{t("Benchmark provider")}<select name="candidate">
        {providers.filter(row=>row.enabled).map(row=><option value={row.id} key={row.id}>{row.name} · {row.model}</option>)}
      </select></label>
      <button className="button secondary fit" disabled={busy}><Timer size={16}/>{t("Run benchmark")}</button>
      {benchmark&&<p role="status">{benchmark.model} · {t("Accuracy")} {Math.round(benchmark.accuracy*100)}% · {benchmark.latency_ms} ms</p>}
    </form>}
  </section>;
}

