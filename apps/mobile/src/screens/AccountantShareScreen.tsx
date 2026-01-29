import React, { useState } from 'react';
import { Share, StyleSheet, Text } from 'react-native';

import Screen from '../components/Screen';
import SectionHeader from '../components/SectionHeader';
import Card from '../components/Card';
import PrimaryButton from '../components/PrimaryButton';
import FadeInView from '../components/FadeInView';
import { apiRequest } from '../services/api';
import { toCsv } from '../utils/csv';
import { useAuth } from '../context/AuthContext';
import { useNetworkStatus } from '../hooks/useNetworkStatus';
import { useTranslation } from '../hooks/useTranslation';
import { colors, spacing } from '../theme';

const formatDate = (date: Date) => date.toISOString().slice(0, 10);

const getTaxYearRange = (today: Date) => {
  const year = today.getFullYear();
  const startThisYear = new Date(year, 3, 6);
  if (today >= startThisYear) {
    return {
      start: formatDate(new Date(year, 3, 6)),
      end: formatDate(new Date(year + 1, 3, 5)),
    };
  }
  return {
    start: formatDate(new Date(year - 1, 3, 6)),
    end: formatDate(new Date(year, 3, 5)),
  };
};

export default function AccountantShareScreen() {
  const { token } = useAuth();
  const { t } = useTranslation();
  const { isOffline } = useNetworkStatus();
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [loadingKey, setLoadingKey] = useState<string | null>(null);

  const handleExportTransactions = async () => {
    setMessage('');
    setError('');
    if (isOffline) {
      setError(t('accountant.offline_error'));
      return;
    }
    setLoadingKey('transactions');
    try {
      const response = await apiRequest('/transactions/transactions/me', { token });
      if (!response.ok) throw new Error();
      const data = await response.json();
      const headers = ['date', 'description', 'amount', 'currency', 'category'];
      const rows = data.map((item: any) => [
        item.date,
        item.description,
        item.amount,
        item.currency,
        item.tax_category || item.category || '',
      ]);
      await Share.share({ message: toCsv(headers, rows) });
      setMessage(t('accountant.exported_transactions'));
    } catch {
      setError(t('accountant.export_error'));
    } finally {
      setLoadingKey(null);
    }
  };

  const handleExportTax = async () => {
    setMessage('');
    setError('');
    if (isOffline) {
      setError(t('accountant.offline_error'));
      return;
    }
    setLoadingKey('tax');
    try {
      const range = getTaxYearRange(new Date());
      const response = await apiRequest('/tax/calculate', {
        method: 'POST',
        token,
        body: JSON.stringify({
          start_date: range.start,
          end_date: range.end,
          jurisdiction: 'UK',
        }),
      });
      if (!response.ok) throw new Error();
      const data = await response.json();
      const headers = ['category', 'total_amount', 'allowable_amount', 'disallowable_amount'];
      const rows = (data.summary_by_category || []).map((item: any) => [
        item.category,
        item.total_amount,
        item.allowable_amount,
        item.disallowable_amount,
      ]);
      await Share.share({ message: toCsv(headers, rows) });
      setMessage(t('accountant.exported_tax'));
    } catch {
      setError(t('accountant.export_error'));
    } finally {
      setLoadingKey(null);
    }
  };

  const handleExportDocuments = async () => {
    setMessage('');
    setError('');
    if (isOffline) {
      setError(t('accountant.offline_error'));
      return;
    }
    setLoadingKey('documents');
    try {
      const response = await apiRequest('/documents', { token });
      if (!response.ok) throw new Error();
      const data = await response.json();
      const headers = ['filename', 'status', 'uploaded_at'];
      const rows = data.map((item: any) => [item.filename, item.status, item.uploaded_at]);
      await Share.share({ message: toCsv(headers, rows) });
      setMessage(t('accountant.exported_documents'));
    } catch {
      setError(t('accountant.export_error'));
    } finally {
      setLoadingKey(null);
    }
  };

  return (
    <Screen>
      <SectionHeader title={t('accountant.title')} subtitle={t('accountant.subtitle')} />
      <FadeInView>
        <Card>
          <Text style={styles.cardTitle}>{t('accountant.exports_title')}</Text>
          <PrimaryButton
            title={loadingKey === 'transactions' ? t('common.loading') : t('accountant.export_transactions')}
            onPress={handleExportTransactions}
            haptic="medium"
          />
          <PrimaryButton
            title={loadingKey === 'tax' ? t('common.loading') : t('accountant.export_tax')}
            onPress={handleExportTax}
            haptic="medium"
            variant="secondary"
            style={styles.secondaryButton}
          />
          <PrimaryButton
            title={loadingKey === 'documents' ? t('common.loading') : t('accountant.export_documents')}
            onPress={handleExportDocuments}
            haptic="medium"
            variant="secondary"
            style={styles.secondaryButton}
          />
          {message ? <Text style={styles.message}>{message}</Text> : null}
          {error ? <Text style={styles.error}>{error}</Text> : null}
        </Card>
      </FadeInView>
    </Screen>
  );
}

const styles = StyleSheet.create({
  cardTitle: {
    fontSize: 16,
    fontWeight: '700',
    color: colors.textPrimary,
    marginBottom: spacing.sm,
  },
  secondaryButton: {
    marginTop: spacing.sm,
  },
  message: {
    marginTop: spacing.sm,
    color: colors.success,
  },
  error: {
    marginTop: spacing.sm,
    color: colors.danger,
  },
});
