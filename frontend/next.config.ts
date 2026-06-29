import type { NextConfig } from "next";

const apiUrl = process.env.NEXT_PUBLIC_API_URL;

const nextConfig: NextConfig = {
  reactStrictMode: true,
  ...(apiUrl
    ? {
        async rewrites() {
          return [
            {
              source: "/api/:path*",
              destination: `${apiUrl}/api/:path*`,
            },
          ];
        },
      }
    : {}),
};

export default nextConfig;
