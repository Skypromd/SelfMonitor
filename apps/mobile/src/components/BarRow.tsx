import React from 'react';
import { StyleSheet, Text, View } from 'react-native';

import { colors, spacing } from '../theme';

type BarRowProps = {
  label: string;
  value: number;
  maxValue: number;
  valueLabel?: string;
  tone?: 'primary' | 'success' | 'warning';
};

const toneColor = {
  primary: colors.primary,
  success: colors.success,
  warning: colors.warning,
};

export default function BarRow({ label, value, maxValue, valueLabel, tone = 'primary' }: BarRowProps) {
  const percent = maxValue > 0 ? Math.min(Math.abs(value) / maxValue, 1) : 0;
  const width = `${Math.round(percent * 100)}%`;

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.label}>{label}</Text>
        <Text style={styles.value}>{valueLabel ?? value.toFixed(2)}</Text>
      </View>
      <View style={styles.track}>
        <View style={[styles.fill, { width, backgroundColor: toneColor[tone] }]} />
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    marginBottom: spacing.md,
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: spacing.xs,
  },
  label: {
    color: colors.textSecondary,
    fontSize: 12,
    fontWeight: '600',
  },
  value: {
    color: colors.textPrimary,
    fontSize: 12,
    fontWeight: '600',
  },
  track: {
    height: 8,
    backgroundColor: colors.surfaceAlt,
    borderRadius: 999,
    overflow: 'hidden',
  },
  fill: {
    height: '100%',
    borderRadius: 999,
  },
});
