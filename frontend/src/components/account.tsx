"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";
import { api,messageOf } from "@/lib/api";
import type { User } from "@/lib/types";
import { translate } from "@/i18n";
import { persistLanguage, usePublicLanguage } from "@/i18n/preference";
import { Brand, LanguageOptions } from "./navigation";
import { ErrorText } from "./ui";

export function AccountPage() {
  const params=useSearchParams();
  const router=useRouter();
  const mode=params.get("mode")??"login";
  const token=params.get("token")??"";
  const language=usePublicLanguage();
  const [error,setError]=useState("");
  const [success,setSuccess]=useState("");
  const [busy,setBusy]=useState(false);
  const [oidc,setOidc]=useState(false);
  useEffect(()=>{void api<{enabled:boolean}>("/auth/oidc/status").then(value=>setOidc(value.enabled)).catch(()=>undefined);},[]);
  const t=translate(language);
  useEffect(()=>{document.documentElement.lang=language;},[language]);
  const heading=({register:"Create account",forgot:"Reset password",reset:"Choose a new password",verify:"Verify your email",
    resend:"Resend verification email",invite:"Accept invitation"})[mode]??"Sign in";
  async function submit(form:FormData) {
    setBusy(true);setError("");setSuccess("");
    try {
      if (mode==="forgot") {await api("/auth/forgot","POST",{email:form.get("email")});setSuccess(t("If the account exists and mail is configured, a reset link will be sent."));}
      else if (mode==="resend") {
        await api("/auth/resend-verification","POST",{email:form.get("email")});
        setSuccess(t("If the account needs verification and mail is configured, a link will be sent."));
      }
      else if(mode==="reset"||mode==="verify") {
        await api("/auth/"+mode,"POST",{token,...(mode==="reset"?{password:form.get("password")}:{})});
        setSuccess(t(mode==="reset"?"Password updated. You can sign in now.":"Email verified. You can sign in now."));
      } else if(mode==="invite"){
        const result=await api<{requires_verification:boolean}>("/auth/invite","POST",{
          token,name:form.get("name"),password:form.get("password"),
        });
        if(result.requires_verification){setSuccess(t("Account created. Check your email for a verification link."));return;}
        router.replace("/");
      } else {
        const user=await api<User>(mode==="register"?"/auth/register":"/auth/login","POST",Object.fromEntries(form));
        if(mode==="register"&&!user.verified) {
          const session=await api<User>("/auth/me","GET",undefined,false).catch(()=>null);
          if(session?.id!==user.id){setSuccess(t("Account created. Check your email for a verification link."));return;}
        }
        router.replace("/");
      }
    } catch(error){setError(messageOf(error));}
    finally{setBusy(false);}
  }
  return <div className="standalone-body"><header className="public-header"><Brand/><nav><Link href="/welcome">{t("About AgentCity")}</Link>
    <Link className="button secondary" href="/">{t("Explore Demo")}</Link></nav></header>
    <main className="panel account-main" key={mode}><h1>{t(heading)}</h1><p>{t("AgentCity Twin workspace access")}</p>
      <ErrorText message={t(error)}/>{success&&<p className="success-note" role="status">{success}</p>}
      <form className="form-stack" onSubmit={event=>{event.preventDefault();void submit(new FormData(event.currentTarget));}}>
        {(mode==="register"||mode==="invite")&&<label>{t("Name")}<input name="name" autoComplete="name" required maxLength={100}/></label>}
        {!["verify","reset","invite"].includes(mode)&&<label>{t("Email address")}<input name="email" type="email" autoComplete="email" required maxLength={254}/></label>}
        {!["forgot","verify","resend"].includes(mode)&&<label>{t("Password")}<input name="password" type="password"
          autoComplete={mode==="login"?"current-password":"new-password"} minLength={10} maxLength={128} required/></label>}
        <button type="submit" className="button primary" disabled={busy}>{t(busy?"Working…":heading)}</button>
      </form>
      {mode==="login"&&oidc&&<div className="account-links">
        <a className="button secondary" href="/api/v1/auth/oidc/start">{t("Sign in with SSO")}</a>
      </div>}
      <div className="account-links">
        {mode==="login"?<><Link className="plain-action" href="/account?mode=register">{t("Create account")}</Link>
          <Link className="plain-action" href="/account?mode=forgot">{t("Reset password")}</Link>
          <Link className="plain-action" href="/account?mode=resend">{t("Resend verification email")}</Link></>
          :<Link className="plain-action" href="/account">{t("Sign in")}</Link>}
      </div>
      <div className="account-links"><LanguageOptions language={language} change={persistLanguage}/></div>
    </main>
  </div>;
}

