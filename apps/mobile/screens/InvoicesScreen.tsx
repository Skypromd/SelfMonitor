import React, { useState, useCallback, useEffect, useRef } from 'react';
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  ActivityIndicator,
  Alert,
  FlatList,
  TextInput,
  Modal,
  ScrollView,
  KeyboardAvoidingView,
  Platform,
  Animated,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { LinearGradient } from 'expo-linear-gradient';
import { colors, spacing, fontSize, borderRadius } from '../theme';
import { apiCall } from '../api';

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

const FILTERS: Array<{ label: string; value: InvoiceStatus | 'all' }> = [
  { label: 'All', value: 'all' },
  { label: 'Draft', value: 'draft' },
  { label: 'Sent', value: 'sent' },
  { label: 'Paid', value: 'paid' },
  { label: 'Overdue', value: 'overdue' },
];

const MOCK_INVOICES: Invoice[] = [
  { id: '1', client_name: 'Acme Ltd', client_email: 'billing@acme.com', amount: 1500, due_date: '2026-04-15', description: 'Web development', status: 'sent' },
  { id: '2', client_name: 'TechCo', client_email: 'pay@techco.io', amount: 3200, due_date: '2026-03-20', description: 'Consulting', status: 'overdue' },
  { id: '3', client_name: 'StartupXYZ', client_email: 'finance@xyz.com', amount: 800, due_date: '2026-05-01', description: 'Logo design', status: 'draft' },
  { id: '4', client_name: 'BigCorp', client_email: 'ap@bigcorp.com', amount: 5000, due_date: '2026-03-01', description: 'Monthly retainer', status: 'paid' },
];

const STATUS_CONFIG: Record<InvoiceStatus, { bg: string; text: string; dot: string }> = {
  draft: { bg: colors.bgElevated, text: colors.textMuted, dot: colors.textMuted },
  sent: { bg: colors.infoBg, text: colors.info, dot: colors.info },
  paid: { bg: colors.incomeBg, text: colors.income, dot: colors.income },
  overdue: { bg: colors.expenseBg, text: colors.expense, dot: colors.expense },
};

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

