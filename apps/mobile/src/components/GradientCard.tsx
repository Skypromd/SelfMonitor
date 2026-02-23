import React from 'react';
import { StyleSheet, ViewStyle } from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';

import { radius, spacing } from '../theme';

type GradientCardProps = {
  children: React.ReactNode;
  colors: string[];
  style?: ViewStyle;
};

export default function GradientCard({ children, colors, style }: GradientCardProps) {
  return (
    <LinearGradient colors={colors} style={[styles.card, style]}>
      {children}
    </LinearGradient>
  );
}

const styles = StyleSheet.create({
  card: {
    borderRadius: radius.lg,
    padding: spacing.lg,
    marginBottom: spacing.lg,
  },
});
