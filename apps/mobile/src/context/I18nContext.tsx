import React, { createContext, useContext, useEffect, useMemo, useState } from 'react';
import * as Localization from 'expo-localization';

import enGB from '../locales/en-GB.json';
import deDE from '../locales/de-DE.json';
import ruRU from '../locales/ru-RU.json';

type Translations = Record<string, Record<string, string>>;

type I18nContextValue = {
  locale: string;
  translations: Translations;
  setLocale: (locale: string) => void;
};

const fallbackTranslations: Record<string, Translations> = {
  'en-GB': enGB,
  'de-DE': deDE,
  'ru-RU': ruRU,
};

const I18nContext = createContext<I18nContextValue>({
  locale: 'en-GB',
  translations: enGB,
  setLocale: () => {},
});

const API_GATEWAY_URL = process.env.EXPO_PUBLIC_API_GATEWAY_URL || 'http://localhost:8000/api';
const LOCALIZATION_URL = process.env.EXPO_PUBLIC_LOCALIZATION_SERVICE_URL || `${API_GATEWAY_URL}/localization`;

export function I18nProvider({ children }: { children: React.ReactNode }) {
  const deviceLocale = Localization.getLocales()[0]?.languageTag || 'en-GB';
  const initialLocale = fallbackTranslations[deviceLocale] ? deviceLocale : 'en-GB';
  const [locale, setLocale] = useState(initialLocale);
  const [translations, setTranslations] = useState<Translations>(fallbackTranslations[initialLocale]);

  useEffect(() => {
    const loadTranslations = async () => {
      const fallback = fallbackTranslations[locale] || fallbackTranslations['en-GB'];
      setTranslations(fallback);
      try {
        const response = await fetch(`${LOCALIZATION_URL}/translations/${locale}/all`);
        if (response.ok) {
          const data = await response.json();
          setTranslations(data);
        }
      } catch {
        setTranslations(fallback);
      }
    };
    loadTranslations();
  }, [locale]);

  const value = useMemo(() => ({ locale, translations, setLocale }), [locale, translations]);

  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>;
}

export const useI18n = () => useContext(I18nContext);
