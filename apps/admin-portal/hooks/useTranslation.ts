// Minimal translation stub — admin portal is English-only
const STRINGS: Record<string, string> = {
  'nav.admin': 'Owner Console',
  'admin.form_title': 'Deactivate User',
  'admin.deactivate_button': 'Deactivate',
};

export function useTranslation() {
  const t = (key: string) => STRINGS[key] ?? key;
  return { t };
}
