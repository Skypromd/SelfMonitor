import React, { useEffect, useMemo, useState } from 'react';
import { StyleSheet, Text, View } from 'react-native';

import Screen from '../components/Screen';
import SectionHeader from '../components/SectionHeader';
import Card from '../components/Card';
import Badge from '../components/Badge';
import PrimaryButton from '../components/PrimaryButton';
import ListItem from '../components/ListItem';
import SyncAnimation from '../components/SyncAnimation';
import InfoRow from '../components/InfoRow';
import { useTranslation } from '../hooks/useTranslation';
import { useNetworkStatus } from '../hooks/useNetworkStatus';
import { flushQueue, getQueueCount } from '../services/offlineQueue';
import { getSyncLogEntries, SyncLogEntry } from '../services/syncLog';
import { useAuth } from '../context/AuthContext';
import { colors, spacing } from '../theme';

export default function SyncCenterScreen() {
  const { t } = useTranslation();
  const { isOffline } = useNetworkStatus();
  const { token } = useAuth();
  const [queuedCount, setQueuedCount] = useState(0);
  const [syncing, setSyncing] = useState(false);
  const [logEntries, setLogEntries] = useState<SyncLogEntry[]>([]);
  const [isRefreshing, setIsRefreshing] = useState(false);

  const loadData = async () => {
    const [count, entries] = await Promise.all([
      getQueueCount(),
      getSyncLogEntries(12),
    ]);
    setQueuedCount(count);
    setLogEntries(entries);
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleRefresh = async () => {
    setIsRefreshing(true);
    await loadData();
    setIsRefreshing(false);
  };

  const handleSyncNow = async () => {
    if (isOffline || syncing) return;
    setSyncing(true);
    const result = await flushQueue(token);
    setQueuedCount(result.remaining);
    await loadData();
    setSyncing(false);
  };

  const lastSyncedAt = useMemo(() => {
    const latest = logEntries.find((entry) => entry.status === 'synced');
    return latest ? new Date(latest.createdAt).toLocaleString() : t('common.not_available');
  }, [logEntries, t]);

  return (
    <Screen refreshing={isRefreshing} onRefresh={handleRefresh}>
      <SectionHeader title={t('sync.center_title')} subtitle={t('sync.center_subtitle')} />
      <Card>
        <View style={styles.statusRow}>
          <Badge label={isOffline ? t('common.offline_label') : t('common.online_label')} tone={isOffline ? 'warning' : 'success'} />
          {syncing || queuedCount ? <SyncAnimation size={52} /> : null}
        </View>
        <InfoRow label={t('common.last_sync')} value={lastSyncedAt} />
        <Text style={styles.pendingText}>{queuedCount} {t('dashboard.sync_pending')}</Text>
        <PrimaryButton
          title={syncing ? t('common.syncing') : t('common.sync_now')}
          onPress={handleSyncNow}
          disabled={syncing || isOffline || queuedCount === 0}
          variant="secondary"
          haptic="light"
          style={styles.syncButton}
        />
      </Card>

      <SectionHeader title={t('sync.activity_title')} subtitle={t('sync.activity_subtitle')} />
      <Card>
        {logEntries.length ? (
          logEntries.map((entry) => (
            <ListItem
              key={entry.id}
              title={t(`sync.action_${entry.action}`)}
              subtitle={`${t(`sync.status_${entry.status}`)} · ${new Date(entry.createdAt).toLocaleString()}`}
              icon={entry.status === 'synced' ? 'checkmark-circle-outline' : entry.status === 'failed' ? 'alert-circle-outline' : 'time-outline'}
            />
          ))
        ) : (
          <Text style={styles.emptyText}>{t('sync.empty')}</Text>
        )}
      </Card>
    </Screen>
  );
}

const styles = StyleSheet.create({
  statusRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  pendingText: {
    marginTop: spacing.xs,
    color: colors.textSecondary,
    fontSize: 12,
    fontWeight: '600',
  },
  syncButton: {
    marginTop: spacing.md,
  },
  emptyText: {
    color: colors.textSecondary,
    fontSize: 12,
    paddingVertical: spacing.md,
  },
});
