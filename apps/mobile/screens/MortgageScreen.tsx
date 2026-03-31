import React, { useState, useCallback } from 'react';
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  ActivityIndicator,
  Alert,
  TextInput,
  ScrollView,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { colors, spacing, fontSize } from '../theme';
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
    readinessScore >= 80 ? colors.success : readinessScore >= 50 ? colors.accentGold : colors.error;

  return (
    <SafeAreaView style={styles.container} edges={['top']}>
      <ScrollView contentContainerStyle={styles.scroll}>
        <Text style={styles.title}>Mortgage Readiness</Text>

        <View style={styles.scoreCard}>
          <View style={[styles.scoreCircle, { borderColor: scoreColor }]}>
            {readinessLoading ? (
              <ActivityIndicator size="large" color={scoreColor} />
            ) : (
              <Text style={[styles.scoreText, { color: scoreColor }]}>
                {readinessScore}%
              </Text>
            )}
          </View>
          <Text style={styles.scoreLabel}>
            Your mortgage readiness: {readinessScore}% — {readinessLabel}
          </Text>
          <TouchableOpacity style={styles.refreshButton} onPress={fetchReadiness}>
            <Text style={styles.refreshButtonText}>Refresh Score</Text>
          </TouchableOpacity>
        </View>

        <View style={styles.card}>
          <Text style={styles.cardTitle}>Affordability Calculator</Text>
          <Text style={styles.label}>Annual Income (£)</Text>
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
          <TouchableOpacity
            style={styles.button}
            onPress={calculateAffordability}
            disabled={affordLoading}
          >
            {affordLoading ? (
              <ActivityIndicator color={colors.text} />
            ) : (
              <Text style={styles.buttonText}>Calculate</Text>
            )}
          </TouchableOpacity>
        </View>

        <View style={styles.card}>
          <Text style={styles.cardTitle}>Stamp Duty Calculator</Text>
          <Text style={styles.label}>Property Value (£)</Text>
          <TextInput
            style={styles.input}
            value={propertyValue}
            onChangeText={setPropertyValue}
            placeholder="e.g. 350000"
            placeholderTextColor={colors.textMuted}
            keyboardType="numeric"
          />
          {stampDuty != null && (
            <View style={styles.resultBox}>
              <Text style={styles.resultText}>
                Stamp Duty: £{stampDuty.toLocaleString('en-GB', { maximumFractionDigits: 0 })}
              </Text>
            </View>
          )}
          <TouchableOpacity
            style={styles.button}
            onPress={calculateStampDuty}
            disabled={stampLoading}
          >
            {stampLoading ? (
              <ActivityIndicator color={colors.text} />
            ) : (
              <Text style={styles.buttonText}>Calculate</Text>
            )}
          </TouchableOpacity>
        </View>

        <View style={styles.card}>
          <Text style={styles.cardTitle}>Document Checklist</Text>
          {checklist.map((item, i) => (
            <TouchableOpacity
              key={i}
              style={styles.checklistRow}
              onPress={() => toggleChecklist(i)}
            >
              <Text style={styles.checkIcon}>{item.done ? '✅' : '⬜'}</Text>
              <Text style={[styles.checkLabel, item.done && styles.checkLabelDone]}>
                {item.label}
              </Text>
            </TouchableOpacity>
          ))}
        </View>

        <TouchableOpacity
          style={styles.matchButton}
          onPress={matchLenders}
          disabled={lenderLoading}
        >
          {lenderLoading ? (
            <ActivityIndicator color={colors.text} />
          ) : (
            <Text style={styles.matchButtonText}>Match Me With Lenders</Text>
          )}
        </TouchableOpacity>

        {lenders.length > 0 && (
          <View style={styles.card}>
            <Text style={styles.cardTitle}>Matched Lenders</Text>
            {lenders.map((l, i) => (
              <View key={i} style={styles.lenderRow}>
                <Text style={styles.lenderName}>{l.name}</Text>
                <View style={styles.lenderDetails}>
                  <Text style={styles.lenderRate}>{l.rate}</Text>
                  <Text style={styles.lenderLtv}>LTV: {l.max_ltv}</Text>
                </View>
              </View>
            ))}
          </View>
        )}
      </ScrollView>
    </SafeAreaView>
  );
}

