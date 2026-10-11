import path from "node:path";
import { loadEnvConfig } from "@next/env";
import type { NextConfig } from "next";

const root = path.resolve(process.cwd(), "../..");
loadEnvConfig(root);
const config: NextConfig = {
  output: "standalone",
  outputFileTracingRoot: root,
  turbopack: { root },
};
export default config;
