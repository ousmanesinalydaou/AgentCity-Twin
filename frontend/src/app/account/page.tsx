import { Suspense } from "react";
import { AccountPage } from "@/components/account";

export default function Account() {
  return <Suspense><AccountPage/></Suspense>;
}

