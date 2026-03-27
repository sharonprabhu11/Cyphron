/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // Prevent Next.js from picking an unrelated workspace root on Windows.
  outputFileTracingRoot: __dirname
};

module.exports = nextConfig;

