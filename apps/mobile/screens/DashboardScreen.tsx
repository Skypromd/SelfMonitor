import { useNavigation } from '@react-navigation/native';
import { Audio } from 'expo-av';
import * as Haptics from 'expo-haptics';
import { LinearGradient } from 'expo-linear-gradient';
import * as Localization from 'expo-localization';
import React, { useCallback, useEffect, useRef, useState } from 'react';
import {
    ActivityIndicator,
    Alert,
    Animated,
    ScrollView,
    StyleSheet,
    Text,
    TextInput,
    TouchableOpacity,
    View,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { apiCall, getVoiceHttpBase } from '../api';
import { useAuth } from '../context/AuthContext';
import { borderRadius, colors, fontSize, spacing } from '../theme';

function jwtSub(jwt: string): string | null {
  const parts = jwt.split('.');
  if (parts.length < 2) return null;
  try {
    let b64 = parts[1].replace(/-/g, '+').replace(/_/g, '/');
    const pad = (4 - (b64.length % 4)) % 4;
    if (pad) b64 += '='.repeat(pad);
    const json = JSON.parse(atob(b64)) as { sub?: unknown };
    const sub = json.sub;
    if (typeof sub === 'string') return sub;
    if (sub != null && (typeof sub === 'number' || typeof sub === 'boolean')) return String(sub);
    return null;
  } catch {
    return null;
  }
}

type Transaction = {
  id: string;
  description: string;
  amount: number;
  date: string;
};

const MOCK_TRANSACTIONS: Transaction[] = [
  { id: '1', description: 'Shell Petrol', amount: -50.0, date: 'Today' },
  { id: '2', description: 'Client X Payment', amount: 1500.0, date: 'Yesterday' },
  { id: '3', description: 'Amazon', amount: -12.99, date: '2d ago' },
  { id: '4', description: 'Freelance Invoice', amount: 2200.0, date: '3d ago' },
  { id: '5', description: 'Office Supplies', amount: -34.5, date: '4d ago' },
];

type QuickAction = { icon: string; label: string; onPress: () => void };

function getGreeting(): string {
  const h = new Date().getHours();
  if (h < 12) return 'Good morning';
  if (h < 18) return 'Good afternoon';
  return 'Good evening';
}

function getGreetingEmoji(): string {
  const h = new Date().getHours();
  if (h < 6) return '🌙';
  if (h < 12) return '☀️';
  if (h < 18) return '🌤️';
  return '🌙';
}

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

  const onPressIn = () => {
    Animated.spring(scale, {
      toValue: 0.96,
      useNativeDriver: true,
    }).start();
  };

  const onPressOut = () => {
    Animated.spring(scale, {
      toValue: 1,
      friction: 3,
      useNativeDriver: true,
    }).start();
  };

  return (
    <Animated.View style={{ transform: [{ scale }] }}>
      <TouchableOpacity
        onPress={onPress}
        onPressIn={onPressIn}
        onPressOut={onPressOut}
        activeOpacity={0.9}
        disabled={disabled}
        style={style}
      >
        {children}
      </TouchableOpacity>
    </Animated.View>
  );
}

