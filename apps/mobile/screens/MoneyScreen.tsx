import React, { useState, useCallback, useRef } from 'react';
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  ActivityIndicator,
  Alert,
  FlatList,
  ScrollView,
  Animated,
  TextInput,
  Modal,
  KeyboardAvoidingView,
  Platform,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { LinearGradient } from 'expo-linear-gradient';
import { colors, spacing, fontSize, borderRadius } from '../theme';
import { apiCall } from '../api';

type SegmentTab = 'overview' | 'transactions' | 'invoices';

type Transaction = {
  id: string;
  description: string;
  amount: number;
  date: string;
  category?: string;
};

type BankConnection = {
  id: string;
  bank_name: string;
  last_synced: string | null;
  last_four?: string;
};

type InvoiceStatus = 'draft' | 'sent' | 'paid' | 'overdue';

type Invoice = {
  id: string;
  client_name: string;
  client_email: string;
  amount: number;
  due_date: string;
  description: string;
  status: InvoiceStatus;
};

const MOCK_TRANSACTIONS: Transaction[] = [
  { id: '1', description: 'Shell Petrol', amount: -50.0, date: 'Today', category: 'Transport' },
  { id: '2', description: 'Client X Payment', amount: 1500.0, date: 'Yesterday', category: 'Income' },
  { id: '3', description: 'Amazon', amount: -12.99, date: '2d ago', category: 'Supplies' },
  { id: '4', description: 'Freelance Invoice', amount: 2200.0, date: '3d ago', category: 'Income' },
  { id: '5', description: 'Office Supplies', amount: -34.5, date: '4d ago', category: 'Supplies' },
  { id: '6', description: 'Uber Eats', amount: -18.5, date: '5d ago', category: 'Food' },
  { id: '7', description: 'Project Alpha', amount: 3500.0, date: '6d ago', category: 'Income' },
];

const MOCK_BANKS: BankConnection[] = [
  { id: '1', bank_name: 'Barclays', last_synced: '2026-04-09T06:15:00Z', last_four: '4532' },
];

const MOCK_INVOICES: Invoice[] = [
  { id: '1', client_name: 'Acme Ltd', client_email: 'billing@acme.com', amount: 1500, due_date: '2026-04-15', description: 'Web development', status: 'sent' },
  { id: '2', client_name: 'TechCo', client_email: 'pay@techco.io', amount: 800, due_date: '2026-03-20', description: 'Consulting', status: 'overdue' },
  { id: '3', client_name: 'StartupXYZ', client_email: 'finance@xyz.com', amount: 100, due_date: '2026-05-01', description: 'Logo design', status: 'draft' },
];

const STATUS_CONFIG: Record<InvoiceStatus, { bg: string; text: string; dot: string }> = {
  draft: { bg: colors.bgElevated, text: colors.textMuted, dot: colors.textMuted },
  sent: { bg: colors.infoBg, text: colors.info, dot: colors.info },
  paid: { bg: colors.incomeBg, text: colors.income, dot: colors.income },
  overdue: { bg: colors.expenseBg, text: colors.expense, dot: colors.expense },
};

const TABS: Array<{ key: SegmentTab; label: string }> = [
  { key: 'overview', label: 'Overview' },
  { key: 'transactions', label: 'Transactions' },
  { key: 'invoices', label: 'Invoices' },
];

function AnimatedPressable({
  onPress,
  style,
  children,
  disabled,
}: {
  onPress: () => void;
  style?: object;
  children: React.ReactNode;
  disabled?: boolean;
}) {
  const scale = useRef(new Animated.Value(1)).current;
  return (
    <Animated.View style={[{ transform: [{ scale }] }, style]}>
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
      >
        {children}
      </TouchableOpacity>
    </Animated.View>
  );
}

function formatLastSynced(iso: string | null): string {
  if (!iso) return 'Never synced';
  const d = new Date(iso);
  const now = new Date();
  const diffH = Math.floor((now.getTime() - d.getTime()) / 3_600_000);
  if (diffH < 1) return 'just now';
  if (diffH < 24) return `${diffH}h ago`;
  return `${Math.floor(diffH / 24)}d ago`;
}

