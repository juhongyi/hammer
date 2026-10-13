import type { NextConfig } from "next";

const config: NextConfig = {
  allowedDevOrigins: ["macbook"],
  async rewrites() {
    return [{ source: "/api/:path*", destination: `${process.env.API_URL || "http://localhost:8000"}/:path*` }];
  },
};
export default config;