export default function DashboardScreen() {
  const { user, token } = useAuth();
  const navigation = useNavigation<any>();
  const [advice, setAdvice] = useState<string | null>(null);
  const [adviceLoading, setAdviceLoading] = useState(false);
  const [voiceBusy, setVoiceBusy] = useState(false);
  const [cisAlert, setCisAlert] = useState<{ openTasks: number; unverified: number; missing: number } | null>(null);

  const [taxYear, setTaxYear] = useState('2024');
  const [taxIncome, setTaxIncome] = useState('');
  const [taxResult, setTaxResult] = useState<any>(null);
  const [taxLoading, setTaxLoading] = useState(false);

  const [forecastStatus, setForecastStatus] = useState<string | null>(null);
  const [forecastLoading, setForecastLoading] = useState(false);

  const heroFade = useRef(new Animated.Value(0)).current;
  const heroSlide = useRef(new Animated.Value(20)).current;

  useEffect(() => {
    Animated.parallel([
      Animated.timing(heroFade, {
        toValue: 1,
        duration: 600,
        useNativeDriver: true,
      }),
      Animated.timing(heroSlide, {
        toValue: 0,
        duration: 600,
        useNativeDriver: true,
      }),
    ]).start();
  }, [heroFade, heroSlide]);

  const fetchAdvice = useCallback(async () => {    setAdviceLoading(true);
    try {
      const res = await apiCall('/advice/generate', {
        method: 'POST',
        body: JSON.stringify({ topic: 'income_protection' }),
      });
      if (!res.ok) throw new Error('Failed to fetch advice');
      const data = await res.json();
      setAdvice(data.advice || data.message || JSON.stringify(data));
    } catch (err: any) {
      Alert.alert('Error', err.message);
    } finally {
      setAdviceLoading(false);
    }
  }, []);

  const fetchCisAlert = useCallback(async () => {
    if (!token) return;
    try {
      const res = await apiCall('/transactions/cis/refund-tracker');
      if (res.ok) {
        const d = await res.json() as { totals?: { open_tasks?: number; unverified_cis_withheld_gbp?: number; missing_obligation_buckets?: number } };
        setCisAlert({
          openTasks: d.totals?.open_tasks ?? 0,
          unverified: d.totals?.unverified_cis_withheld_gbp ?? 0,
          missing: d.totals?.missing_obligation_buckets ?? 0,
        });
      }
    } catch { /* non-critical */ }
  }, [token]);

  useEffect(() => {
    void fetchCisAlert();
  }, [fetchCisAlert]);

  const calculateTax = useCallback(async () => {
    if (!taxIncome) {
      Alert.alert('Error', 'Please enter income amount');
      return;
    }
    setTaxLoading(true);
    try {
      const res = await apiCall('/tax/calculate', {
        method: 'POST',
        body: JSON.stringify({
          tax_year: parseInt(taxYear, 10),
          gross_income: parseFloat(taxIncome),
        }),
      });
      if (!res.ok) throw new Error('Failed to calculate tax');
      const data = await res.json();
      setTaxResult(data);
    } catch (err: any) {
      Alert.alert('Error', err.message);
    } finally {
      setTaxLoading(false);
    }
  }, [taxYear, taxIncome]);

  const fetchForecast = useCallback(async () => {
    setForecastLoading(true);
    try {
      const res = await apiCall('/analytics/forecast/cash-flow', {
        method: 'POST',
        body: JSON.stringify({}),
      });
      if (!res.ok) throw new Error('Failed to fetch forecast');
      const data = await res.json();
      setForecastStatus(data.status || data.message || 'Forecast generated');
    } catch (err: any) {
      Alert.alert('Error', err.message);
    } finally {
      setForecastLoading(false);
    }
  }, []);

  const userName = user?.email?.split('@')[0] || 'there';

  const quickActions: QuickAction[] = [
    { icon: '🔄', label: 'Sync', onPress: () => navigation.navigate('Money') },
    { icon: '📸', label: 'Scan', onPress: () => navigation.navigate('Scan') },
    { icon: '�️', label: 'CIS', onPress: () => navigation.navigate('Me', { screen: 'CisRefundTracker' }) },
    { icon: '�🏠', label: 'Mortgage', onPress: () => navigation.navigate('Me', { screen: 'Mortgage' }) },
    { icon: '📄', label: 'Invoice', onPress: () => navigation.navigate('Money') },
  ];

  const handleVoiceExpense = useCallback(async () => {
    if (!token || voiceBusy) return;
    const sub = jwtSub(token);
    if (!sub) {
      Alert.alert('Voice expense', 'Could not read your session. Please sign in again.');
      return;
    }
    setVoiceBusy(true);
    let recording: Audio.Recording | undefined;
    try {
      const perm = await Audio.requestPermissionsAsync();
      if (!perm.granted) {
        Alert.alert('Voice expense', 'Microphone permission is required.');
        return;
      }
      await Audio.setAudioModeAsync({
        allowsRecordingIOS: true,
        playsInSilentModeIOS: true,
        staysActiveInBackground: false,
      });
      recording = new Audio.Recording();
      await recording.prepareToRecordAsync(Audio.RecordingOptionsPresets.HIGH_QUALITY);
      await recording.startAsync();
      await new Promise<void>(resolve => setTimeout(resolve, 4000));
      const uri = recording.getURI();
      await recording.stopAndUnloadAsync();
      recording = undefined;
      if (!uri) {
        throw new Error('Recording failed');
      }
      const lang = (Localization.getLocales()[0]?.languageCode ?? 'en').slice(0, 2);
      const form = new FormData();
      form.append('user_id', sub);
      form.append('token', token);
      form.append('language', lang);
      form.append('audio', { uri, name: 'clip.m4a', type: 'audio/m4a' } as unknown as Blob);
      const res = await fetch(`${getVoiceHttpBase()}/voice/transcribe-intent`, {
        method: 'POST',
        body: form,
      });
      const data = (await res.json().catch(() => ({}))) as {
        detail?: string | string[];
        text?: string;
        intent?: { amount: number; category: string; currency: string } | null;
      };
      if (!res.ok) {
        const detail = data.detail;
        const msg = Array.isArray(detail) ? detail.join(', ') : typeof detail === 'string' ? detail : `HTTP ${res.status}`;
        Alert.alert('Voice expense', msg);
        return;
      }
      const intent = data.intent;
      if (intent && typeof intent.amount === 'number' && intent.category) {
        const msg = `${intent.category} · ${intent.currency} ${intent.amount.toFixed(2)}`;
        Alert.alert('Captured expense', msg, [
          { text: 'OK', style: 'cancel' },
          { text: 'Open Money', onPress: () => navigation.navigate('Money') },
        ]);
        void Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success);
      } else {
        const hint = data.text?.trim() ? data.text.trim() : 'Could not detect amount and category. Try e.g. “paid 12 lunch”.';
        Alert.alert('Voice expense', hint, [
          { text: 'OK', style: 'cancel' },
          { text: 'Open Money', onPress: () => navigation.navigate('Money') },
        ]);
      }
    } catch (e) {
      const message = e instanceof Error ? e.message : String(e);
      Alert.alert('Voice expense', message);
    } finally {
      if (recording) {
        try {
          await recording.stopAndUnloadAsync();
        } catch {
          /* already stopped */
        }
      }
      setVoiceBusy(false);
    }
  }, [navigation, token]);

  return (
    <SafeAreaView style={styles.container} edges={['top']}>
      <ScrollView
        contentContainerStyle={styles.scroll}
        showsVerticalScrollIndicator={false}
      >
        {/* Greeting */}
        <Animated.View
          style={[
            styles.greetingRow,
            { opacity: heroFade, transform: [{ translateY: heroSlide }] },
          ]}
        >
          <Text style={styles.greeting}>
            {getGreeting()}, {userName} {getGreetingEmoji()}
          </Text>
          <TouchableOpacity
            style={[styles.voiceMic, (!token || voiceBusy) && styles.voiceMicDisabled]}
            onPress={() => void handleVoiceExpense()}
            disabled={!token || voiceBusy}
            accessibilityLabel={voiceBusy ? 'Recording voice expense' : 'Voice quick expense'}
          >
            <Text style={styles.voiceMicIcon}>{voiceBusy ? '⏺' : '🎤'}</Text>
          </TouchableOpacity>
        </Animated.View>

        {/* Hero Balance */}
        <Animated.View
          style={[
            styles.heroSection,
            { opacity: heroFade, transform: [{ translateY: heroSlide }] },
          ]}
        >
          <Text style={styles.heroAmount}>£12,450.00</Text>
          <Text style={styles.heroLabel}>Total Balance</Text>

          <View style={styles.pillRow}>
            <View style={styles.incomePill}>
              <Text style={styles.pillIcon}>↗</Text>
              <View>
                <Text style={styles.incomePillAmount}>£8,200</Text>
                <Text style={styles.pillLabel}>Income</Text>
              </View>
            </View>
            <View style={styles.expensePill}>
              <Text style={styles.pillIcon}>↘</Text>
              <View>
                <Text style={styles.expensePillAmount}>£3,100</Text>
                <Text style={styles.pillLabel}>Expenses</Text>
              </View>
            </View>
          </View>
        </Animated.View>

        {/* Quick Actions */}
        <View style={styles.sectionHeader}>
          <Text style={styles.sectionTitle}>Quick Actions</Text>
        </View>
        <ScrollView
          horizontal
          showsHorizontalScrollIndicator={false}
          contentContainerStyle={styles.quickActionsRow}
        >
          {quickActions.map((action, i) => (
            <AnimatedPressable key={i} onPress={action.onPress} style={styles.quickActionItem}>
              <View style={styles.quickActionCircle}>
                <Text style={styles.quickActionIcon}>{action.icon}</Text>
              </View>
              <Text style={styles.quickActionLabel}>{action.label}</Text>
            </AnimatedPressable>
          ))}
        </ScrollView>

        {/* Next Deadline Card */}
        <AnimatedPressable onPress={() => navigation.navigate('Tax')} style={styles.deadlineCardWrapper}>
          <View style={styles.deadlineCard}>
            <View style={styles.deadlineRow}>
              <Text style={styles.deadlineIcon}>⏰</Text>
              <View style={styles.deadlineInfo}>
                <Text style={styles.deadlineTitle}>MTD Q2 due in 23 days</Text>
                <Text style={styles.deadlineAction}>Prepare Report →</Text>
              </View>
            </View>
          </View>
        </AnimatedPressable>

        {/* Quarter Readiness Card */}
        <AnimatedPressable onPress={() => { void Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light); navigation.navigate('Tax'); }} style={styles.deadlineCardWrapper}>
          <View style={[styles.deadlineCard, { borderColor: 'rgba(13,148,136,0.4)', backgroundColor: 'rgba(13,148,136,0.06)' }]}>
            <View style={styles.deadlineRow}>
              <Text style={styles.deadlineIcon}>✅</Text>
              <View style={[styles.deadlineInfo, { flex: 1 }]}>
                <Text style={[styles.deadlineTitle, { color: colors.accentTeal }]}>Quarter Readiness</Text>
                <Text style={styles.deadlineAction}>Fix blockers · Submit in 7 min →</Text>
              </View>
            </View>
            <View style={[styles.mortgageProgress, { marginTop: 8 }]}>
              <View style={[styles.mortgageProgressFill, { width: '65%', backgroundColor: colors.accentTeal }]} />
            </View>
            <Text style={{ fontSize: 11, color: colors.textMuted, marginTop: 4 }}>65% ready · 3 blockers remaining</Text>
          </View>
        </AnimatedPressable>

        {/* CIS Alert Banner */}
        {cisAlert && (cisAlert.openTasks > 0 || cisAlert.missing > 0) && (
          <AnimatedPressable onPress={() => { void Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Medium); navigation.navigate('Me', { screen: 'CisRefundTracker' }); }} style={styles.deadlineCardWrapper}>
            <View style={[styles.deadlineCard, { borderColor: 'rgba(245,158,11,0.4)', backgroundColor: 'rgba(245,158,11,0.08)' }]}>
              <View style={styles.deadlineRow}>
                <Text style={styles.deadlineIcon}>⚠️</Text>
                <View style={styles.deadlineInfo}>
                  <Text style={[styles.deadlineTitle, { color: '#f59e0b' }]}>
                    CIS: {cisAlert.openTasks > 0 ? `${cisAlert.openTasks} open task${cisAlert.openTasks !== 1 ? 's' : ''}` : `${cisAlert.missing} missing bucket${cisAlert.missing !== 1 ? 's' : ''}`}
                  </Text>
                  <Text style={styles.deadlineAction}>Upload statements to verify →</Text>
                </View>
              </View>
            </View>
          </AnimatedPressable>
        )}

        {/* Mortgage Readiness Card */}
        <AnimatedPressable onPress={() => navigation.navigate('Me', { screen: 'Mortgage' })} style={styles.deadlineCardWrapper}>
          <View style={styles.mortgageCard}>
            <View style={styles.deadlineRow}>
              <Text style={styles.deadlineIcon}>🏠</Text>
              <View style={styles.deadlineInfo}>
                <Text style={styles.deadlineTitle}>Mortgage: 72% ready</Text>
                <Text style={styles.deadlineAction}>Check Details →</Text>
              </View>
            </View>
            <View style={styles.mortgageProgress}>
              <View style={[styles.mortgageProgressFill, { width: '72%' }]} />
            </View>
          </View>
        </AnimatedPressable>

        {/* Tax Status Card */}
        <View style={styles.sectionHeader}>
          <Text style={styles.sectionTitle}>Tax Status</Text>
        </View>
        <View style={styles.taxCard}>
          <LinearGradient
            colors={[colors.accentTealBg, 'transparent']}
            style={styles.taxCardGradient}
          />
          <View style={styles.taxCardHeader}>
            <Text style={styles.taxFlag}>🇬🇧</Text>
            <View style={{ flex: 1 }}>
              <Text style={styles.taxCardTitle}>MTD Q2 due in 23 days</Text>
              <Text style={styles.taxCardSubtitle}>Estimated tax: £4,280</Text>
            </View>
          </View>
          <View style={styles.progressTrack}>
            <View style={[styles.progressFill, { width: '72%' }]} />
          </View>
          <Text style={styles.progressLabel}>72% complete</Text>
        </View>

        {/* Financial Advice Card */}
        <View style={styles.sectionHeader}>
          <Text style={styles.sectionTitle}>Financial Advice</Text>
        </View>
        <View style={styles.card}>
          <Text style={styles.cardDescription}>
            Get AI-powered income protection advice
          </Text>
          {advice && (
            <View style={styles.adviceBox}>
              <Text style={styles.adviceText}>{advice}</Text>
            </View>
          )}
          <AnimatedPressable onPress={fetchAdvice} disabled={adviceLoading}>
            <LinearGradient
              colors={[colors.gradientStart, colors.gradientEnd]}
              start={{ x: 0, y: 0 }}
              end={{ x: 1, y: 0 }}
              style={styles.gradientButton}
            >
              {adviceLoading ? (
                <ActivityIndicator color={colors.text} />
              ) : (
                <Text style={styles.gradientButtonText}>Get Advice</Text>
              )}
            </LinearGradient>
          </AnimatedPressable>
        </View>

        {/* Tax Estimator Card */}
        <View style={styles.sectionHeader}>
          <Text style={styles.sectionTitle}>Tax Estimator</Text>
        </View>
        <View style={styles.card}>
          <Text style={styles.inputLabel}>Tax Year</Text>
          <TextInput
            style={styles.input}
            value={taxYear}
            onChangeText={setTaxYear}
            keyboardType="numeric"
            placeholderTextColor={colors.textMuted}
          />
          <Text style={styles.inputLabel}>Gross Income (£)</Text>
          <TextInput
            style={styles.input}
            value={taxIncome}
            onChangeText={setTaxIncome}
            placeholder="e.g. 50000"
            placeholderTextColor={colors.textMuted}
            keyboardType="numeric"
          />
          {taxResult && (
            <View style={styles.taxResultBox}>
              <View style={styles.taxResultRow}>
                <Text style={styles.taxResultLabel}>Tax</Text>
                <Text style={styles.taxResultValue}>
                  £{taxResult.tax_due?.toFixed(2) ?? 'N/A'}
                </Text>
              </View>
              <View style={styles.taxResultRow}>
                <Text style={styles.taxResultLabel}>NI</Text>
                <Text style={styles.taxResultValue}>
                  £{taxResult.national_insurance?.toFixed(2) ?? 'N/A'}
                </Text>
              </View>
              <View style={[styles.taxResultRow, { borderBottomWidth: 0 }]}>
                <Text style={styles.taxResultLabel}>Net</Text>
                <Text style={[styles.taxResultValue, { color: colors.income }]}>
                  £{taxResult.net_income?.toFixed(2) ?? 'N/A'}
                </Text>
              </View>
            </View>
          )}
          <AnimatedPressable onPress={calculateTax} disabled={taxLoading}>
            <LinearGradient
              colors={[colors.gradientStart, colors.gradientEnd]}
              start={{ x: 0, y: 0 }}
              end={{ x: 1, y: 0 }}
              style={styles.gradientButton}
            >
              {taxLoading ? (
                <ActivityIndicator color={colors.text} />
              ) : (
                <Text style={styles.gradientButtonText}>Calculate Tax</Text>
              )}
            </LinearGradient>
          </AnimatedPressable>
        </View>

        {/* Cash Flow Forecast Card */}
        <View style={styles.sectionHeader}>
          <Text style={styles.sectionTitle}>Cash Flow Forecast</Text>
        </View>
        <View style={styles.card}>
          <Text style={styles.cardDescription}>
            Generate a cash flow forecast based on your data
          </Text>
          {forecastStatus && (
            <View style={styles.forecastStatusBox}>
              <Text style={styles.forecastStatusText}>{forecastStatus}</Text>
            </View>
          )}
          <AnimatedPressable onPress={fetchForecast} disabled={forecastLoading}>
            <LinearGradient
              colors={[colors.gradientStart, colors.gradientEnd]}
              start={{ x: 0, y: 0 }}
              end={{ x: 1, y: 0 }}
              style={styles.gradientButton}
            >
              {forecastLoading ? (
                <ActivityIndicator color={colors.text} />
              ) : (
                <Text style={styles.gradientButtonText}>Generate Forecast</Text>
              )}
            </LinearGradient>
          </AnimatedPressable>
        </View>

        {/* Recent Transactions */}
        <View style={styles.sectionHeader}>
          <Text style={styles.sectionTitle}>Recent Transactions</Text>
        </View>
        <View style={styles.transactionsCard}>
          {MOCK_TRANSACTIONS.map((tx, i) => (
            <View
              key={tx.id}
              style={[
                styles.txRow,
                i === MOCK_TRANSACTIONS.length - 1 && { borderBottomWidth: 0 },
              ]}
            >
              <View style={styles.txLeft}>
                <View
                  style={[
                    styles.txDot,
                    { backgroundColor: tx.amount > 0 ? colors.income : colors.expense },
                  ]}
                />
                <View>
                  <Text style={styles.txDescription}>{tx.description}</Text>
                  <Text style={styles.txDate}>{tx.date}</Text>
                </View>
              </View>
              <Text
                style={[
                  styles.txAmount,
                  { color: tx.amount > 0 ? colors.income : colors.expense },
                ]}
              >
                {tx.amount > 0 ? '+' : ''}£{Math.abs(tx.amount).toFixed(2)}
              </Text>
            </View>
          ))}
        </View>
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
  greetingRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: spacing.lg,
    paddingTop: spacing.lg,
    gap: spacing.md,
  },
  greeting: {
    flex: 1,
    fontSize: fontSize.lg,
    fontWeight: '600',
    color: colors.textSecondary,
  },
  voiceMic: {
    width: 44,
    height: 44,
    borderRadius: 22,
    backgroundColor: colors.bgCard,
    borderWidth: 1,
    borderColor: colors.borderLight,
    alignItems: 'center',
    justifyContent: 'center',
  },
  voiceMicDisabled: {
    opacity: 0.45,
  },
  voiceMicIcon: {
    fontSize: 22,
  },
  heroSection: {
    alignItems: 'center',
    paddingVertical: spacing.xl,
    paddingHorizontal: spacing.lg,
  },
  heroAmount: {
    fontSize: fontSize.hero,
    fontWeight: '800',
    color: colors.text,
    letterSpacing: -1,
  },
  heroLabel: {
    fontSize: fontSize.sm,
    color: colors.textMuted,
    marginTop: spacing.xs,
    textTransform: 'uppercase',
    letterSpacing: 1.5,
  },
  pillRow: {
    flexDirection: 'row',
    gap: spacing.md,
    marginTop: spacing.lg,
  },
  incomePill: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: colors.incomeBg,
    borderRadius: borderRadius.lg,
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm,
    gap: spacing.sm,
  },
  expensePill: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: colors.expenseBg,
    borderRadius: borderRadius.lg,
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm,
    gap: spacing.sm,
  },
  pillIcon: {
    fontSize: fontSize.lg,
    fontWeight: '700',
    color: colors.text,
  },
  incomePillAmount: {
    fontSize: fontSize.md,
    fontWeight: '700',
    color: colors.income,
  },
  expensePillAmount: {
    fontSize: fontSize.md,
    fontWeight: '700',
    color: colors.expense,
  },
  pillLabel: {
    fontSize: fontSize.xs,
    color: colors.textMuted,
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
  quickActionsRow: {
    paddingHorizontal: spacing.lg,
    gap: spacing.lg,
  },
  quickActionItem: {
    alignItems: 'center',
  },
  quickActionCircle: {
    width: 56,
    height: 56,
    borderRadius: 28,
    backgroundColor: colors.bgCard,
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 1,
    borderColor: colors.borderLight,
  },
  quickActionIcon: {
    fontSize: 24,
  },
  quickActionLabel: {
    fontSize: fontSize.xs,
    color: colors.textSecondary,
    marginTop: spacing.xs,
    fontWeight: '600',
  },
  taxCard: {
    marginHorizontal: spacing.lg,
    backgroundColor: colors.bgCard,
    borderRadius: borderRadius.xl,
    padding: spacing.lg,
    overflow: 'hidden',
    borderWidth: 1,
    borderColor: colors.border,
  },
  taxCardGradient: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    borderRadius: borderRadius.xl,
  },
  taxCardHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.sm,
    marginBottom: spacing.md,
  },
  taxFlag: {
    fontSize: 24,
  },
  taxCardTitle: {
    fontSize: fontSize.md,
    fontWeight: '700',
    color: colors.text,
  },
  taxCardSubtitle: {
    fontSize: fontSize.sm,
    color: colors.textSecondary,
    marginTop: 2,
  },
  progressTrack: {
    height: 6,
    backgroundColor: colors.bgElevated,
    borderRadius: 3,
    overflow: 'hidden',
  },
  progressFill: {
    height: '100%',
    backgroundColor: colors.accentTeal,
    borderRadius: 3,
  },
  progressLabel: {
    fontSize: fontSize.xs,
    color: colors.textMuted,
    marginTop: spacing.xs,
    textAlign: 'right',
  },
  card: {
    marginHorizontal: spacing.lg,
    backgroundColor: colors.bgCard,
    borderRadius: borderRadius.xl,
    padding: spacing.lg,
    borderWidth: 1,
    borderColor: colors.border,
  },
  cardDescription: {
    fontSize: fontSize.sm,
    color: colors.textSecondary,
    marginBottom: spacing.md,
  },
  adviceBox: {
    backgroundColor: colors.accentTealBg,
    borderRadius: borderRadius.md,
    padding: spacing.md,
    marginBottom: spacing.md,
  },
  adviceText: {
    fontSize: fontSize.sm,
    color: colors.accentTeal,
    lineHeight: 20,
  },
  inputLabel: {
    fontSize: fontSize.xs,
    color: colors.textMuted,
    marginBottom: spacing.xs,
    marginTop: spacing.sm,
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
  taxResultBox: {
    backgroundColor: colors.bgElevated,
    borderRadius: borderRadius.md,
    padding: spacing.md,
    marginTop: spacing.md,
  },
  taxResultRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    paddingVertical: spacing.sm,
    borderBottomWidth: 1,
    borderBottomColor: colors.border,
  },
  taxResultLabel: {
    fontSize: fontSize.sm,
    color: colors.textMuted,
  },
  taxResultValue: {
    fontSize: fontSize.sm,
    color: colors.text,
    fontWeight: '700',
  },
  forecastStatusBox: {
    backgroundColor: colors.accentTealBg,
    borderRadius: borderRadius.md,
    padding: spacing.md,
    marginBottom: spacing.md,
  },
  forecastStatusText: {
    fontSize: fontSize.sm,
    color: colors.accentTeal,
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
  transactionsCard: {
    marginHorizontal: spacing.lg,
    backgroundColor: colors.bgCard,
    borderRadius: borderRadius.xl,
    padding: spacing.md,
    borderWidth: 1,
    borderColor: colors.border,
  },
  txRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingVertical: spacing.md,
    paddingHorizontal: spacing.sm,
    borderBottomWidth: 1,
    borderBottomColor: colors.border,
  },
  txLeft: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.sm,
    flex: 1,
  },
  txDot: {
    width: 8,
    height: 8,
    borderRadius: 4,
  },
  txDescription: {
    fontSize: fontSize.md,
    color: colors.text,
    fontWeight: '600',
  },
  txDate: {
    fontSize: fontSize.xs,
    color: colors.textMuted,
    marginTop: 2,
  },
  txAmount: {
    fontSize: fontSize.md,
    fontWeight: '700',
  },
  deadlineCardWrapper: {
    paddingHorizontal: spacing.lg,
    paddingTop: spacing.md,
  },
  deadlineCard: {
    backgroundColor: colors.bgCard,
    borderRadius: borderRadius.lg,
    padding: spacing.lg,
    borderWidth: 1,
    borderColor: colors.warning,
  },
  mortgageCard: {
    backgroundColor: colors.bgCard,
    borderRadius: borderRadius.lg,
    padding: spacing.lg,
    borderWidth: 1,
    borderColor: colors.accentTeal,
  },
  deadlineRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.sm,
  },
  deadlineIcon: {
    fontSize: 24,
  },
  deadlineInfo: {
    flex: 1,
  },
  deadlineTitle: {
    fontSize: fontSize.md,
    fontWeight: '700',
    color: colors.text,
  },
  deadlineAction: {
    fontSize: fontSize.sm,
    color: colors.accentTeal,
    fontWeight: '600',
    marginTop: 2,
  },
  mortgageProgress: {
    height: 4,
    backgroundColor: colors.bgElevated,
    borderRadius: 2,
    overflow: 'hidden',
    marginTop: spacing.md,
  },
  mortgageProgressFill: {
    height: '100%',
    backgroundColor: colors.accentTeal,
    borderRadius: 2,
  },
});
