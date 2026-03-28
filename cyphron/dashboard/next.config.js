/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // Prevent Next.js from picking an unrelated workspace root on Windows.
  outputFileTracingRoot: __dirname,
  // Reduces dev-server chunk races that can surface as MODULE_NOT_FOUND for numbered chunks (e.g. ./611.js).
  experimental: {
    webpackBuildWorker: false,
  },
};

module.exports = nextConfig;

