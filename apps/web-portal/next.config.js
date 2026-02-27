/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,

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
}

module.exports = nextConfig
