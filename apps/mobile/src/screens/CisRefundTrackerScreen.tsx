import React, { useCallback, useEffect, useState } from 'react';
import { ActivityIndicator, StyleSheet, Text, View } from 'react-native';

import Screen from '../components/Screen';
import SectionHeader from '../components/SectionHeader';
import Card from '../components/Card';
import FadeInView from '../components/FadeInView';
import { apiRequest } from '../services/api';
import { useAuth } from '../context/AuthContext';
import { useTranslation } from '../hooks/useTranslation';
import { colors, spacing } from '../theme';

type Totals = {
  verified_cis_withheld_gbp: number;
  unverified_cis_withheld_gbp: number;
  missing_obligation_buckets: number;
  open_tasks: number;
  estimate_note: string;
};

type ContractorRow = {
  display_name: string;
  status: string;
  cis_withheld_gbp: number;
  reconciliation_worst: string;
  open_payment_count: number;
};

type MonthBlock = {
  tax_month_label: string;
  contractors: ContractorRow[];
};

type TrackerPayload = {
  schema_version: string;
  totals: Totals;
  by_tax_month: MonthBlock[];
};

const fmt = (n: number) =>
  `£${Math.abs(n).toLocaleString('en-GB', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

export default function CisRefundTrackerScreen() {
  const { token } = useAuth();
  const { t } = useTranslation();
  const [data, setData] = useState<TrackerPayload | null>(null);
  const [error, setError] = useState('');
  const [refreshing, setRefreshing] = useState(false);

  // `t` is not referentially stable; keep only `token` in deps to avoid refetch loops.
  const load = useCallback(async () => {
    setError('');
    try {
      const r = await apiRequest('/transactions/cis/refund-tracker', { token });
      const j = await r.json().catch(() => ({}));
      if (!r.ok) {
        setError(typeof j.detail === 'string' ? j.detail : t('cis.load_error'));
        setData(null);
        return;
      }
      setData(j as TrackerPayload);
    } catch {
      setError(t('cis.load_error'));
      setData(null);
    }
  }, [token]);

  useEffect(() => {
    void load();
  }, [load]);

  const onRefresh = async () => {
    setRefreshing(true);
    await load();
    setRefreshing(false);
  };

  return (
    <Screen refreshing={refreshing} onRefresh={onRefresh}>
      <SectionHeader title={t('cis.tracker_title')} subtitle={t('cis.tracker_subtitle')} />
      <FadeInView>
        {error ? <Text style={styles.err}>{error}</Text> : null}

        {!data && !error ? (
          <ActivityIndicator color={colors.primary} style={{ marginVertical: spacing.lg }} />
        ) : null}

        {data ? (
          <>
            <Card>
              <View style={styles.grid}>
                <View style={styles.stat}>
                  <Text style={styles.statLabel}>{t('cis.verified_withheld')}</Text>
                  <Text style={styles.statVal}>{fmt(data.totals.verified_cis_withheld_gbp)}</Text>
                </View>
                <View style={styles.stat}>
                  <Text style={styles.statLabel}>{t('cis.unverified_withheld')}</Text>
                  <Text style={[styles.statVal, { color: colors.warning }]}>{fmt(data.totals.unverified_cis_withheld_gbp)}</Text>
                </View>
                <View style={styles.stat}>
                  <Text style={styles.statLabel}>{t('cis.missing_buckets')}</Text>
                  <Text style={styles.statVal}>{data.totals.missing_obligation_buckets}</Text>
                </View>
                <View style={styles.stat}>
                  <Text style={styles.statLabel}>{t('cis.open_tasks')}</Text>
                  <Text style={styles.statVal}>{data.totals.open_tasks}</Text>
                </View>
              </View>
              <Text style={styles.note}>{data.totals.estimate_note || t('cis.disclaimer')}</Text>
              <Text style={styles.hint}>{t('cis.open_txn_hint')}</Text>
            </Card>

            {data.by_tax_month.length === 0 ? (
              <Text style={styles.muted}>{t('cis.no_data')}</Text>
            ) : null}

            {data.by_tax_month.map((block) => (
              <Card key={block.tax_month_label} style={styles.sectionCard}>
                <Text style={styles.sectionTitle}>{block.tax_month_label}</Text>
                {block.contractors.map((c) => (
                  <View key={`${block.tax_month_label}-${c.display_name}`} style={styles.row}>
                    <View style={{ flex: 1 }}>
                      <Text style={styles.rowTitle}>{c.display_name}</Text>
                      <Text style={styles.rowMeta}>
                        {c.status}
                        {c.open_payment_count > 0 ? ` · ${c.open_payment_count}` : ''}
                      </Text>
                    </View>
                    <Text style={styles.rowAmt}>{fmt(c.cis_withheld_gbp)}</Text>
                  </View>
                ))}
              </Card>
            ))}
          </>
        ) : null}
      </FadeInView>
    </Screen>
  );
}

const styles = StyleSheet.create({
  err: { color: colors.danger, marginBottom: spacing.sm },
  grid: { flexDirection: 'row', flexWrap: 'wrap', gap: 10 },
  stat: {
    width: '47%',
    backgroundColor: colors.surface,
    borderRadius: 12,
    padding: spacing.sm,
    borderWidth: 1,
    borderColor: colors.border,
  },
  statLabel: { fontSize: 12, color: colors.textSecondary },
  statVal: { fontSize: 16, fontWeight: '700', color: colors.textPrimary, marginTop: 4 },
  note: { fontSize: 12, color: colors.textSecondary, lineHeight: 18, marginTop: spacing.md },
  hint: { fontSize: 12, color: colors.textSecondary, marginTop: spacing.sm },
  muted: { fontSize: 14, color: colors.textSecondary, marginTop: spacing.md },
  sectionCard: { marginTop: spacing.md },
  sectionTitle: { fontSize: 16, fontWeight: '600', color: colors.textPrimary, marginBottom: 8 },
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 10,
    borderBottomWidth: 1,
    borderBottomColor: colors.border,
  },
  rowTitle: { fontSize: 14, fontWeight: '600', color: colors.textPrimary },
  rowMeta: { fontSize: 12, color: colors.textSecondary, marginTop: 2 },
  rowAmt: { fontSize: 14, fontWeight: '700', color: colors.primary },
});
