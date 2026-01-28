import React, { useEffect, useState } from 'react';
import { ScrollView, StyleSheet, Text, View } from 'react-native';

import Card from '../components/Card';
import SectionHeader from '../components/SectionHeader';
import PrimaryButton from '../components/PrimaryButton';
import { useTranslation } from '../hooks/useTranslation';
import { apiRequest } from '../services/api';
import { useAuth } from '../context/AuthContext';

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

  useEffect(() => {
    const fetchTransactions = async () => {
      try {
        const response = await apiRequest('/transactions/transactions/me', { token });
        if (!response.ok) return;
        const data = await response.json();
        setTransactions(data || []);
      } catch {
        setTransactions([]);
      }
    };
    fetchTransactions();
  }, [token]);

  return (
    <ScrollView style={styles.container}>
      <SectionHeader title={t('transactions.title')} subtitle={t('transactions.subtitle')} />
      <Card>
        <Text style={styles.cardTitle}>{t('transactions.connect_bank')}</Text>
        <PrimaryButton title={t('transactions.connect_bank')} onPress={() => {}} />
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
              <Text style={styles.amount}>{txn.amount.toFixed(2)} {txn.currency}</Text>
              <Text style={styles.category}>{txn.category || '-'}</Text>
            </View>
          </Card>
        ))
      )}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    padding: 16,
  },
  cardTitle: {
    fontSize: 16,
    fontWeight: '600',
    marginBottom: 12,
    color: '#0f172a',
  },
  empty: {
    color: '#64748b',
  },
  rowTitle: {
    fontSize: 16,
    fontWeight: '600',
    color: '#0f172a',
  },
  rowSubtitle: {
    color: '#64748b',
    marginTop: 4,
  },
  rowFooter: {
    marginTop: 12,
    flexDirection: 'row',
    justifyContent: 'space-between',
  },
  amount: {
    fontWeight: '600',
    color: '#2563eb',
  },
  category: {
    color: '#64748b',
  },
});
