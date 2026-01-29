import React, { useEffect, useMemo, useState } from 'react';
import { Share, StyleSheet, Text, View } from 'react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';

import Screen from '../components/Screen';
import SectionHeader from '../components/SectionHeader';
import Card from '../components/Card';
import InputField from '../components/InputField';
import PrimaryButton from '../components/PrimaryButton';
import ListItem from '../components/ListItem';
import Badge from '../components/Badge';
import Chip from '../components/Chip';
import FadeInView from '../components/FadeInView';
import InfoRow from '../components/InfoRow';
import { toCsv } from '../utils/csv';
import { useTranslation } from '../hooks/useTranslation';
import { colors, spacing } from '../theme';

type Client = {
  id: string;
  name: string;
  email: string;
};

type Invoice = {
  id: string;
  clientName: string;
  amount: number;
  dueDate: string;
  status: 'draft' | 'sent' | 'paid';
};

const CLIENTS_KEY = 'invoices.clients.v1';
const INVOICES_KEY = 'invoices.list.v1';

export default function InvoicesScreen() {
  const { t, tDynamic } = useTranslation();
  const [tab, setTab] = useState<'invoices' | 'clients'>('invoices');
  const [clients, setClients] = useState<Client[]>([]);
  const [invoices, setInvoices] = useState<Invoice[]>([]);
  const [clientName, setClientName] = useState('');
  const [clientEmail, setClientEmail] = useState('');
  const [invoiceClient, setInvoiceClient] = useState('');
  const [invoiceAmount, setInvoiceAmount] = useState('');
  const [invoiceDueDate, setInvoiceDueDate] = useState('');
  const [invoiceStatus, setInvoiceStatus] = useState<'draft' | 'sent' | 'paid'>('sent');
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');

  useEffect(() => {
    const loadData = async () => {
      try {
        const storedClients = await AsyncStorage.getItem(CLIENTS_KEY);
        const storedInvoices = await AsyncStorage.getItem(INVOICES_KEY);
        if (storedClients) setClients(JSON.parse(storedClients));
        if (storedInvoices) setInvoices(JSON.parse(storedInvoices));
      } catch {
        return;
      }
    };
    loadData();
  }, []);

  const saveClients = async (next: Client[]) => {
    setClients(next);
    try {
      await AsyncStorage.setItem(CLIENTS_KEY, JSON.stringify(next));
    } catch {
      return;
    }
  };

  const saveInvoices = async (next: Invoice[]) => {
    setInvoices(next);
    try {
      await AsyncStorage.setItem(INVOICES_KEY, JSON.stringify(next));
    } catch {
      return;
    }
  };

  const addClient = async () => {
    setMessage('');
    setError('');
    if (!clientName) {
      setError(t('invoices.client_required'));
      return;
    }
    const next: Client = {
      id: `${Date.now()}`,
      name: clientName,
      email: clientEmail || t('invoices.no_email'),
    };
    await saveClients([next, ...clients]);
    setClientName('');
    setClientEmail('');
    setMessage(t('invoices.client_saved'));
  };

  const addInvoice = async () => {
    setMessage('');
    setError('');
    const amount = Number(invoiceAmount);
    if (!invoiceClient || !amount || amount <= 0) {
      setError(t('invoices.invoice_required'));
      return;
    }
    const next: Invoice = {
      id: `${Date.now()}`,
      clientName: invoiceClient,
      amount,
      dueDate: invoiceDueDate || t('invoices.no_due_date'),
      status: invoiceStatus,
    };
    await saveInvoices([next, ...invoices]);
    setInvoiceClient('');
    setInvoiceAmount('');
    setInvoiceDueDate('');
    setInvoiceStatus('sent');
    setMessage(t('invoices.invoice_saved'));
  };

  const togglePaid = async (invoice: Invoice) => {
    const nextStatus = invoice.status === 'paid' ? 'sent' : 'paid';
    const updated = invoices.map((item) => item.id === invoice.id ? { ...item, status: nextStatus } : item);
    await saveInvoices(updated);
  };

  const outstandingTotal = useMemo(() => {
    return invoices.filter((item) => item.status !== 'paid').reduce((sum, item) => sum + item.amount, 0);
  }, [invoices]);

  const overdueCount = useMemo(() => {
    const today = new Date();
    return invoices.filter((item) => {
      const due = new Date(item.dueDate);
      return item.status !== 'paid' && !Number.isNaN(due.getTime()) && due < today;
    }).length;
  }, [invoices]);

  const exportInvoices = async () => {
    const headers = ['client', 'amount', 'due_date', 'status'];
    const rows = invoices.map((item) => [item.clientName, item.amount.toFixed(2), item.dueDate, item.status]);
    const csv = toCsv(headers, rows);
    await Share.share({ message: csv });
  };

  return (
    <Screen>
      <SectionHeader title={t('invoices.title')} subtitle={t('invoices.subtitle')} />
      <View style={styles.tabRow}>
        <View style={styles.tabChip}>
          <Chip label={t('invoices.tab_invoices')} selected={tab === 'invoices'} onPress={() => setTab('invoices')} />
        </View>
        <View style={styles.tabChip}>
          <Chip label={t('invoices.tab_clients')} selected={tab === 'clients'} onPress={() => setTab('clients')} />
        </View>
      </View>

      {tab === 'invoices' ? (
        <>
          <FadeInView>
            <Card>
              <Text style={styles.cardTitle}>{t('invoices.add_invoice')}</Text>
              <InputField label={t('invoices.client_name')} value={invoiceClient} onChangeText={setInvoiceClient} />
              <InputField label={t('invoices.amount')} value={invoiceAmount} onChangeText={setInvoiceAmount} keyboardType="decimal-pad" />
              <InputField label={t('invoices.due_date')} value={invoiceDueDate} onChangeText={setInvoiceDueDate} />
              <View style={styles.statusRow}>
                <View style={styles.statusChip}>
                  <Chip label={t('invoices.status_draft')} selected={invoiceStatus === 'draft'} onPress={() => setInvoiceStatus('draft')} />
                </View>
                <View style={styles.statusChip}>
                  <Chip label={t('invoices.status_sent')} selected={invoiceStatus === 'sent'} onPress={() => setInvoiceStatus('sent')} />
                </View>
                <View style={styles.statusChip}>
                  <Chip label={t('invoices.status_paid')} selected={invoiceStatus === 'paid'} onPress={() => setInvoiceStatus('paid')} />
                </View>
              </View>
              <PrimaryButton title={t('invoices.save_invoice')} onPress={addInvoice} haptic="medium" />
              {message ? <Text style={styles.message}>{message}</Text> : null}
              {error ? <Text style={styles.error}>{error}</Text> : null}
            </Card>
          </FadeInView>

          <FadeInView delay={120}>
            <Card>
              <Text style={styles.cardTitle}>{t('invoices.summary_title')}</Text>
              <InfoRow label={t('invoices.outstanding')} value={`GBP ${outstandingTotal.toFixed(2)}`} />
              <InfoRow label={t('invoices.overdue')} value={`${overdueCount}`} />
              <PrimaryButton title={t('invoices.export_csv')} onPress={exportInvoices} variant="secondary" haptic="light" style={styles.secondaryButton} />
            </Card>
          </FadeInView>

          <SectionHeader title={t('invoices.list_title')} subtitle={t('invoices.list_subtitle')} />
          <FadeInView delay={180}>
            <Card>
              {invoices.length ? (
                invoices.map((invoice) => (
                  <ListItem
                    key={invoice.id}
                    title={`${invoice.clientName} · GBP ${invoice.amount.toFixed(2)}`}
                    subtitle={`${invoice.dueDate}`}
                    icon="receipt-outline"
                    badge={<Badge label={tDynamic(`invoices.status_${invoice.status}`)} tone={invoice.status === 'paid' ? 'success' : 'warning'} />}
                    onPress={() => togglePaid(invoice)}
                  />
                ))
              ) : (
                <Text style={styles.emptyText}>{t('invoices.empty_invoices')}</Text>
              )}
            </Card>
          </FadeInView>
        </>
      ) : (
        <>
          <FadeInView>
            <Card>
              <Text style={styles.cardTitle}>{t('invoices.add_client')}</Text>
              <InputField label={t('invoices.client_name')} value={clientName} onChangeText={setClientName} />
              <InputField label={t('invoices.client_email')} value={clientEmail} onChangeText={setClientEmail} />
              <PrimaryButton title={t('invoices.save_client')} onPress={addClient} haptic="medium" />
              {message ? <Text style={styles.message}>{message}</Text> : null}
              {error ? <Text style={styles.error}>{error}</Text> : null}
            </Card>
          </FadeInView>

          <SectionHeader title={t('invoices.clients_title')} subtitle={t('invoices.clients_subtitle')} />
          <FadeInView delay={120}>
            <Card>
              {clients.length ? (
                clients.map((client) => (
                  <ListItem
                    key={client.id}
                    title={client.name}
                    subtitle={client.email}
                    icon="person-outline"
                  />
                ))
              ) : (
                <Text style={styles.emptyText}>{t('invoices.empty_clients')}</Text>
              )}
            </Card>
          </FadeInView>
        </>
      )}
    </Screen>
  );
}

const styles = StyleSheet.create({
  tabRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    marginBottom: spacing.sm,
  },
  tabChip: {
    marginRight: spacing.sm,
    marginBottom: spacing.sm,
  },
  cardTitle: {
    fontSize: 16,
    fontWeight: '700',
    color: colors.textPrimary,
    marginBottom: spacing.sm,
  },
  statusRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    marginBottom: spacing.sm,
  },
  statusChip: {
    marginRight: spacing.sm,
    marginBottom: spacing.sm,
  },
  message: {
    marginTop: spacing.sm,
    color: colors.success,
  },
  error: {
    marginTop: spacing.sm,
    color: colors.danger,
  },
  secondaryButton: {
    marginTop: spacing.sm,
  },
  emptyText: {
    color: colors.textSecondary,
    fontSize: 12,
    paddingVertical: spacing.md,
  },
});
