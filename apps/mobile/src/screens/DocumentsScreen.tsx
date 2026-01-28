import React from 'react';
import { ScrollView, StyleSheet, Text } from 'react-native';

import Card from '../components/Card';
import SectionHeader from '../components/SectionHeader';
import PrimaryButton from '../components/PrimaryButton';
import { useTranslation } from '../hooks/useTranslation';

export default function DocumentsScreen() {
  const { t } = useTranslation();

  return (
    <ScrollView style={styles.container}>
      <SectionHeader title={t('documents.title')} subtitle={t('documents.subtitle')} />
      <Card>
        <Text style={styles.cardTitle}>{t('documents.title')}</Text>
        <PrimaryButton title={t('documents.scan_button')} onPress={() => {}} />
        <Text style={styles.divider}>or</Text>
        <PrimaryButton title={t('documents.upload_button')} onPress={() => {}} />
      </Card>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    padding: 16,
  },
  cardTitle: {
    fontSize: 16,
    fontWeight: '600',
    marginBottom: 12,
    color: '#0f172a',
  },
  divider: {
    textAlign: 'center',
    color: '#94a3b8',
    marginVertical: 12,
  },
});
