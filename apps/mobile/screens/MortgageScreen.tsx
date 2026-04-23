import React, { useState, useCallback, useRef } from 'react';
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  ActivityIndicator,
  Alert,
  TextInput,
  ScrollView,
  Animated,
  Switch,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { LinearGradient } from 'expo-linear-gradient';
import { colors, spacing, fontSize, borderRadius } from '../theme';
import { apiCall } from '../api';

type LenderMatch = {
  name: string;
  rate: string;
  max_ltv: string;
};

type ChecklistItem = {
  label: string;
  done: boolean;
};

const INITIAL_CHECKLIST: ChecklistItem[] = [
  { label: 'Proof of income (SA302 / tax returns)', done: true },
  { label: 'Bank statements (3 months)', done: true },
  { label: 'ID verification', done: false },
  { label: 'Proof of address', done: false },
  { label: 'Business accounts (2 years)', done: true },
  { label: 'Credit report review', done: false },
];

const MOCK_LENDERS: LenderMatch[] = [
  { name: 'Halifax', rate: '4.29%', max_ltv: '90%' },
  { name: 'Nationwide', rate: '4.49%', max_ltv: '85%' },
  { name: 'Barclays', rate: '4.59%', max_ltv: '90%' },
];

const MEDAL = ['🏆', '🥈', '🥉'];

function AnimatedPressable({
  onPress,
  style,
  children,
  disabled,
}: {
  onPress: () => void;
  style?: any;
  children: React.ReactNode;
  disabled?: boolean;
}) {
  const scale = useRef(new Animated.Value(1)).current;

  return (
    <Animated.View style={[{ transform: [{ scale }] }, style]}>
      <TouchableOpacity
        onPress={onPress}
        onPressIn={() =>
          Animated.spring(scale, { toValue: 0.96, useNativeDriver: true }).start()
        }
        onPressOut={() =>
          Animated.spring(scale, { toValue: 1, friction: 3, useNativeDriver: true }).start()
        }
        activeOpacity={0.9}
        disabled={disabled}
      >
        {children}
      </TouchableOpacity>
    </Animated.View>
  );
}

