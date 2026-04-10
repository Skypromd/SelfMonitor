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
        body: JSON.stringify({}),
      });
      if (res.ok) {
        const data = await res.json();
        if (data.score != null) setReadinessScore(data.score);
        if (data.label) setReadinessLabel(data.label);
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
    try {
      const incomeNum = parseFloat(income);
      const res = await apiCall('/mortgage/affordability', {
        method: 'POST',
        body: JSON.stringify({ income: incomeNum }),
      });
      if (res.ok) {
        const data = await res.json();
        setAffordabilityResults(data.scenarios || [
          { label: 'Conservative (3x)', amount: incomeNum * 3 },
          { label: 'Standard (4x)', amount: incomeNum * 4 },
          { label: 'Stretch (4.5x)', amount: incomeNum * 4.5 },
        ]);
      } else {
        const incomeNum2 = parseFloat(income);
        setAffordabilityResults([
          { label: 'Conservative (3x)', amount: incomeNum2 * 3 },
          { label: 'Standard (4x)', amount: incomeNum2 * 4 },
          { label: 'Stretch (4.5x)', amount: incomeNum2 * 4.5 },
        ]);
      }
    } catch {
      const incomeNum = parseFloat(income);
      setAffordabilityResults([
        { label: 'Conservative (3x)', amount: incomeNum * 3 },
        { label: 'Standard (4x)', amount: incomeNum * 4 },
        { label: 'Stretch (4.5x)', amount: incomeNum * 4.5 },
      ]);
    } finally {
      setAffordLoading(false);
    }
  }, [income]);

  const calculateStampDuty = useCallback(async () => {
    if (!propertyValue) {
      Alert.alert('Error', 'Enter the property value');
      return;
    }
    setStampLoading(true);
    try {
      const val = parseFloat(propertyValue);
      const res = await apiCall('/mortgage/stamp-duty', {
        method: 'POST',
        body: JSON.stringify({ property_value: val }),
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
    try {
      const res = await apiCall('/mortgage/lender-match', {
        method: 'POST',
        body: JSON.stringify({}),
      });
      if (res.ok) {
        const data = await res.json();
        setLenders(data.lenders || MOCK_LENDERS);
      } else {
        setLenders(MOCK_LENDERS);
      }
    } catch {
      setLenders(MOCK_LENDERS);
    } finally {
      setLenderLoading(false);
    }
  }, []);

  const toggleChecklist = (index: number) => {
    setChecklist((prev) =>
      prev.map((item, i) => (i === index ? { ...item, done: !item.done } : item))
    );
  };

  const scoreColor =
    readinessScore >= 80 ? colors.income : readinessScore >= 50 ? colors.warning : colors.expense;
  const completedChecklist = checklist.filter((c) => c.done).length;

  const maxBorrow = income ? parseFloat(income) * 4.5 : null;
  const monthlyPayment = maxBorrow ? Math.round((maxBorrow * 0.058) / 12) : null;

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
