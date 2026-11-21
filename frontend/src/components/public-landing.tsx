"use client";

import dynamic from "next/dynamic";
import Image from "next/image";
import Link from "next/link";
import { Activity, BadgeCheck, Bot, Database, FlaskConical, Globe2, Layers3, LockKeyhole, Route } from "lucide-react";
import { useEffect, useState } from "react";
import { translate } from "@/i18n";
import { persistLanguage, usePublicLanguage } from "@/i18n/preference";
import { api } from "@/lib/api";
import type { City, Coordinates, Incident, Layers } from "@/lib/types";
import { Brand, LanguageOptions } from "./navigation";
import { Dialog, ErrorText } from "./ui";

const Map = dynamic(()=>import("./map/city-map"),{ssr:false,loading:()=> <div className="map-area debrecen-fallback"/>});
const features = [
  {icon:Layers3,title:"Model city conditions",text:"The digital twin brings the road network, transit routes, sensors, and incidents into one map. Each layer helps you see what a decision could affect."},
  {icon:Bot,title:"Coordinate specialist agents",text:"The orchestrator builds a plan and assigns work to specialists in traffic, transit, safety, and other relevant areas. The execution plan shows their tools and findings."},
  {icon:Activity,title:"Compare simulated interventions",text:"Compare a forecast with no new action against the recommended response. Move through five time points to see how the effects change."},
  {icon:BadgeCheck,title:"Explain the recommendation",text:"The Critic checks the results before the decision agent ranks them. Inspect the evidence and record an operator review when required."},
  {icon:LockKeyhole,title:"Control model execution",text:"Keep model execution local or connect approved cloud providers. Workspace policy controls where advisory requests run."},
  {icon:FlaskConical,title:"Repeat experiments",text:"Adjust assumptions, compare agent or provider configurations, and export the run with its seed and input fingerprint."},
];
const useCases = [
  {icon:Route,title:"City operations",text:"Compare diversions, transit priority, and advisories when a junction becomes unavailable."},
  {icon:Globe2,title:"Campus planning",text:"Evaluate the effects of arrivals, closures, and large events on campus access."},
  {icon:Database,title:"Research and public administration",text:"Test policy weights, document assumptions, and retain evidence for independent review."},
];

export function PublicLanding() {
  const language=usePublicLanguage();
  const [languagesOpen,setLanguagesOpen]=useState(false);
  const [preview,setPreview]=useState(false);
  const [selected,setSelected]=useState<Coordinates|null>(null);
  const [info,setInfo]=useState<{city:City;layers:Layers;incidents:Incident[]}|null>(null);
  const [error,setError]=useState("");
  const [plans,setPlans]=useState<{name:string;description:string;price:string}[]>([]);
  const t=translate(language);
  useEffect(()=>{document.documentElement.lang=language;},[language]);
  useEffect(()=>{void api<{name:string;description:string;price:string}[]>("/public/plans").then(setPlans).catch(()=>undefined);},[]);
  function open() {
    setPreview(true);setError("");
    if(!info)void api<typeof info>("/public/demo").then(setInfo).catch(()=>setError(t("The preview is unavailable. Try again.")));
  }
  return <div className="standalone-body">
    <header className="public-header"><Brand/><nav aria-label={t("Public navigation")}>
      <a href="#workflow">{t("How it works")}</a><a href="#developers">{t("Developers")}</a>
      <button className="icon-button" onClick={()=>setLanguagesOpen(true)} aria-label={t("Language")}><Globe2 size={17}/></button>
      <Link className="button secondary" href="/account">{t("Sign in")}</Link>
      <Link className="button primary" href="/">{t("Launch Digital Twin")}</Link>
    </nav></header>
    <main className="public-wrap">
      <section className="public-hero"><div>
        <div className="eyebrow">{t("Urban decision intelligence")}</div>
        <h1>{t("Understand the city")} <span>{t("before changing it.")}</span></h1>
        <p>{t("See how a road closure, transit disruption, or campus event could affect the rest of the city. Compare responses before putting a decision into practice.")}</p>
        <div className="public-actions"><Link className="button primary" href="/">{t("Launch Digital Twin")}</Link>
          <button className="button secondary" onClick={open}>{t("Explore Demo")}</button></div>
      </div><div className="hero-map">
        <Image src="/brand/skyline.webp" width={1000} height={667} alt={t("AgentCity Twin skyline artwork")} priority/>
      </div></section>
      <section className="public-section" id="workflow"><h2>{t("From scenario to auditable decision")}</h2>
        <p>{t("Try a rush-hour incident near the University of Debrecen. Follow the agents, scrub the timeline, and compare the recommended response with the baseline.")}</p>
        <div className="public-feature-grid">{features.map(({icon:Icon,title,text})=><article key={title}>
          <span className="icon-tile"><Icon size={19}/></span><h3>{t(title)}</h3><p>{t(text)}</p>
        </article>)}</div></section>
      <section className="public-section" id="use-cases"><h2>{t("Use cases")}</h2>
        <div className="public-feature-grid">{useCases.map(({icon:Icon,title,text})=><article key={title}>
          <span className="icon-tile"><Icon size={19}/></span><h3>{t(title)}</h3><p>{t(text)}</p>
        </article>)}</div></section>
      <section className="public-section" id="developers"><h2>{t("Open map and model integrations")}</h2>
        <p>{t("Connect GeoJSON, CSV, and GTFS shapes. Work with the versioned API and choose a local or approved cloud model provider.")}</p>
        <div className="public-links"><a className="button secondary" href="/api-docs">{t("API documentation")}</a>
          <Link className="button primary" href="/account?mode=register">{t("Create account")}</Link></div>
      </section>
      <section className="public-section" id="about"><h2>{t("About AgentCity Twin")}</h2>
        <p>{t("The Debrecen demo uses real map geography with simulated city conditions. The simulation computes the numbers, and local or approved cloud models provide specialist advice.")}</p>
        <div className="public-links"><Link className="button secondary" href="/contact">{t("Contact")}</Link></div>
      </section>
      {!!plans.length&&<section className="public-section" id="plans"><h2>{t("Access plans")}</h2>
        <div className="public-feature-grid">{plans.map(plan=><article key={plan.name}>
          <h3>{plan.name}</h3>{plan.price&&<p><strong>{plan.price}</strong></p>}<p>{plan.description}</p>
          <Link className="button secondary" href="/contact">{t("Request access")}</Link>
        </article>)}</div>
      </section>}
      <footer className="public-foot"><span>AgentCity Twin</span><a href="#workflow">{t("How it works")}</a></footer>
    </main>
    <Dialog open={preview} title={t("Debrecen Digital Twin")} close={()=>setPreview(false)} wide>
      <ErrorText message={error}/>{error&&<button className="button secondary" onClick={open}>{t("Retry")}</button>}
      {preview&&info?<Map city={info.city} data={info.layers} incidents={info.incidents} selected={selected} select={setSelected} mode="Current" t={t}/>
        :!error&&<p role="status">{t("Loading workspace…")}</p>}
      <div className="form-actions"><Link href="/" className="button primary">{t("Launch Digital Twin")}</Link></div>
    </Dialog>
    <Dialog open={languagesOpen} title={t("Language")} close={()=>setLanguagesOpen(false)}>
      <LanguageOptions language={language} change={value=>{persistLanguage(value);setLanguagesOpen(false);}}/>
    </Dialog>
  </div>;
}

