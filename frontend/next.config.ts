import type { NextConfig } from "next";

// Server-side only: where /api/* is proxied. Proxying keeps the session cookie
// first-party on the frontend domain, so Google sign-in works without
// third-party cookies.
function normalizeBackendUrl(raw?: string): string {
  const trimmed = raw?.trim();
  if (!trimmed) {
    return "http://localhost:8000";
  }
  const withProtocol = /^https?:\/\//i.test(trimmed)
    ? trimmed
    : `https://${trimmed}`;
  return withProtocol.replace(/\/+$/, "");
}

const backendUrl = normalizeBackendUrl(process.env.BACKEND_URL);

const nextConfig: NextConfig = {
  reactStrictMode: true,
  async rewrites() {
    return [{ source: "/api/:path*", destination: `${backendUrl}/:path*` }];
  },
};

export default nextConfig;
