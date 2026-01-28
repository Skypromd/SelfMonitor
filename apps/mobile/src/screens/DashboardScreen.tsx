import React, { useEffect, useState } from 'react';
import { ScrollView, StyleSheet, Text, View } from 'react-native';

import Card from '../components/Card';
import SectionHeader from '../components/SectionHeader';
import PrimaryButton from '../components/PrimaryButton';
import { apiRequest } from '../services/api';
import { useAuth } from '../context/AuthContext';
import { useTranslation } from '../hooks/useTranslation';

type Transaction = {
  amount: number;
  category?: string | null;
  tax_category?: string | null;
  business_use_percent?: number | null;
};

export default function DashboardScreen() {
  const { token } = useAuth();
  const { t } = useTranslation();
  const [readinessScore, setReadinessScore] = useState(0);
  const [cashFlow, setCashFlow] = useState<number | null>(null);

  useEffect(() => {
    const loadReadiness = async () => {
      try {
        const response = await apiRequest('/transactions/transactions/me', { token });
        if (!response.ok) return;
        const data: Transaction[] = await response.json();
        if (!data.length) {
          setReadinessScore(0);
          return;
        }
        const missingCategories = data.filter(item => !item.tax_category && !item.category).length;
        const missingBusinessUse = data.filter(item => item.amount < 0 && item.business_use_percent == null).length;
        const categoryScore = (data.length - missingCategories) / data.length;
        const businessScore = (data.length - missingBusinessUse) / data.length;
        setReadinessScore(Math.round((categoryScore * 0.6 + businessScore * 0.4) * 100));
      } catch {
        setReadinessScore(0);
      }
    };

    const loadCashFlow = async () => {
      try {
        const response = await apiRequest('/analytics/forecast/cash-flow', {
          method: 'POST',
          token,
          body: JSON.stringify({ days_to_forecast: 30 }),
        });
        if (!response.ok) return;
        const data = await response.json();
        if (data.forecast?.length) {
          const last = data.forecast[data.forecast.length - 1];
          setCashFlow(last.balance);
        }
      } catch {
        setCashFlow(null);
      }
    };

    loadReadiness();
    loadCashFlow();
  }, [token]);

  return (
    <ScrollView style={styles.container}>
      <SectionHeader title={t('dashboard.title')} subtitle={t('dashboard.readiness_subtitle')} />

      <Card>
        <Text style={styles.cardTitle}>{t('dashboard.readiness_title')}</Text>
        <Text style={styles.score}>{readinessScore}%</Text>
        <Text style={styles.caption}>{t('dashboard.readiness_subtitle')}</Text>
      </Card>

      <Card>
        <Text style={styles.cardTitle}>{t('dashboard.cashflow_title')}</Text>
        <Text style={styles.score}>
          {cashFlow === null ? t('common.loading') : `£${cashFlow.toFixed(2)}`}
        </Text>
        <Text style={styles.caption}>{t('dashboard.cashflow_title')}</Text>
      </Card>

      <Card>
        <Text style={styles.cardTitle}>{t('dashboard.quick_actions')}</Text>
        <View style={styles.buttonStack}>
          <PrimaryButton title={t('dashboard.add_expense')} onPress={() => {}} />
          <PrimaryButton title={t('dashboard.scan_receipt')} onPress={() => {}} />
          <PrimaryButton title={t('dashboard.generate_report')} onPress={() => {}} />
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
  cardTitle: {
    fontSize: 16,
    fontWeight: '600',
    color: '#0f172a',
    marginBottom: 8,
  },
  score: {
    fontSize: 28,
    fontWeight: '700',
    color: '#2563eb',
  },
  caption: {
    marginTop: 8,
    color: '#64748b',
  },
  buttonStack: {
    gap: 12,
  },
});
