import React, { useState, useCallback, useEffect } from 'react';
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
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { colors, spacing, fontSize } from '../theme';
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
];

const MOCK_INVOICES: Invoice[] = [
  { id: '1', client_name: 'Acme Ltd', client_email: 'billing@acme.com', amount: 1500, due_date: '2026-04-15', description: 'Web development', status: 'sent' },
  { id: '2', client_name: 'TechCo', client_email: 'pay@techco.io', amount: 3200, due_date: '2026-03-20', description: 'Consulting', status: 'overdue' },
  { id: '3', client_name: 'StartupXYZ', client_email: 'finance@xyz.com', amount: 800, due_date: '2026-05-01', description: 'Logo design', status: 'draft' },
  { id: '4', client_name: 'BigCorp', client_email: 'ap@bigcorp.com', amount: 5000, due_date: '2026-03-01', description: 'Monthly retainer', status: 'paid' },
];

const STATUS_STYLES: Record<InvoiceStatus, { bg: string; text: string }> = {
  draft: { bg: colors.bgCard, text: colors.textMuted },
  sent: { bg: 'rgba(13,148,136,0.15)', text: colors.accentTealLight },
  paid: { bg: colors.successBg, text: colors.success },
  overdue: { bg: colors.errorBg, text: colors.error },
};

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
    const statusStyle = STATUS_STYLES[item.status];
    return (
      <View style={styles.invoiceCard}>
        <View style={styles.invoiceHeader}>
          <Text style={styles.clientName}>{item.client_name}</Text>
          <View style={[styles.statusBadge, { backgroundColor: statusStyle.bg }]}>
            <Text style={[styles.statusText, { color: statusStyle.text }]}>
              {item.status.charAt(0).toUpperCase() + item.status.slice(1)}
            </Text>
          </View>
        </View>
        <Text style={styles.invoiceDescription} numberOfLines={1}>
          {item.description}
        </Text>
        <View style={styles.invoiceFooter}>
          <Text style={styles.invoiceAmount}>£{item.amount.toFixed(2)}</Text>
          <Text style={styles.invoiceDate}>Due: {item.due_date}</Text>
        </View>
      </View>
    );
  };

  return (
    <SafeAreaView style={styles.container} edges={['top']}>
      <View style={styles.header}>
        <Text style={styles.title}>Invoices</Text>
      </View>

      <View style={styles.filterRow}>
        {FILTERS.map((f) => (
          <TouchableOpacity
            key={f.value}
            style={[styles.filterTab, filter === f.value && styles.filterTabActive]}
            onPress={() => setFilter(f.value)}
          >
            <Text
              style={[
                styles.filterTabText,
                filter === f.value && styles.filterTabTextActive,
              ]}
            >
              {f.label}
            </Text>
          </TouchableOpacity>
        ))}
      </View>

      {loading ? (
        <ActivityIndicator size="large" color={colors.accentTeal} style={styles.loader} />
      ) : (
        <FlatList
          data={filtered}
          keyExtractor={(item) => item.id}
          renderItem={renderInvoice}
          contentContainerStyle={styles.list}
          ListEmptyComponent={
            <Text style={styles.emptyText}>No invoices found.</Text>
          }
        />
      )}

      <TouchableOpacity
        style={styles.fab}
        onPress={() => setShowCreate(true)}
      >
        <Text style={styles.fabText}>+</Text>
      </TouchableOpacity>

      <Modal visible={showCreate} animationType="slide" transparent>
        <KeyboardAvoidingView
          behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
          style={styles.modalOverlay}
        >
          <View style={styles.modalContent}>
            <ScrollView>
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
                <TouchableOpacity
                  style={styles.createButton}
                  onPress={createInvoice}
                  disabled={creating}
                >
                  {creating ? (
                    <ActivityIndicator color={colors.text} />
                  ) : (
                    <Text style={styles.createButtonText}>Create Invoice</Text>
                  )}
                </TouchableOpacity>
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
    padding: spacing.md,
    paddingBottom: spacing.sm,
  },
  title: {
    fontSize: fontSize.xl,
    fontWeight: '700',
    color: colors.text,
  },
  filterRow: {
    flexDirection: 'row',
    paddingHorizontal: spacing.md,
    marginBottom: spacing.md,
    gap: spacing.sm,
  },
  filterTab: {
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm,
    borderRadius: 20,
    backgroundColor: colors.bgElevated,
    borderWidth: 1,
    borderColor: colors.border,
  },
  filterTabActive: {
    backgroundColor: colors.accentTeal,
    borderColor: colors.accentTeal,
  },
  filterTabText: {
    fontSize: fontSize.sm,
    color: colors.textMuted,
    fontWeight: '600',
  },
  filterTabTextActive: {
    color: colors.text,
  },
  list: {
    padding: spacing.md,
    paddingTop: 0,
    paddingBottom: 80,
  },
  invoiceCard: {
    backgroundColor: colors.bgElevated,
    borderRadius: 12,
    padding: spacing.lg,
    marginBottom: spacing.sm,
    borderWidth: 1,
    borderColor: colors.border,
  },
  invoiceHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: spacing.xs,
  },
  clientName: {
    fontSize: fontSize.md,
    fontWeight: '600',
    color: colors.text,
    flex: 1,
  },
  statusBadge: {
    borderRadius: 12,
    paddingHorizontal: spacing.sm,
    paddingVertical: spacing.xs,
  },
  statusText: {
    fontSize: fontSize.xs,
    fontWeight: '600',
  },
  invoiceDescription: {
    fontSize: fontSize.sm,
    color: colors.textMuted,
    marginBottom: spacing.sm,
  },
  invoiceFooter: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  invoiceAmount: {
    fontSize: fontSize.lg,
    fontWeight: '700',
    color: colors.text,
  },
  invoiceDate: {
    fontSize: fontSize.xs,
    color: colors.textMuted,
  },
  fab: {
    position: 'absolute',
    right: spacing.lg,
    bottom: spacing.lg,
    width: 56,
    height: 56,
    borderRadius: 28,
    backgroundColor: colors.accentTeal,
    alignItems: 'center',
    justifyContent: 'center',
    elevation: 6,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.25,
    shadowRadius: 4,
  },
  fabText: {
    fontSize: 28,
    color: colors.text,
    fontWeight: '600',
    lineHeight: 30,
  },
  modalOverlay: {
    flex: 1,
    justifyContent: 'flex-end',
    backgroundColor: 'rgba(0,0,0,0.5)',
  },
  modalContent: {
    backgroundColor: colors.bg,
    borderTopLeftRadius: 20,
    borderTopRightRadius: 20,
    padding: spacing.lg,
    maxHeight: '85%',
  },
  modalTitle: {
    fontSize: fontSize.xl,
    fontWeight: '700',
    color: colors.text,
    marginBottom: spacing.lg,
  },
  label: {
    fontSize: fontSize.sm,
    color: colors.textMuted,
    marginBottom: spacing.xs,
    marginTop: spacing.sm,
  },
  input: {
    backgroundColor: colors.bgCard,
    borderRadius: 8,
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
  },
  createButton: {
    backgroundColor: colors.accentTeal,
    borderRadius: 8,
    padding: spacing.md,
    alignItems: 'center',
  },
  createButtonText: {
    color: colors.text,
    fontSize: fontSize.md,
    fontWeight: '600',
  },
  cancelButton: {
    backgroundColor: 'transparent',
    borderRadius: 8,
    padding: spacing.md,
    alignItems: 'center',
    borderWidth: 1,
    borderColor: colors.border,
  },
  cancelButtonText: {
    color: colors.textMuted,
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
