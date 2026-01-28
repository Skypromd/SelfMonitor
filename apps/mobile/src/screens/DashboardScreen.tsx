import React, { useEffect, useState } from 'react';
import { StyleSheet, Text, View } from 'react-native';

import SectionHeader from '../components/SectionHeader';
import PrimaryButton from '../components/PrimaryButton';
import GradientCard from '../components/GradientCard';
import StatCard from '../components/StatCard';
import Screen from '../components/Screen';
import { apiRequest } from '../services/api';
import { useAuth } from '../context/AuthContext';
import { useTranslation } from '../hooks/useTranslation';
import { colors, spacing } from '../theme';

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
    <Screen>
      <GradientCard colors={['#2563eb', '#1d4ed8']}>
        <Text style={styles.heroTitle}>{t('dashboard.title')}</Text>
        <Text style={styles.heroSubtitle}>{t('dashboard.readiness_subtitle')}</Text>
        <View style={styles.heroStats}>
          <View style={styles.heroStat}>
            <Text style={styles.heroStatValue}>{readinessScore}%</Text>
            <Text style={styles.heroStatLabel}>{t('dashboard.readiness_title')}</Text>
          </View>
          <View style={styles.heroStat}>
            <Text style={styles.heroStatValue}>
              {cashFlow === null ? t('common.loading') : `GBP ${cashFlow.toFixed(2)}`}
            </Text>
            <Text style={styles.heroStatLabel}>{t('dashboard.cashflow_title')}</Text>
          </View>
        </View>
      </GradientCard>

      <SectionHeader title={t('dashboard.quick_actions')} subtitle={t('dashboard.readiness_subtitle')} />
      <View style={styles.quickActions}>
        <PrimaryButton title={t('dashboard.add_expense')} onPress={() => {}} variant="secondary" />
        <PrimaryButton title={t('dashboard.scan_receipt')} onPress={() => {}} variant="secondary" />
        <PrimaryButton title={t('dashboard.generate_report')} onPress={() => {}} variant="secondary" />
      </View>

      <SectionHeader title={t('dashboard.readiness_title')} subtitle={t('dashboard.readiness_subtitle')} />
      <StatCard
        label={t('dashboard.readiness_title')}
        value={`${readinessScore}%`}
        icon="sparkles-outline"
        tone="success"
      />
      <StatCard
        label={t('dashboard.cashflow_title')}
        value={cashFlow === null ? t('common.loading') : `GBP ${cashFlow.toFixed(2)}`}
        icon="pulse-outline"
        tone="primary"
      />
    </Screen>
  );
}

const styles = StyleSheet.create({
  heroTitle: {
    color: colors.surface,
    fontSize: 28,
    fontWeight: '700',
  },
  heroSubtitle: {
    color: '#dbeafe',
    marginTop: spacing.xs,
    fontSize: 14,
  },
  heroStats: {
    marginTop: spacing.lg,
    gap: spacing.md,
  },
  heroStat: {
    backgroundColor: 'rgba(255, 255, 255, 0.15)',
    padding: spacing.md,
    borderRadius: 14,
  },
  heroStatValue: {
    color: colors.surface,
    fontSize: 20,
    fontWeight: '700',
  },
  heroStatLabel: {
    color: '#dbeafe',
    marginTop: spacing.xs,
    fontSize: 12,
  },
  quickActions: {
    gap: spacing.md,
  },
});
