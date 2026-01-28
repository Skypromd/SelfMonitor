import React from 'react';
import { StyleSheet, Text } from 'react-native';

import Card from '../components/Card';
import SectionHeader from '../components/SectionHeader';
import PrimaryButton from '../components/PrimaryButton';
import GradientCard from '../components/GradientCard';
import Screen from '../components/Screen';
import { useTranslation } from '../hooks/useTranslation';
import { colors, spacing } from '../theme';

export default function DocumentsScreen() {
  const { t } = useTranslation();

  return (
    <Screen>
      <GradientCard colors={['#0f172a', '#1e293b']}>
        <Text style={styles.heroTitle}>{t('documents.title')}</Text>
        <Text style={styles.heroSubtitle}>{t('documents.subtitle')}</Text>
      </GradientCard>
      <Card>
        <Text style={styles.cardTitle}>{t('documents.scan_button')}</Text>
        <PrimaryButton title={t('documents.scan_button')} onPress={() => {}} />
      </Card>
      <Card>
        <Text style={styles.cardTitle}>{t('documents.upload_button')}</Text>
        <PrimaryButton title={t('documents.upload_button')} onPress={() => {}} variant="secondary" />
      </Card>
    </Screen>
  );
}

const styles = StyleSheet.create({
  heroTitle: {
    color: colors.surface,
    fontSize: 26,
    fontWeight: '700',
  },
  heroSubtitle: {
    color: '#cbd5f5',
    marginTop: spacing.xs,
  },
  cardTitle: {
    fontSize: 16,
    fontWeight: '600',
    marginBottom: spacing.sm,
    color: colors.textPrimary,
  },
});
