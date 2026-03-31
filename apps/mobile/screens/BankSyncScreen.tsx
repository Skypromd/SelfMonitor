import React, { useState, useCallback } from 'react';
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  ActivityIndicator,
  Alert,
  FlatList,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { colors, spacing, fontSize } from '../theme';
import { apiCall } from '../api';

type BankConnection = {
  id: string;
  bank_name: string;
  last_synced: string | null;
};

const MOCK_BANKS: BankConnection[] = [
  { id: '1', bank_name: 'Barclays Business', last_synced: '2026-03-31T09:15:00Z' },
  { id: '2', bank_name: 'Starling Bank', last_synced: '2026-03-30T14:22:00Z' },
  { id: '3', bank_name: 'Monzo Business', last_synced: null },
];

function formatLastSynced(iso: string | null): string {
  if (!iso) return 'Never synced';
  const d = new Date(iso);
  const now = new Date();
  const diffMs = now.getTime() - d.getTime();
  const diffH = Math.floor(diffMs / 3_600_000);
  if (diffH < 1) return 'Synced just now';
  if (diffH < 24) return `Synced ${diffH}h ago`;
  const diffD = Math.floor(diffH / 24);
  return `Synced ${diffD}d ago`;
}

export default function BankSyncScreen() {
  const [banks, setBanks] = useState<BankConnection[]>(MOCK_BANKS);
  const [syncsUsed, setSyncsUsed] = useState(0);
  const [syncLimit] = useState(1);
  const [syncingId, setSyncingId] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [connectLoading, setConnectLoading] = useState(false);

  const limitReached = syncsUsed >= syncLimit;

  const fetchConnections = useCallback(async () => {
    setLoading(true);
    try {
      const res = await apiCall('/banking/connections');
      if (!res.ok) throw new Error('Failed to fetch connections');
      const data = await res.json();
      if (Array.isArray(data)) setBanks(data);
    } catch {
      // keep mock data on failure
    } finally {
      setLoading(false);
    }
  }, []);

  const syncBank = useCallback(
    async (bankId: string) => {
      if (limitReached) return;
      setSyncingId(bankId);
      try {
        const res = await apiCall(`/banking/connections/${bankId}/sync`, {
          method: 'POST',
        });
        if (!res.ok) throw new Error('Sync failed');
        setSyncsUsed((prev) => prev + 1);
        setBanks((prev) =>
          prev.map((b) =>
            b.id === bankId ? { ...b, last_synced: new Date().toISOString() } : b
          )
        );
        Alert.alert('Success', 'Bank synced successfully');
      } catch (err: any) {
        Alert.alert('Error', err.message);
      } finally {
        setSyncingId(null);
      }
    },
    [limitReached]
  );

  const connectNewBank = useCallback(async () => {
    setConnectLoading(true);
    try {
      const res = await apiCall('/banking/connections/initiate', {
        method: 'POST',
        body: JSON.stringify({}),
      });
      if (!res.ok) throw new Error('Failed to initiate connection');
      const data = await res.json();
      Alert.alert('Bank Connection', data.authorization_url || 'Connection initiated');
      fetchConnections();
    } catch (err: any) {
      Alert.alert('Error', err.message);
    } finally {
      setConnectLoading(false);
    }
  }, [fetchConnections]);

  const renderBank = ({ item }: { item: BankConnection }) => (
    <View style={styles.bankCard}>
      <View style={styles.bankInfo}>
        <Text style={styles.bankName}>{item.bank_name}</Text>
        <Text style={styles.lastSynced}>{formatLastSynced(item.last_synced)}</Text>
      </View>
      <TouchableOpacity
        style={[styles.syncButton, limitReached && styles.syncButtonDisabled]}
        onPress={() => syncBank(item.id)}
        disabled={limitReached || syncingId === item.id}
      >
        {syncingId === item.id ? (
          <ActivityIndicator color={colors.text} size="small" />
        ) : (
          <Text style={styles.syncButtonText}>🔄 Sync</Text>
        )}
      </TouchableOpacity>
    </View>
  );

  return (
    <SafeAreaView style={styles.container} edges={['top']}>
      <View style={styles.header}>
        <Text style={styles.title}>Bank Sync</Text>
        <Text style={styles.subtitle}>Manage your connected bank accounts</Text>
      </View>

      <View style={styles.syncCounter}>
        <Text style={styles.syncCounterText}>
          {syncsUsed} of {syncLimit} sync{syncLimit !== 1 ? 's' : ''} used today
        </Text>
        {limitReached && (
          <Text style={styles.nextSyncText}>Next sync: tomorrow</Text>
        )}
      </View>

      {limitReached && (
        <TouchableOpacity style={styles.upgradeCard}>
          <Text style={styles.upgradeTitle}>Need more syncs?</Text>
          <Text style={styles.upgradeText}>
            Upgrade to Pro for unlimited daily syncs
          </Text>
        </TouchableOpacity>
      )}

      {loading ? (
        <ActivityIndicator size="large" color={colors.accentTeal} style={styles.loader} />
      ) : (
        <FlatList
          data={banks}
          keyExtractor={(item) => item.id}
          renderItem={renderBank}
          contentContainerStyle={styles.list}
          ListEmptyComponent={
            <Text style={styles.emptyText}>No banks connected yet.</Text>
          }
        />
      )}

      <View style={styles.footer}>
        <TouchableOpacity
          style={styles.connectButton}
          onPress={connectNewBank}
          disabled={connectLoading}
        >
          {connectLoading ? (
            <ActivityIndicator color={colors.text} />
          ) : (
            <Text style={styles.connectButtonText}>Connect New Bank</Text>
          )}
        </TouchableOpacity>
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.bg,
  },
  header: {
    padding: spacing.md,
    paddingBottom: spacing.sm,
  },
  title: {
    fontSize: fontSize.xl,
    fontWeight: '700',
    color: colors.text,
  },
  subtitle: {
    fontSize: fontSize.sm,
    color: colors.textMuted,
    marginTop: spacing.xs,
  },
  syncCounter: {
    marginHorizontal: spacing.md,
    backgroundColor: colors.bgElevated,
    borderRadius: 10,
    padding: spacing.md,
    borderWidth: 1,
    borderColor: colors.border,
    marginBottom: spacing.md,
  },
  syncCounterText: {
    fontSize: fontSize.sm,
    color: colors.text,
    fontWeight: '600',
  },
  nextSyncText: {
    fontSize: fontSize.xs,
    color: colors.accentGold,
    marginTop: spacing.xs,
  },
  upgradeCard: {
    marginHorizontal: spacing.md,
    backgroundColor: 'rgba(217,119,6,0.1)',
    borderRadius: 10,
    padding: spacing.md,
    borderWidth: 1,
    borderColor: colors.accentGold,
    marginBottom: spacing.md,
  },
  upgradeTitle: {
    fontSize: fontSize.md,
    fontWeight: '600',
    color: colors.accentGoldLight,
  },
  upgradeText: {
    fontSize: fontSize.sm,
    color: colors.textMuted,
    marginTop: spacing.xs,
  },
  list: {
    padding: spacing.md,
    paddingTop: 0,
  },
  bankCard: {
    backgroundColor: colors.bgElevated,
    borderRadius: 12,
    padding: spacing.lg,
    marginBottom: spacing.sm,
    borderWidth: 1,
    borderColor: colors.border,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  bankInfo: {
    flex: 1,
    marginRight: spacing.md,
  },
  bankName: {
    fontSize: fontSize.md,
    fontWeight: '600',
    color: colors.text,
  },
  lastSynced: {
    fontSize: fontSize.xs,
    color: colors.textMuted,
    marginTop: spacing.xs,
  },
  syncButton: {
    backgroundColor: colors.accentTeal,
    borderRadius: 8,
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm,
  },
  syncButtonDisabled: {
    backgroundColor: colors.bgCard,
  },
  syncButtonText: {
    color: colors.text,
    fontSize: fontSize.sm,
    fontWeight: '600',
  },
  footer: {
    padding: spacing.md,
  },
  connectButton: {
    backgroundColor: colors.accentTeal,
    borderRadius: 8,
    padding: spacing.md,
    alignItems: 'center',
  },
  connectButtonText: {
    color: colors.text,
    fontSize: fontSize.md,
    fontWeight: '600',
  },
  loader: {
    marginTop: spacing.xl,
  },
  emptyText: {
    color: colors.textMuted,
    fontSize: fontSize.sm,
    textAlign: 'center',
    marginTop: spacing.xl,
  },
});
