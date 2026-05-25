/** @type {import('next').NextConfig} */
const nextConfig = {
  serverExternalPackages: ["better-sqlite3"],
  transpilePackages: ["@hso/agent-runtime", "@hso/shared", "@hso/storage"]
};

export default nextConfig;
