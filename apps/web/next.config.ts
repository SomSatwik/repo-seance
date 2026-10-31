import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  /* config options here */
  output: "standalone",
  cacheComponents: true,
  partialPrefetching: true,
  reactCompiler: true,
  allowedDevOrigins: [
    "*.trycloudflare.com",
    "crew-determining-teeth-passive.trycloudflare.com",
    "mainland-mirrors-widely-advertise.trycloudflare.com",
  ],
  async rewrites() {
    return [
      {
        source: "/api-proxy/:path*",
        destination: "http://127.0.0.1:8000/:path*",
      },
    ];
  },
  turbopack: {
    rules: {
      "*.css": {
        loaders: ["@tailwindcss/turbopack"],
        as: "*.css",
      },
    },
  },
};

export default nextConfig;
