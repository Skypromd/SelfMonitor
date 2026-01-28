import React, { useEffect, useMemo, useState } from 'react';
import { Linking, Modal, StyleSheet, Text, View } from 'react-native';
import * as DocumentPicker from 'expo-document-picker';

import Card from '../components/Card';
import SectionHeader from '../components/SectionHeader';
import PrimaryButton from '../components/PrimaryButton';
import Screen from '../components/Screen';
import StatCard from '../components/StatCard';
import InputField from '../components/InputField';
import Badge from '../components/Badge';
import ListItem from '../components/ListItem';
import EmptyState from '../components/EmptyState';
import FadeInView from '../components/FadeInView';
import Chip from '../components/Chip';
import { useTranslation } from '../hooks/useTranslation';
import { apiRequest } from '../services/api';
import { useAuth } from '../context/AuthContext';
import { colors, spacing } from '../theme';

type Transaction = {
  id: string;
  date: string;
  description: string;
  amount: number;
  currency: string;
  category?: string | null;
  tax_category?: string | null;
  business_use_percent?: number | null;
};

type Provider = {
  id: string;
  display_name: string;
  configured?: string;
};

type PickedFile = {
  uri: string;
  name: string;
  mimeType: string;
};

export default function TransactionsScreen() {
  const { token } = useAuth();
  const { t } = useTranslation();
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [summary, setSummary] = useState({ income: 0, expenses: 0 });
  const [providers, setProviders] = useState<Provider[]>([]);
  const [selectedProvider, setSelectedProvider] = useState('mock_bank');
  const [consentUrl, setConsentUrl] = useState('');
  const [accountId, setAccountId] = useState('');
  const [manualAccountId, setManualAccountId] = useState('');
  const [csvFile, setCsvFile] = useState<PickedFile | null>(null);
  const [csvMessage, setCsvMessage] = useState('');
  const [csvError, setCsvError] = useState('');
  const [isUploading, setIsUploading] = useState(false);
  const [connectMessage, setConnectMessage] = useState('');
  const [connectError, setConnectError] = useState('');
  const [categoryModalOpen, setCategoryModalOpen] = useState(false);
  const [selectedTransaction, setSelectedTransaction] = useState<Transaction | null>(null);
  const effectiveAccountId = manualAccountId || accountId;

  const categoryOptions = useMemo(() => ([
    { value: 'income', label: t('transactions.category_income') },
    { value: 'groceries', label: t('transactions.category_groceries') },
    { value: 'transport', label: t('transactions.category_transport') },
    { value: 'food_and_drink', label: t('transactions.category_food') },
    { value: 'subscriptions', label: t('transactions.category_subscriptions') },
    { value: 'other', label: t('transactions.category_other') },
  ]), [t]);

  useEffect(() => {
    const fetchProviders = async () => {
      try {
        const response = await apiRequest('/banking/providers');
        if (!response.ok) return;
        const data = await response.json();
        setProviders(data || []);
        if (data?.length) {
          setSelectedProvider(data[0].id);
        }
      } catch {
        setProviders([]);
      }
    };

    const fetchTransactions = async () => {
      try {
        const path = effectiveAccountId
          ? `/transactions/accounts/${effectiveAccountId}/transactions`
          : '/transactions/transactions/me';
        const response = await apiRequest(path, { token });
        if (!response.ok) return;
        const data = await response.json();
        setTransactions(data || []);
        const income = data.filter((t: Transaction) => t.amount > 0).reduce((sum: number, t: Transaction) => sum + t.amount, 0);
        const expenses = data.filter((t: Transaction) => t.amount < 0).reduce((sum: number, t: Transaction) => sum + Math.abs(t.amount), 0);
        setSummary({ income, expenses });
      } catch {
        setTransactions([]);
        setSummary({ income: 0, expenses: 0 });
      }
    };
    fetchProviders();
    fetchTransactions();
  }, [token, effectiveAccountId]);

  const providerOptions = providers.length
    ? providers
    : [{ id: 'mock_bank', display_name: t('transactions.mock_provider'), configured: 'true' }];

  const handleInitiate = async () => {
    setConnectMessage('');
    setConnectError('');
    try {
      const response = await apiRequest('/banking/connections/initiate', {
        method: 'POST',
        token,
        body: JSON.stringify({
          provider_id: selectedProvider,
          redirect_uri: 'selfmonitor://banking/callback',
        }),
      });
      if (!response.ok) throw new Error(t('transactions.connect_error'));
      const data = await response.json();
      setConsentUrl(data.consent_url || '');
      if (data.consent_url) {
        Linking.openURL(data.consent_url);
      }
    } catch (err: any) {
      setConnectError(err.message || t('transactions.connect_error'));
    }
  };

  const handleGrant = async () => {
    setConnectMessage('');
    setConnectError('');
    try {
      const response = await apiRequest(`/banking/connections/callback?code=fake_auth_code&provider_id=${selectedProvider}`);
      if (!response.ok) throw new Error(t('transactions.connect_error'));
      const data = await response.json();
      setAccountId(data.account_id || '');
      setConnectMessage(t('transactions.connect_success'));
      setConsentUrl('');
    } catch (err: any) {
      setConnectError(err.message || t('transactions.connect_error'));
    }
  };

  const handlePickCsv = async () => {
    setCsvMessage('');
    setCsvError('');
    const result = await DocumentPicker.getDocumentAsync({
      type: ['text/csv', 'text/comma-separated-values', 'application/vnd.ms-excel'],
    });
    if (result.canceled) return;
    const asset = result.assets[0];
    setCsvFile({
      uri: asset.uri,
      name: asset.name || 'transactions.csv',
      mimeType: asset.mimeType || 'text/csv',
    });
  };

  const handleUploadCsv = async () => {
    setCsvMessage('');
    setCsvError('');
    if (!effectiveAccountId) {
      setCsvError(t('transactions.csv_account_error'));
      return;
    }
    if (!csvFile) {
      setCsvError(t('transactions.csv_select_error'));
      return;
    }
    try {
      setIsUploading(true);
      const formData = new FormData();
      formData.append('account_id', effectiveAccountId);
      formData.append('file', {
        uri: csvFile.uri,
        name: csvFile.name,
        type: csvFile.mimeType,
      } as any);
      const response = await apiRequest('/transactions/import/csv', {
        method: 'POST',
        token,
        body: formData,
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || t('transactions.csv_upload_error'));
      setCsvMessage(`${t('transactions.csv_success')} ${data.imported_count}. ${t('transactions.csv_skipped_label')} ${data.skipped_count}.`);
      setCsvFile(null);
    } catch (err: any) {
      setCsvError(err.message || t('transactions.csv_upload_error'));
    } finally {
      setIsUploading(false);
    }
  };

  const handleSelectCategory = async (newCategory: string) => {
    if (!selectedTransaction) return;
    try {
      const response = await apiRequest(`/transactions/transactions/${selectedTransaction.id}`, {
        method: 'PATCH',
        token,
        body: JSON.stringify({ category: newCategory }),
      });
      if (!response.ok) throw new Error();
      setTransactions((prev) =>
        prev.map((txn) => txn.id === selectedTransaction.id ? { ...txn, category: newCategory } : txn)
      );
      setCategoryModalOpen(false);
    } catch {
      setCategoryModalOpen(false);
    }
  };

  const openCategoryModal = (txn: Transaction) => {
    setSelectedTransaction(txn);
    setCategoryModalOpen(true);
  };

  const getCategoryLabel = (txn: Transaction) => {
    const category = txn.tax_category || txn.category;
    if (!category) return t('transactions.category_missing');
    const match = categoryOptions.find((item) => item.value === category);
    return match ? match.label : category;
  };

  return (
    <Screen>
      <SectionHeader title={t('transactions.title')} subtitle={t('transactions.subtitle')} />
      <FadeInView>
        <View style={styles.statsRow}>
          <StatCard label={t('transactions.income_label')} value={`GBP ${summary.income.toFixed(2)}`} icon="trending-up-outline" />
          <StatCard label={t('transactions.expense_label')} value={`GBP ${summary.expenses.toFixed(2)}`} icon="trending-down-outline" tone="warning" />
        </View>
      </FadeInView>
      <FadeInView delay={80}>
        <Card>
          <Text style={styles.cardTitle}>{t('transactions.connect_bank')}</Text>
          <View style={styles.providerRow}>
            {providerOptions.map((provider) => (
              <View key={provider.id} style={styles.providerChip}>
                <Chip
                  label={provider.display_name}
                  selected={provider.id === selectedProvider}
                  onPress={() => setSelectedProvider(provider.id)}
                />
              </View>
            ))}
          </View>
          <PrimaryButton title={t('transactions.connect_bank')} onPress={handleInitiate} variant="secondary" />
          {consentUrl ? (
            <PrimaryButton title={t('transactions.confirm_consent')} onPress={handleGrant} style={styles.secondaryButton} />
          ) : null}
          {connectMessage ? <Text style={styles.message}>{connectMessage}</Text> : null}
          {connectError ? <Text style={styles.error}>{connectError}</Text> : null}
        </Card>
      </FadeInView>
      <FadeInView delay={160}>
        <Card>
          <Text style={styles.cardTitle}>{t('transactions.csv_import')}</Text>
          <InputField
            label={t('transactions.csv_account_label')}
            placeholder={t('transactions.csv_account_placeholder')}
            value={manualAccountId}
            onChangeText={setManualAccountId}
            helperText={accountId ? `${t('transactions.connected_account_label')} ${accountId}` : undefined}
          />
          <PrimaryButton
            title={csvFile ? t('transactions.csv_change_file') : t('transactions.csv_choose_file')}
            onPress={handlePickCsv}
            variant="secondary"
          />
          <PrimaryButton
            title={isUploading ? t('transactions.csv_uploading') : t('transactions.csv_upload_button')}
            onPress={handleUploadCsv}
            disabled={isUploading}
            style={styles.secondaryButton}
          />
          {csvFile ? <Text style={styles.helper}>{csvFile.name}</Text> : null}
          {csvMessage ? <Text style={styles.message}>{csvMessage}</Text> : null}
          {csvError ? <Text style={styles.error}>{csvError}</Text> : null}
        </Card>
      </FadeInView>

      <SectionHeader title={t('transactions.recent_title')} subtitle={t('transactions.recent_subtitle')} />
      <FadeInView delay={200}>
        <Card>
          {transactions.length === 0 ? (
            <EmptyState
              title={t('transactions.empty_title')}
              subtitle={t('transactions.empty_state')}
              icon="card-outline"
            />
          ) : (
            transactions.map(txn => (
              <ListItem
                key={txn.id}
                title={txn.description}
                subtitle={`${txn.date} · ${getCategoryLabel(txn)}`}
                icon={txn.amount >= 0 ? 'arrow-down-outline' : 'arrow-up-outline'}
                meta={`GBP ${Math.abs(txn.amount).toFixed(2)}`}
                badge={!txn.tax_category && !txn.category ? (
                  <Badge label={t('transactions.needs_category')} tone="warning" />
                ) : undefined}
                onPress={() => openCategoryModal(txn)}
              />
            ))
          )}
        </Card>
      </FadeInView>

      <Modal transparent visible={categoryModalOpen} animationType="slide">
        <View style={styles.modalBackdrop}>
          <View style={styles.modalContent}>
            <Text style={styles.modalTitle}>{t('transactions.category_modal_title')}</Text>
            {categoryOptions.map((option) => (
              <PrimaryButton
                key={option.value}
                title={option.label}
                onPress={() => handleSelectCategory(option.value)}
                variant={selectedTransaction?.category === option.value ? 'primary' : 'secondary'}
                style={styles.modalButton}
              />
            ))}
            <PrimaryButton
              title={t('common.cancel')}
              onPress={() => setCategoryModalOpen(false)}
              variant="secondary"
            />
          </View>
        </View>
      </Modal>
    </Screen>
  );
}

const styles = StyleSheet.create({
  statsRow: {
    marginBottom: spacing.lg,
  },
  cardTitle: {
    fontSize: 16,
    fontWeight: '600',
    marginBottom: 12,
    color: colors.textPrimary,
  },
  providerRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    marginBottom: spacing.md,
  },
  providerChip: {
    marginRight: spacing.sm,
    marginBottom: spacing.sm,
  },
  secondaryButton: {
    marginTop: spacing.sm,
  },
  helper: {
    marginTop: spacing.sm,
    color: colors.textSecondary,
  },
  message: {
    marginTop: spacing.sm,
    color: colors.success,
  },
  error: {
    marginTop: spacing.sm,
    color: colors.danger,
  },
  modalBackdrop: {
    flex: 1,
    backgroundColor: 'rgba(15, 23, 42, 0.5)',
    justifyContent: 'flex-end',
  },
  modalContent: {
    backgroundColor: colors.surface,
    padding: spacing.lg,
    borderTopLeftRadius: 20,
    borderTopRightRadius: 20,
  },
  modalTitle: {
    fontSize: 16,
    fontWeight: '700',
    color: colors.textPrimary,
    marginBottom: spacing.md,
  },
  modalButton: {
    marginBottom: spacing.sm,
  },
});
