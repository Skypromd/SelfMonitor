import React, { useEffect, useState } from 'react';
import { StyleSheet, Text, View } from 'react-native';

import Card from '../components/Card';
import SectionHeader from '../components/SectionHeader';
import PrimaryButton from '../components/PrimaryButton';
import Screen from '../components/Screen';
import Badge from '../components/Badge';
import InfoRow from '../components/InfoRow';
import FadeInView from '../components/FadeInView';
import MiniBarChart from '../components/MiniBarChart';
import BarRow from '../components/BarRow';
import DonutChart from '../components/DonutChart';
import { useNetworkStatus } from '../hooks/useNetworkStatus';
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

type PeriodSummary = {
  start_date: string;
  end_date: string;
  total_income: number;
  total_expenses: number;
  net_profit: number;
  transaction_count: number;
  summary_by_category: Array<{
    category: string;
    income_total: number;
    expense_total: number;
    net_total: number;
  }>;
};

export default function ReportsScreen() {
  const { token } = useAuth();
  const { t } = useTranslation();
  const { isOffline } = useNetworkStatus();
  const [cadence, setCadence] = useState<Cadence | null>(null);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [summary, setSummary] = useState<PeriodSummary | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isRefreshing, setIsRefreshing] = useState(false);

  const sortedCategories = summary?.summary_by_category
    ? [...summary.summary_by_category].sort((a, b) => Math.abs(b.net_total) - Math.abs(a.net_total))
    : [];
  const categoryMax = sortedCategories.length
    ? Math.max(...sortedCategories.map((item) => Math.abs(item.net_total)))
    : 0;
  const expenseRatio = summary && summary.total_income > 0 ? summary.total_expenses / summary.total_income : 0;
  const profitMargin = summary && summary.total_income > 0 ? summary.net_profit / summary.total_income : 0;

  const fetchCadence = async () => {
    try {
      const response = await apiRequest('/analytics/reports/reporting-cadence', { token });
      if (!response.ok) return;
      setCadence(await response.json());
    } catch {
      setCadence(null);
    }
  };

  useEffect(() => {
    fetchCadence();
  }, [token]);

  const runReport = async (type: 'monthly' | 'quarterly' | 'profit_loss' | 'tax_year' | 'mortgage') => {
    setMessage('');
    setError('');
    setSummary(null);
    if (isOffline) {
      setError(t('reports.offline_error'));
      return;
    }
    setIsLoading(true);
    try {
      const now = new Date();
      const year = now.getFullYear();
      const month = now.getMonth() + 1;
      const quarter = Math.ceil(month / 3);
      const endDate = now.toISOString().slice(0, 10);
      const startDate = new Date(now.getTime() - 30 * 86400000).toISOString().slice(0, 10);
      const taxYearStart = month >= 4 ? `${year}-04-06` : `${year - 1}-04-06`;
      const taxYearEnd = month >= 4 ? `${year + 1}-04-05` : `${year}-04-05`;

      const pathMap = {
        monthly: `/analytics/reports/monthly-summary?year=${year}&month=${month}`,
        quarterly: `/analytics/reports/quarterly-summary?year=${year}&quarter=${quarter}`,
        profit_loss: `/analytics/reports/profit-loss?start_date=${startDate}&end_date=${endDate}`,
        tax_year: `/analytics/reports/tax-year-summary?tax_year=${taxYearStart}/${taxYearEnd}`,
        mortgage: '/analytics/reports/mortgage-readiness',
      };

      const response = await apiRequest(pathMap[type], { token });
      if (response.status === 402) {
        setError(t('reports.pro_required'));
        return;
      }
      if (!response.ok) throw new Error(t('reports.request_failed'));
      if (type === 'mortgage') {
        setMessage(t('reports.mortgage_message'));
        return;
      }
      const data = await response.json();
      setSummary(data);
      const messageMap = {
        monthly: t('reports.monthly_message'),
        quarterly: t('reports.quarterly_message'),
        profit_loss: t('reports.profit_loss_message'),
        tax_year: t('reports.tax_year_message'),
        mortgage: t('reports.mortgage_message'),
      };
      setMessage(messageMap[type]);
    } catch (err: any) {
      setError(err.message || t('reports.request_failed'));
    } finally {
      setIsLoading(false);
    }
  };

  const handleRefresh = async () => {
    setIsRefreshing(true);
    await fetchCadence();
    setIsRefreshing(false);
  };

  return (
    <Screen refreshing={isRefreshing} onRefresh={handleRefresh}>
      <SectionHeader title={t('reports.title')} subtitle={t('reports.subtitle')} />
      {cadence && (
        <FadeInView>
          <Card>
            <Text style={styles.cardTitle}>{t('reports.cadence_title')}</Text>
            <InfoRow label={t('reports.cadence_turnover')} value={`GBP ${cadence.turnover_last_12_months.toFixed(2)}`} />
            <InfoRow label={t('reports.cadence_threshold')} value={`GBP ${cadence.threshold.toFixed(2)}`} />
            <Text style={cadence.quarterly_required ? styles.warning : styles.ok}>
              {cadence.quarterly_required ? t('reports.cadence_quarterly_required') : t('reports.cadence_monthly_ok')}
            </Text>
          </Card>
        </FadeInView>
      )}
      <FadeInView delay={80}>
        <Card>
          <View style={styles.titleRow}>
            <Text style={styles.cardTitle}>{t('reports.monthly')}</Text>
          </View>
          <PrimaryButton title={t('reports.monthly')} onPress={() => runReport('monthly')} disabled={isLoading} haptic="medium" />
        </Card>
      </FadeInView>
      <FadeInView delay={120}>
        <Card>
          <View style={styles.titleRow}>
            <Text style={styles.cardTitle}>{t('reports.quarterly')}</Text>
            <Badge label={t('reports.pro_badge')} tone="info" />
          </View>
          <PrimaryButton title={t('reports.quarterly')} onPress={() => runReport('quarterly')} disabled={isLoading} haptic="medium" />
        </Card>
      </FadeInView>
      <FadeInView delay={160}>
        <Card>
          <View style={styles.titleRow}>
            <Text style={styles.cardTitle}>{t('reports.profit_loss')}</Text>
            <Badge label={t('reports.pro_badge')} tone="info" />
          </View>
          <PrimaryButton title={t('reports.profit_loss')} onPress={() => runReport('profit_loss')} disabled={isLoading} haptic="medium" />
        </Card>
      </FadeInView>
      <FadeInView delay={200}>
        <Card>
          <View style={styles.titleRow}>
            <Text style={styles.cardTitle}>{t('reports.tax_year')}</Text>
            <Badge label={t('reports.pro_badge')} tone="info" />
          </View>
          <PrimaryButton title={t('reports.tax_year')} onPress={() => runReport('tax_year')} disabled={isLoading} haptic="medium" />
        </Card>
      </FadeInView>
      <FadeInView delay={240}>
        <Card>
          <View style={styles.titleRow}>
            <Text style={styles.cardTitle}>{t('reports.mortgage')}</Text>
            <Badge label={t('reports.pro_badge')} tone="info" />
          </View>
          <PrimaryButton title={t('reports.mortgage')} onPress={() => runReport('mortgage')} disabled={isLoading} haptic="medium" />
        </Card>
      </FadeInView>

      {summary ? (
        <FadeInView delay={280}>
          <Card>
            <Text style={styles.cardTitle}>{t('reports.summary_title')}</Text>
            <InfoRow label={t('reports.summary_income')} value={`GBP ${summary.total_income.toFixed(2)}`} />
            <InfoRow label={t('reports.summary_expenses')} value={`GBP ${summary.total_expenses.toFixed(2)}`} />
            <InfoRow label={t('reports.summary_net')} value={`GBP ${summary.net_profit.toFixed(2)}`} />
            <InfoRow label={t('reports.summary_count')} value={`${summary.transaction_count}`} />
            <InfoRow label={t('reports.summary_period')} value={`${summary.start_date} → ${summary.end_date}`} />
          </Card>
        </FadeInView>
      ) : null}

      {sortedCategories.length ? (
        <FadeInView delay={320}>
          <Card>
            <Text style={styles.cardTitle}>{t('reports.category_breakdown')}</Text>
            <MiniBarChart
              data={sortedCategories.slice(0, 8).map((item) => item.net_total)}
              height={60}
              positiveColor={colors.success}
              negativeColor={colors.warning}
            />
            <View style={styles.categoryList}>
              {sortedCategories.slice(0, 5).map((item) => (
                <BarRow
                  key={item.category}
                  label={item.category}
                  value={item.net_total}
                  maxValue={categoryMax}
                  valueLabel={`GBP ${item.net_total.toFixed(2)}`}
                  tone={item.net_total >= 0 ? 'success' : 'warning'}
                />
              ))}
            </View>
          </Card>
        </FadeInView>
      ) : null}

      {summary ? (
        <FadeInView delay={360}>
          <Card>
            <Text style={styles.cardTitle}>{t('reports.performance_title')}</Text>
            <View style={styles.performanceRow}>
              <View style={[styles.performanceItem, styles.performanceItemSpacer]}>
                <DonutChart
                  value={profitMargin}
                  label={t('reports.profit_margin')}
                  color={colors.success}
                />
              </View>
              <View style={styles.performanceItem}>
                <DonutChart
                  value={expenseRatio}
                  label={t('reports.expense_ratio')}
                  color={colors.warning}
                />
              </View>
            </View>
          </Card>
        </FadeInView>
      ) : null}

      {message ? <Text style={styles.message}>{message}</Text> : null}
      {error ? <Text style={styles.error}>{error}</Text> : null}
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
  titleRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  message: {
    marginTop: spacing.md,
    color: colors.success,
  },
  error: {
    marginTop: spacing.md,
    color: colors.danger,
  },
  categoryList: {
    marginTop: spacing.md,
  },
  performanceRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
  },
  performanceItem: {
    flex: 1,
  },
  performanceItemSpacer: {
    marginRight: spacing.md,
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
