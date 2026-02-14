import { useContext } from 'react';
import { IntlMessageFormat } from 'intl-messageformat';
import { I18nContext } from '../context/i18n';

type TranslationPrimitive = string | number | boolean | Date;
type TranslationValues = Record<string, TranslationPrimitive | null | undefined>;

const MESSAGE_FORMAT_CACHE = new Map<string, IntlMessageFormat>();

const getCachedMessageFormatter = (locale: string, messageTemplate: string): IntlMessageFormat => {
  const cacheKey = `${locale}::${messageTemplate}`;
  const cachedFormatter = MESSAGE_FORMAT_CACHE.get(cacheKey);
  if (cachedFormatter) {
    return cachedFormatter;
  }
  const formatter = new IntlMessageFormat(messageTemplate, locale);
  MESSAGE_FORMAT_CACHE.set(cacheKey, formatter);
  return formatter;
};

export const useTranslation = () => {
  const { formatStandards, locale, translations } = useContext(I18nContext);
  const activeLocale = locale || formatStandards.locale || 'en-GB';

  const t = (key: string, values: TranslationValues = {}): string => {
    const [namespace, ...subkeyParts] = key.split('.');
    const subkey = subkeyParts.join('.');
    const messageTemplate = translations[namespace]?.[subkey];
    if (!messageTemplate) {
      return key;
    }
    try {
      const formatter = getCachedMessageFormatter(activeLocale, messageTemplate);
      return String(formatter.format(values));
    } catch {
      return messageTemplate;
    }
  };

  const tp = (key: string, count: number, values: TranslationValues = {}) => {
    return t(key, { ...values, count });
  };

  const formatNumber = (value: number, options: Intl.NumberFormatOptions = {}): string => {
    return new Intl.NumberFormat(activeLocale, {
      maximumFractionDigits: formatStandards.number_max_fraction_digits,
      minimumFractionDigits: formatStandards.number_min_fraction_digits,
      ...options,
    }).format(value);
  };

  const formatCurrency = (
    value: number,
    currency: string = formatStandards.default_currency,
    options: Intl.NumberFormatOptions = {}
  ): string => {
    return new Intl.NumberFormat(activeLocale, {
      currency,
      maximumFractionDigits: formatStandards.number_max_fraction_digits,
      minimumFractionDigits: 2,
      style: 'currency',
      ...options,
    }).format(value);
  };

  const formatDate = (value: Date | string | number, options: Intl.DateTimeFormatOptions = {}): string => {
    const dateValue = value instanceof Date ? value : new Date(value);
    if (Number.isNaN(dateValue.getTime())) {
      return '';
    }
    return new Intl.DateTimeFormat(activeLocale, {
      dateStyle: formatStandards.date_style,
      timeZone: formatStandards.time_zone,
      ...options,
    }).format(dateValue);
  };

  const formatDateTime = (value: Date | string | number, options: Intl.DateTimeFormatOptions = {}): string => {
    const dateValue = value instanceof Date ? value : new Date(value);
    if (Number.isNaN(dateValue.getTime())) {
      return '';
    }
    return new Intl.DateTimeFormat(activeLocale, {
      dateStyle: formatStandards.date_style,
      timeStyle: formatStandards.time_style,
      timeZone: formatStandards.time_zone,
      ...options,
    }).format(dateValue);
  };

  return { formatCurrency, formatDate, formatDateTime, formatNumber, tp, t };
};
