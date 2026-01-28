import React from 'react';
import { ScrollView, StyleSheet, Text } from 'react-native';

import SectionHeader from '../components/SectionHeader';
import Card from '../components/Card';
import PrimaryButton from '../components/PrimaryButton';
import { useTranslation } from '../hooks/useTranslation';

export default function MarketplaceScreen() {
  const { t } = useTranslation();

  return (
    <ScrollView style={styles.container}>
      <SectionHeader title={t('marketplace.title')} subtitle={t('marketplace.subtitle')} />
      <Card>
        <Text style={styles.partnerTitle}>Accounting & Tax</Text>
        <Text style={styles.partnerSubtitle}>Certified partners for Self-Assessment submissions.</Text>
        <PrimaryButton title="Request contact" onPress={() => {}} />
      </Card>
      <Card>
        <Text style={styles.partnerTitle}>Insurance</Text>
        <Text style={styles.partnerSubtitle}>Income protection and liability cover.</Text>
        <PrimaryButton title="Request contact" onPress={() => {}} />
      </Card>
      <Card>
        <Text style={styles.partnerTitle}>Mortgage Advisors</Text>
        <Text style={styles.partnerSubtitle}>Specialists in self-employed applications.</Text>
        <PrimaryButton title="Request contact" onPress={() => {}} />
      </Card>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    padding: 16,
  },
  partnerTitle: {
    fontSize: 16,
    fontWeight: '600',
    color: '#0f172a',
    marginBottom: 4,
  },
  partnerSubtitle: {
    color: '#64748b',
    marginBottom: 12,
  },
});
