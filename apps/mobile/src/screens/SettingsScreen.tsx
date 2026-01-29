import React, { useEffect, useState } from 'react';
import { StyleSheet, Text, Pressable, Switch, View } from 'react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';

import SectionHeader from '../components/SectionHeader';
import Card from '../components/Card';
import Screen from '../components/Screen';
import { useTranslation } from '../hooks/useTranslation';
import { useI18n } from '../context/I18nContext';
import type { TranslationKey } from '../locales/translationKeys';
import { colors, spacing } from '../theme';

const LOCALES: { code: string; labelKey: TranslationKey; fallback: string }[] = [
  { code: 'en-GB', labelKey: 'settings.language_en_gb', fallback: 'English (UK)' },
  { code: 'de-DE', labelKey: 'settings.language_de_de', fallback: 'Deutsch' },
  { code: 'ru-RU', labelKey: 'settings.language_ru_ru', fallback: 'Russian' },
  { code: 'ro-MD', labelKey: 'settings.language_ro_md', fallback: 'Romanian (MD)' },
  { code: 'uk-UA', labelKey: 'settings.language_uk_ua', fallback: 'Ukrainian' },
  { code: 'pl-PL', labelKey: 'settings.language_pl_pl', fallback: 'Polish' },
];
const PREFS_KEY = 'settings.preferences.v1';

export default function SettingsScreen() {
  const { t } = useTranslation();
  const { locale, setLocale } = useI18n();
  const [prefs, setPrefs] = useState({
    push: true,
    taxReminders: true,
    monthlyDigest: false,
  });

  useEffect(() => {
    const loadPrefs = async () => {
      try {
        const stored = await AsyncStorage.getItem(PREFS_KEY);
        if (stored) {
          setPrefs(JSON.parse(stored));
        }
      } catch {
        return;
      }
    };
    loadPrefs();
  }, []);

  const updatePrefs = async (next: typeof prefs) => {
    setPrefs(next);
    try {
      await AsyncStorage.setItem(PREFS_KEY, JSON.stringify(next));
    } catch {
      return;
    }
  };

  return (
    <Screen>
      <SectionHeader title={t('settings.title')} subtitle={t('settings.subtitle')} />
      <Card>
        <Text style={styles.sectionTitle}>{t('settings.language_label')}</Text>
        <View style={styles.localeRow}>
          {LOCALES.map((item) => {
            const label = t(item.labelKey);
            const displayLabel = label === item.labelKey ? item.fallback : label;
            return (
            <View key={item.code} style={styles.localeItem}>
              <Pressable
                onPress={() => setLocale(item.code)}
                style={[styles.localePill, locale === item.code && styles.localePillActive]}
              >
                <Text style={[styles.localeText, locale === item.code && styles.localeTextActive]}>
                  {displayLabel}
                </Text>
              </Pressable>
            </View>
          );
          })}
        </View>
      </Card>
      <Card>
        <Text style={styles.sectionTitle}>{t('settings.notifications_title')}</Text>
        <View style={styles.toggleRow}>
          <View>
            <Text style={styles.toggleLabel}>{t('settings.push_label')}</Text>
            <Text style={styles.toggleHelper}>{t('settings.push_helper')}</Text>
          </View>
          <Switch
            value={prefs.push}
            onValueChange={(value) => updatePrefs({ ...prefs, push: value })}
            trackColor={{ true: colors.primary, false: colors.border }}
          />
        </View>
        <View style={styles.toggleRow}>
          <View>
            <Text style={styles.toggleLabel}>{t('settings.tax_label')}</Text>
            <Text style={styles.toggleHelper}>{t('settings.tax_helper')}</Text>
          </View>
          <Switch
            value={prefs.taxReminders}
            onValueChange={(value) => updatePrefs({ ...prefs, taxReminders: value })}
            trackColor={{ true: colors.primary, false: colors.border }}
          />
        </View>
        <View style={styles.toggleRow}>
          <View>
            <Text style={styles.toggleLabel}>{t('settings.digest_label')}</Text>
            <Text style={styles.toggleHelper}>{t('settings.digest_helper')}</Text>
          </View>
          <Switch
            value={prefs.monthlyDigest}
            onValueChange={(value) => updatePrefs({ ...prefs, monthlyDigest: value })}
            trackColor={{ true: colors.primary, false: colors.border }}
          />
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
    flexWrap: 'wrap',
  },
  localeItem: {
    marginRight: spacing.md,
    marginBottom: spacing.sm,
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
  toggleRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingVertical: spacing.sm,
    borderBottomWidth: 1,
    borderBottomColor: colors.border,
  },
  toggleLabel: {
    color: colors.textPrimary,
    fontWeight: '600',
  },
  toggleHelper: {
    color: colors.textSecondary,
    fontSize: 12,
    marginTop: spacing.xs,
  },
});
