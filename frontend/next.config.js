/** @type {import('next').NextConfig} */
const backendApi =
  process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "") ||
  "https://talentlenspublic-production.up.railway.app";

const nextConfig = {
  basePath: "/talentlens",
  assetPrefix: "/talentlens",
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${backendApi}/api/:path*`,
      },
    ];
  },
};

module.exports = nextConfig;
