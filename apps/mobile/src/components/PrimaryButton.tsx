import React from 'react';
import { Pressable, Text, StyleSheet, ViewStyle } from 'react-native';

import { colors, radius, spacing } from '../theme';

type PrimaryButtonProps = {
  title: string;
  onPress: () => void;
  disabled?: boolean;
  variant?: 'primary' | 'secondary';
  style?: ViewStyle;
};

export default function PrimaryButton({ title, onPress, disabled, variant = 'primary', style }: PrimaryButtonProps) {
  const isSecondary = variant === 'secondary';
  return (
    <Pressable
      onPress={onPress}
      disabled={disabled}
      style={({ pressed }) => [
        styles.button,
        isSecondary && styles.secondary,
        pressed && styles.pressed,
        disabled && styles.disabled,
        style,
      ]}
    >
      <Text style={[styles.text, isSecondary && styles.secondaryText]}>{title}</Text>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  button: {
    backgroundColor: colors.primary,
    paddingVertical: spacing.md,
    paddingHorizontal: spacing.lg,
    borderRadius: radius.md,
    alignItems: 'center',
    borderWidth: 1,
    borderColor: colors.primary,
  },
  secondary: {
    backgroundColor: colors.surface,
    borderColor: colors.border,
  },
  pressed: {
    opacity: 0.9,
  },
  disabled: {
    backgroundColor: '#94a3b8',
  },
  text: {
    color: colors.surface,
    fontWeight: '600',
    fontSize: 15,
  },
  secondaryText: {
    color: colors.textPrimary,
  },
});
