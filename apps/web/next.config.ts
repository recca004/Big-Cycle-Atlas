import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Dev-only: allow reaching the dev server via the LAN IP / 127.0.0.1 without
  // cross-origin warnings on /_next/* resources. localhost is allowed by default.
  allowedDevOrigins: ["127.0.0.1", "192.168.1.20"],
};

export default nextConfig;