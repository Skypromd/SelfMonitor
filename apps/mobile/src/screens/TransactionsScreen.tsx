import React, { useEffect, useState } from 'react';
import { StyleSheet, Text, View } from 'react-native';

import Card from '../components/Card';
import SectionHeader from '../components/SectionHeader';
import PrimaryButton from '../components/PrimaryButton';
import Screen from '../components/Screen';
import StatCard from '../components/StatCard';
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
};

export default function TransactionsScreen() {
  const { token } = useAuth();
  const { t } = useTranslation();
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [summary, setSummary] = useState({ income: 0, expenses: 0 });

  useEffect(() => {
    const fetchTransactions = async () => {
      try {
        const response = await apiRequest('/transactions/transactions/me', { token });
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
    fetchTransactions();
  }, [token]);

  return (
    <Screen>
      <SectionHeader title={t('transactions.title')} subtitle={t('transactions.subtitle')} />
      <View style={styles.statsRow}>
        <StatCard label={t('transactions.income_label')} value={`GBP ${summary.income.toFixed(2)}`} icon="trending-up-outline" />
        <StatCard label={t('transactions.expense_label')} value={`GBP ${summary.expenses.toFixed(2)}`} icon="trending-down-outline" tone="warning" />
      </View>
      <Card>
        <Text style={styles.cardTitle}>{t('transactions.connect_bank')}</Text>
        <PrimaryButton title={t('transactions.connect_bank')} onPress={() => {}} variant="secondary" />
        <View style={{ height: 12 }} />
        <PrimaryButton title={t('transactions.csv_import')} onPress={() => {}} />
      </Card>

      {transactions.length === 0 ? (
        <Card>
          <Text style={styles.empty}>{t('transactions.empty_state')}</Text>
        </Card>
      ) : (
        transactions.map(txn => (
          <Card key={txn.id}>
            <Text style={styles.rowTitle}>{txn.description}</Text>
            <Text style={styles.rowSubtitle}>{txn.date}</Text>
            <View style={styles.rowFooter}>
              <Text style={styles.amount}>GBP {txn.amount.toFixed(2)}</Text>
              <Text style={styles.category}>{txn.category || '-'}</Text>
            </View>
          </Card>
        ))
      )}
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
  empty: {
    color: colors.textSecondary,
  },
  rowTitle: {
    fontSize: 16,
    fontWeight: '600',
    color: colors.textPrimary,
  },
  rowSubtitle: {
    color: colors.textSecondary,
    marginTop: 4,
  },
  rowFooter: {
    marginTop: 12,
    flexDirection: 'row',
    justifyContent: 'space-between',
  },
  amount: {
    fontWeight: '600',
    color: colors.primary,
  },
  category: {
    color: colors.textSecondary,
  },
});
