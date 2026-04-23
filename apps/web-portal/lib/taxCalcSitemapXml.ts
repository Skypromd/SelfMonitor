import type { IncomingMessage } from 'http';

import { TAX_CALC_SEO_LANGS } from './taxCalculatorSeoCopy';
import { taxCalcSeoPath } from './taxCalcSeoUrl';

function escapeXml(s: string): string {
  return s
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

export function siteOriginFromRequest(req: IncomingMessage): string {
  const env = process.env.NEXT_PUBLIC_SITE_ORIGIN?.replace(/\/$/, '').trim();
  if (env && env.startsWith('http')) return env;
  const host = req.headers.host;
  const xf = req.headers['x-forwarded-proto'];
  const proto = typeof xf === 'string' ? xf.split(',')[0].trim() : 'http';
  if (!host) return 'http://localhost:3000';
  return `${proto}://${host}`;
}

export function buildTaxCalculatorSitemapXml(origin: string): string {
  const lastmod = new Date().toISOString().split('T')[0];
  const entries: { loc: string; lastmod: string; changefreq: string; priority: string }[] = [
    {
      loc: `${origin}${taxCalcSeoPath('en')}`,
      lastmod,
      changefreq: 'weekly',
      priority: '0.9',
    },
    ...TAX_CALC_SEO_LANGS.map((lang) => ({
      loc: `${origin}${taxCalcSeoPath(lang)}`,
      lastmod,
      changefreq: 'weekly',
      priority: '0.85',
    })),
  ];
  const body = entries
    .map(
      (u) => `  <url>
    <loc>${escapeXml(u.loc)}</loc>
    <lastmod>${u.lastmod}</lastmod>
    <changefreq>${u.changefreq}</changefreq>
    <priority>${u.priority}</priority>
  </url>`
    )
    .join('\n');
  return `<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
${body}
</urlset>`;
}

export function buildTaxCalculatorRobotsTxt(origin: string): string {
  const sitemap = `${origin.replace(/\/$/, '')}/sitemap-seo-tax-calculator.xml`;
  return [
    'User-agent: *',
    'Allow: /',
    'Disallow: /api/',
    'Disallow: /admin',
    '',
    `Sitemap: ${sitemap}`,
    '',
  ].join('\n');
}
