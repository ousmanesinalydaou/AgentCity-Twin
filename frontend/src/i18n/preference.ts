"use client";

import { useSyncExternalStore } from "react";
import { languages, type Language } from "./index";

const key="agentcity-language";
function subscribe(callback:()=>void) {
  window.addEventListener("storage",callback);
  window.addEventListener(key,callback);
  return ()=>{
    window.removeEventListener("storage",callback);
    window.removeEventListener(key,callback);
  };
}
function read():Language {
  try {
    const value=window.localStorage.getItem(key);
    if(value&&Object.hasOwn(languages,value))return value as Language;
  } catch {}
  return "en";
}
export function persistLanguage(value:Language) {
  try {
    if(window.localStorage.getItem(key)!==value){
      window.localStorage.setItem(key,value);
      window.dispatchEvent(new Event(key));
    }
  } catch {}
}
export function usePublicLanguage() {
  return useSyncExternalStore(subscribe,read,()=>"en" as Language);
}

