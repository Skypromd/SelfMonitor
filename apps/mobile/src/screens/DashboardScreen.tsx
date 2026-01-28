import React, { useEffect, useState } from 'react';
import { StyleSheet, Text, View } from 'react-native';
import { useNavigation } from '@react-navigation/native';

import SectionHeader from '../components/SectionHeader';
import PrimaryButton from '../components/PrimaryButton';
import GradientCard from '../components/GradientCard';
import StatCard from '../components/StatCard';
import Screen from '../components/Screen';
import ProgressBar from '../components/ProgressBar';
import Badge from '../components/Badge';
import FadeInView from '../components/FadeInView';
import InfoRow from '../components/InfoRow';
import PulseDot from '../components/PulseDot';
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
  const navigation = useNavigation();
  const [readinessScore, setReadinessScore] = useState(0);
  const [cashFlow, setCashFlow] = useState<number | null>(null);
  const [readinessMeta, setReadinessMeta] = useState({
    missingCategories: 0,
    missingBusinessUse: 0,
    total: 0,
  });

  useEffect(() => {
    const loadReadiness = async () => {
      try {
        const response = await apiRequest('/transactions/transactions/me', { token });
        if (!response.ok) return;
        const data: Transaction[] = await response.json();
        if (!data.length) {
          setReadinessScore(0);
          setReadinessMeta({ missingCategories: 0, missingBusinessUse: 0, total: 0 });
          return;
        }
        const missingCategories = data.filter(item => !item.tax_category && !item.category).length;
        const missingBusinessUse = data.filter(item => item.amount < 0 && item.business_use_percent == null).length;
        const categoryScore = (data.length - missingCategories) / data.length;
        const businessScore = (data.length - missingBusinessUse) / data.length;
        setReadinessScore(Math.round((categoryScore * 0.6 + businessScore * 0.4) * 100));
        setReadinessMeta({ missingCategories, missingBusinessUse, total: data.length });
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

  const readinessLabel = readinessScore >= 80
    ? t('dashboard.readiness_good')
    : readinessScore >= 50
      ? t('dashboard.readiness_medium')
      : t('dashboard.readiness_low');

  return (
    <Screen>
      <FadeInView>
        <GradientCard colors={['#2563eb', '#1d4ed8']}>
          <View style={styles.heroHeader}>
            <View>
              <Text style={styles.heroTitle}>{t('dashboard.title')}</Text>
              <Text style={styles.heroSubtitle}>{t('dashboard.readiness_subtitle')}</Text>
              <View style={styles.liveRow}>
                <PulseDot />
                <Text style={styles.liveText}>{t('dashboard.live_label')}</Text>
              </View>
            </View>
            <Badge label={readinessLabel} tone={readinessScore >= 80 ? 'success' : readinessScore >= 50 ? 'warning' : 'danger'} />
          </View>
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
          <View style={styles.progressRow}>
            <ProgressBar value={readinessScore / 100} tone={readinessScore >= 80 ? 'success' : readinessScore >= 50 ? 'warning' : 'primary'} />
          </View>
        </GradientCard>
      </FadeInView>

      <SectionHeader title={t('dashboard.quick_actions')} subtitle={t('dashboard.readiness_subtitle')} />
      <FadeInView delay={80}>
        <View style={styles.quickActions}>
          <View style={styles.quickActionItem}>
            <PrimaryButton title={t('dashboard.add_expense')} onPress={() => navigation.navigate('Transactions' as never)} variant="secondary" />
          </View>
          <View style={styles.quickActionItem}>
            <PrimaryButton title={t('dashboard.scan_receipt')} onPress={() => navigation.navigate('Documents' as never)} variant="secondary" />
          </View>
          <View style={styles.quickActionItem}>
            <PrimaryButton title={t('dashboard.generate_report')} onPress={() => navigation.navigate('Reports' as never)} variant="secondary" />
          </View>
        </View>
      </FadeInView>

      <SectionHeader title={t('dashboard.readiness_title')} subtitle={t('dashboard.data_quality_subtitle')} />
      <FadeInView delay={160}>
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
        <View style={styles.metaCard}>
          <InfoRow label={t('dashboard.total_transactions')} value={`${readinessMeta.total}`} />
          <InfoRow label={t('dashboard.missing_categories')} value={`${readinessMeta.missingCategories}`} />
          <InfoRow label={t('dashboard.missing_business_use')} value={`${readinessMeta.missingBusinessUse}`} />
        </View>
      </FadeInView>
    </Screen>
  );
}

const styles = StyleSheet.create({
  heroTitle: {
    color: colors.surface,
    fontSize: 28,
    fontWeight: '700',
  },
  heroHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  heroSubtitle: {
    color: '#dbeafe',
    marginTop: spacing.xs,
    fontSize: 14,
  },
  liveRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginTop: spacing.sm,
  },
  liveText: {
    color: '#dbeafe',
    marginLeft: spacing.sm,
    fontSize: 12,
    fontWeight: '600',
  },
  heroStats: {
    marginTop: spacing.lg,
  },
  heroStat: {
    backgroundColor: 'rgba(255, 255, 255, 0.15)',
    padding: spacing.md,
    borderRadius: 14,
    marginBottom: spacing.md,
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
  progressRow: {
    marginTop: spacing.md,
  },
  quickActions: {
    marginBottom: spacing.sm,
  },
  quickActionItem: {
    marginBottom: spacing.md,
  },
  metaCard: {
    marginTop: spacing.md,
    padding: spacing.md,
    borderRadius: 16,
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.border,
  },
});