export default function InvoicesScreen() {
  const [invoices, setInvoices] = useState<Invoice[]>(MOCK_INVOICES);
  const [filter, setFilter] = useState<InvoiceStatus | 'all'>('all');
  const [loading, setLoading] = useState(false);
  const [showCreate, setShowCreate] = useState(false);
  const [creating, setCreating] = useState(false);

  const [clientName, setClientName] = useState('');
  const [clientEmail, setClientEmail] = useState('');
  const [amount, setAmount] = useState('');
  const [dueDate, setDueDate] = useState('');
  const [description, setDescription] = useState('');

  const filtered =
    filter === 'all'
      ? invoices
      : invoices.filter((inv) => inv.status === filter);

  const totalOutstanding = invoices
    .filter((inv) => inv.status === 'sent' || inv.status === 'overdue')
    .reduce((sum, inv) => sum + inv.amount, 0);

  const fetchInvoices = useCallback(async (): Promise<void> => {
    setLoading(true);
    try {
      const res = await apiCall('/invoices');
      if (!res.ok) throw new Error('Failed to fetch invoices');
      const data = await res.json();
      if (Array.isArray(data)) setInvoices(data);
    } catch {
      // keep mock data
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchInvoices();
  }, [fetchInvoices]);

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
        due_date: dueDate || new Date(Date.now() + 30 * 86_400_000).toISOString().split('T')[0],
        description,
        status: 'draft',
      };
      const res = await apiCall('/invoices', {
        method: 'POST',
        body: JSON.stringify(payload),
      });
      let newInvoice: Invoice;
      if (res.ok) {
        newInvoice = await res.json();
      } else {
        newInvoice = {
          id: String(Date.now()),
          ...payload,
          status: 'draft' as InvoiceStatus,
        };
      }
      setInvoices((prev) => [newInvoice, ...prev]);
      resetForm();
      setShowCreate(false);
      Alert.alert('Created', 'Invoice created as draft');
    } catch (err: any) {
      Alert.alert('Error', err.message);
    } finally {
      setCreating(false);
    }
  }, [clientName, clientEmail, amount, dueDate, description]);

  const resetForm = () => {
    setClientName('');
    setClientEmail('');
    setAmount('');
    setDueDate('');
    setDescription('');
  };

  const renderInvoice = ({ item }: { item: Invoice }) => {
    const cfg = STATUS_CONFIG[item.status];
    return (
      <View style={styles.invoiceCard}>
        <View style={styles.invoiceHeader}>
          <View style={styles.invoiceHeaderLeft}>
            <Text style={styles.clientName}>{item.client_name}</Text>
            <Text style={styles.invoiceDescription} numberOfLines={1}>
              {item.description}
            </Text>
          </View>
          <View style={[styles.statusBadge, { backgroundColor: cfg.bg }]}>
            <View style={[styles.statusDot, { backgroundColor: cfg.dot }]} />
            <Text style={[styles.statusText, { color: cfg.text }]}>
              {item.status.charAt(0).toUpperCase() + item.status.slice(1)}
            </Text>
          </View>
        </View>
        <View style={styles.invoiceFooter}>
          <Text style={styles.invoiceAmount}>£{item.amount.toLocaleString('en-GB', { minimumFractionDigits: 2 })}</Text>
          <Text style={styles.invoiceDate}>Due {item.due_date}</Text>
        </View>
      </View>
    );
  };

  return (
    <SafeAreaView style={styles.container} edges={['top']}>
      <View style={styles.header}>
        <Text style={styles.title}>Invoices</Text>
        <Text style={styles.outstandingText}>
          £{totalOutstanding.toLocaleString('en-GB', { minimumFractionDigits: 2 })} outstanding
        </Text>
      </View>

      <ScrollView
        horizontal
        showsHorizontalScrollIndicator={false}
        contentContainerStyle={styles.filterRow}
      >
        {FILTERS.map((f) => (
          <TouchableOpacity
            key={f.value}
            style={[styles.filterChip, filter === f.value && styles.filterChipActive]}
            onPress={() => setFilter(f.value)}
          >
            <Text
              style={[
                styles.filterChipText,
                filter === f.value && styles.filterChipTextActive,
              ]}
            >
              {f.label}
            </Text>
          </TouchableOpacity>
        ))}
      </ScrollView>

      {loading ? (
        <ActivityIndicator size="large" color={colors.accentTeal} style={styles.loader} />
      ) : (
        <FlatList
          data={filtered}
          keyExtractor={(item) => item.id}
          renderItem={renderInvoice}
          contentContainerStyle={styles.list}
          showsVerticalScrollIndicator={false}
          ListEmptyComponent={
            <View style={styles.emptyContainer}>
              <Text style={styles.emptyEmoji}>📄</Text>
              <Text style={styles.emptyText}>No invoices found</Text>
            </View>
          }
        />
      )}

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
  outstandingText: {
    fontSize: fontSize.sm,
    color: colors.warning,
    marginTop: spacing.xs,
    fontWeight: '600',
  },
  filterRow: {
    paddingHorizontal: spacing.lg,
    paddingBottom: spacing.md,
    gap: spacing.sm,
  },
  filterChip: {
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm,
    borderRadius: borderRadius.full,
    backgroundColor: colors.bgCard,
    borderWidth: 1,
    borderColor: colors.border,
  },
  filterChipActive: {
    backgroundColor: colors.accentTeal,
    borderColor: colors.accentTeal,
  },
  filterChipText: {
    fontSize: fontSize.sm,
    color: colors.textMuted,
    fontWeight: '600',
  },
  filterChipTextActive: {
    color: colors.textInverse,
  },
  list: {
    paddingHorizontal: spacing.lg,
    paddingBottom: 100,
  },
  invoiceCard: {
    backgroundColor: colors.bgCard,
    borderRadius: borderRadius.xl,
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
  invoiceHeaderLeft: {
    flex: 1,
    marginRight: spacing.sm,
  },
  clientName: {
    fontSize: fontSize.md,
    fontWeight: '700',
    color: colors.text,
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
  invoiceDescription: {
    fontSize: fontSize.sm,
    color: colors.textMuted,
    marginTop: 2,
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
  loader: {
    marginTop: spacing.xl,
  },
  emptyContainer: {
    alignItems: 'center',
    paddingVertical: spacing.xxl,
  },
  emptyEmoji: {
    fontSize: 40,
    marginBottom: spacing.md,
  },
  emptyText: {
    color: colors.textMuted,
    fontSize: fontSize.md,
  },
});
