import React from 'react';
import { Linking, StyleSheet, Text, View } from 'react-native';

import SectionHeader from '../components/SectionHeader';
import Card from '../components/Card';
import PrimaryButton from '../components/PrimaryButton';
import Screen from '../components/Screen';
import FadeInView from '../components/FadeInView';
import Badge from '../components/Badge';
import { useTranslation } from '../hooks/useTranslation';
import { colors, spacing } from '../theme';

export default function MarketplaceScreen() {
  const { t } = useTranslation();
  const handleRequest = (subject: string) => {
    const encoded = encodeURIComponent(subject);
    Linking.openURL(`mailto:partners@selfmonitor.app?subject=${encoded}`);
  };

  return (
    <Screen>
      <SectionHeader title={t('marketplace.title')} subtitle={t('marketplace.subtitle')} />
      <FadeInView>
        <Card>
          <View style={styles.tag}>
            <Badge label={t('marketplace.featured_label')} tone="info" />
          </View>
          <Text style={styles.partnerTitle}>{t('marketplace.accounting_title')}</Text>
          <Text style={styles.partnerSubtitle}>{t('marketplace.accounting_subtitle')}</Text>
          <PrimaryButton
            title={t('marketplace.request_contact')}
            onPress={() => handleRequest(t('marketplace.accounting_subject'))}
            haptic="medium"
          />
        </Card>
      </FadeInView>
      <FadeInView delay={120}>
        <Card>
          <View style={styles.tag}>
            <Badge label={t('marketplace.featured_label')} tone="success" />
          </View>
          <Text style={styles.partnerTitle}>{t('marketplace.insurance_title')}</Text>
          <Text style={styles.partnerSubtitle}>{t('marketplace.insurance_subtitle')}</Text>
          <PrimaryButton
            title={t('marketplace.request_contact')}
            onPress={() => handleRequest(t('marketplace.insurance_subject'))}
            haptic="medium"
          />
        </Card>
      </FadeInView>
      <FadeInView delay={240}>
        <Card>
          <View style={styles.tag}>
            <Badge label={t('marketplace.featured_label')} tone="warning" />
          </View>
          <Text style={styles.partnerTitle}>{t('marketplace.mortgage_title')}</Text>
          <Text style={styles.partnerSubtitle}>{t('marketplace.mortgage_subtitle')}</Text>
          <PrimaryButton
            title={t('marketplace.request_contact')}
            onPress={() => handleRequest(t('marketplace.mortgage_subject'))}
            haptic="medium"
          />
        </Card>
      </FadeInView>
    </Screen>
  );
}

const styles = StyleSheet.create({
  tag: {
    marginBottom: spacing.sm,
  },
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
