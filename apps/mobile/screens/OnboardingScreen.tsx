import React, { useState, useRef, useEffect } from 'react';
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  TextInput,
  Animated,
  ScrollView,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { colors, spacing, fontSize, borderRadius } from '../theme';

const STEPS = 4;

const BUSINESS_TYPES = [
  { id: 'sole_trader', emoji: '🧾', label: 'Sole Trader', description: 'Running your own business' },
  { id: 'freelancer', emoji: '💻', label: 'Freelancer', description: 'Selling your skills & time' },
  { id: 'contractor', emoji: '🔧', label: 'Contractor', description: 'Working through contracts' },
  { id: 'landlord', emoji: '🏠', label: 'Landlord', description: 'Earning rental income' },
];

function computeTaxBreakdown(income: number) {
  const personalAllowance = 12570;
  const basicRateLimit = 50270;
  const higherRateLimit = 125140;

  let incomeTax = 0;
  const taxable = Math.max(0, income - personalAllowance);
  if (taxable > 0) {
    const basicBand = Math.min(taxable, basicRateLimit - personalAllowance);
    incomeTax += basicBand * 0.2;
  }
  if (taxable > basicRateLimit - personalAllowance) {
    const higherBand = Math.min(
      taxable - (basicRateLimit - personalAllowance),
      higherRateLimit - basicRateLimit
    );
    incomeTax += higherBand * 0.4;
  }
  if (taxable > higherRateLimit - personalAllowance) {
    incomeTax += (taxable - (higherRateLimit - personalAllowance)) * 0.45;
  }

  let ni = 0;
  const niLower = 12570;
  const niUpper = 50270;
  if (income > niLower) {
    const band1 = Math.min(income - niLower, niUpper - niLower);
    ni += band1 * 0.06;
  }
  if (income > niUpper) {
    ni += (income - niUpper) * 0.02;
  }

  return {
    incomeTax: Math.round(incomeTax),
    nationalInsurance: Math.round(ni),
    takeHome: Math.round(income - incomeTax - ni),
  };
}

type Props = {
  onComplete: () => void;
};

