"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { Brand } from "@/components/navigation";
import { ErrorText } from "@/components/ui";
import { translate } from "@/i18n";
import { usePublicLanguage } from "@/i18n/preference";
import { api, messageOf } from "@/lib/api";

export default function Contact() {
  const [status,setStatus]=useState({busy:false,error:"",id:""});
  const language=usePublicLanguage();
  const t=translate(language);
  useEffect(()=>{document.documentElement.lang=language;},[language]);
  async function send(form:FormData) {
    setStatus({busy:true,error:"",id:""});
    try {const result=await api<{id:string}>("/public/contact","POST",Object.fromEntries(form));setStatus({busy:false,error:"",id:result.id});}
    catch(error){setStatus({busy:false,error:messageOf(error),id:""});}
  }
  return <div className="standalone-body"><header className="public-header"><Brand/><nav>
    <Link className="button secondary" href="/welcome">{t("About AgentCity")}</Link><Link className="button primary" href="/">{t("Launch Digital Twin")}</Link>
  </nav></header><main className="panel account-main"><h1>{t("Contact")}</h1><p>{t("Ask about organizational access, research, or city data integration.")}</p>
    <ErrorText message={t(status.error)}/>
    {status.id?<p className="success-note" role="status">{t("Message received.")} {t("Reference")} {status.id.slice(0,8)}.</p>:
      <form className="form-stack" onSubmit={event=>{event.preventDefault();void send(new FormData(event.currentTarget));}}>
        <label>{t("Name")}<input name="name" minLength={2} maxLength={100} required autoComplete="name"/></label>
        <label>{t("Email address")}<input name="email" type="email" maxLength={254} required autoComplete="email"/></label>
        <label>{t("Message")}<textarea name="message" minLength={10} maxLength={2000} rows={5} required/></label>
        <button className="button primary" disabled={status.busy}>{t(status.busy?"Sending…":"Send message")}</button>
      </form>}
  </main></div>;
}