export default function MortgageScreen() {
  const [readinessScore, setReadinessScore] = useState(62);
  const [readinessLabel, setReadinessLabel] = useState('Almost Ready');
  const [readinessLoading, setReadinessLoading] = useState(false);

  const [income, setIncome] = useState('');
  const [affordabilityResults, setAffordabilityResults] = useState<
    Array<{ label: string; amount: number }> | null
  >(null);
  const [affordLoading, setAffordLoading] = useState(false);
  const [affordEmployment, setAffordEmployment] = useState<'employed' | 'self_employed'>('self_employed');
  const [affordCredit, setAffordCredit] = useState<'clean' | 'minor' | 'adverse'>('clean');
  const [affordPropertyType, setAffordPropertyType] = useState<
    'standard_residential' | 'buy_to_let' | 'leasehold_flat'
  >('standard_residential');
  const [affordCcjPast6y, setAffordCcjPast6y] = useState(false);
  const [affordDeposit, setAffordDeposit] = useState('');
  const [affordApiMaxLoan, setAffordApiMaxLoan] = useState<number | null>(null);
  const [affordApiMonthly, setAffordApiMonthly] = useState<number | null>(null);

  const [propertyValue, setPropertyValue] = useState('');
  const [stampDuty, setStampDuty] = useState<number | null>(null);
  const [stampLoading, setStampLoading] = useState(false);

  const [checklist, setChecklist] = useState<ChecklistItem[]>(INITIAL_CHECKLIST);

  const [lenders, setLenders] = useState<LenderMatch[]>([]);
  const [lenderLoading, setLenderLoading] = useState(false);

  const fetchReadiness = useCallback(async () => {
    setReadinessLoading(true);
    try {
      const res = await apiCall('/analytics/mortgage/readiness', {
        method: 'POST',
        body: JSON.stringify({
          mortgage_type: 'home_mover',
          employment_profile: 'sole_trader',
          lender_profile: 'high_street_mainstream',
          include_adverse_credit_pack: false,
          max_documents_scan: 200,
        }),
      });
      if (res.ok) {
        const data = (await res.json()) as {
          overall_completion_percent?: number;
          readiness_status?: string;
        };
        if (typeof data.overall_completion_percent === 'number') {
          setReadinessScore(Math.round(data.overall_completion_percent));
        }
        const st = data.readiness_status;
        if (st === 'not_ready') setReadinessLabel('Not ready');
        else if (st === 'almost_ready') setReadinessLabel('Almost ready');
        else if (st === 'ready_for_broker_review') setReadinessLabel('Ready for broker review');
      }
    } catch {
      // keep defaults
    } finally {
      setReadinessLoading(false);
    }
  }, []);

  const calculateAffordability = useCallback(async () => {
    if (!income) {
      Alert.alert('Error', 'Enter your annual income');
      return;
    }
    setAffordLoading(true);
    setAffordApiMaxLoan(null);
    setAffordApiMonthly(null);
    const incomeNum = parseFloat(income.replace(/,/g, ''));
    const priceRaw = propertyValue.trim() ? parseFloat(propertyValue.replace(/,/g, '')) : NaN;
    const depRaw = affordDeposit.trim() ? parseFloat(affordDeposit.replace(/,/g, '')) : NaN;
    const body = {
      annual_income_gbp: incomeNum,
      employment: affordEmployment,
      property_price_gbp: !Number.isNaN(priceRaw) && priceRaw > 0 ? priceRaw : null,
      deposit_gbp: !Number.isNaN(depRaw) && depRaw >= 0 ? depRaw : null,
      annual_interest_rate_pct: 5,
      term_years: 30,
      first_time_buyer: false,
      additional_property: false,
      credit_band: affordCredit,
      years_trading: null,
      property_type: affordPropertyType,
      ccj_in_past_6y: affordCcjPast6y,
    };
    try {
      const res = await apiCall('/analytics/mortgage/affordability', {
        method: 'POST',
        body: JSON.stringify(body),
      });
      const data = (await res.json()) as {
        lender_scenarios?: Array<{ label: string; max_loan_from_income_gbp: number; illustrative_fit_score: number }>;
        max_loan_from_income_gbp?: number;
        monthly_payment_gbp?: number;
      };
      if (res.ok && Array.isArray(data.lender_scenarios)) {
        setAffordApiMaxLoan(typeof data.max_loan_from_income_gbp === 'number' ? data.max_loan_from_income_gbp : null);
        setAffordApiMonthly(typeof data.monthly_payment_gbp === 'number' ? data.monthly_payment_gbp : null);
        setAffordabilityResults(
          data.lender_scenarios.slice(0, 6).map((s) => ({
            label: `${s.label} (fit ${s.illustrative_fit_score})`,
            amount: s.max_loan_from_income_gbp,
          }))
        );
      } else {
        throw new Error('affordability failed');
      }
    } catch {
      setAffordabilityResults([
        { label: 'Conservative (3x)', amount: incomeNum * 3 },
        { label: 'Standard (4x)', amount: incomeNum * 4 },
        { label: 'Stretch (4.5x)', amount: incomeNum * 4.5 },
      ]);
    } finally {
      setAffordLoading(false);
    }
  }, [
    income,
    propertyValue,
    affordDeposit,
    affordEmployment,
    affordCredit,
    affordPropertyType,
    affordCcjPast6y,
  ]);

  const calculateStampDuty = useCallback(async () => {
    if (!propertyValue) {
      Alert.alert('Error', 'Enter the property value');
      return;
    }
    setStampLoading(true);
    try {
      const val = parseFloat(propertyValue);
      const q = new URLSearchParams({
        property_value: String(val),
        is_first_time_buyer: 'false',
        is_additional_property: 'false',
      });
      const res = await apiCall(`/analytics/mortgage/stamp-duty?${q.toString()}`, {
        method: 'POST',
      });
      if (res.ok) {
        const data = await res.json();
        setStampDuty(data.stamp_duty ?? computeStampDuty(val));
      } else {
        setStampDuty(computeStampDuty(val));
      }
    } catch {
      setStampDuty(computeStampDuty(parseFloat(propertyValue)));
    } finally {
      setStampLoading(false);
    }
  }, [propertyValue]);

  const matchLenders = useCallback(async () => {
    setLenderLoading(true);
    const inc = parseFloat(income.replace(/,/g, '')) || 55_000;
    const pv = parseFloat(propertyValue.replace(/,/g, '')) || 300_000;
    const dep = Math.min(Math.max(Math.round(pv * 0.1), 0), pv * 0.95);
    const q = new URLSearchParams({
      annual_income: String(inc),
      deposit_available: String(dep),
      property_value: String(pv),
      trading_years: '2',
      has_sa302: 'true',
      has_adverse_credit: 'false',
      interest_rate: '5',
      mortgage_term_years: '25',
    });
    try {
      const res = await apiCall(`/analytics/mortgage/lender-match?${q.toString()}`, {
        method: 'POST',
      });
      if (res.ok) {
        const data = (await res.json()) as Array<{
          name: string;
          income_multiple: number;
          max_ltv: number;
        }>;
        if (Array.isArray(data) && data.length > 0) {
          setLenders(
            data.slice(0, 8).map((row) => ({
              name: row.name,
              rate: `${row.income_multiple}x income`,
              max_ltv: `${row.max_ltv}%`,
            }))
          );
        } else {
          setLenders(MOCK_LENDERS);
        }
      } else {
        setLenders(MOCK_LENDERS);
      }
    } catch {
      setLenders(MOCK_LENDERS);
    } finally {
      setLenderLoading(false);
    }
  }, [income, propertyValue]);

  const toggleChecklist = (index: number) => {
    setChecklist((prev) =>
      prev.map((item, i) => (i === index ? { ...item, done: !item.done } : item))
    );
  };

  const scoreColor =
    readinessScore >= 80 ? colors.income : readinessScore >= 50 ? colors.warning : colors.expense;
  const completedChecklist = checklist.filter((c) => c.done).length;

  const incomeNumHero = income ? parseFloat(income.replace(/,/g, '')) : NaN;
  const maxBorrow =
    affordApiMaxLoan != null && !Number.isNaN(affordApiMaxLoan)
      ? affordApiMaxLoan
      : !Number.isNaN(incomeNumHero) && incomeNumHero > 0
        ? incomeNumHero * 4.5
        : null;
  const monthlyPayment =
    affordApiMonthly != null && !Number.isNaN(affordApiMonthly)
      ? Math.round(affordApiMonthly)
      : maxBorrow
        ? Math.round((maxBorrow * 0.058) / 12)
        : null;

  return (
    <SafeAreaView style={styles.container} edges={['top']}>
      <ScrollView
        contentContainerStyle={styles.scroll}
        showsVerticalScrollIndicator={false}
      >
        <Text style={styles.title}>🏠 Mortgage Readiness</Text>

        {/* Score Circle */}
        <View style={styles.scoreCard}>
          <View style={[styles.scoreCircleOuter, { borderColor: scoreColor }]}>
            <View style={styles.scoreCircleInner}>
              {readinessLoading ? (
                <ActivityIndicator size="large" color={scoreColor} />
              ) : (
                <>
                  <Text style={[styles.scoreValue, { color: scoreColor }]}>
                    {readinessScore}%
                  </Text>
                  <Text style={styles.scoreWord}>Score</Text>
                </>
              )}
            </View>
          </View>
          <Text style={styles.scoreLabel}>{readinessLabel}</Text>
          <AnimatedPressable onPress={fetchReadiness}>
            <View style={styles.refreshPill}>
              <Text style={styles.refreshPillText}>↻ Refresh</Text>
            </View>
          </AnimatedPressable>
        </View>

        {/* Affordability */}
        <View style={styles.sectionHeader}>
          <Text style={styles.sectionTitle}>Affordability</Text>
        </View>
        <View style={styles.card}>
          {maxBorrow && (
            <View style={styles.affordHero}>
              <Text style={styles.affordLabel}>You could borrow up to</Text>
              <Text style={styles.affordAmount}>
                £{maxBorrow.toLocaleString('en-GB', { maximumFractionDigits: 0 })}
              </Text>
              {monthlyPayment && (
                <Text style={styles.affordMonthly}>
                  Monthly: ~£{monthlyPayment.toLocaleString('en-GB')}
                </Text>
              )}
            </View>
          )}
          <Text style={styles.inputLabel}>Annual Income (£)</Text>
          <TextInput
            style={styles.input}
            value={income}
            onChangeText={setIncome}
            placeholder="e.g. 55000"
            placeholderTextColor={colors.textMuted}
            keyboardType="numeric"
          />
          <Text style={styles.inputLabel}>Employment (for multiple)</Text>
          <View style={styles.chipRow}>
            {(
              [
                { v: 'self_employed' as const, t: 'Self-employed' },
                { v: 'employed' as const, t: 'Employed' },
              ]
            ).map(({ v, t }) => (
              <TouchableOpacity
                key={v}
                style={[styles.chip, affordEmployment === v && styles.chipOn]}
                onPress={() => setAffordEmployment(v)}
              >
                <Text style={[styles.chipText, affordEmployment === v && styles.chipTextOn]}>{t}</Text>
              </TouchableOpacity>
            ))}
          </View>
          <Text style={styles.inputLabel}>Illustrative credit</Text>
          <View style={styles.chipRow}>
            {(
              [
                { v: 'clean' as const, t: 'Clean' },
                { v: 'minor' as const, t: 'Minor' },
                { v: 'adverse' as const, t: 'Adverse' },
              ]
            ).map(({ v, t }) => (
              <TouchableOpacity
                key={v}
                style={[styles.chip, affordCredit === v && styles.chipOn]}
                onPress={() => setAffordCredit(v)}
              >
                <Text style={[styles.chipText, affordCredit === v && styles.chipTextOn]}>{t}</Text>
              </TouchableOpacity>
            ))}
          </View>
          <Text style={styles.inputLabel}>Property type (fit model)</Text>
          <View style={styles.chipWrap}>
            {(
              [
                { v: 'standard_residential' as const, t: 'House / res.' },
                { v: 'leasehold_flat' as const, t: 'Leasehold flat' },
                { v: 'buy_to_let' as const, t: 'BTL' },
              ]
            ).map(({ v, t }) => (
              <TouchableOpacity
                key={v}
                style={[styles.chip, affordPropertyType === v && styles.chipOn]}
                onPress={() => setAffordPropertyType(v)}
              >
                <Text style={[styles.chipText, affordPropertyType === v && styles.chipTextOn]}>{t}</Text>
              </TouchableOpacity>
            ))}
          </View>
          <View style={styles.switchRow}>
            <Text style={styles.switchLabel}>CCJ in past 6 years (self-reported)</Text>
            <Switch
              value={affordCcjPast6y}
              onValueChange={setAffordCcjPast6y}
              trackColor={{ false: colors.border, true: colors.accentTeal }}
            />
          </View>
          <Text style={styles.inputLabel}>Deposit (£, optional)</Text>
          <TextInput
            style={styles.input}
            value={affordDeposit}
            onChangeText={setAffordDeposit}
            placeholder="For LTV with property value below"
            placeholderTextColor={colors.textMuted}
            keyboardType="numeric"
          />
          <Text style={styles.fieldHint}>
            Optional: set Property value in Stamp Duty section for price-based LTV and payments.
          </Text>
          {affordabilityResults && (
            <View style={styles.scenarioList}>
              {affordabilityResults.map((s, i) => (
                <View key={i} style={styles.scenarioRow}>
                  <Text style={styles.scenarioLabel}>{s.label}</Text>
                  <Text style={styles.scenarioAmount}>
                    £{s.amount.toLocaleString('en-GB', { maximumFractionDigits: 0 })}
                  </Text>
                </View>
              ))}
            </View>
          )}
          <AnimatedPressable onPress={calculateAffordability} disabled={affordLoading}>
            <LinearGradient
              colors={[colors.gradientStart, colors.gradientEnd]}
              start={{ x: 0, y: 0 }}
              end={{ x: 1, y: 0 }}
              style={styles.gradientButton}
            >
              {affordLoading ? (
                <ActivityIndicator color={colors.text} />
              ) : (
                <Text style={styles.gradientButtonText}>Calculate →</Text>
              )}
            </LinearGradient>
          </AnimatedPressable>
        </View>

        {/* Best Lenders */}
        <View style={styles.sectionHeader}>
          <Text style={styles.sectionTitle}>Best Lenders for You</Text>
        </View>
        {lenders.length > 0 ? (
          <View style={styles.card}>
            {lenders.map((l, i) => (
              <View
                key={i}
                style={[
                  styles.lenderRow,
                  i === lenders.length - 1 && { borderBottomWidth: 0 },
                ]}
              >
                <View style={styles.lenderLeft}>
                  <Text style={styles.lenderMedal}>{MEDAL[i] || '🏅'}</Text>
                  <Text style={styles.lenderName}>{l.name}</Text>
                </View>
                <View style={styles.lenderRight}>
                  <Text style={styles.lenderRate}>{l.rate}</Text>
                  <Text style={styles.lenderLtv}>LTV {l.max_ltv}</Text>
                </View>
              </View>
            ))}
          </View>
        ) : (
          <AnimatedPressable onPress={matchLenders} disabled={lenderLoading}>
            <LinearGradient
              colors={[colors.gradientStart, colors.gradientEnd]}
              start={{ x: 0, y: 0 }}
              end={{ x: 1, y: 0 }}
              style={[styles.gradientButton, { marginHorizontal: spacing.lg }]}
            >
              {lenderLoading ? (
                <ActivityIndicator color={colors.text} />
              ) : (
                <Text style={styles.gradientButtonText}>Match Me With Lenders</Text>
              )}
            </LinearGradient>
          </AnimatedPressable>
        )}

        {/* Stamp Duty */}
        <View style={styles.sectionHeader}>
          <Text style={styles.sectionTitle}>Stamp Duty</Text>
        </View>
        <View style={styles.card}>
          <Text style={styles.inputLabel}>Property Value (£)</Text>
          <TextInput
            style={styles.input}
            value={propertyValue}
            onChangeText={setPropertyValue}
            placeholder="e.g. 350000"
            placeholderTextColor={colors.textMuted}
            keyboardType="numeric"
          />
          {stampDuty != null && (
            <View style={styles.stampResult}>
              <Text style={styles.stampLabel}>Stamp Duty</Text>
              <Text style={styles.stampValue}>
                £{stampDuty.toLocaleString('en-GB', { maximumFractionDigits: 0 })}
              </Text>
              {stampDuty === 0 && (
                <Text style={styles.stampNote}>First-time buyer relief may apply</Text>
              )}
            </View>
          )}
          <AnimatedPressable onPress={calculateStampDuty} disabled={stampLoading}>
            <LinearGradient
              colors={[colors.gradientStart, colors.gradientEnd]}
              start={{ x: 0, y: 0 }}
              end={{ x: 1, y: 0 }}
              style={styles.gradientButton}
            >
              {stampLoading ? (
                <ActivityIndicator color={colors.text} />
              ) : (
                <Text style={styles.gradientButtonText}>Calculate</Text>
              )}
            </LinearGradient>
          </AnimatedPressable>
        </View>

        {/* Document Checklist */}
        <View style={styles.sectionHeader}>
          <Text style={styles.sectionTitle}>
            Document Checklist ({completedChecklist}/{checklist.length})
          </Text>
        </View>
        <View style={styles.card}>
          <View style={styles.checklistProgress}>
            <View
              style={[
                styles.checklistProgressFill,
                { width: `${(completedChecklist / checklist.length) * 100}%` },
              ]}
            />
          </View>
          {checklist.map((item, i) => (
            <TouchableOpacity
              key={i}
              style={styles.checklistRow}
              onPress={() => toggleChecklist(i)}
              activeOpacity={0.7}
            >
              <View
                style={[
                  styles.checkBox,
                  item.done && styles.checkBoxDone,
                ]}
              >
                {item.done && <Text style={styles.checkMark}>✓</Text>}
              </View>
              <Text style={[styles.checkLabel, item.done && styles.checkLabelDone]}>
                {item.label}
              </Text>
            </TouchableOpacity>
          ))}
        </View>

        {/* Mortgage Pack CTA */}
        <AnimatedPressable onPress={() => Alert.alert('Coming Soon', 'Mortgage pack PDF generation is coming soon')}>
          <View style={styles.packButton}>
            <Text style={styles.packButtonEmoji}>📋</Text>
            <Text style={styles.packButtonText}>Get Mortgage Pack PDF</Text>
          </View>
        </AnimatedPressable>
      </ScrollView>
    </SafeAreaView>
  );
}

