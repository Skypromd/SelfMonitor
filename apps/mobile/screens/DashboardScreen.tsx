import React, { useState, useCallback } from 'react';
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  ActivityIndicator,
  Alert,
  ScrollView,
  TextInput,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { colors, spacing, fontSize } from '../theme';
import { apiCall } from '../api';
import { useAuth } from '../context/AuthContext';

export default function DashboardScreen() {
  const { user } = useAuth();
  const [advice, setAdvice] = useState<string | null>(null);
  const [adviceLoading, setAdviceLoading] = useState(false);

  const [taxYear, setTaxYear] = useState('2024');
  const [taxIncome, setTaxIncome] = useState('');
  const [taxResult, setTaxResult] = useState<any>(null);
  const [taxLoading, setTaxLoading] = useState(false);

  const [forecastStatus, setForecastStatus] = useState<string | null>(null);
  const [forecastLoading, setForecastLoading] = useState(false);

  const fetchAdvice = useCallback(async () => {
    setAdviceLoading(true);
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

  return (
    <SafeAreaView style={styles.container} edges={['top']}>
      <ScrollView contentContainerStyle={styles.scroll}>
        <Text style={styles.welcome}>
          Welcome, {user?.email || 'User'}
        </Text>

        <View style={styles.card}>
          <Text style={styles.cardTitle}>Financial Advice</Text>
          <Text style={styles.cardDescription}>
            Get AI-powered income protection advice
          </Text>
          {advice && <Text style={styles.adviceText}>{advice}</Text>}
          <TouchableOpacity
            style={styles.button}
            onPress={fetchAdvice}
            disabled={adviceLoading}
          >
            {adviceLoading ? (
              <ActivityIndicator color={colors.text} />
            ) : (
              <Text style={styles.buttonText}>Get Advice</Text>
            )}
          </TouchableOpacity>
        </View>

        <View style={styles.card}>
          <Text style={styles.cardTitle}>Tax Estimator</Text>
          <Text style={styles.label}>Tax Year</Text>
          <TextInput
            style={styles.input}
            value={taxYear}
            onChangeText={setTaxYear}
            keyboardType="numeric"
            placeholderTextColor={colors.textMuted}
          />
          <Text style={styles.label}>Gross Income (£)</Text>
          <TextInput
            style={styles.input}
            value={taxIncome}
            onChangeText={setTaxIncome}
            placeholder="e.g. 50000"
            placeholderTextColor={colors.textMuted}
            keyboardType="numeric"
          />
          {taxResult && (
            <View style={styles.resultBox}>
              <Text style={styles.resultText}>
                Tax: £{taxResult.tax_due?.toFixed(2) ?? 'N/A'}
              </Text>
              <Text style={styles.resultText}>
                NI: £{taxResult.national_insurance?.toFixed(2) ?? 'N/A'}
              </Text>
              <Text style={styles.resultText}>
                Net: £{taxResult.net_income?.toFixed(2) ?? 'N/A'}
              </Text>
            </View>
          )}
          <TouchableOpacity
            style={styles.button}
            onPress={calculateTax}
            disabled={taxLoading}
          >
            {taxLoading ? (
              <ActivityIndicator color={colors.text} />
            ) : (
              <Text style={styles.buttonText}>Calculate Tax</Text>
            )}
          </TouchableOpacity>
        </View>

        <View style={styles.card}>
          <Text style={styles.cardTitle}>Cash Flow Forecast</Text>
          <Text style={styles.cardDescription}>
            Generate a cash flow forecast based on your data
          </Text>
          {forecastStatus && (
            <Text style={styles.statusText}>{forecastStatus}</Text>
          )}
          <TouchableOpacity
            style={styles.button}
            onPress={fetchForecast}
            disabled={forecastLoading}
          >
            {forecastLoading ? (
              <ActivityIndicator color={colors.text} />
            ) : (
              <Text style={styles.buttonText}>Generate Forecast</Text>
            )}
          </TouchableOpacity>
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
    padding: spacing.md,
    paddingBottom: spacing.xl,
  },
  welcome: {
    fontSize: fontSize.xl,
    fontWeight: '700',
    color: colors.text,
    marginBottom: spacing.lg,
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
    marginBottom: spacing.xs,
  },
  cardDescription: {
    fontSize: fontSize.sm,
    color: colors.textMuted,
    marginBottom: spacing.md,
  },
  adviceText: {
    fontSize: fontSize.sm,
    color: colors.accentTealLight,
    backgroundColor: colors.successBg,
    borderRadius: 8,
    padding: spacing.md,
    marginBottom: spacing.md,
  },
  label: {
    fontSize: fontSize.sm,
    color: colors.textMuted,
    marginBottom: spacing.xs,
    marginTop: spacing.sm,
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
  resultBox: {
    backgroundColor: colors.successBg,
    borderRadius: 8,
    padding: spacing.md,
    marginTop: spacing.md,
  },
  resultText: {
    fontSize: fontSize.sm,
    color: colors.success,
    marginBottom: spacing.xs,
  },
  statusText: {
    fontSize: fontSize.sm,
    color: colors.accentTealLight,
    marginBottom: spacing.md,
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
});
