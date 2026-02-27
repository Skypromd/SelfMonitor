import React, { useState, useCallback } from 'react';
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  ActivityIndicator,
  Alert,
  FlatList,
  TextInput,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { colors, spacing, fontSize } from '../theme';
import { apiCall } from '../api';

const CATEGORIES = [
  'income',
  'rent',
  'utilities',
  'food',
  'transport',
  'entertainment',
  'business_expense',
  'other',
];

type Transaction = {
  id: string;
  date: string;
  description: string;
  amount: number;
  category: string;
};

export default function TransactionsScreen() {
  const [accountId, setAccountId] = useState('');
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [loading, setLoading] = useState(false);
  const [connectLoading, setConnectLoading] = useState(false);
  const [connectionStatus, setConnectionStatus] = useState<string | null>(null);

  const connectBank = useCallback(async () => {
    setConnectLoading(true);
    try {
      const res = await apiCall('/banking/connections/initiate', {
        method: 'POST',
        body: JSON.stringify({}),
      });
      if (!res.ok) throw new Error('Failed to initiate bank connection');
      const data = await res.json();
      setConnectionStatus(data.authorization_url || data.message || 'Connection initiated');
      if (data.account_id) setAccountId(data.account_id);
    } catch (err: any) {
      Alert.alert('Error', err.message);
    } finally {
      setConnectLoading(false);
    }
  }, []);

  const fetchTransactions = useCallback(async () => {
    if (!accountId) {
      Alert.alert('Error', 'Please enter or connect an account first');
      return;
    }
    setLoading(true);
    try {
      const res = await apiCall(`/transactions/accounts/${accountId}/transactions`);
      if (!res.ok) throw new Error('Failed to fetch transactions');
      const data = await res.json();
      setTransactions(Array.isArray(data) ? data : data.transactions || []);
    } catch (err: any) {
      Alert.alert('Error', err.message);
    } finally {
      setLoading(false);
    }
  }, [accountId]);

  const updateCategory = useCallback(async (txId: string, category: string) => {
    try {
      const res = await apiCall(`/transactions/transactions/${txId}`, {
        method: 'PATCH',
        body: JSON.stringify({ category }),
      });
      if (!res.ok) throw new Error('Failed to update category');
      setTransactions((prev) =>
        prev.map((t) => (t.id === txId ? { ...t, category } : t))
      );
    } catch (err: any) {
      Alert.alert('Error', err.message);
    }
  }, []);

  const renderTransaction = ({ item }: { item: Transaction }) => (
    <View style={styles.txCard}>
      <View style={styles.txHeader}>
        <Text style={styles.txDescription} numberOfLines={1}>
          {item.description}
        </Text>
        <Text style={[styles.txAmount, item.amount >= 0 ? styles.positive : styles.negative]}>
          £{Math.abs(item.amount).toFixed(2)}
        </Text>
      </View>
      <Text style={styles.txDate}>{item.date}</Text>
      <View style={styles.categoryRow}>
        <FlatList
          horizontal
          data={CATEGORIES}
          keyExtractor={(cat) => cat}
          showsHorizontalScrollIndicator={false}
          renderItem={({ item: cat }) => (
            <TouchableOpacity
              style={[
                styles.categoryChip,
                item.category === cat && styles.categoryChipActive,
              ]}
              onPress={() => updateCategory(item.id, cat)}
            >
              <Text
                style={[
                  styles.categoryText,
                  item.category === cat && styles.categoryTextActive,
                ]}
              >
                {cat}
              </Text>
            </TouchableOpacity>
          )}
        />
      </View>
    </View>
  );

  return (
    <SafeAreaView style={styles.container} edges={['top']}>
      <View style={styles.header}>
        <Text style={styles.title}>Transactions</Text>
      </View>

      <View style={styles.connectSection}>
        <TouchableOpacity
          style={styles.button}
          onPress={connectBank}
          disabled={connectLoading}
        >
          {connectLoading ? (
            <ActivityIndicator color={colors.text} />
          ) : (
            <Text style={styles.buttonText}>Connect a Bank Account</Text>
          )}
        </TouchableOpacity>
        {connectionStatus && (
          <Text style={styles.statusText}>{connectionStatus}</Text>
        )}
      </View>

      <View style={styles.fetchSection}>
        <TextInput
          style={styles.input}
          placeholder="Account ID"
          placeholderTextColor={colors.textMuted}
          value={accountId}
          onChangeText={setAccountId}
        />
        <TouchableOpacity
          style={styles.fetchButton}
          onPress={fetchTransactions}
          disabled={loading}
        >
          {loading ? (
            <ActivityIndicator color={colors.text} />
          ) : (
            <Text style={styles.buttonText}>Load</Text>
          )}
        </TouchableOpacity>
      </View>

      <FlatList
        data={transactions}
        keyExtractor={(item) => item.id}
        renderItem={renderTransaction}
        contentContainerStyle={styles.list}
        ListEmptyComponent={
          <Text style={styles.emptyText}>
            No transactions loaded. Connect a bank or enter an account ID above.
          </Text>
        }
      />
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
    paddingBottom: 0,
  },
  title: {
    fontSize: fontSize.xl,
    fontWeight: '700',
    color: colors.text,
  },
  connectSection: {
    padding: spacing.md,
  },
  fetchSection: {
    flexDirection: 'row',
    paddingHorizontal: spacing.md,
    gap: spacing.sm,
    marginBottom: spacing.sm,
  },
  input: {
    flex: 1,
    backgroundColor: colors.bgCard,
    borderRadius: 8,
    padding: spacing.md,
    color: colors.text,
    fontSize: fontSize.sm,
    borderWidth: 1,
    borderColor: colors.border,
  },
  fetchButton: {
    backgroundColor: colors.accentTeal,
    borderRadius: 8,
    paddingHorizontal: spacing.lg,
    justifyContent: 'center',
    alignItems: 'center',
  },
  button: {
    backgroundColor: colors.accentTeal,
    borderRadius: 8,
    padding: spacing.md,
    alignItems: 'center',
  },
  buttonText: {
    color: colors.text,
    fontSize: fontSize.md,
    fontWeight: '600',
  },
  statusText: {
    color: colors.accentTealLight,
    fontSize: fontSize.xs,
    marginTop: spacing.sm,
  },
  list: {
    padding: spacing.md,
    paddingTop: 0,
  },
  txCard: {
    backgroundColor: colors.bgElevated,
    borderRadius: 10,
    padding: spacing.md,
    marginBottom: spacing.sm,
    borderWidth: 1,
    borderColor: colors.border,
  },
  txHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: spacing.xs,
  },
  txDescription: {
    flex: 1,
    fontSize: fontSize.md,
    color: colors.text,
    marginRight: spacing.sm,
  },
  txAmount: {
    fontSize: fontSize.md,
    fontWeight: '600',
  },
  positive: {
    color: colors.success,
  },
  negative: {
    color: colors.error,
  },
  txDate: {
    fontSize: fontSize.xs,
    color: colors.textMuted,
    marginBottom: spacing.sm,
  },
  categoryRow: {
    flexDirection: 'row',
  },
  categoryChip: {
    backgroundColor: colors.bgCard,
    borderRadius: 16,
    paddingHorizontal: spacing.sm,
    paddingVertical: spacing.xs,
    marginRight: spacing.xs,
  },
  categoryChipActive: {
    backgroundColor: colors.accentTeal,
  },
  categoryText: {
    fontSize: fontSize.xs,
    color: colors.textMuted,
  },
  categoryTextActive: {
    color: colors.text,
  },
  emptyText: {
    color: colors.textMuted,
    fontSize: fontSize.sm,
    textAlign: 'center',
    marginTop: spacing.xl,
  },
});
