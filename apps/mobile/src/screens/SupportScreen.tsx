import React from 'react';
import { ScrollView, StyleSheet, Text } from 'react-native';

import SectionHeader from '../components/SectionHeader';
import Card from '../components/Card';
import { useTranslation } from '../hooks/useTranslation';

export default function SupportScreen() {
  const { t } = useTranslation();

  return (
    <ScrollView style={styles.container}>
      <SectionHeader title={t('support.title')} subtitle={t('support.subtitle')} />
      <Card>
        <Text style={styles.label}>Email</Text>
        <Text style={styles.value}>support@selfmonitor.app</Text>
        <Text style={styles.label}>Help Center</Text>
        <Text style={styles.value}>selfmonitor.app/help</Text>
      </Card>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    padding: 16,
  },
  label: {
    color: '#64748b',
    marginBottom: 4,
  },
  value: {
    color: '#0f172a',
    fontWeight: '600',
    marginBottom: 12,
  },
});
