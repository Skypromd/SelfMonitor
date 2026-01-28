import React from 'react';
import { StyleSheet, Text } from 'react-native';

import SectionHeader from '../components/SectionHeader';
import Card from '../components/Card';
import Screen from '../components/Screen';
import { useTranslation } from '../hooks/useTranslation';
import { colors, spacing } from '../theme';

export default function SupportScreen() {
  const { t } = useTranslation();

  return (
    <Screen>
      <SectionHeader title={t('support.title')} subtitle={t('support.subtitle')} />
      <Card>
        <Text style={styles.label}>{t('support.email_label')}</Text>
        <Text style={styles.value}>support@selfmonitor.app</Text>
        <Text style={styles.label}>{t('support.help_label')}</Text>
        <Text style={styles.value}>selfmonitor.app/help</Text>
      </Card>
    </Screen>
  );
}

const styles = StyleSheet.create({
  label: {
    color: colors.textSecondary,
    marginBottom: spacing.xs,
  },
  value: {
    color: colors.textPrimary,
    fontWeight: '600',
    marginBottom: spacing.sm,
  },
});
