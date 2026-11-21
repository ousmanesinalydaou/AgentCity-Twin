import type { Metadata } from "next";
import "@fontsource-variable/inter";
import "@fontsource-variable/space-grotesk";
import "maplibre-gl/dist/maplibre-gl.css";
import "./base.css";
import "./detail.css";

export const metadata: Metadata = {
  title: "AgentCity Twin | Urban Intelligence",
  description: "An agentic digital twin for intelligent urban decision-making.",
  icons: { icon: "/brand/icon.webp" },
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en"><body>{children}</body></html>;
}

