import React, { useState, useCallback } from 'react';
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  ActivityIndicator,
  Alert,
  ScrollView,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { colors, spacing, fontSize } from '../theme';
import { apiCall } from '../api';

export default function ReportsScreen() {
  const [report, setReport] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  const generateReport = useCallback(async () => {
    setLoading(true);
    try {
      const res = await apiCall('/analytics/reports/mortgage-readiness');
      if (!res.ok) throw new Error('Failed to generate report');
      const data = await res.json();
      setReport(data);
    } catch (err: any) {
      Alert.alert('Error', err.message);
    } finally {
      setLoading(false);
    }
  }, []);

  return (
    <SafeAreaView style={styles.container} edges={['top']}>
      <ScrollView contentContainerStyle={styles.scroll}>
        <Text style={styles.title}>Reports</Text>
        <Text style={styles.subtitle}>Generate financial readiness reports</Text>

        <View style={styles.card}>
          <Text style={styles.cardTitle}>Mortgage Readiness Report</Text>
          <Text style={styles.cardDescription}>
            Comprehensive analysis of your financial readiness for a mortgage application.
          </Text>
          <TouchableOpacity
            style={styles.button}
            onPress={generateReport}
            disabled={loading}
          >
            {loading ? (
              <ActivityIndicator color={colors.text} />
            ) : (
              <Text style={styles.buttonText}>Generate Report</Text>
            )}
          </TouchableOpacity>
        </View>

        {report && (
          <View style={styles.reportCard}>
            <Text style={styles.reportTitle}>Report Results</Text>
            {report.score !== undefined && (
              <View style={styles.scoreRow}>
                <Text style={styles.scoreLabel}>Readiness Score</Text>
                <Text style={styles.scoreValue}>{report.score}/100</Text>
              </View>
            )}
            {report.summary && (
              <Text style={styles.reportText}>{report.summary}</Text>
            )}
            {report.recommendations && Array.isArray(report.recommendations) && (
              <View style={styles.recommendationsSection}>
                <Text style={styles.recommendationsTitle}>Recommendations</Text>
                {report.recommendations.map((rec: string, index: number) => (
                  <View key={index} style={styles.recommendationRow}>
                    <Text style={styles.recommendationBullet}>•</Text>
                    <Text style={styles.recommendationText}>{rec}</Text>
                  </View>
                ))}
              </View>
            )}
            {!report.score && !report.summary && (
              <Text style={styles.reportText}>{JSON.stringify(report, null, 2)}</Text>
            )}
          </View>
        )}
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
  title: {
    fontSize: fontSize.xl,
    fontWeight: '700',
    color: colors.text,
  },
  subtitle: {
    fontSize: fontSize.sm,
    color: colors.textMuted,
    marginTop: spacing.xs,
    marginBottom: spacing.lg,
  },
  card: {
    backgroundColor: colors.bgElevated,
    borderRadius: 12,
    padding: spacing.lg,
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
    lineHeight: 20,
  },
  button: {
    backgroundColor: colors.accentTeal,
    borderRadius: 8,
    padding: spacing.md,
    alignItems: 'center',
  },
  buttonText: {
    color: colors.text,
    fontSize: fontSize.md,
    fontWeight: '600',
  },
  reportCard: {
    backgroundColor: colors.bgElevated,
    borderRadius: 12,
    padding: spacing.lg,
    marginTop: spacing.md,
    borderWidth: 1,
    borderColor: colors.accentTeal,
  },
  reportTitle: {
    fontSize: fontSize.lg,
    fontWeight: '600',
    color: colors.accentTealLight,
    marginBottom: spacing.md,
  },
  scoreRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    backgroundColor: colors.successBg,
    borderRadius: 8,
    padding: spacing.md,
    marginBottom: spacing.md,
  },
  scoreLabel: {
    fontSize: fontSize.md,
    color: colors.text,
  },
  scoreValue: {
    fontSize: fontSize.xl,
    fontWeight: '700',
    color: colors.accentTealLight,
  },
  reportText: {
    fontSize: fontSize.sm,
    color: colors.textMuted,
    lineHeight: 20,
  },
  recommendationsSection: {
    marginTop: spacing.md,
  },
  recommendationsTitle: {
    fontSize: fontSize.md,
    fontWeight: '600',
    color: colors.accentGold,
    marginBottom: spacing.sm,
  },
  recommendationRow: {
    flexDirection: 'row',
    marginBottom: spacing.xs,
  },
  recommendationBullet: {
    color: colors.accentTeal,
    fontSize: fontSize.md,
    marginRight: spacing.sm,
  },
  recommendationText: {
    fontSize: fontSize.sm,
    color: colors.textMuted,
    flex: 1,
    lineHeight: 20,
  },
});
