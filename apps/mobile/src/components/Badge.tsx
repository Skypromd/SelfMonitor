import React from 'react';
import { StyleSheet, Text, View } from 'react-native';

import { colors, radius, spacing } from '../theme';

type BadgeTone = 'neutral' | 'success' | 'warning' | 'danger' | 'info';

type BadgeProps = {
  label: string;
  tone?: BadgeTone;
};

const toneStyles: Record<BadgeTone, { background: string; text: string }> = {
  neutral: { background: '#e2e8f0', text: colors.textSecondary },
  success: { background: '#dcfce7', text: colors.success },
  warning: { background: '#fef9c3', text: colors.warning },
  danger: { background: '#fee2e2', text: colors.danger },
  info: { background: '#e0f2fe', text: colors.info },
};

export default function Badge({ label, tone = 'neutral' }: BadgeProps) {
  const toneStyle = toneStyles[tone];
  return (
    <View style={[styles.badge, { backgroundColor: toneStyle.background }]}>
      <Text style={[styles.text, { color: toneStyle.text }]}>{label}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  badge: {
    alignSelf: 'flex-start',
    paddingVertical: spacing.xs,
    paddingHorizontal: spacing.sm,
    borderRadius: radius.sm,
  },
  text: {
    fontSize: 12,
    fontWeight: '600',
  },
});
