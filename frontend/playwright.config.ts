import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir:"./tests/e2e",
  timeout:45_000,
  workers:1,
  use:{
    baseURL:process.env.AGENTCITY_TEST_URL ?? "http://localhost:3100",
    headless:true,
    launchOptions:{args:["--use-gl=angle","--use-angle=swiftshader","--enable-unsafe-swiftshader"]},
  },
});

