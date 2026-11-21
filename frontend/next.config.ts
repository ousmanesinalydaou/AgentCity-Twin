import type { NextConfig } from "next";

const backend = process.env.BACKEND_URL ?? "http://127.0.0.1:8100";
const config: NextConfig = {
  output: "standalone",
  agentRules: false,
  devIndicators: false,
  poweredByHeader: false,
  async rewrites() {
    return [
      { source: "/api/v1/:path*", destination: backend + "/api/v1/:path*" },
      { source: "/api-docs", destination: backend + "/docs" },
      { source: "/openapi.json", destination: backend + "/openapi.json" },
    ];
  },
  async headers() {
    return [{ source: "/:path*", headers: [
      { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
      { key: "X-Frame-Options", value: "DENY" },
      { key: "X-Content-Type-Options", value: "nosniff" },
    ] }];
  },
};
export default config;

