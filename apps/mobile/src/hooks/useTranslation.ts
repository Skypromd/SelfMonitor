import { useI18n } from '../context/I18nContext';

export const useTranslation = () => {
  const { translations } = useI18n();

  const t = (key: string): string => {
    const [namespace, subkey] = key.split('.');
    if (translations[namespace] && translations[namespace][subkey]) {
      return translations[namespace][subkey];
    }
    return key;
  };

  return { t };
};