function computeStampDuty(value: number): number {
  if (value <= 250_000) return 0;
  let duty = 0;
  if (value > 250_000) duty += Math.min(value - 250_000, 675_000) * 0.05;
  if (value > 925_000) duty += Math.min(value - 925_000, 575_000) * 0.1;
  if (value > 1_500_000) duty += (value - 1_500_000) * 0.12;
  return Math.round(duty);
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.bg,
  },
  scroll: {
    paddingBottom: spacing.xxl,
  },
  title: {
    fontSize: fontSize.xl,
    fontWeight: '800',
    color: colors.text,
    paddingHorizontal: spacing.lg,
    paddingTop: spacing.lg,
    marginBottom: spacing.md,
  },
  scoreCard: {
    marginHorizontal: spacing.lg,
    backgroundColor: colors.bgCard,
    borderRadius: borderRadius.xl,
    padding: spacing.xl,
    alignItems: 'center',
    borderWidth: 1,
    borderColor: colors.border,
    marginBottom: spacing.sm,
  },
  scoreCircleOuter: {
    width: 140,
    height: 140,
    borderRadius: 70,
    borderWidth: 6,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: spacing.md,
  },
  scoreCircleInner: {
    alignItems: 'center',
  },
  scoreValue: {
    fontSize: fontSize.hero,
    fontWeight: '800',
  },
  scoreWord: {
    fontSize: fontSize.xs,
    color: colors.textMuted,
    textTransform: 'uppercase',
    letterSpacing: 1,
  },
  scoreLabel: {
    fontSize: fontSize.lg,
    fontWeight: '600',
    color: colors.text,
    marginBottom: spacing.md,
  },
  refreshPill: {
    backgroundColor: colors.bgElevated,
    borderRadius: borderRadius.full,
    paddingHorizontal: spacing.lg,
    paddingVertical: spacing.sm,
    borderWidth: 1,
    borderColor: colors.borderLight,
  },
  refreshPillText: {
    fontSize: fontSize.sm,
    color: colors.accentTeal,
    fontWeight: '600',
  },
  sectionHeader: {
    paddingHorizontal: spacing.lg,
    paddingTop: spacing.lg,
    paddingBottom: spacing.sm,
  },
  sectionTitle: {
    fontSize: fontSize.sm,
    fontWeight: '700',
    color: colors.textMuted,
    textTransform: 'uppercase',
    letterSpacing: 1,
  },
  card: {
    marginHorizontal: spacing.lg,
    backgroundColor: colors.bgCard,
    borderRadius: borderRadius.xl,
    padding: spacing.lg,
    borderWidth: 1,
    borderColor: colors.border,
  },
  affordHero: {
    alignItems: 'center',
    paddingBottom: spacing.md,
    marginBottom: spacing.md,
    borderBottomWidth: 1,
    borderBottomColor: colors.border,
  },
  affordLabel: {
    fontSize: fontSize.sm,
    color: colors.textMuted,
  },
  affordAmount: {
    fontSize: fontSize.xxl,
    fontWeight: '800',
    color: colors.text,
    marginTop: spacing.xs,
  },
  affordMonthly: {
    fontSize: fontSize.sm,
    color: colors.textSecondary,
    marginTop: spacing.xs,
  },
  inputLabel: {
    fontSize: fontSize.xs,
    color: colors.textMuted,
    marginBottom: spacing.xs,
    textTransform: 'uppercase',
    letterSpacing: 0.5,
  },
  chipRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 8,
    marginBottom: spacing.md,
  },
  chipWrap: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 8,
    marginBottom: spacing.md,
  },
  chip: {
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm,
    borderRadius: borderRadius.full,
    borderWidth: 1,
    borderColor: colors.border,
    backgroundColor: colors.bgElevated,
  },
  chipOn: {
    borderColor: colors.accentTeal,
    backgroundColor: 'rgba(13,148,136,0.12)',
  },
  chipText: {
    fontSize: fontSize.sm,
    color: colors.textMuted,
    fontWeight: '600',
  },
  chipTextOn: {
    color: colors.accentTeal,
  },
  switchRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: spacing.md,
    paddingVertical: spacing.xs,
  },
  switchLabel: {
    flex: 1,
    fontSize: fontSize.sm,
    color: colors.text,
    paddingRight: spacing.md,
  },
  fieldHint: {
    fontSize: fontSize.xs,
    color: colors.textMuted,
    marginBottom: spacing.md,
  },
  input: {
    backgroundColor: colors.bgElevated,
    borderRadius: borderRadius.sm,
    padding: spacing.md,
    color: colors.text,
    fontSize: fontSize.md,
    borderWidth: 1,
    borderColor: colors.border,
  },
  scenarioList: {
    marginTop: spacing.md,
    backgroundColor: colors.bgElevated,
    borderRadius: borderRadius.md,
    overflow: 'hidden',
  },
  scenarioRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    padding: spacing.md,
    borderBottomWidth: 1,
    borderBottomColor: colors.border,
  },
  scenarioLabel: {
    fontSize: fontSize.sm,
    color: colors.textMuted,
  },
  scenarioAmount: {
    fontSize: fontSize.sm,
    color: colors.text,
    fontWeight: '700',
  },
  gradientButton: {
    borderRadius: borderRadius.md,
    padding: spacing.md,
    alignItems: 'center',
    marginTop: spacing.md,
  },
  gradientButtonText: {
    color: colors.text,
    fontSize: fontSize.md,
    fontWeight: '700',
  },
  lenderRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: spacing.md,
    borderBottomWidth: 1,
    borderBottomColor: colors.border,
  },
  lenderLeft: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.sm,
  },
  lenderMedal: {
    fontSize: 20,
  },
  lenderName: {
    fontSize: fontSize.md,
    color: colors.text,
    fontWeight: '700',
  },
  lenderRight: {
    alignItems: 'flex-end',
  },
  lenderRate: {
    fontSize: fontSize.md,
    color: colors.accentTeal,
    fontWeight: '700',
  },
  lenderLtv: {
    fontSize: fontSize.xs,
    color: colors.textMuted,
    marginTop: 2,
  },
  stampResult: {
    backgroundColor: colors.incomeBg,
    borderRadius: borderRadius.md,
    padding: spacing.md,
    marginTop: spacing.md,
    alignItems: 'center',
  },
  stampLabel: {
    fontSize: fontSize.xs,
    color: colors.textMuted,
    textTransform: 'uppercase',
  },
  stampValue: {
    fontSize: fontSize.xxl,
    fontWeight: '800',
    color: colors.income,
    marginTop: spacing.xs,
  },
  stampNote: {
    fontSize: fontSize.xs,
    color: colors.textMuted,
    marginTop: spacing.xs,
  },
  checklistProgress: {
    height: 4,
    backgroundColor: colors.bgElevated,
    borderRadius: 2,
    overflow: 'hidden',
    marginBottom: spacing.md,
  },
  checklistProgressFill: {
    height: '100%',
    backgroundColor: colors.accentTeal,
    borderRadius: 2,
  },
  checklistRow: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: spacing.sm,
    gap: spacing.sm,
  },
  checkBox: {
    width: 22,
    height: 22,
    borderRadius: 6,
    borderWidth: 2,
    borderColor: colors.borderLight,
    alignItems: 'center',
    justifyContent: 'center',
  },
  checkBoxDone: {
    backgroundColor: colors.accentTeal,
    borderColor: colors.accentTeal,
  },
  checkMark: {
    color: colors.textInverse,
    fontSize: 12,
    fontWeight: '700',
  },
  checkLabel: {
    fontSize: fontSize.sm,
    color: colors.text,
    flex: 1,
  },
  checkLabelDone: {
    color: colors.textMuted,
    textDecorationLine: 'line-through',
  },
  packButton: {
    marginHorizontal: spacing.lg,
    marginTop: spacing.lg,
    backgroundColor: colors.bgCard,
    borderRadius: borderRadius.xl,
    padding: spacing.lg,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: spacing.sm,
    borderWidth: 1,
    borderColor: colors.accentTeal,
  },
  packButtonEmoji: {
    fontSize: 20,
  },
  packButtonText: {
    fontSize: fontSize.md,
    color: colors.accentTeal,
    fontWeight: '700',
  },
});
