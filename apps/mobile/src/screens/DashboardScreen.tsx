import React, { useEffect, useState } from 'react';
import { StyleSheet, Text, View } from 'react-native';
import { useNavigation } from '@react-navigation/native';

import SectionHeader from '../components/SectionHeader';
import Card from '../components/Card';
import PrimaryButton from '../components/PrimaryButton';
import GradientCard from '../components/GradientCard';
import StatCard from '../components/StatCard';
import Screen from '../components/Screen';
import ProgressBar from '../components/ProgressBar';
import Badge from '../components/Badge';
import FadeInView from '../components/FadeInView';
import InfoRow from '../components/InfoRow';
import PulseDot from '../components/PulseDot';
import InteractiveLineChart from '../components/InteractiveLineChart';
import GlassCard from '../components/GlassCard';
import SyncAnimation from '../components/SyncAnimation';
import ListItem from '../components/ListItem';
import Chip from '../components/Chip';
import { useNetworkStatus } from '../hooks/useNetworkStatus';
import { apiRequest } from '../services/api';
import { flushQueue, getQueueCount } from '../services/offlineQueue';
import { getSyncLogEntries, SyncLogEntry } from '../services/syncLog';
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
  const { isOffline } = useNetworkStatus();
  const [readinessScore, setReadinessScore] = useState(0);
  const [cashFlow, setCashFlow] = useState<number | null>(null);
  const [forecastPoints, setForecastPoints] = useState<number[]>([]);
  const [lastSync, setLastSync] = useState<string | null>(null);
  const [queuedCount, setQueuedCount] = useState(0);
  const [syncing, setSyncing] = useState(false);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [syncLog, setSyncLog] = useState<SyncLogEntry[]>([]);
  const [rangeDays, setRangeDays] = useState(14);
  const [readinessMeta, setReadinessMeta] = useState({
    missingCategories: 0,
    missingBusinessUse: 0,
    total: 0,
  });

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
      setLastSync(new Date().toISOString());
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
        setForecastPoints(data.forecast.map((item: { balance: number }) => item.balance));
        setLastSync(new Date().toISOString());
      }
    } catch {
      setCashFlow(null);
    }
  };

  const loadQueueCount = async () => {
    const count = await getQueueCount();
    setQueuedCount(count);
  };

  const loadSyncLog = async () => {
    const entries = await getSyncLogEntries(4);
    setSyncLog(entries);
  };

  useEffect(() => {
    loadReadiness();
    loadCashFlow();
    loadQueueCount();
    loadSyncLog();
  }, [token]);

  const handleRefresh = async () => {
    setIsRefreshing(true);
    await Promise.all([loadReadiness(), loadCashFlow(), loadQueueCount(), loadSyncLog()]);
    setIsRefreshing(false);
  };

  const handleSync = async () => {
    if (isOffline || syncing) return;
    setSyncing(true);
    const result = await flushQueue(token);
    setQueuedCount(result.remaining);
    setLastSync(new Date().toISOString());
    await loadSyncLog();
    setSyncing(false);
  };

  const readinessLabel = readinessScore >= 80
    ? t('dashboard.readiness_good')
    : readinessScore >= 50
      ? t('dashboard.readiness_medium')
      : t('dashboard.readiness_low');
  const lastSyncLabel = lastSync ? new Date(lastSync).toLocaleString() : t('common.not_available');
  const now = new Date();
  const deadlineYear = now.getMonth() === 0 && now.getDate() <= 31 ? now.getFullYear() : now.getFullYear() + 1;
  const nextDeadline = new Date(deadlineYear, 0, 31);
  const deadlineLabel = nextDeadline.toLocaleDateString();

  return (
    <Screen refreshing={isRefreshing} onRefresh={handleRefresh}>
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
            <PrimaryButton title={t('dashboard.add_expense')} onPress={() => navigation.navigate('Transactions' as never)} variant="secondary" haptic="light" />
          </View>
          <View style={styles.quickActionItem}>
            <PrimaryButton title={t('dashboard.scan_receipt')} onPress={() => navigation.navigate('Documents' as never)} variant="secondary" haptic="light" />
          </View>
          <View style={styles.quickActionItem}>
            <PrimaryButton title={t('dashboard.generate_report')} onPress={() => navigation.navigate('Reports' as never)} variant="secondary" haptic="light" />
          </View>
        </View>
      </FadeInView>

      <SectionHeader title={t('dashboard.deadline_title')} subtitle={t('dashboard.deadline_subtitle')} />
      <FadeInView delay={120}>
        <GlassCard>
          <Text style={styles.deadlineDate}>{deadlineLabel}</Text>
          <Text style={styles.deadlineHint}>{t('dashboard.deadline_hint')}</Text>
          <PrimaryButton
            title={t('dashboard.deadline_action')}
            onPress={() => navigation.navigate('Reports' as never)}
            variant="secondary"
            haptic="light"
            style={styles.deadlineButton}
          />
        </GlassCard>
      </FadeInView>

      <SectionHeader title={t('dashboard.sync_title')} subtitle={t('dashboard.sync_subtitle')} />
      <FadeInView delay={140}>
        <Card>
          <View style={styles.syncRow}>
            <Badge label={isOffline ? t('common.offline_label') : t('common.online_label')} tone={isOffline ? 'warning' : 'success'} />
            {syncing || queuedCount ? (
              <View style={styles.syncIndicator}>
                <SyncAnimation size={48} />
              </View>
            ) : null}
          </View>
          <InfoRow label={t('common.last_sync')} value={lastSyncLabel} />
          <Text style={styles.syncCount}>{queuedCount} {t('dashboard.sync_pending')}</Text>
          <PrimaryButton
            title={syncing ? t('common.syncing') : t('common.sync_now')}
            onPress={handleSync}
            disabled={syncing || isOffline || queuedCount === 0}
            variant="secondary"
            haptic="light"
            style={styles.syncButton}
          />
          {syncLog.length ? (
            <View style={styles.syncLog}>
              {syncLog.map((entry) => (
                <ListItem
                  key={entry.id}
                  title={t(`sync.action_${entry.action}`)}
                  subtitle={`${t(`sync.status_${entry.status}`)} · ${new Date(entry.createdAt).toLocaleTimeString()}`}
                  icon={entry.status === 'synced' ? 'checkmark-circle-outline' : entry.status === 'failed' ? 'alert-circle-outline' : 'time-outline'}
                />
              ))}
            </View>
          ) : (
            <Text style={styles.syncEmpty}>{t('sync.empty')}</Text>
          )}
        </Card>
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
        <Card>
          <Text style={styles.cardTitle}>{t('dashboard.cashflow_trend')}</Text>
          {forecastPoints.length ? (
            <InteractiveLineChart
              data={forecastPoints.slice(-rangeDays)}
              height={120}
              label={t('dashboard.cashflow_label')}
              valueFormatter={(value) => `GBP ${value.toFixed(2)}`}
              enableZoom
            />
          ) : (
            <Text style={styles.emptyText}>{t('dashboard.cashflow_empty')}</Text>
          )}
          <View style={styles.rangeRow}>
            <View style={styles.rangeChip}>
              <Chip label={t('dashboard.range_7d')} selected={rangeDays === 7} onPress={() => setRangeDays(7)} />
            </View>
            <View style={styles.rangeChip}>
              <Chip label={t('dashboard.range_14d')} selected={rangeDays === 14} onPress={() => setRangeDays(14)} />
            </View>
            <View style={styles.rangeChip}>
              <Chip label={t('dashboard.range_30d')} selected={rangeDays === 30} onPress={() => setRangeDays(30)} />
            </View>
          </View>
          <InfoRow label={t('common.last_sync')} value={lastSyncLabel} />
        </Card>
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
  cardTitle: {
    fontSize: 16,
    fontWeight: '700',
    color: colors.textPrimary,
    marginBottom: spacing.sm,
  },
  emptyText: {
    color: colors.textSecondary,
    marginBottom: spacing.sm,
  },
  rangeRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    marginTop: spacing.sm,
    marginBottom: spacing.sm,
  },
  rangeChip: {
    marginRight: spacing.sm,
    marginBottom: spacing.sm,
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
  deadlineDate: {
    fontSize: 24,
    fontWeight: '700',
    color: colors.textPrimary,
  },
  deadlineHint: {
    marginTop: spacing.xs,
    color: colors.textSecondary,
  },
  deadlineButton: {
    marginTop: spacing.lg,
  },
  syncRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: spacing.sm,
  },
  syncIndicator: {
    alignItems: 'center',
    justifyContent: 'center',
  },
  syncCount: {
    color: colors.textSecondary,
    fontSize: 12,
    fontWeight: '600',
    marginTop: spacing.xs,
  },
  syncButton: {
    marginTop: spacing.md,
  },
  syncLog: {
    marginTop: spacing.md,
  },
  syncEmpty: {
    marginTop: spacing.md,
    color: colors.textSecondary,
    fontSize: 12,
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
