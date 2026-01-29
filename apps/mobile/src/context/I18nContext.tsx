import React, { createContext, useContext, useEffect, useMemo, useState } from 'react';
import * as Localization from 'expo-localization';
import AsyncStorage from '@react-native-async-storage/async-storage';

import enGB from '../locales/en-GB.json';
import deDE from '../locales/de-DE.json';
import ruRU from '../locales/ru-RU.json';
import roMD from '../locales/ro-MD.json';
import ukUA from '../locales/uk-UA.json';
import plPL from '../locales/pl-PL.json';

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
  'ro-MD': roMD,
  'uk-UA': ukUA,
  'pl-PL': plPL,
};

const LOCALE_STORAGE_KEY = 'settings.locale.v1';

const normalizeLocale = (tag?: string) => {
  if (!tag) return 'en-GB';
  if (fallbackTranslations[tag]) return tag;
  const lower = tag.toLowerCase();
  const aliasMap: Record<string, string> = {
    en: 'en-GB',
    'en-gb': 'en-GB',
    'en-us': 'en-GB',
    de: 'de-DE',
    'de-de': 'de-DE',
    ru: 'ru-RU',
    'ru-ru': 'ru-RU',
    ro: 'ro-MD',
    'ro-ro': 'ro-MD',
    'ro-md': 'ro-MD',
    uk: 'uk-UA',
    'uk-ua': 'uk-UA',
    pl: 'pl-PL',
    'pl-pl': 'pl-PL',
  };
  if (aliasMap[lower]) return aliasMap[lower];
  const base = lower.split('-')[0];
  return aliasMap[base] || 'en-GB';
};

const mergeTranslations = (fallback: Translations, remote?: Translations) => {
  if (!remote) return fallback;
  const merged: Translations = { ...fallback };
  Object.keys(remote).forEach((namespace) => {
    merged[namespace] = { ...(fallback[namespace] || {}), ...(remote[namespace] || {}) };
  });
  return merged;
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
  const initialLocale = normalizeLocale(deviceLocale);
  const [locale, setLocaleState] = useState(initialLocale);
  const [translations, setTranslations] = useState<Translations>(fallbackTranslations[initialLocale]);

  useEffect(() => {
    let mounted = true;
    const loadStoredLocale = async () => {
      try {
        const stored = await AsyncStorage.getItem(LOCALE_STORAGE_KEY);
        if (!mounted || !stored) return;
        const normalized = normalizeLocale(stored);
        setLocaleState(normalized);
      } catch {
        return;
      }
    };
    loadStoredLocale();
    return () => {
      mounted = false;
    };
  }, []);

  const setLocale = (nextLocale: string) => {
    const normalized = normalizeLocale(nextLocale);
    setLocaleState(normalized);
    AsyncStorage.setItem(LOCALE_STORAGE_KEY, normalized).catch(() => {
      return;
    });
  };

  useEffect(() => {
    const loadTranslations = async () => {
      const fallback = fallbackTranslations[locale] || fallbackTranslations['en-GB'];
      setTranslations(fallback);
      try {
        const response = await fetch(`${LOCALIZATION_URL}/translations/${locale}/all`);
        if (response.ok) {
          const data = await response.json();
          setTranslations(mergeTranslations(fallback, data));
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
