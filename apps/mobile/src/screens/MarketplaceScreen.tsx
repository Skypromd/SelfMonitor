import React from 'react';
import { StyleSheet, Text } from 'react-native';

import SectionHeader from '../components/SectionHeader';
import Card from '../components/Card';
import PrimaryButton from '../components/PrimaryButton';
import Screen from '../components/Screen';
import { useTranslation } from '../hooks/useTranslation';
import { colors, spacing } from '../theme';

export default function MarketplaceScreen() {
  const { t } = useTranslation();

  return (
    <Screen>
      <SectionHeader title={t('marketplace.title')} subtitle={t('marketplace.subtitle')} />
      <Card>
        <Text style={styles.partnerTitle}>{t('marketplace.accounting_title')}</Text>
        <Text style={styles.partnerSubtitle}>{t('marketplace.accounting_subtitle')}</Text>
        <PrimaryButton title={t('marketplace.request_contact')} onPress={() => {}} />
      </Card>
      <Card>
        <Text style={styles.partnerTitle}>{t('marketplace.insurance_title')}</Text>
        <Text style={styles.partnerSubtitle}>{t('marketplace.insurance_subtitle')}</Text>
        <PrimaryButton title={t('marketplace.request_contact')} onPress={() => {}} />
      </Card>
      <Card>
        <Text style={styles.partnerTitle}>{t('marketplace.mortgage_title')}</Text>
        <Text style={styles.partnerSubtitle}>{t('marketplace.mortgage_subtitle')}</Text>
        <PrimaryButton title={t('marketplace.request_contact')} onPress={() => {}} />
      </Card>
    </Screen>
  );
}

const styles = StyleSheet.create({
  partnerTitle: {
    fontSize: 16,
    fontWeight: '600',
    color: colors.textPrimary,
    marginBottom: spacing.xs,
  },
  partnerSubtitle: {
    color: colors.textSecondary,
    marginBottom: spacing.sm,
  },
});
