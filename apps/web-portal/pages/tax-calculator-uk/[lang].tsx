import type { GetStaticPaths, GetStaticProps } from 'next';
import Head from 'next/head';
import TaxCalculatorPublic from '../../components/TaxCalculatorPublic';
import {
  getTaxCalcSeoLang,
  getTaxCalculatorCopyForSeoLang,
  TAX_CALC_SEO_LANGS,
  type TaxCalcSeoLang,
} from '../../lib/taxCalculatorSeoCopy';
import { absoluteTaxCalcSeoUrl, taxCalcHreflangRows } from '../../lib/taxCalcSeoUrl';

type Props = { lang: TaxCalcSeoLang };

function siteOrigin(): string | null {
  const o = process.env.NEXT_PUBLIC_SITE_ORIGIN?.replace(/\/$/, '');
  return o && o.startsWith('http') ? o : null;
}

export default function TaxCalculatorUkLocalizedPage({ lang }: Props) {
  const copy = getTaxCalculatorCopyForSeoLang(lang);
  const origin = siteOrigin();
  const langLinks = [
    { href: '/tax-calculator-uk', label: 'EN' },
    ...TAX_CALC_SEO_LANGS.map((l) => ({
      href: `/tax-calculator-uk/${l}`,
      label: l.toUpperCase(),
    })),
  ];
  const canonical = origin ? absoluteTaxCalcSeoUrl(origin, lang) : null;

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

export const getStaticPaths: GetStaticPaths = async () => ({
  paths: TAX_CALC_SEO_LANGS.map((lang) => ({ params: { lang } })),
  fallback: false,
});

export const getStaticProps: GetStaticProps<Props> = async ({ params }) => {
  const raw = typeof params?.lang === 'string' ? params.lang : '';
  const lang = getTaxCalcSeoLang(raw);
  if (!lang) {
    return { notFound: true };
  }
  return { props: { lang } };
};
