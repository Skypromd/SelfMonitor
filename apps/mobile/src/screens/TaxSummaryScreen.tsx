import React, { useMemo, useState } from 'react';
import { Share, StyleSheet, Text, View } from 'react-native';
import { useNavigation } from '@react-navigation/native';

import Screen from '../components/Screen';
import SectionHeader from '../components/SectionHeader';
import Card from '../components/Card';
import InputField from '../components/InputField';
import PrimaryButton from '../components/PrimaryButton';
import InfoRow from '../components/InfoRow';
import BarRow from '../components/BarRow';
import Chip from '../components/Chip';
import Badge from '../components/Badge';
import FadeInView from '../components/FadeInView';
import { apiRequest } from '../services/api';
import { toCsv } from '../utils/csv';
import { useAuth } from '../context/AuthContext';
import { useTranslation } from '../hooks/useTranslation';
import { useSubscriptionPlan } from '../hooks/useSubscriptionPlan';
import { colors, spacing } from '../theme';

type TaxSummaryItem = {
  category: string;
  total_amount: number;
  allowable_amount: number;
  disallowable_amount: number;
};

type TaxResult = {
  start_date: string;
  end_date: string;
  total_income: number;
  total_expenses: number;
  total_allowable_expenses: number;
  total_disallowable_expenses: number;
  taxable_profit: number;
  income_tax_due: number;
  class2_nic: number;
  class4_nic: number;
  estimated_tax_due: number;
  summary_by_category: TaxSummaryItem[];
};

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

const getPreviousTaxYearRange = (today: Date) => {
  const current = getTaxYearRange(today);
  const currentStart = new Date(current.start);
  const previousStart = new Date(currentStart.getFullYear() - 1, 3, 6);
  const previousEnd = new Date(currentStart.getFullYear(), 3, 5);
  return { start: formatDate(previousStart), end: formatDate(previousEnd) };
};

