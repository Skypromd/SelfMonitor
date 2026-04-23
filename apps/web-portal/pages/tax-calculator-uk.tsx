import Head from 'next/head';
import TaxCalculatorPublic from '../components/TaxCalculatorPublic';
import { TAX_CALCULATOR_COPY_EN, TAX_CALC_SEO_LANGS } from '../lib/taxCalculatorSeoCopy';
import { absoluteTaxCalcSeoUrl, taxCalcHreflangRows } from '../lib/taxCalcSeoUrl';

function siteOrigin(): string | null {
  const o = process.env.NEXT_PUBLIC_SITE_ORIGIN?.replace(/\/$/, '');
  return o && o.startsWith('http') ? o : null;
}

export default function TaxCalculatorUkPage() {
  const copy = TAX_CALCULATOR_COPY_EN;
  const origin = siteOrigin();
  const langLinks = [
    { href: '/tax-calculator-uk', label: 'EN' },
    ...TAX_CALC_SEO_LANGS.map((l) => ({
      href: `/tax-calculator-uk/${l}`,
      label: l.toUpperCase(),
    })),
  ];
  const canonical = origin ? absoluteTaxCalcSeoUrl(origin, 'en') : null;

  return (
    <>
      <Head>
        <title>{copy.metaTitle}</title>
        <meta name="description" content={copy.metaDescription} />
        <meta property="og:title" content={copy.metaTitle} />
        <meta property="og:description" content={copy.metaDescription} />
        {canonical && <link rel="canonical" href={canonical} />}
        {origin &&
          taxCalcHreflangRows().map(({ hreflang, seoLang }) => (
            <link
              key={hreflang}
              rel="alternate"
              hrefLang={hreflang}
              href={absoluteTaxCalcSeoUrl(origin, seoLang)}
            />
          ))}
        {origin && (
          <link rel="alternate" hrefLang="x-default" href={absoluteTaxCalcSeoUrl(origin, 'en')} />
        )}
      </Head>
      <TaxCalculatorPublic copy={copy} langLinks={langLinks} />
    </>
  );
}