export default function MoneyScreen() {
  const [activeTab, setActiveTab] = useState<SegmentTab>('overview');
  const [banks] = useState<BankConnection[]>(MOCK_BANKS);
  const [syncsUsed, setSyncsUsed] = useState(0);
  const [syncingId, setSyncingId] = useState<string | null>(null);
  const [transactions] = useState<Transaction[]>(MOCK_TRANSACTIONS);
  const [invoices, setInvoices] = useState<Invoice[]>(MOCK_INVOICES);
  const [showCreate, setShowCreate] = useState(false);
  const [creating, setCreating] = useState(false);
  const [clientName, setClientName] = useState('');
  const [clientEmail, setClientEmail] = useState('');
  const [amount, setAmount] = useState('');
  const [dueDate, setDueDate] = useState('');
  const [description, setDescription] = useState('');

  const totalIncome = 8200;
  const totalExpenses = 3100;
  const monthlyIncome = 4200;
  const monthlyExpenses = 1850;
  const monthlyProfit = monthlyIncome - monthlyExpenses;

  const pendingInvoices = invoices.filter(
    (i) => i.status === 'sent' || i.status === 'overdue'
  );
  const overdueInvoices = invoices.filter((i) => i.status === 'overdue');
  const pendingTotal = pendingInvoices.reduce((s, i) => s + i.amount, 0);
  const overdueTotal = overdueInvoices.reduce((s, i) => s + i.amount, 0);

  const syncBank = useCallback(
    async (bankId: string) => {
      if (syncsUsed >= 1) return;
      setSyncingId(bankId);
      try {
        const res = await apiCall(`/banking/connections/${bankId}/sync`, { method: 'POST' });
        if (!res.ok) throw new Error('Sync failed');
        setSyncsUsed((prev) => prev + 1);
        Alert.alert('Success', 'Bank synced successfully');
      } catch (err: unknown) {
        const msg = err instanceof Error ? err.message : 'Sync failed';
        Alert.alert('Error', msg);
      } finally {
        setSyncingId(null);
      }
    },
    [syncsUsed]
  );

  const resetForm = () => {
    setClientName('');
    setClientEmail('');
    setAmount('');
    setDueDate('');
    setDescription('');
  };

  const createInvoice = useCallback(async () => {
    if (!clientName || !amount) {
      Alert.alert('Error', 'Client name and amount are required');
      return;
    }
    setCreating(true);
    try {
      const payload = {
        client_name: clientName,
        client_email: clientEmail,
        amount: parseFloat(amount),
        due_date:
          dueDate ||
          new Date(Date.now() + 30 * 86_400_000).toISOString().split('T')[0],
        description,
        status: 'draft' as InvoiceStatus,
      };
      const res = await apiCall('/invoices', {
        method: 'POST',
        body: JSON.stringify(payload),
      });
      let newInvoice: Invoice;
      if (res.ok) {
        newInvoice = await res.json();
      } else {
        newInvoice = { id: String(Date.now()), ...payload };
      }
      setInvoices((prev) => [newInvoice, ...prev]);
      resetForm();
      setShowCreate(false);
      Alert.alert('Created', 'Invoice created as draft');
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed';
      Alert.alert('Error', msg);
    } finally {
      setCreating(false);
    }
  }, [clientName, clientEmail, amount, dueDate, description]);

  const renderOverview = () => (
    <ScrollView
      contentContainerStyle={styles.tabContent}
      showsVerticalScrollIndicator={false}
    >
      <View style={styles.summaryRow}>
        <View style={styles.summaryCard}>
          <Text style={styles.summaryIcon}>↗</Text>
          <Text style={styles.incomeAmount}>£{totalIncome.toLocaleString()}</Text>
          <Text style={styles.summaryLabel}>Income</Text>
        </View>
        <View style={styles.summaryCard}>
          <Text style={styles.summaryIcon}>↘</Text>
          <Text style={styles.expenseAmount}>£{totalExpenses.toLocaleString()}</Text>
          <Text style={styles.summaryLabel}>Expenses</Text>
        </View>
      </View>

      <View style={styles.sectionHeader}>
        <Text style={styles.sectionTitle}>🏦 Bank Accounts</Text>
      </View>
      {banks.map((bank) => (
        <View key={bank.id} style={styles.bankCard}>
          <View style={styles.bankRow}>
            <View style={styles.bankInfo}>
              <Text style={styles.bankName}>{bank.bank_name}</Text>
              <Text style={styles.bankMeta}>
                ••{bank.last_four}  ·  Last synced: {formatLastSynced(bank.last_synced)}
              </Text>
              <Text style={styles.bankSync}>
                {syncsUsed} of 1 sync used today
              </Text>
            </View>
            <AnimatedPressable
              onPress={() => syncBank(bank.id)}
              disabled={syncsUsed >= 1 || syncingId === bank.id}
            >
              <LinearGradient
                colors={
                  syncsUsed >= 1
                    ? [colors.bgCard, colors.bgCard]
                    : [colors.gradientStart, colors.gradientEnd]
                }
                start={{ x: 0, y: 0 }}
                end={{ x: 1, y: 0 }}
                style={styles.syncBtn}
              >
                {syncingId === bank.id ? (
                  <ActivityIndicator color={colors.text} size="small" />
                ) : (
                  <Text
                    style={[
                      styles.syncBtnText,
                      syncsUsed >= 1 && { color: colors.textMuted },
                    ]}
                  >
                    🔄 Sync
                  </Text>
                )}
              </LinearGradient>
            </AnimatedPressable>
          </View>
        </View>
      ))}

      <View style={styles.sectionHeader}>
        <Text style={styles.sectionTitle}>📊 This Month</Text>
      </View>
      <View style={styles.card}>
        <View style={styles.monthRow}>
          <Text style={styles.monthLabel}>Income</Text>
          <Text style={[styles.monthValue, { color: colors.income }]}>
            £{monthlyIncome.toLocaleString()}
          </Text>
        </View>
        <View style={styles.monthRow}>
          <Text style={styles.monthLabel}>Expenses</Text>
          <Text style={[styles.monthValue, { color: colors.expense }]}>
            £{monthlyExpenses.toLocaleString()}
          </Text>
        </View>
        <View style={[styles.monthRow, { borderBottomWidth: 0 }]}>
          <Text style={styles.monthLabel}>Profit</Text>
          <Text style={[styles.monthValue, { color: colors.accentTeal }]}>
            £{monthlyProfit.toLocaleString()}
          </Text>
        </View>
      </View>

      <View style={styles.sectionHeader}>
        <Text style={styles.sectionTitle}>📋 Invoices</Text>
      </View>
      <View style={styles.card}>
        <Text style={styles.invoiceSummary}>
          Pending: {pendingInvoices.length} (£{pendingTotal.toLocaleString()})
        </Text>
        {overdueInvoices.length > 0 && (
          <Text style={styles.overdueSummary}>
            🚨 Overdue: {overdueInvoices.length} (£{overdueTotal.toLocaleString()})
          </Text>
        )}
      </View>
    </ScrollView>
  );

  const renderTransactions = () => (
    <FlatList
      data={transactions}
      keyExtractor={(item) => item.id}
      contentContainerStyle={styles.tabContent}
      showsVerticalScrollIndicator={false}
      renderItem={({ item, index }) => (
        <View
          style={[
            styles.txRow,
            index === transactions.length - 1 && { borderBottomWidth: 0 },
          ]}
        >
          <View style={styles.txLeft}>
            <View
              style={[
                styles.txDot,
                {
                  backgroundColor:
                    item.amount > 0 ? colors.income : colors.expense,
                },
              ]}
            />
            <View style={styles.txInfo}>
              <Text style={styles.txDesc}>{item.description}</Text>
              <View style={styles.txMeta}>
                <Text style={styles.txDate}>{item.date}</Text>
                {item.category && (
                  <View style={styles.categoryBadge}>
                    <Text style={styles.categoryText}>{item.category}</Text>
                  </View>
                )}
              </View>
            </View>
          </View>
          <Text
            style={[
              styles.txAmount,
              { color: item.amount > 0 ? colors.income : colors.expense },
            ]}
          >
            {item.amount > 0 ? '+' : ''}£{Math.abs(item.amount).toFixed(2)}
          </Text>
        </View>
      )}
      ListEmptyComponent={
        <Text style={styles.emptyText}>No transactions yet</Text>
      }
    />
  );

  const renderInvoices = () => (
    <View style={styles.invoicesContainer}>
      <FlatList
        data={invoices}
        keyExtractor={(item) => item.id}
        contentContainerStyle={styles.tabContent}
        showsVerticalScrollIndicator={false}
        renderItem={({ item }) => {
          const cfg = STATUS_CONFIG[item.status];
          return (
            <View style={styles.invoiceCard}>
              <View style={styles.invoiceHeader}>
                <View style={styles.invoiceLeft}>
                  <Text style={styles.invoiceClient}>{item.client_name}</Text>
                  <Text style={styles.invoiceDesc}>{item.description}</Text>
                </View>
                <View style={[styles.statusBadge, { backgroundColor: cfg.bg }]}>
                  <View style={[styles.statusDot, { backgroundColor: cfg.dot }]} />
                  <Text style={[styles.statusText, { color: cfg.text }]}>
                    {item.status.charAt(0).toUpperCase() + item.status.slice(1)}
                  </Text>
                </View>
              </View>
              <View style={styles.invoiceFooter}>
                <Text style={styles.invoiceAmount}>
                  £{item.amount.toLocaleString('en-GB', { minimumFractionDigits: 2 })}
                </Text>
                <Text style={styles.invoiceDate}>Due {item.due_date}</Text>
              </View>
            </View>
          );
        }}
        ListEmptyComponent={
          <Text style={styles.emptyText}>No invoices yet</Text>
        }
      />
      <AnimatedPressable
        onPress={() => setShowCreate(true)}
        style={styles.fabWrapper}
      >
        <LinearGradient
          colors={[colors.gradientStart, colors.gradientEnd]}
          style={styles.fab}
        >
          <Text style={styles.fabText}>+</Text>
        </LinearGradient>
      </AnimatedPressable>
    </View>
  );

  return (
    <SafeAreaView style={styles.container} edges={['top']}>
      <View style={styles.header}>
        <Text style={styles.title}>💰 Money</Text>
      </View>

      <ScrollView
        horizontal
        showsHorizontalScrollIndicator={false}
        contentContainerStyle={styles.segmentRow}
      >
        {TABS.map((tab) => (
          <TouchableOpacity
            key={tab.key}
            style={[
              styles.segmentTab,
              activeTab === tab.key && styles.segmentTabActive,
            ]}
            onPress={() => setActiveTab(tab.key)}
            activeOpacity={0.8}
          >
            <Text
              style={[
                styles.segmentText,
                activeTab === tab.key && styles.segmentTextActive,
              ]}
            >
              {tab.label}
            </Text>
          </TouchableOpacity>
        ))}
      </ScrollView>

      {activeTab === 'overview' && renderOverview()}
      {activeTab === 'transactions' && renderTransactions()}
      {activeTab === 'invoices' && renderInvoices()}

      <Modal visible={showCreate} animationType="slide" transparent>
        <KeyboardAvoidingView
          behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
          style={styles.modalOverlay}
        >
          <View style={styles.modalContent}>
            <View style={styles.modalHandle} />
            <ScrollView showsVerticalScrollIndicator={false}>
              <Text style={styles.modalTitle}>New Invoice</Text>
              <Text style={styles.label}>Client Name *</Text>
              <TextInput
                style={styles.input}
                value={clientName}
                onChangeText={setClientName}
                placeholder="e.g. Acme Ltd"
                placeholderTextColor={colors.textMuted}
              />
              <Text style={styles.label}>Client Email</Text>
              <TextInput
                style={styles.input}
                value={clientEmail}
                onChangeText={setClientEmail}
                placeholder="billing@client.com"
                placeholderTextColor={colors.textMuted}
                keyboardType="email-address"
                autoCapitalize="none"
              />
              <Text style={styles.label}>Amount (£) *</Text>
              <TextInput
                style={styles.input}
                value={amount}
                onChangeText={setAmount}
                placeholder="0.00"
                placeholderTextColor={colors.textMuted}
                keyboardType="numeric"
              />
              <Text style={styles.label}>Due Date</Text>
              <TextInput
                style={styles.input}
                value={dueDate}
                onChangeText={setDueDate}
                placeholder="YYYY-MM-DD"
                placeholderTextColor={colors.textMuted}
              />
              <Text style={styles.label}>Description</Text>
              <TextInput
                style={[styles.input, styles.textArea]}
                value={description}
                onChangeText={setDescription}
                placeholder="Work description"
                placeholderTextColor={colors.textMuted}
                multiline
                numberOfLines={3}
              />
              <View style={styles.modalButtons}>
                <AnimatedPressable onPress={createInvoice} disabled={creating}>
                  <LinearGradient
                    colors={[colors.gradientStart, colors.gradientEnd]}
                    start={{ x: 0, y: 0 }}
                    end={{ x: 1, y: 0 }}
                    style={styles.createButton}
                  >
                    {creating ? (
                      <ActivityIndicator color={colors.text} />
                    ) : (
                      <Text style={styles.createButtonText}>Create Invoice</Text>
                    )}
                  </LinearGradient>
                </AnimatedPressable>
                <TouchableOpacity
                  style={styles.cancelButton}
                  onPress={() => {
                    resetForm();
                    setShowCreate(false);
                  }}
                >
                  <Text style={styles.cancelButtonText}>Cancel</Text>
                </TouchableOpacity>
              </View>
            </ScrollView>
          </View>
        </KeyboardAvoidingView>
      </Modal>
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
  segmentRow: {
    paddingHorizontal: spacing.lg,
    paddingBottom: spacing.md,
    gap: spacing.sm,
  },
  segmentTab: {
    paddingHorizontal: spacing.lg,
    paddingVertical: spacing.sm,
    borderRadius: borderRadius.full,
    backgroundColor: colors.bgCard,
    borderWidth: 1,
    borderColor: colors.border,
  },
  segmentTabActive: {
    backgroundColor: colors.accentTeal,
    borderColor: colors.accentTeal,
  },
  segmentText: {
    fontSize: fontSize.sm,
    color: colors.textMuted,
    fontWeight: '600',
  },
  segmentTextActive: {
    color: colors.textInverse,
  },
  tabContent: {
    paddingHorizontal: spacing.lg,
    paddingBottom: spacing.xxl,
  },
  summaryRow: {
    flexDirection: 'row',
    gap: spacing.md,
    marginBottom: spacing.md,
  },
  summaryCard: {
    flex: 1,
    backgroundColor: colors.bgCard,
    borderRadius: borderRadius.lg,
    padding: spacing.lg,
    alignItems: 'center',
    borderWidth: 1,
    borderColor: colors.border,
  },
  summaryIcon: {
    fontSize: fontSize.lg,
    fontWeight: '700',
    color: colors.text,
    marginBottom: spacing.xs,
  },
  incomeAmount: {
    fontSize: fontSize.xl,
    fontWeight: '800',
    color: colors.income,
  },
  expenseAmount: {
    fontSize: fontSize.xl,
    fontWeight: '800',
    color: colors.expense,
  },
  summaryLabel: {
    fontSize: fontSize.xs,
    color: colors.textMuted,
    marginTop: spacing.xs,
    textTransform: 'uppercase',
  },
  sectionHeader: {
    paddingTop: spacing.lg,
    paddingBottom: spacing.sm,
  },
  sectionTitle: {
    fontSize: fontSize.sm,
    fontWeight: '700',
    color: colors.textMuted,
    textTransform: 'uppercase',
    letterSpacing: 1,
  },
  bankCard: {
    backgroundColor: colors.bgCard,
    borderRadius: borderRadius.lg,
    padding: spacing.lg,
    borderWidth: 1,
    borderColor: colors.border,
    marginBottom: spacing.md,
  },
  bankRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  bankInfo: {
    flex: 1,
    marginRight: spacing.md,
  },
  bankName: {
    fontSize: fontSize.lg,
    fontWeight: '700',
    color: colors.text,
  },
  bankMeta: {
    fontSize: fontSize.sm,
    color: colors.textMuted,
    marginTop: 2,
  },
  bankSync: {
    fontSize: fontSize.xs,
    color: colors.textMuted,
    marginTop: 2,
  },
  syncBtn: {
    borderRadius: borderRadius.md,
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm,
  },
  syncBtnText: {
    color: colors.text,
    fontSize: fontSize.sm,
    fontWeight: '700',
  },
  card: {
    backgroundColor: colors.bgCard,
    borderRadius: borderRadius.lg,
    padding: spacing.lg,
    borderWidth: 1,
    borderColor: colors.border,
  },
  monthRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    paddingVertical: spacing.sm,
    borderBottomWidth: 1,
    borderBottomColor: colors.border,
  },
  monthLabel: {
    fontSize: fontSize.md,
    color: colors.textSecondary,
  },
  monthValue: {
    fontSize: fontSize.md,
    fontWeight: '700',
  },
  invoiceSummary: {
    fontSize: fontSize.md,
    color: colors.text,
    fontWeight: '600',
  },
  overdueSummary: {
    fontSize: fontSize.md,
    color: colors.expense,
    fontWeight: '600',
    marginTop: spacing.sm,
  },
  txRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingVertical: spacing.md,
    borderBottomWidth: 1,
    borderBottomColor: colors.border,
  },
  txLeft: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.sm,
    flex: 1,
  },
  txDot: {
    width: 8,
    height: 8,
    borderRadius: 4,
  },
  txInfo: {
    flex: 1,
  },
  txDesc: {
    fontSize: fontSize.md,
    color: colors.text,
    fontWeight: '600',
  },
  txMeta: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.sm,
    marginTop: 2,
  },
  txDate: {
    fontSize: fontSize.xs,
    color: colors.textMuted,
  },
  categoryBadge: {
    backgroundColor: colors.bgCard,
    borderRadius: borderRadius.full,
    paddingHorizontal: spacing.sm,
    paddingVertical: 2,
  },
  categoryText: {
    fontSize: fontSize.xs,
    color: colors.textSecondary,
    fontWeight: '600',
  },
  txAmount: {
    fontSize: fontSize.md,
    fontWeight: '700',
  },
  invoicesContainer: {
    flex: 1,
  },
  invoiceCard: {
    backgroundColor: colors.bgCard,
    borderRadius: borderRadius.lg,
    padding: spacing.lg,
    marginBottom: spacing.md,
    borderWidth: 1,
    borderColor: colors.border,
  },
  invoiceHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: spacing.md,
  },
  invoiceLeft: {
    flex: 1,
    marginRight: spacing.sm,
  },
  invoiceClient: {
    fontSize: fontSize.md,
    fontWeight: '700',
    color: colors.text,
  },
  invoiceDesc: {
    fontSize: fontSize.sm,
    color: colors.textMuted,
    marginTop: 2,
  },
  statusBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    borderRadius: borderRadius.full,
    paddingHorizontal: spacing.sm,
    paddingVertical: spacing.xs,
    gap: spacing.xs,
  },
  statusDot: {
    width: 6,
    height: 6,
    borderRadius: 3,
  },
  statusText: {
    fontSize: fontSize.xs,
    fontWeight: '700',
  },
  invoiceFooter: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  invoiceAmount: {
    fontSize: fontSize.xl,
    fontWeight: '800',
    color: colors.text,
  },
  invoiceDate: {
    fontSize: fontSize.xs,
    color: colors.textMuted,
  },
  fabWrapper: {
    position: 'absolute',
    right: spacing.lg,
    bottom: spacing.lg,
  },
  fab: {
    width: 60,
    height: 60,
    borderRadius: 30,
    alignItems: 'center',
    justifyContent: 'center',
    elevation: 8,
    shadowColor: colors.accentTeal,
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.3,
    shadowRadius: 8,
  },
  fabText: {
    fontSize: 28,
    color: colors.textInverse,
    fontWeight: '600',
    lineHeight: 30,
  },
  emptyText: {
    color: colors.textMuted,
    fontSize: fontSize.md,
    textAlign: 'center',
    marginTop: spacing.xl,
  },
  modalOverlay: {
    flex: 1,
    justifyContent: 'flex-end',
    backgroundColor: colors.overlay,
  },
  modalContent: {
    backgroundColor: colors.bg,
    borderTopLeftRadius: borderRadius.xl,
    borderTopRightRadius: borderRadius.xl,
    padding: spacing.lg,
    maxHeight: '85%',
  },
  modalHandle: {
    width: 40,
    height: 4,
    borderRadius: 2,
    backgroundColor: colors.borderLight,
    alignSelf: 'center',
    marginBottom: spacing.md,
  },
  modalTitle: {
    fontSize: fontSize.xl,
    fontWeight: '800',
    color: colors.text,
    marginBottom: spacing.lg,
  },
  label: {
    fontSize: fontSize.xs,
    color: colors.textMuted,
    marginBottom: spacing.xs,
    marginTop: spacing.sm,
    textTransform: 'uppercase',
    letterSpacing: 0.5,
  },
  input: {
    backgroundColor: colors.bgCard,
    borderRadius: borderRadius.sm,
    padding: spacing.md,
    color: colors.text,
    fontSize: fontSize.md,
    borderWidth: 1,
    borderColor: colors.border,
  },
  textArea: {
    minHeight: 80,
    textAlignVertical: 'top',
  },
  modalButtons: {
    marginTop: spacing.lg,
    gap: spacing.sm,
    paddingBottom: spacing.xl,
  },
  createButton: {
    borderRadius: borderRadius.md,
    padding: spacing.md,
    alignItems: 'center',
  },
  createButtonText: {
    color: colors.textInverse,
    fontSize: fontSize.md,
    fontWeight: '700',
  },
  cancelButton: {
    backgroundColor: 'transparent',
    borderRadius: borderRadius.md,
    padding: spacing.md,
    alignItems: 'center',
    borderWidth: 1,
    borderColor: colors.borderLight,
  },
  cancelButtonText: {
    color: colors.textMuted,
    fontSize: fontSize.md,
    fontWeight: '600',
  },
});
