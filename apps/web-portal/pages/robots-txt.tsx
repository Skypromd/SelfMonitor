import type { GetServerSideProps } from 'next';

import { buildTaxCalculatorRobotsTxt, siteOriginFromRequest } from '../lib/taxCalcSitemapXml';

export const getServerSideProps: GetServerSideProps = async ({ req, res }) => {
  const origin = siteOriginFromRequest(req);
  const body = buildTaxCalculatorRobotsTxt(origin);
  res.setHeader('Content-Type', 'text/plain; charset=utf-8');
  res.setHeader('Cache-Control', 'public, s-maxage=86400, stale-while-revalidate=604800');
  res.write(body);
  res.end();
  return { props: {} };
};

export default function RobotsTxt() {
  return null;
}
