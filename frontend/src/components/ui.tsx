"use client";

import { useEffect, useRef, type ReactNode } from "react";
import { ArrowDownRight, ArrowUpRight, CircleAlert, X } from "lucide-react";

export function Dialog({ title, open, close, children, wide = false }: {
  title:string;open:boolean;close:()=>void;children:ReactNode;wide?:boolean;
}) {
  const ref = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    const dialog = ref.current;
    if (open && !dialog?.open) dialog?.showModal();
    if (!open && dialog?.open) dialog.close();
  }, [open]);
  return <dialog ref={ref} className={wide ? "dialog wide" : "dialog"} onClose={close}
    onClick={(event) => { if (event.target === event.currentTarget) close(); }} aria-label={title}>
    <div className="dialog-inner">
      <header className="dialog-header"><h2>{title}</h2><button className="icon-button" aria-label="Close" onClick={close}><X size={18}/></button></header>
      {open&&children}
    </div>
  </dialog>;
}

export function ErrorText({ message }: {message:string|null|undefined}) {
  return message ? <div className="error-note" role="alert"><CircleAlert size={16}/>{message}</div> : null;
}

export function Delta({ value, suffix, inverse = false }: {value:number;suffix:string;inverse?:boolean}) {
  const good = inverse ? value < 0 : value > 0;
  const Icon = value < 0 ? ArrowDownRight : ArrowUpRight;
  return <span className={good ? "delta positive" : "delta caution"}><Icon size={13}/>{Math.abs(value)}{suffix}</span>;
}

export function Empty({ title, description }: {title:string;description?:string}) {
  return <div className="empty"><strong>{title}</strong>{description && <p>{description}</p>}</div>;
}

