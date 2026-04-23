import { useFocusEffect } from '@react-navigation/native';
import React, { useCallback, useState } from 'react';
import { Share, StyleSheet, Text } from 'react-native';

import Screen from '../components/Screen';
import SectionHeader from '../components/SectionHeader';
import Card from '../components/Card';
import PrimaryButton from '../components/PrimaryButton';
import FadeInView from '../components/FadeInView';
import { apiRequest } from '../services/api';
import { readStoredTransactionsBusinessId } from '../services/transactionsBusinessStorage';

const API_GATEWAY_URL = process.env.EXPO_PUBLIC_API_GATEWAY_URL || 'http://localhost:8080/api';
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
  const [transactionsBusinessId, setTransactionsBusinessId] = useState<string | null>(null);

  useFocusEffect(
    useCallback(() => {
      if (!token) {
        setTransactionsBusinessId(null);
        return;
      }
      void readStoredTransactionsBusinessId(token).then(setTransactionsBusinessId);
    }, [token]),
  );

  const handleExportTransactions = async () => {
    setMessage('');
    setError('');
    if (isOffline) {
      setError(t('accountant.offline_error'));
      return;
    }
    setLoadingKey('transactions');
    try {
      const response = await apiRequest('/transactions/transactions/me', {
        token,
        businessId: transactionsBusinessId,
      });
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

  const handleCisEvidenceAccountantLink = async () => {
    setMessage('');
    setError('');
    if (isOffline) {
      setError(t('accountant.offline_error'));
      return;
    }
    setLoadingKey('cis_evidence');
    try {
      const response = await apiRequest('/transactions/cis/evidence-pack/share-token', {
        method: 'POST',
        token,
        body: '{}',
      });
      if (response.status === 403) {
        setError(t('accountant.cis_evidence_plan'));
        return;
      }
      if (!response.ok) {
        setError(t('accountant.cis_evidence_failed'));
        return;
      }
      const data = (await response.json()) as { token: string; relative_download_path: string };
      const path = `${data.relative_download_path}?token=${encodeURIComponent(data.token)}`;
      const url = `${API_GATEWAY_URL.replace(/\/$/, '')}/transactions${path.startsWith('/') ? '' : '/'}${path}`;
      const note = t('accountant.cis_evidence_note');
      await Share.share({
        message: `${t('accountant.cis_evidence_shared')}\n\n${url}\n\n${note}`,
      });
      setMessage(t('accountant.cis_evidence_done'));
    } catch {
      setError(t('accountant.cis_evidence_failed'));
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
          <PrimaryButton
            title={
              loadingKey === 'cis_evidence' ? t('common.loading') : t('accountant.cis_evidence_link')
            }
            onPress={handleCisEvidenceAccountantLink}
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
