/**
 * Canonical / hreflang paths for public tax calculator landings.
 * Must match `next.config.js` i18n.defaultLocale (default locale has no URL prefix in Next).
 */
import { TAX_CALC_SEO_LANGS, type TaxCalcSeoLang } from './taxCalculatorSeoCopy';

export const NEXT_I18N_DEFAULT_LOCALE = 'ru-RU';

export function taxCalcSeoPath(seoLang: 'en' | TaxCalcSeoLang): string {
  return seoLang === 'en' ? '/tax-calculator-uk' : `/tax-calculator-uk/${seoLang}`;
}

/** Absolute URL for SEO (single preferred URL per language, default-locale routing). */
export function absoluteTaxCalcSeoUrl(origin: string, seoLang: 'en' | TaxCalcSeoLang): string {
  const base = origin.replace(/\/$/, '');
  return `${base}${taxCalcSeoPath(seoLang)}`;
}

export function taxCalcHreflangRows(): { hreflang: string; seoLang: 'en' | TaxCalcSeoLang }[] {
  return [
    { hreflang: 'en-GB', seoLang: 'en' },
    ...TAX_CALC_SEO_LANGS.map((l) => ({ hreflang: l, seoLang: l })),
  ];
}
