/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  eslint: {
    ignoreDuringBuilds: false,
  },

  i18n: {
    // These are all the locales you want to support in
    // your application
    locales: ['ru-RU', 'en-GB', 'pl-PL', 'ro-RO', 'it-IT', 'pt-PT', 'es-ES', 'tr-TR', 'bn-BD', 'uk-UA'],
    // This is the default locale you want to be used when visiting
    // a non-locale prefixed path e.g. `/hello`
    defaultLocale: 'ru-RU',
  },

  // This allows us to use environment variables on the client-side
  env: {
    NEXT_PUBLIC_API_GATEWAY_URL: process.env.NEXT_PUBLIC_API_GATEWAY_URL,
  },

  /** Single marketing home: old `/landing` URL → `/` (no duplicate page) */
  async redirects() {
    return [
      {
        source: '/landing',
        destination: '/',
        permanent: true,
        locale: false,
      },
    ];
  },

  /**
   * Proxy API to nginx-gateway — browser calls same-origin `/api/...`, Next forwards to :8000.
   * Requires gateway: `docker compose up -d nginx-gateway` from repo root.
   */
  async rewrites() {
    const base = process.env.NEXT_PUBLIC_API_GATEWAY_URL || 'http://localhost:8000/api';
    const origin = base.replace(/\/api\/?$/, '') || 'http://localhost:8000';
    return [
      {
        source: '/api/:path*',
        destination: `${origin}/api/:path*`,
      },
      {
        source: '/sitemap-seo-tax-calculator.xml',
        destination: '/sitemap-seo-tax-calculator',
        locale: false,
      },
      {
        source: '/robots.txt',
        destination: '/robots-txt',
        locale: false,
      },
    ];
  },
}

module.exports = nextConfig
