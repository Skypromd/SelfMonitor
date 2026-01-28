import React from 'react';
import { ScrollView, StyleSheet, Text, Pressable, View } from 'react-native';

import SectionHeader from '../components/SectionHeader';
import Card from '../components/Card';
import { useTranslation } from '../hooks/useTranslation';
import { useI18n } from '../context/I18nContext';

const LOCALES = ['en-GB', 'de-DE', 'ru-RU'];

export default function SettingsScreen() {
  const { t } = useTranslation();
  const { locale, setLocale } = useI18n();

  return (
    <ScrollView style={styles.container}>
      <SectionHeader title={t('settings.title')} subtitle={t('settings.subtitle')} />
      <Card>
        <Text style={styles.sectionTitle}>Language</Text>
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
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    padding: 16,
  },
  sectionTitle: {
    fontSize: 16,
    fontWeight: '600',
    marginBottom: 12,
    color: '#0f172a',
  },
  localeRow: {
    flexDirection: 'row',
    gap: 12,
  },
  localePill: {
    paddingVertical: 8,
    paddingHorizontal: 14,
    borderRadius: 999,
    borderWidth: 1,
    borderColor: '#e2e8f0',
  },
  localePillActive: {
    borderColor: '#2563eb',
    backgroundColor: '#eff6ff',
  },
  localeText: {
    color: '#64748b',
    fontWeight: '600',
  },
  localeTextActive: {
    color: '#1d4ed8',
  },
});