export default function TaxSummaryScreen() {
  const { token } = useAuth();
  const { t } = useTranslation();
  const { plan } = useSubscriptionPlan();
  const navigation = useNavigation();
  const [startDate, setStartDate] = useState(getTaxYearRange(new Date()).start);
  const [endDate, setEndDate] = useState(getTaxYearRange(new Date()).end);
  const [result, setResult] = useState<TaxResult | null>(null);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const categoryMax = useMemo(() => {
    if (!result?.summary_by_category?.length) return 0;
    return Math.max(...result.summary_by_category.map((item) => Math.abs(item.total_amount)));
  }, [result]);

  const handleRange = (range: { start: string; end: string }) => {
    setStartDate(range.start);
    setEndDate(range.end);
  };

  const calculateTax = async () => {
    setMessage('');
    setError('');
    setIsLoading(true);
    try {
      const response = await apiRequest('/tax/calculate', {
        method: 'POST',
        token,
        body: JSON.stringify({
          start_date: startDate,
          end_date: endDate,
          jurisdiction: 'UK',
        }),
      });
      if (!response.ok) throw new Error(t('tax.calculate_error'));
      const data = await response.json();
      setResult(data);
      setMessage(t('tax.calculate_success'));
    } catch (err: any) {
      setError(err.message || t('tax.calculate_error'));
    } finally {
      setIsLoading(false);
    }
  };

  const submitToHmrc = async () => {
    setMessage('');
    setError('');
    setIsSubmitting(true);
    try {
      const response = await apiRequest('/tax/calculate-and-submit', {
        method: 'POST',
        token,
        body: JSON.stringify({
          start_date: startDate,
          end_date: endDate,
          jurisdiction: 'UK',
        }),
      });
      if (response.status === 402) {
        setError(t('tax.pro_required'));
        return;
      }
      if (!response.ok) throw new Error(t('tax.submit_error'));
      setMessage(t('tax.submit_success'));
    } catch (err: any) {
      setError(err.message || t('tax.submit_error'));
    } finally {
      setIsSubmitting(false);
    }
  };

  const exportCsv = async () => {
    if (!result) return;
    const headers = ['category', 'total_amount', 'allowable_amount', 'disallowable_amount'];
    const rows = result.summary_by_category.map((item) => [
      item.category,
      item.total_amount,
      item.allowable_amount,
      item.disallowable_amount,
    ]);
    const csv = toCsv(headers, rows);
    await Share.share({ message: csv });
  };

  return (
    <Screen>
      <SectionHeader title={t('tax.title')} subtitle={t('tax.subtitle')} />
      <FadeInView>
        <Card>
          <Text style={styles.cardTitle}>{t('tax.range_title')}</Text>
          <View style={styles.rangeRow}>
            <View style={styles.rangeChip}>
              <Chip label={t('tax.current_year')} onPress={() => handleRange(getTaxYearRange(new Date()))} />
            </View>
            <View style={styles.rangeChip}>
              <Chip label={t('tax.previous_year')} onPress={() => handleRange(getPreviousTaxYearRange(new Date()))} />
            </View>
          </View>
          <InputField label={t('tax.start_date')} value={startDate} onChangeText={setStartDate} />
          <InputField label={t('tax.end_date')} value={endDate} onChangeText={setEndDate} />
          <PrimaryButton title={isLoading ? t('common.loading') : t('tax.calculate')} onPress={calculateTax} haptic="medium" />
          <PrimaryButton
            title={t('tax.submit')}
            onPress={submitToHmrc}
            haptic="medium"
            variant="secondary"
            style={styles.secondaryButton}
            disabled={isSubmitting || plan === 'free'}
          />
          {plan === 'free' ? (
            <>
              <Text style={styles.proNote}>{t('tax.pro_note')}</Text>
              <PrimaryButton
                title={t('upgrade.cta')}
                onPress={() => navigation.navigate('Upgrade' as never)}
                variant="secondary"
                haptic="light"
                style={styles.secondaryButton}
              />
            </>
          ) : null}
          {message ? <Text style={styles.message}>{message}</Text> : null}
          {error ? <Text style={styles.error}>{error}</Text> : null}
        </Card>
      </FadeInView>

      {result ? (
        <FadeInView delay={120}>
          <Card>
            <View style={styles.titleRow}>
              <Text style={styles.cardTitle}>{t('tax.summary_title')}</Text>
              <Badge label={t('tax.jurisdiction_label')} tone="info" />
            </View>
            <InfoRow label={t('tax.total_income')} value={`GBP ${result.total_income.toFixed(2)}`} />
            <InfoRow label={t('tax.total_expenses')} value={`GBP ${result.total_expenses.toFixed(2)}`} />
            <InfoRow label={t('tax.allowable_expenses')} value={`GBP ${result.total_allowable_expenses.toFixed(2)}`} />
            <InfoRow label={t('tax.disallowable_expenses')} value={`GBP ${result.total_disallowable_expenses.toFixed(2)}`} />
            <InfoRow label={t('tax.taxable_profit')} value={`GBP ${result.taxable_profit.toFixed(2)}`} />
            <InfoRow label={t('tax.income_tax')} value={`GBP ${result.income_tax_due.toFixed(2)}`} />
            <InfoRow label={t('tax.class2')} value={`GBP ${result.class2_nic.toFixed(2)}`} />
            <InfoRow label={t('tax.class4')} value={`GBP ${result.class4_nic.toFixed(2)}`} />
            <InfoRow label={t('tax.estimated_tax')} value={`GBP ${result.estimated_tax_due.toFixed(2)}`} />
            <PrimaryButton title={t('tax.export_csv')} onPress={exportCsv} variant="secondary" haptic="light" style={styles.secondaryButton} />
          </Card>
        </FadeInView>
      ) : null}

      {result?.summary_by_category?.length ? (
        <FadeInView delay={180}>
          <Card>
            <Text style={styles.cardTitle}>{t('tax.category_breakdown')}</Text>
            {result.summary_by_category.map((item) => (
              <BarRow
                key={item.category}
                label={item.category}
                value={item.total_amount}
                maxValue={categoryMax}
                valueLabel={`GBP ${item.total_amount.toFixed(2)}`}
                tone={item.total_amount >= 0 ? 'success' : 'warning'}
              />
            ))}
          </Card>
        </FadeInView>
      ) : null}
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
  rangeRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    marginBottom: spacing.md,
  },
  rangeChip: {
    marginRight: spacing.sm,
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
  proNote: {
    marginTop: spacing.sm,
    color: colors.textSecondary,
    fontSize: 12,
  },
  titleRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
});
