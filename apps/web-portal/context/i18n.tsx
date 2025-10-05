import { createContext, useState, ReactNode } from 'react';

type Translations = {
  [key: string]: { [key: string]: string }
};

type I18nContextType = {
  translations: Translations;
  setTranslations: (translations: Translations) => void;
};

export const I18nContext = createContext<I18nContextType>({
  translations: {},
  setTranslations: () => {},
});

export const I18nProvider = ({ children }: { children: ReactNode }) => {
  const [translations, setTranslations] = useState<Translations>({});

  return (
    <I18nContext.Provider value={{ translations, setTranslations }}>
      {children}
    </I18nContext.Provider>
  );
};