const MOCK_LENDERS: LenderMatch[] = [
  { name: 'Halifax', rate: '4.29%', max_ltv: '90%' },
  { name: 'Nationwide', rate: '4.49%', max_ltv: '85%' },
  { name: 'Barclays', rate: '4.59%', max_ltv: '90%' },
];

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
    padding: spacing.md,
    paddingBottom: spacing.xl,
  },
  title: {
    fontSize: fontSize.xl,
    fontWeight: '700',
    color: colors.text,
    marginBottom: spacing.lg,
  },
  scoreCard: {
    backgroundColor: colors.bgElevated,
    borderRadius: 12,
    padding: spacing.lg,
    alignItems: 'center',
    marginBottom: spacing.md,
    borderWidth: 1,
    borderColor: colors.border,
  },
  scoreCircle: {
    width: 120,
    height: 120,
    borderRadius: 60,
    borderWidth: 6,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: spacing.md,
  },
  scoreText: {
    fontSize: fontSize.xxl,
    fontWeight: '700',
  },
  scoreLabel: {
    fontSize: fontSize.sm,
    color: colors.text,
    textAlign: 'center',
    marginBottom: spacing.md,
  },
  refreshButton: {
    backgroundColor: colors.bgCard,
    borderRadius: 8,
    paddingHorizontal: spacing.lg,
    paddingVertical: spacing.sm,
  },
  refreshButtonText: {
    fontSize: fontSize.sm,
    color: colors.accentTealLight,
    fontWeight: '600',
  },
  card: {
    backgroundColor: colors.bgElevated,
    borderRadius: 12,
    padding: spacing.lg,
    marginBottom: spacing.md,
    borderWidth: 1,
    borderColor: colors.border,
  },
  cardTitle: {
    fontSize: fontSize.lg,
    fontWeight: '600',
    color: colors.text,
    marginBottom: spacing.md,
  },
  label: {
    fontSize: fontSize.sm,
    color: colors.textMuted,
    marginBottom: spacing.xs,
  },
  input: {
    backgroundColor: colors.bgCard,
    borderRadius: 8,
    padding: spacing.md,
    color: colors.text,
    fontSize: fontSize.md,
    borderWidth: 1,
    borderColor: colors.border,
  },
  scenarioList: {
    marginTop: spacing.md,
  },
  scenarioRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    paddingVertical: spacing.sm,
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
    fontWeight: '600',
  },
  resultBox: {
    backgroundColor: colors.successBg,
    borderRadius: 8,
    padding: spacing.md,
    marginTop: spacing.md,
  },
  resultText: {
    fontSize: fontSize.md,
    color: colors.success,
    fontWeight: '600',
  },
  button: {
    backgroundColor: colors.accentTeal,
    borderRadius: 8,
    padding: spacing.md,
    alignItems: 'center',
    marginTop: spacing.md,
  },
  buttonText: {
    color: colors.text,
    fontSize: fontSize.md,
    fontWeight: '600',
  },
  checklistRow: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: spacing.sm,
  },
  checkIcon: {
    fontSize: 18,
    marginRight: spacing.sm,
  },
  checkLabel: {
    fontSize: fontSize.sm,
    color: colors.text,
    flex: 1,
  },
  checkLabelDone: {
    color: colors.textMuted,
  },
  matchButton: {
    backgroundColor: colors.accentGold,
    borderRadius: 8,
    padding: spacing.md,
    alignItems: 'center',
    marginBottom: spacing.md,
  },
  matchButtonText: {
    color: colors.text,
    fontSize: fontSize.md,
    fontWeight: '600',
  },
  lenderRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: spacing.sm,
    borderBottomWidth: 1,
    borderBottomColor: colors.border,
  },
  lenderName: {
    fontSize: fontSize.md,
    color: colors.text,
    fontWeight: '600',
  },
  lenderDetails: {
    alignItems: 'flex-end',
  },
  lenderRate: {
    fontSize: fontSize.sm,
    color: colors.accentTealLight,
    fontWeight: '600',
  },
  lenderLtv: {
    fontSize: fontSize.xs,
    color: colors.textMuted,
  },
});
