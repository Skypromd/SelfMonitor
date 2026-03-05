/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  env: {
    SUPPORT_API_URL: process.env.SUPPORT_API_URL || 'http://localhost:8020',
    SUPPORT_WS_URL:  process.env.SUPPORT_WS_URL  || 'ws://localhost:8020',
  },
};

module.exports = nextConfig;
