import React from 'react';
import { StyleSheet, Text, View } from 'react-native';
import { Ionicons } from '@expo/vector-icons';

import Card from './Card';
import { colors, spacing } from '../theme';

type StatCardProps = {
  label: string;
  value: string;
  icon: keyof typeof Ionicons.glyphMap;
  tone?: 'primary' | 'success' | 'warning';
};

const toneColor = {
  primary: colors.primary,
  success: colors.success,
  warning: colors.warning,
};

export default function StatCard({ label, value, icon, tone = 'primary' }: StatCardProps) {
  return (
    <Card>
      <View style={styles.row}>
        <Ionicons name={icon} size={24} color={toneColor[tone]} />
        <Text style={styles.label}>{label}</Text>
      </View>
      <Text style={styles.value}>{value}</Text>
    </Card>
  );
}

const styles = StyleSheet.create({
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: spacing.sm,
  },
  label: {
    color: colors.textSecondary,
    fontSize: 14,
    marginLeft: spacing.sm,
  },
  value: {
    fontSize: 26,
    fontWeight: '700',
    color: colors.textPrimary,
  },
});
