import React from 'react';
import { StyleSheet, Text, Pressable, View } from 'react-native';

import SectionHeader from '../components/SectionHeader';
import Card from '../components/Card';
import Screen from '../components/Screen';
import { useTranslation } from '../hooks/useTranslation';
import { useI18n } from '../context/I18nContext';
import { colors, spacing } from '../theme';

const LOCALES = ['en-GB', 'de-DE', 'ru-RU'];

export default function SettingsScreen() {
  const { t } = useTranslation();
  const { locale, setLocale } = useI18n();

  return (
    <Screen>
      <SectionHeader title={t('settings.title')} subtitle={t('settings.subtitle')} />
      <Card>
        <Text style={styles.sectionTitle}>{t('settings.language_label')}</Text>
        <View style={styles.localeRow}>
          {LOCALES.map((item) => (
            <Pressable
              key={item}
              onPress={() => setLocale(item)}
              style={[styles.localePill, locale === item && styles.localePillActive]}
            >
              <Text style={[styles.localeText, locale === item && styles.localeTextActive]}>
                {item.split('-')[0].toUpperCase()}
              </Text>
            </Pressable>
          ))}
        </View>
      </Card>
    </Screen>
  );
}

const styles = StyleSheet.create({
  sectionTitle: {
    fontSize: 16,
    fontWeight: '600',
    marginBottom: spacing.md,
    color: colors.textPrimary,
  },
  localeRow: {
    flexDirection: 'row',
    gap: spacing.md,
  },
  localePill: {
    paddingVertical: spacing.sm,
    paddingHorizontal: spacing.md,
    borderRadius: 999,
    borderWidth: 1,
    borderColor: colors.border,
  },
  localePillActive: {
    borderColor: colors.primary,
    backgroundColor: '#eff6ff',
  },
  localeText: {
    color: colors.textSecondary,
    fontWeight: '600',
  },
  localeTextActive: {
    color: colors.primaryDark,
  },
});