export default function OnboardingScreen({ onComplete }: Props) {
  const [step, setStep] = useState(0);
  const [selectedType, setSelectedType] = useState<string | null>(null);
  const [incomeInput, setIncomeInput] = useState('');
  const checkScale = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    if (step === 3) {
      Animated.spring(checkScale, {
        toValue: 1,
        tension: 50,
        friction: 5,
        useNativeDriver: true,
      }).start();
    } else {
      checkScale.setValue(0);
    }
  }, [step, checkScale]);

  const incomeNum = parseFloat(incomeInput) || 0;
  const taxBreakdown = incomeNum > 0 ? computeTaxBreakdown(incomeNum) : null;

  const canContinue = () => {
    if (step === 0) return selectedType !== null;
    if (step === 2) return incomeNum > 0;
    return true;
  };

  const handleNext = async () => {
    if (step < STEPS - 1) {
      setStep(step + 1);
    } else {
      await AsyncStorage.setItem('onboarding_complete', 'true');
      onComplete();
    }
  };

  const renderDots = () => (
    <View style={styles.dotsRow}>
      {Array.from({ length: STEPS }).map((_, i) => (
        <View
          key={i}
          style={[styles.dot, i === step ? styles.dotActive : styles.dotInactive]}
        />
      ))}
    </View>
  );

  const renderStep0 = () => (
    <View style={styles.stepContainer}>
      <Text style={styles.welcomeTitle}>Welcome to SelfMonitor</Text>
      <Text style={styles.welcomeSubtitle}>What do you do?</Text>
      <View style={styles.cardsGrid}>
        {BUSINESS_TYPES.map((bt) => (
          <TouchableOpacity
            key={bt.id}
            style={[
              styles.typeCard,
              selectedType === bt.id && styles.typeCardSelected,
            ]}
            onPress={() => setSelectedType(bt.id)}
            activeOpacity={0.8}
          >
            <Text style={styles.typeEmoji}>{bt.emoji}</Text>
            <Text style={styles.typeLabel}>{bt.label}</Text>
            <Text style={styles.typeDescription}>{bt.description}</Text>
          </TouchableOpacity>
        ))}
      </View>
    </View>
  );

  const renderStep1 = () => (
    <View style={styles.stepContainer}>
      <Text style={styles.bankIcon}>🏦</Text>
      <Text style={styles.stepTitle}>Connect your bank</Text>
      <Text style={styles.stepSubtitle}>Import transactions automatically</Text>
      <TouchableOpacity style={styles.primaryButton} onPress={handleNext} activeOpacity={0.8}>
        <Text style={styles.primaryButtonText}>Connect Bank</Text>
      </TouchableOpacity>
      <TouchableOpacity onPress={handleNext} style={styles.skipLink}>
        <Text style={styles.skipText}>Skip for now →</Text>
      </TouchableOpacity>
    </View>
  );

  const renderStep2 = () => (
    <View style={styles.stepContainer}>
      <Text style={styles.stepTitle}>Your quick tax estimate</Text>
      <Text style={styles.inputLabel}>Annual income (£)</Text>
      <TextInput
        style={styles.input}
        value={incomeInput}
        onChangeText={setIncomeInput}
        keyboardType="numeric"
        placeholder="e.g. 45000"
        placeholderTextColor={colors.textMuted}
      />
      {taxBreakdown && (
        <View style={styles.taxBreakdown}>
          <View style={styles.taxRow}>
            <Text style={styles.taxLabel}>Income Tax</Text>
            <Text style={styles.taxValue}>£{taxBreakdown.incomeTax.toLocaleString()}</Text>
          </View>
          <View style={styles.taxRow}>
            <Text style={styles.taxLabel}>National Insurance</Text>
            <Text style={styles.taxValue}>£{taxBreakdown.nationalInsurance.toLocaleString()}</Text>
          </View>
          <View style={[styles.taxRow, { borderBottomWidth: 0 }]}>
            <Text style={styles.taxLabel}>Take home</Text>
            <Text style={[styles.taxValue, { color: colors.income }]}>
              £{taxBreakdown.takeHome.toLocaleString()}
            </Text>
          </View>
        </View>
      )}
    </View>
  );

  const renderStep3 = () => (
    <View style={styles.stepContainer}>
      <Animated.View style={[styles.checkCircle, { transform: [{ scale: checkScale }] }]}>
        <Text style={styles.checkMark}>✓</Text>
      </Animated.View>
      <Text style={styles.stepTitle}>You're all set!</Text>
      <Text style={styles.stepSubtitle}>Your dashboard is ready</Text>
      <View style={styles.bulletList}>
        <Text style={styles.bulletItem}>📊 Track income & expenses</Text>
        <Text style={styles.bulletItem}>🇬🇧 File taxes to HMRC</Text>
        <Text style={styles.bulletItem}>🏠 Check mortgage readiness</Text>
      </View>
    </View>
  );

  return (
    <SafeAreaView style={styles.container} edges={['top', 'bottom']}>
      <ScrollView
        contentContainerStyle={styles.scroll}
        showsVerticalScrollIndicator={false}
        keyboardShouldPersistTaps="handled"
      >
        {renderDots()}
        {step === 0 && renderStep0()}
        {step === 1 && renderStep1()}
        {step === 2 && renderStep2()}
        {step === 3 && renderStep3()}
      </ScrollView>

      {step !== 1 && (
        <View style={styles.footer}>
          <TouchableOpacity
            style={[styles.continueButton, !canContinue() && styles.continueButtonDisabled]}
            onPress={handleNext}
            disabled={!canContinue()}
            activeOpacity={0.8}
          >
            <Text style={styles.continueButtonText}>
              {step === 3 ? 'Go to Dashboard →' : 'Continue'}
            </Text>
          </TouchableOpacity>
        </View>
      )}
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.bg,
  },
  scroll: {
    flexGrow: 1,
    paddingHorizontal: spacing.lg,
    paddingBottom: spacing.xxl,
  },
  dotsRow: {
    flexDirection: 'row',
    justifyContent: 'center',
    gap: spacing.sm,
    paddingTop: spacing.lg,
    paddingBottom: spacing.xl,
  },
  dot: {
    width: 10,
    height: 10,
    borderRadius: 5,
  },
  dotActive: {
    backgroundColor: colors.accentTeal,
  },
  dotInactive: {
    backgroundColor: colors.bgCard,
  },
  stepContainer: {
    flex: 1,
    alignItems: 'center',
    paddingTop: spacing.xl,
  },
  welcomeTitle: {
    fontSize: fontSize.xxl,
    fontWeight: '800',
    color: colors.text,
    textAlign: 'center',
    marginBottom: spacing.sm,
  },
  welcomeSubtitle: {
    fontSize: fontSize.lg,
    color: colors.textSecondary,
    marginBottom: spacing.xl,
  },
  cardsGrid: {
    width: '100%',
    gap: spacing.md,
  },
  typeCard: {
    backgroundColor: colors.bgCard,
    borderRadius: borderRadius.lg,
    padding: spacing.lg,
    borderWidth: 2,
    borderColor: colors.border,
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.md,
  },
  typeCardSelected: {
    borderColor: colors.accentTeal,
    backgroundColor: colors.accentTealBg,
  },
  typeEmoji: {
    fontSize: 32,
  },
  typeLabel: {
    fontSize: fontSize.lg,
    fontWeight: '700',
    color: colors.text,
  },
  typeDescription: {
    fontSize: fontSize.sm,
    color: colors.textMuted,
    flex: 1,
  },
  bankIcon: {
    fontSize: 64,
    marginBottom: spacing.lg,
  },
  stepTitle: {
    fontSize: fontSize.xl,
    fontWeight: '800',
    color: colors.text,
    textAlign: 'center',
    marginBottom: spacing.sm,
  },
  stepSubtitle: {
    fontSize: fontSize.md,
    color: colors.textSecondary,
    textAlign: 'center',
    marginBottom: spacing.xl,
  },
  primaryButton: {
    backgroundColor: colors.accentTeal,
    borderRadius: borderRadius.md,
    paddingVertical: spacing.md,
    paddingHorizontal: spacing.xxl,
    alignItems: 'center',
    width: '100%',
  },
  primaryButtonText: {
    color: colors.textInverse,
    fontSize: fontSize.md,
    fontWeight: '700',
  },
  skipLink: {
    marginTop: spacing.lg,
  },
  skipText: {
    fontSize: fontSize.sm,
    color: colors.textMuted,
  },
  inputLabel: {
    fontSize: fontSize.sm,
    color: colors.textMuted,
    alignSelf: 'flex-start',
    marginBottom: spacing.sm,
    textTransform: 'uppercase',
    letterSpacing: 0.5,
  },
  input: {
    backgroundColor: colors.bgCard,
    borderRadius: borderRadius.sm,
    padding: spacing.md,
    color: colors.text,
    fontSize: fontSize.xl,
    fontWeight: '700',
    borderWidth: 1,
    borderColor: colors.border,
    width: '100%',
    textAlign: 'center',
  },
  taxBreakdown: {
    width: '100%',
    backgroundColor: colors.bgCard,
    borderRadius: borderRadius.lg,
    padding: spacing.md,
    marginTop: spacing.lg,
    borderWidth: 1,
    borderColor: colors.border,
  },
  taxRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    paddingVertical: spacing.sm,
    borderBottomWidth: 1,
    borderBottomColor: colors.border,
  },
  taxLabel: {
    fontSize: fontSize.md,
    color: colors.textSecondary,
  },
  taxValue: {
    fontSize: fontSize.md,
    fontWeight: '700',
    color: colors.text,
  },
  checkCircle: {
    width: 100,
    height: 100,
    borderRadius: 50,
    backgroundColor: colors.accentTeal,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: spacing.lg,
  },
  checkMark: {
    fontSize: 48,
    color: colors.textInverse,
    fontWeight: '700',
  },
  bulletList: {
    width: '100%',
    gap: spacing.md,
    marginTop: spacing.md,
  },
  bulletItem: {
    fontSize: fontSize.lg,
    color: colors.text,
    paddingVertical: spacing.sm,
    paddingHorizontal: spacing.md,
    backgroundColor: colors.bgCard,
    borderRadius: borderRadius.md,
    overflow: 'hidden',
  },
  footer: {
    paddingHorizontal: spacing.lg,
    paddingBottom: spacing.md,
  },
  continueButton: {
    backgroundColor: colors.accentTeal,
    borderRadius: borderRadius.md,
    padding: spacing.md,
    alignItems: 'center',
  },
  continueButtonDisabled: {
    backgroundColor: colors.bgCard,
  },
  continueButtonText: {
    color: colors.textInverse,
    fontSize: fontSize.md,
    fontWeight: '700',
  },
});
