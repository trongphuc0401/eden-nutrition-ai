import type { NextConfig } from "next";

// Server-side only: where /api/* is proxied. Proxying keeps the session cookie
// first-party on the frontend domain, so Google sign-in works without
// third-party cookies.
const backendUrl = (process.env.BACKEND_URL ?? "http://localhost:8000").replace(/\/$/, "");

const nextConfig: NextConfig = {
  reactStrictMode: true,
  async rewrites() {
    return [{ source: "/api/:path*", destination: `${backendUrl}/:path*` }];
  },
};

export default nextConfig;
