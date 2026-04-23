import type { GetServerSideProps } from 'next';

import { buildTaxCalculatorSitemapXml, siteOriginFromRequest } from '../lib/taxCalcSitemapXml';

export const getServerSideProps: GetServerSideProps = async ({ req, res }) => {
  const origin = siteOriginFromRequest(req);
  const xml = buildTaxCalculatorSitemapXml(origin);
  res.setHeader('Content-Type', 'application/xml; charset=utf-8');
  res.setHeader('Cache-Control', 'public, s-maxage=3600, stale-while-revalidate=86400');
  res.write(xml);
  res.end();
  return { props: {} };
};

export default function SitemapSeoTaxCalculator() {
  return null;
}
