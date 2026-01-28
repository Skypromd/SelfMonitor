import React, { useEffect, useState } from 'react';
import { StyleSheet, Text } from 'react-native';

import Card from '../components/Card';
import SectionHeader from '../components/SectionHeader';
import PrimaryButton from '../components/PrimaryButton';
import Screen from '../components/Screen';
import { useTranslation } from '../hooks/useTranslation';
import { apiRequest } from '../services/api';
import { useAuth } from '../context/AuthContext';
import { colors, spacing } from '../theme';

type Cadence = {
  cadence: string;
  turnover_last_12_months: number;
  threshold: number;
  quarterly_required: boolean;
};

export default function ReportsScreen() {
  const { token } = useAuth();
  const { t } = useTranslation();
  const [cadence, setCadence] = useState<Cadence | null>(null);
  const [message, setMessage] = useState('');

  useEffect(() => {
    const fetchCadence = async () => {
      try {
        const response = await apiRequest('/analytics/reports/reporting-cadence', { token });
        if (!response.ok) return;
        setCadence(await response.json());
      } catch {
        setCadence(null);
      }
    };
    fetchCadence();
  }, [token]);

  return (
    <Screen>
      <SectionHeader title={t('reports.title')} subtitle={t('reports.subtitle')} />
      {cadence && (
        <Card>
          <Text style={styles.cardTitle}>{t('reports.cadence_title')}</Text>
          <Text>{t('reports.cadence_turnover')} GBP {cadence.turnover_last_12_months.toFixed(2)}</Text>
          <Text>{t('reports.cadence_threshold')} GBP {cadence.threshold.toFixed(2)}</Text>
          <Text style={cadence.quarterly_required ? styles.warning : styles.ok}>
            {cadence.quarterly_required ? t('reports.cadence_quarterly_required') : t('reports.cadence_monthly_ok')}
          </Text>
        </Card>
      )}
      <Card>
        <Text style={styles.cardTitle}>{t('reports.monthly')}</Text>
        <PrimaryButton title={t('reports.monthly')} onPress={() => setMessage(t('reports.monthly_message'))} />
      </Card>
      <Card>
        <Text style={styles.cardTitle}>{t('reports.quarterly')}</Text>
        <PrimaryButton title={t('reports.quarterly')} onPress={() => setMessage(t('reports.quarterly_message'))} />
      </Card>
      <Card>
        <Text style={styles.cardTitle}>{t('reports.profit_loss')}</Text>
        <PrimaryButton title={t('reports.profit_loss')} onPress={() => setMessage(t('reports.profit_loss_message'))} />
      </Card>
      <Card>
        <Text style={styles.cardTitle}>{t('reports.tax_year')}</Text>
        <PrimaryButton title={t('reports.tax_year')} onPress={() => setMessage(t('reports.tax_year_message'))} />
      </Card>
      <Card>
        <Text style={styles.cardTitle}>{t('reports.mortgage')}</Text>
        <PrimaryButton title={t('reports.mortgage')} onPress={() => setMessage(t('reports.mortgage_message'))} />
      </Card>
      {message ? <Text style={styles.message}>{message}</Text> : null}
    </Screen>
  );
}

const styles = StyleSheet.create({
  cardTitle: {
    fontSize: 16,
    fontWeight: '600',
    marginBottom: 12,
    color: colors.textPrimary,
  },
  message: {
    marginTop: spacing.md,
    color: colors.success,
  },
  warning: {
    marginTop: spacing.sm,
    color: colors.danger,
    fontWeight: '600',
  },
  ok: {
    marginTop: spacing.sm,
    color: colors.success,
    fontWeight: '600',
  },
});
