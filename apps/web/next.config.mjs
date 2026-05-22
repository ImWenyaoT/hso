const gatewayUrl = process.env.HSO_GATEWAY_URL ?? "http://127.0.0.1:8765";

/** @type {import('next').NextConfig} */
const nextConfig = {
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${gatewayUrl}/api/:path*`
      }
    ];
  }
};

export default nextConfig;
