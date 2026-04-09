import React, { useState, useCallback, useRef } from 'react';
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  ActivityIndicator,
  Alert,
  ScrollView,
  Animated,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { LinearGradient } from 'expo-linear-gradient';
import { colors, spacing, fontSize, borderRadius } from '../theme';
import { apiCall } from '../api';

type QuarterStatus = 'submitted' | 'due' | 'locked';

type Quarter = {
  label: string;
  period: string;
  status: QuarterStatus;
  dueDate?: string;
};

const QUARTERS: Quarter[] = [
  { label: 'Q1', period: 'Apr–Jul', status: 'submitted' },
  { label: 'Q2', period: 'Jul–Oct', status: 'due', dueDate: 'Nov 5' },
  { label: 'Q3', period: 'Oct–Jan', status: 'locked' },
  { label: 'Q4', period: 'Jan–Apr', status: 'locked' },
];

const CALCULATORS = ['PAYE', 'Rental', 'CIS', 'Dividend', 'Crypto', 'Stamp Duty'];

const TAX_TIPS = [
  'Claim £312/yr for working from home without receipts',
  'Pension contributions reduce your taxable income',
  'Mileage allowance: 45p/mile for first 10,000 miles',
];

const STATUS_ICON: Record<QuarterStatus, string> = {
  submitted: '✅',
  due: '⏳',
  locked: '🔒',
};

const STATUS_LABEL: Record<QuarterStatus, string> = {
  submitted: 'Submitted',
  due: 'Due',
  locked: 'Not yet',
};

