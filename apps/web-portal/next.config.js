/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,

  i18n: {
    // These are all the locales you want to support in
    // your application
    locales: ['en-GB', 'de-DE', 'ru-RU', 'uk-UA', 'pl-PL', 'ro-MD', 'tr-TR', 'hu-HU'],
    // This is the default locale you want to be used when visiting
    // a non-locale prefixed path e.g. `/hello`
    defaultLocale: 'en-GB',
  },

  // This allows us to use environment variables on the client-side
  env: {
    NEXT_PUBLIC_API_GATEWAY_URL: process.env.NEXT_PUBLIC_API_GATEWAY_URL,
  },
}

module.exports = nextConfig
