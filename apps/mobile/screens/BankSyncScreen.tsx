import React, { useState, useCallback, useRef } from 'react';
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  ActivityIndicator,
  Alert,
  FlatList,
  Animated,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { LinearGradient } from 'expo-linear-gradient';
import { colors, spacing, fontSize, borderRadius } from '../theme';
import { apiCall } from '../api';

type BankConnection = {
  id: string;
  bank_name: string;
  last_synced: string | null;
  account_type?: string;
  last_four?: string;
};

const MOCK_BANKS: BankConnection[] = [
  { id: '1', bank_name: 'Barclays Business', last_synced: '2026-03-31T09:15:00Z', account_type: 'Current Account', last_four: '4532' },
  { id: '2', bank_name: 'Starling Bank', last_synced: '2026-03-30T14:22:00Z', account_type: 'Business Account', last_four: '7891' },
  { id: '3', bank_name: 'Monzo Business', last_synced: null, account_type: 'Current Account', last_four: '2045' },
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

function AnimatedPressable({
  onPress,
  style,
  children,
  disabled,
}: {
  onPress: () => void;
  style?: any;
  children: React.ReactNode;
  disabled?: boolean;
}) {
  const scale = useRef(new Animated.Value(1)).current;

  return (
    <Animated.View style={{ transform: [{ scale }] }}>
      <TouchableOpacity
        onPress={onPress}
        onPressIn={() =>
          Animated.spring(scale, { toValue: 0.96, useNativeDriver: true }).start()
        }
        onPressOut={() =>
          Animated.spring(scale, { toValue: 1, friction: 3, useNativeDriver: true }).start()
        }
        activeOpacity={0.9}
        disabled={disabled}
        style={style}
      >
        {children}
      </TouchableOpacity>
    </Animated.View>
  );
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
      <View style={styles.bankHeader}>
        <Text style={styles.bankEmoji}>🏦</Text>
        <View style={styles.bankInfo}>
          <Text style={styles.bankName}>{item.bank_name}</Text>
          <Text style={styles.accountType}>{item.account_type || 'Account'}</Text>
          {item.last_four && (
            <Text style={styles.lastFour}>••••{item.last_four}</Text>
          )}
        </View>
      </View>

      <View style={styles.bankFooter}>
        <Text style={styles.lastSynced}>{formatLastSynced(item.last_synced)}</Text>
        <AnimatedPressable
          onPress={() => syncBank(item.id)}
          disabled={limitReached || syncingId === item.id}
        >
          <LinearGradient
            colors={
              limitReached
                ? [colors.bgCard, colors.bgCard]
                : [colors.gradientStart, colors.gradientEnd]
            }
            start={{ x: 0, y: 0 }}
            end={{ x: 1, y: 0 }}
            style={styles.syncButton}
          >
            {syncingId === item.id ? (
              <ActivityIndicator color={colors.text} size="small" />
            ) : (
              <Text
                style={[
                  styles.syncButtonText,
                  limitReached && { color: colors.textMuted },
                ]}
              >
                🔄 Sync Now
              </Text>
            )}
          </LinearGradient>
        </AnimatedPressable>
      </View>
    </View>
  );

  return (
    <SafeAreaView style={styles.container} edges={['top']}>
      <View style={styles.header}>
        <Text style={styles.title}>Bank Accounts</Text>
        <Text style={styles.subtitle}>
          {formatLastSynced(banks.find((b) => b.last_synced)?.last_synced ?? null)}
        </Text>
      </View>

      <View style={styles.syncCounter}>
        <View style={styles.syncCounterInner}>
          <Text style={styles.syncCounterText}>
            {syncsUsed} of {syncLimit} sync{syncLimit !== 1 ? 's' : ''} used today
          </Text>
          {limitReached && (
            <Text style={styles.nextSyncText}>Resets tomorrow</Text>
          )}
        </View>
        <View style={styles.syncDots}>
          {Array.from({ length: syncLimit }).map((_, i) => (
            <View
              key={i}
              style={[
                styles.syncDot,
                i < syncsUsed
                  ? { backgroundColor: colors.accentTeal }
                  : { backgroundColor: colors.bgCard },
              ]}
            />
          ))}
        </View>
      </View>

      {loading ? (
        <ActivityIndicator size="large" color={colors.accentTeal} style={styles.loader} />
      ) : (
        <FlatList
          data={banks}
          keyExtractor={(item) => item.id}
          renderItem={renderBank}
          contentContainerStyle={styles.list}
          showsVerticalScrollIndicator={false}
          ListFooterComponent={
            <>
              <AnimatedPressable onPress={connectNewBank} disabled={connectLoading}>
                <View style={styles.connectCard}>
                  {connectLoading ? (
                    <ActivityIndicator color={colors.accentTeal} />
                  ) : (
                    <>
                      <Text style={styles.connectIcon}>+</Text>
                      <Text style={styles.connectText}>Connect New Bank</Text>
                    </>
                  )}
                </View>
              </AnimatedPressable>

              {limitReached && (
                <View style={styles.upgradeCard}>
                  <Text style={styles.upgradeEmoji}>💡</Text>
                  <Text style={styles.upgradeTitle}>Need more syncs?</Text>
                  <Text style={styles.upgradeText}>
                    Upgrade to Growth (£12/mo) for 2 syncs per day
                  </Text>
                  <AnimatedPressable onPress={() => {}}>
                    <View style={styles.upgradeButton}>
                      <Text style={styles.upgradeButtonText}>Upgrade →</Text>
                    </View>
                  </AnimatedPressable>
                </View>
              )}
            </>
          }
          ListEmptyComponent={
            <Text style={styles.emptyText}>No banks connected yet.</Text>
          }
        />
      )}
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.bg,
  },
  header: {
    paddingHorizontal: spacing.lg,
    paddingTop: spacing.lg,
    paddingBottom: spacing.sm,
  },
  title: {
    fontSize: fontSize.xl,
    fontWeight: '800',
    color: colors.text,
  },
  subtitle: {
    fontSize: fontSize.sm,
    color: colors.textMuted,
    marginTop: spacing.xs,
  },
  syncCounter: {
    marginHorizontal: spacing.lg,
    backgroundColor: colors.bgCard,
    borderRadius: borderRadius.lg,
    padding: spacing.md,
    borderWidth: 1,
    borderColor: colors.border,
    marginBottom: spacing.md,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  syncCounterInner: {
    flex: 1,
  },
  syncCounterText: {
    fontSize: fontSize.sm,
    color: colors.text,
    fontWeight: '600',
  },
  nextSyncText: {
    fontSize: fontSize.xs,
    color: colors.warning,
    marginTop: 2,
  },
  syncDots: {
    flexDirection: 'row',
    gap: spacing.xs,
  },
  syncDot: {
    width: 10,
    height: 10,
    borderRadius: 5,
  },
  list: {
    paddingHorizontal: spacing.lg,
    paddingBottom: spacing.xxl,
  },
  bankCard: {
    backgroundColor: colors.bgCard,
    borderRadius: borderRadius.xl,
    padding: spacing.lg,
    marginBottom: spacing.md,
    borderWidth: 1,
    borderColor: colors.border,
  },
  bankHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.md,
    marginBottom: spacing.md,
  },
  bankEmoji: {
    fontSize: 28,
  },
  bankInfo: {
    flex: 1,
  },
  bankName: {
    fontSize: fontSize.lg,
    fontWeight: '700',
    color: colors.text,
  },
  accountType: {
    fontSize: fontSize.sm,
    color: colors.textSecondary,
    marginTop: 2,
  },
  lastFour: {
    fontSize: fontSize.xs,
    color: colors.textMuted,
    marginTop: 2,
  },
  bankFooter: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  lastSynced: {
    fontSize: fontSize.xs,
    color: colors.textMuted,
  },
  syncButton: {
    borderRadius: borderRadius.md,
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm,
  },
  syncButtonText: {
    color: colors.text,
    fontSize: fontSize.sm,
    fontWeight: '700',
  },
  connectCard: {
    borderRadius: borderRadius.xl,
    padding: spacing.lg,
    borderWidth: 2,
    borderColor: colors.borderLight,
    borderStyle: 'dashed',
    alignItems: 'center',
    justifyContent: 'center',
    flexDirection: 'row',
    gap: spacing.sm,
    marginBottom: spacing.md,
  },
  connectIcon: {
    fontSize: fontSize.xl,
    color: colors.accentTeal,
    fontWeight: '300',
  },
  connectText: {
    fontSize: fontSize.md,
    color: colors.accentTeal,
    fontWeight: '600',
  },
  upgradeCard: {
    backgroundColor: colors.warningBg,
    borderRadius: borderRadius.xl,
    padding: spacing.lg,
    borderWidth: 1,
    borderColor: colors.warning,
  },
  upgradeEmoji: {
    fontSize: 24,
    marginBottom: spacing.sm,
  },
  upgradeTitle: {
    fontSize: fontSize.lg,
    fontWeight: '700',
    color: colors.warning,
    marginBottom: spacing.xs,
  },
  upgradeText: {
    fontSize: fontSize.sm,
    color: colors.textSecondary,
    marginBottom: spacing.md,
  },
  upgradeButton: {
    backgroundColor: colors.warning,
    borderRadius: borderRadius.md,
    paddingVertical: spacing.sm,
    paddingHorizontal: spacing.lg,
    alignSelf: 'flex-start',
  },
  upgradeButtonText: {
    color: colors.textInverse,
    fontSize: fontSize.sm,
    fontWeight: '700',
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