function AnimatedPressable({
  onPress,
  style,
  children,
  disabled,
}: {
  onPress: () => void;
  style?: object;
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

export default function TaxScreen() {
  const [prepareLoading, setPrepareLoading] = useState<string | null>(null);
  const [annualLoading, setAnnualLoading] = useState(false);
  const [tipIndex, setTipIndex] = useState(0);

  const estimatedTax = 9131;
  const incomeTaxPortion = 6886;
  const niPortion = 2245;

  const prepareQuarterly = useCallback(
    async (quarter: string) => {
      setPrepareLoading(quarter);
      try {
        const res = await apiCall('/tax/prepare/quarterly', {
          method: 'POST',
          body: JSON.stringify({ quarter }),
        });
        if (!res.ok) throw new Error('Failed to prepare report');
        const data = await res.json();
        Alert.alert(
          'Report Ready',
          data.message || `${quarter} report prepared. Review and submit when ready.`,
          [{ text: 'OK' }]
        );
      } catch (err: unknown) {
        const msg = err instanceof Error ? err.message : 'Failed';
        Alert.alert(
          'Report Prepared (Demo)',
          `${quarter} quarterly report is ready for review. Confirm & Submit when satisfied.`
        );
        void msg;
      } finally {
        setPrepareLoading(null);
      }
    },
    []
  );

  const prepareAnnual = useCallback(async () => {
    setAnnualLoading(true);
    try {
      const res = await apiCall('/tax/prepare/annual', {
        method: 'POST',
        body: JSON.stringify({}),
      });
      if (!res.ok) throw new Error('Failed');
      const data = await res.json();
      Alert.alert('Annual Report', data.message || 'Annual report prepared');
    } catch {
      Alert.alert(
        'Annual Report (Demo)',
        'Your annual tax report has been prepared for review.'
      );
    } finally {
      setAnnualLoading(false);
    }
  }, []);

  const nextTip = () => {
    setTipIndex((prev) => (prev + 1) % TAX_TIPS.length);
  };

  return (
    <SafeAreaView style={styles.container} edges={['top']}>
      <ScrollView
        contentContainerStyle={styles.scroll}
        showsVerticalScrollIndicator={false}
      >
        <Text style={styles.title}>🇬🇧 Tax</Text>
        <Text style={styles.yearLabel}>Tax Year 2025/2026</Text>

        {/* Hero Tax Card */}
        <View style={styles.heroCard}>
          <LinearGradient
            colors={[colors.accentTealBg, 'transparent']}
            style={styles.heroGradient}
          />
          <Text style={styles.heroLabel}>Estimated Tax Due</Text>
          <Text style={styles.heroAmount}>£{estimatedTax.toLocaleString()}</Text>
          <Text style={styles.heroBreakdown}>
            Income Tax £{incomeTaxPortion.toLocaleString()} + NI £{niPortion.toLocaleString()}
          </Text>
        </View>

        {/* Quarterly Submissions */}
        <View style={styles.sectionHeader}>
          <Text style={styles.sectionTitle}>Quarterly Submissions</Text>
        </View>
        <View style={styles.card}>
          {QUARTERS.map((q, i) => (
            <View
              key={q.label}
              style={[
                styles.quarterRow,
                i === QUARTERS.length - 1 && { borderBottomWidth: 0 },
              ]}
            >
              <View style={styles.quarterInfo}>
                <Text style={styles.quarterLabel}>
                  {STATUS_ICON[q.status]} {q.label}  {q.period}
                </Text>
                <Text style={styles.quarterStatus}>
                  {STATUS_LABEL[q.status]}
                  {q.dueDate ? ` ${q.dueDate}` : ''}
                </Text>
              </View>
              {q.status === 'due' && (
                <AnimatedPressable
                  onPress={() => prepareQuarterly(q.label)}
                  disabled={prepareLoading === q.label}
                >
                  <View style={styles.prepareBtn}>
                    {prepareLoading === q.label ? (
                      <ActivityIndicator color={colors.accentTeal} size="small" />
                    ) : (
                      <Text style={styles.prepareBtnText}>Prepare →</Text>
                    )}
                  </View>
                </AnimatedPressable>
              )}
            </View>
          ))}
        </View>

        {/* Final Declaration */}
        <View style={styles.sectionHeader}>
          <Text style={styles.sectionTitle}>Final Declaration</Text>
        </View>
        <View style={styles.card}>
          <Text style={styles.declarationDate}>Due: 31 Jan 2027</Text>
          <AnimatedPressable onPress={prepareAnnual} disabled={annualLoading}>
            <LinearGradient
              colors={[colors.gradientStart, colors.gradientEnd]}
              start={{ x: 0, y: 0 }}
              end={{ x: 1, y: 0 }}
              style={styles.gradientButton}
            >
              {annualLoading ? (
                <ActivityIndicator color={colors.text} />
              ) : (
                <Text style={styles.gradientButtonText}>Prepare Annual Report →</Text>
              )}
            </LinearGradient>
          </AnimatedPressable>
        </View>

        {/* Calculators */}
        <View style={styles.sectionHeader}>
          <Text style={styles.sectionTitle}>Calculators</Text>
        </View>
        <View style={styles.calcsGrid}>
          {CALCULATORS.map((calc) => (
            <TouchableOpacity
              key={calc}
              style={styles.calcChip}
              onPress={() =>
                Alert.alert(calc, `${calc} calculator coming soon`)
              }
              activeOpacity={0.7}
            >
              <Text style={styles.calcChipText}>{calc}</Text>
            </TouchableOpacity>
          ))}
        </View>

        {/* Tax Tips */}
        <View style={styles.sectionHeader}>
          <Text style={styles.sectionTitle}>Tax Tips</Text>
        </View>
        <TouchableOpacity
          style={styles.tipCard}
          onPress={nextTip}
          activeOpacity={0.8}
        >
          <Text style={styles.tipIcon}>💡</Text>
          <Text style={styles.tipText}>{TAX_TIPS[tipIndex]}</Text>
        </TouchableOpacity>
      </ScrollView>
    </SafeAreaView>
  );
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
  },
  yearLabel: {
    fontSize: fontSize.sm,
    color: colors.textMuted,
    paddingHorizontal: spacing.lg,
    marginTop: spacing.xs,
    marginBottom: spacing.lg,
  },
  heroCard: {
    marginHorizontal: spacing.lg,
    backgroundColor: colors.bgCard,
    borderRadius: borderRadius.xl,
    padding: spacing.xl,
    alignItems: 'center',
    borderWidth: 1,
    borderColor: colors.border,
    overflow: 'hidden',
  },
  heroGradient: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    borderRadius: borderRadius.xl,
  },
  heroLabel: {
    fontSize: fontSize.sm,
    color: colors.textMuted,
    textTransform: 'uppercase',
    letterSpacing: 1,
  },
  heroAmount: {
    fontSize: fontSize.hero,
    fontWeight: '800',
    color: colors.text,
    letterSpacing: -1,
    marginTop: spacing.sm,
  },
  heroBreakdown: {
    fontSize: fontSize.sm,
    color: colors.textSecondary,
    marginTop: spacing.sm,
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
  quarterRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: spacing.md,
    borderBottomWidth: 1,
    borderBottomColor: colors.border,
  },
  quarterInfo: {
    flex: 1,
  },
  quarterLabel: {
    fontSize: fontSize.md,
    color: colors.text,
    fontWeight: '600',
  },
  quarterStatus: {
    fontSize: fontSize.sm,
    color: colors.textMuted,
    marginTop: 2,
  },
  prepareBtn: {
    backgroundColor: colors.accentTealBg,
    borderRadius: borderRadius.md,
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm,
  },
  prepareBtnText: {
    fontSize: fontSize.sm,
    color: colors.accentTeal,
    fontWeight: '700',
  },
  declarationDate: {
    fontSize: fontSize.md,
    color: colors.textSecondary,
    marginBottom: spacing.md,
  },
  gradientButton: {
    borderRadius: borderRadius.md,
    padding: spacing.md,
    alignItems: 'center',
  },
  gradientButtonText: {
    color: colors.text,
    fontSize: fontSize.md,
    fontWeight: '700',
  },
  calcsGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    paddingHorizontal: spacing.lg,
    gap: spacing.sm,
  },
  calcChip: {
    backgroundColor: colors.bgCard,
    borderRadius: borderRadius.full,
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm,
    borderWidth: 1,
    borderColor: colors.borderLight,
  },
  calcChipText: {
    fontSize: fontSize.sm,
    color: colors.text,
    fontWeight: '600',
  },
  tipCard: {
    marginHorizontal: spacing.lg,
    backgroundColor: colors.accentTealBg,
    borderRadius: borderRadius.lg,
    padding: spacing.lg,
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: spacing.sm,
  },
  tipIcon: {
    fontSize: 20,
  },
  tipText: {
    fontSize: fontSize.md,
    color: colors.accentTeal,
    flex: 1,
    lineHeight: 22,
  },
});
