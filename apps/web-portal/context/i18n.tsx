import { createContext, useState, ReactNode } from 'react';

type Translations = {
  [key: string]: { [key: string]: string }
};

export type LocaleFormatStandards = {
  locale: string;
  default_currency: string;
  date_style: 'short' | 'medium' | 'long' | 'full';
  time_style: 'short' | 'medium' | 'long' | 'full';
  time_zone: string;
  number_min_fraction_digits: number;
  number_max_fraction_digits: number;
};

export const buildDefaultFormatStandards = (locale: string): LocaleFormatStandards => ({
  locale,
  default_currency: locale === 'de-DE' ? 'EUR' : 'GBP',
  date_style: 'medium',
  time_style: 'short',
  time_zone: locale === 'de-DE' ? 'Europe/Berlin' : 'Europe/London',
  number_min_fraction_digits: 0,
  number_max_fraction_digits: 2,
});

type I18nContextType = {
  formatStandards: LocaleFormatStandards;
  locale: string;
  setFormatStandards: (formatStandards: LocaleFormatStandards) => void;
  setLocale: (locale: string) => void;
  translations: Translations;
  setTranslations: (translations: Translations) => void;
};

export const I18nContext = createContext<I18nContextType>({
  formatStandards: buildDefaultFormatStandards('en-GB'),
  locale: 'en-GB',
  setFormatStandards: () => {},
  setLocale: () => {},
  translations: {},
  setTranslations: () => {},
});

export const I18nProvider = ({ children }: { children: ReactNode }) => {
  const [translations, setTranslations] = useState<Translations>({});
  const [locale, setLocale] = useState('en-GB');
  const [formatStandards, setFormatStandards] = useState<LocaleFormatStandards>(buildDefaultFormatStandards('en-GB'));

  return (
    <I18nContext.Provider
      value={{ formatStandards, locale, setFormatStandards, setLocale, translations, setTranslations }}
    >
      {children}
    </I18nContext.Provider>
  );
};
