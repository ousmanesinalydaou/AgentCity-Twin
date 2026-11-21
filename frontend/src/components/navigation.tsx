"use client";

import Link from "next/link";
import Image from "next/image";
import { Activity, Bell, Bot, ChevronDown, ChevronRight, CircleHelp, FlaskConical, Globe2, LayoutGrid,
  Leaf, Map, Menu, Radio, Route, Search, Settings2, SlidersHorizontal, TramFront, X, FileText } from "lucide-react";
import type { LucideIcon } from "lucide-react";
import type { City, Notice, User, Workspace } from "@/lib/types";
import { languages, type Language, type Translate } from "@/i18n";

export const navigation: {id:string;name:string;icon:LucideIcon}[][] = [
  [
    {id:"overview",name:"Overview",icon:LayoutGrid},{id:"twin",name:"Digital Twin",icon:Map},
    {id:"scenarios",name:"Scenarios",icon:SlidersHorizontal},{id:"simulations",name:"Simulations",icon:Activity},
    {id:"agents",name:"Agents",icon:Bot},
  ],
  [
    {id:"sensors",name:"Sensors",icon:Radio},{id:"mobility",name:"Mobility",icon:TramFront},
    {id:"environment",name:"Environment",icon:Leaf},{id:"reports",name:"Reports",icon:FileText},
    {id:"research",name:"Research",icon:FlaskConical},
  ],
  [{id:"settings",name:"Settings",icon:Settings2}],
];
export type Popup = "search"|"notifications"|"language"|"user"|"activity"|null;

export function Brand() {
  return <Link className="brand" href="/"><span className="brand-emblem"><Image src="/brand/icon.webp" alt="" width={34} height={34} priority/></span>
    <span>AgentCity<span className="brand-twin"> Twin</span></span></Link>;
}

export function Topbar({t,user,city,cities,workspace,workspaces,cityChange,workspaceChange,onPopup,notices,toggleNav}: {
  t:Translate;user:User|null;city:City|null;cities:City[];workspace:string;workspaces:Workspace[];
  cityChange:(id:string)=>void;workspaceChange:(id:string)=>void;onPopup:(value:Popup)=>void;notices:Notice[];toggleNav:()=>void;
}) {
  return <header className="topbar">
    <button className="icon-button mobile-menu" aria-label={t("Open navigation")} onClick={toggleNav}><Menu size={21}/></button>
    <Brand/>
    <div className="top-context">
      <span className="top-separator"/>
      <label className="select-chip city-picker">{city?.id==="debrecen"?<span className="city-flag" aria-hidden="true"/>:<Globe2 className="city-symbol" size={15} aria-hidden="true"/>} <select aria-label={t("City")} value={city?.id ?? ""} onChange={event=>cityChange(event.target.value)}>
        {cities.map(item=><option key={item.id} value={item.id}>{item.name}, {item.country}</option>)}
      </select><ChevronDown size={13}/></label>
      <ChevronRight size={14} className="top-chevron"/>
      <label className="select-chip workspace-picker"><select aria-label={t("Workspace")} value={workspace} onChange={event=>workspaceChange(event.target.value)}>
        {workspaces.map(item=><option key={item.id} value={item.id}>{t(item.name)}</option>)}
      </select><ChevronDown size={13}/></label>
    </div>
    <div className="top-actions">
      <button className="search-trigger" onClick={()=>onPopup("search")} aria-label={t("Search")}><Search size={16}/><span>{t("Search")}</span><kbd>Ctrl K</kbd></button>
      <button className="icon-button top-language" title={t("Language")} aria-label={t("Language")} onClick={()=>onPopup("language")}><Globe2 size={18}/></button>
      <button className="icon-button bell-trigger" title={t("Notifications")} aria-label={t("Notifications")} onClick={()=>onPopup("notifications")}><Bell size={18}/>{notices.some(item=>item.unread)&&<i/>}</button>
      <span className="top-separator"/>
      <button className="user-trigger" aria-label={t("My account")} title={user?.name ?? t("My account")} onClick={()=>onPopup("user")}><span>{user?.name.split(" ").map(part=>part[0]).slice(0,2).join("").toUpperCase() || "AC"}</span><ChevronDown size={13}/></button>
    </div>
  </header>;
}

export function SideNav({active,change,t,isOpen,close,demo,showResearch}: {
  active:string;change:(s:string)=>void;t:Translate;isOpen:boolean;close:()=>void;demo:boolean;showResearch:boolean;
}) {
  const heading = ["Workspace","Data & analysis",""];
  return <>
    {isOpen && <button className="nav-scrim" aria-label={t("Close navigation")} onClick={close}/>}
    <aside className={`sidebar ${isOpen?"is-open":""}`}>
      <div className="mobile-nav-heading"><Brand/><button className="icon-button" onClick={close} aria-label={t("Close navigation")}><X size={19}/></button></div>
      <nav aria-label={t("Operational views")} className="side-nav">
        {navigation.map((group,index)=><div className="nav-group" key={group[0].id}>
          {heading[index]&&<div className="nav-label">{t(heading[index])}</div>}
          {group.filter(entry=>entry.id!=="research"||showResearch).map(({id,name,icon:Icon})=><button key={id} className={`nav-item ${active===id?"active":""}`} onClick={()=>{change(id);close();}} aria-current={active===id?"page":undefined}>
            <Icon size={18} strokeWidth={1.75}/><span>{t(name)}</span>{active===id&&<span className="nav-active-dot"/>}</button>)}
        </div>)}
      </nav>
      <div className="sidebar-footer">
        <Link className="nav-item help-link" href="/welcome"><CircleHelp size={18}/><span>{t("About AgentCity")}</span><ChevronRight size={14}/></Link>
        <div className="system-status"><span/><div><strong>{t("System operational")}</strong><small>{t(demo?"Demo workspace":"City Operations")}</small></div></div>
      </div>
    </aside>
  </>;
}

export function LanguageOptions({language,change}: {language:Language;change:(value:Language)=>void}) {
  return <div className="language-options">{Object.entries(languages).map(([key,name])=>
    <button type="button" aria-pressed={language === key} className="button secondary" key={key} onClick={()=>change(key as Language)}>
      <Globe2 size={16}/>{name}
    </button>)}</div>;
}

export const sideIcons:Record<string,LucideIcon> = {
  orchestrator:Route,traffic:Activity,mobility:TramFront,environment:Leaf,safety:Radio,campus:Map,
};

