import React, { useCallback, useState } from 'react';
import {
  ActivityIndicator,
  RefreshControl,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { apiCall } from '../api';
import { colors, fontSize, spacing } from '../theme';

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
  const [data, setData] = useState<TrackerPayload | null>(null);
  const [error, setError] = useState('');
  const [refreshing, setRefreshing] = useState(false);

  const load = useCallback(async () => {
    setError('');
    try {
      const r = await apiCall('/transactions/cis/refund-tracker');
      const j = await r.json().catch(() => ({}));
      if (!r.ok) {
        setError(typeof j.detail === 'string' ? j.detail : 'Could not load CIS tracker');
        setData(null);
        return;
      }
      setData(j as TrackerPayload);
    } catch {
      setError('Network error');
      setData(null);
    }
  }, []);

  React.useEffect(() => {
    void load();
  }, [load]);

  const onRefresh = async () => {
    setRefreshing(true);
    await load();
    setRefreshing(false);
  };

  return (
    <SafeAreaView style={styles.safe} edges={['top']}>
      <ScrollView
        contentContainerStyle={styles.scroll}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor={colors.accentTeal} />}
      >
        <Text style={styles.title}>CIS refund tracker</Text>
        <Text style={styles.sub}>
          UK tax months — verified vs unverified withholding. Estimates only; not a guarantee of refund.
        </Text>

        {error ? <Text style={styles.err}>{error}</Text> : null}

        {!data && !error ? (
          <ActivityIndicator color={colors.accentTeal} style={{ marginTop: spacing.lg }} />
        ) : null}

        {data ? (
          <>
            <View style={styles.grid}>
              <View style={styles.stat}>
                <Text style={styles.statLabel}>Verified withheld</Text>
                <Text style={styles.statVal}>{fmt(data.totals.verified_cis_withheld_gbp)}</Text>
              </View>
              <View style={styles.stat}>
                <Text style={styles.statLabel}>Unverified</Text>
                <Text style={[styles.statVal, { color: colors.warning }]}>{fmt(data.totals.unverified_cis_withheld_gbp)}</Text>
              </View>
              <View style={styles.stat}>
                <Text style={styles.statLabel}>Missing</Text>
                <Text style={styles.statVal}>{data.totals.missing_obligation_buckets}</Text>
              </View>
              <View style={styles.stat}>
                <Text style={styles.statLabel}>Open tasks</Text>
                <Text style={styles.statVal}>{data.totals.open_tasks}</Text>
              </View>
            </View>
            <Text style={styles.note}>{data.totals.estimate_note}</Text>

            {data.by_tax_month.length === 0 ? (
              <Text style={styles.muted}>No CIS periods yet. Sync bank data and review CIS hints on Money.</Text>
            ) : null}

            {data.by_tax_month.map((block) => (
              <View key={block.tax_month_label} style={styles.section}>
                <Text style={styles.sectionTitle}>{block.tax_month_label}</Text>
                {block.contractors.map((c) => (
                  <View key={`${block.tax_month_label}-${c.display_name}`} style={styles.row}>
                    <View style={{ flex: 1 }}>
                      <Text style={styles.rowTitle}>{c.display_name}</Text>
                      <Text style={styles.rowMeta}>
                        {c.status}
                        {c.open_payment_count > 0 ? ` · ${c.open_payment_count} open payment(s)` : ''}
                      </Text>
                    </View>
                    <Text style={styles.rowAmt}>{fmt(c.cis_withheld_gbp)}</Text>
                  </View>
                ))}
              </View>
            ))}
          </>
        ) : null}
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.bg },
  scroll: { padding: spacing.md, paddingBottom: spacing.xl },
  title: { fontSize: fontSize.xl, fontWeight: '700', color: colors.text, marginBottom: 6 },
  sub: { fontSize: fontSize.sm, color: colors.textMuted, lineHeight: 20, marginBottom: spacing.md },
  err: { color: colors.error, marginBottom: spacing.sm },
  grid: { flexDirection: 'row', flexWrap: 'wrap', gap: 10, marginBottom: spacing.md },
  stat: {
    width: '47%',
    backgroundColor: colors.bgElevated,
    borderRadius: 12,
    padding: spacing.sm,
    borderWidth: 1,
    borderColor: colors.border,
  },
  statLabel: { fontSize: fontSize.xs, color: colors.textMuted },
  statVal: { fontSize: fontSize.md, fontWeight: '700', color: colors.text, marginTop: 4 },
  note: { fontSize: fontSize.xs, color: colors.textMuted, lineHeight: 18, marginBottom: spacing.lg },
  muted: { fontSize: fontSize.sm, color: colors.textMuted },
  section: { marginBottom: spacing.lg },
  sectionTitle: { fontSize: fontSize.md, fontWeight: '600', color: colors.text, marginBottom: 8 },
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 10,
    borderBottomWidth: 1,
    borderBottomColor: colors.border,
  },
  rowTitle: { fontSize: fontSize.sm, fontWeight: '600', color: colors.text },
  rowMeta: { fontSize: fontSize.xs, color: colors.textMuted, marginTop: 2 },
  rowAmt: { fontSize: fontSize.sm, fontWeight: '700', color: colors.accentTeal },
});
