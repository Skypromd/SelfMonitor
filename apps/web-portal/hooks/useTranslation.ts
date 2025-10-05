import { useContext } from 'react';
import { I18nContext } from '../context/i18n';

export const useTranslation = () => {
  const { translations } = useContext(I18nContext);

  const t = (key: string): string => {
    const [namespace, subkey] = key.split('.');
    if (translations[namespace] && translations[namespace][subkey]) {
      return translations[namespace][subkey];
    }
    // Return the key itself as a fallback
    return key;
  };

  return { t };
};
