import React from 'react';
import { Image, Pressable, StyleSheet, Text, View } from 'react-native';

import { colors, radius, spacing } from '../theme';

type ChipProps = {
  label: string;
  selected?: boolean;
  onPress?: () => void;
  logoUrl?: string;
};

export default function Chip({ label, selected, onPress, logoUrl }: ChipProps) {
  return (
    <Pressable
      onPress={onPress}
      style={({ pressed }) => [
        styles.chip,
        selected && styles.selected,
        pressed && styles.pressed,
      ]}
    >
      <View style={styles.inner}>
        {logoUrl ? (
          <Image source={{ uri: logoUrl }} style={styles.logo} accessibilityIgnoresInvertColors />
        ) : null}
        <Text style={[styles.text, selected && styles.textSelected]}>{label}</Text>
      </View>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  chip: {
    borderRadius: radius.sm,
    borderWidth: 1,
    borderColor: colors.border,
    paddingVertical: spacing.xs,
    paddingHorizontal: spacing.sm,
    backgroundColor: colors.surface,
  },
  inner: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
  },
  logo: {
    width: 16,
    height: 16,
    borderRadius: 4,
  },
  selected: {
    borderColor: colors.primary,
    backgroundColor: '#eff6ff',
  },
  pressed: {
    opacity: 0.9,
  },
  text: {
    color: colors.textSecondary,
    fontWeight: '600',
    fontSize: 12,
  },
  textSelected: {
    color: colors.primaryDark,
  },
});
