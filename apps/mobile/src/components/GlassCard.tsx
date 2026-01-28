import React from 'react';
import { StyleSheet, View, ViewStyle } from 'react-native';
import { BlurView } from 'expo-blur';

import { colors, radius, shadow, spacing } from '../theme';

type GlassCardProps = {
  children: React.ReactNode;
  style?: ViewStyle;
  intensity?: number;
};

export default function GlassCard({ children, style, intensity = 25 }: GlassCardProps) {
  return (
    <View style={[styles.wrapper, style]}>
      <BlurView tint="light" intensity={intensity} style={styles.blur}>
        <View style={styles.content}>{children}</View>
      </BlurView>
    </View>
  );
}

const styles = StyleSheet.create({
  wrapper: {
    borderRadius: radius.lg,
    overflow: 'hidden',
    borderWidth: 1,
    borderColor: 'rgba(148, 163, 184, 0.35)',
    ...shadow.card,
  },
  blur: {
    borderRadius: radius.lg,
  },
  content: {
    padding: spacing.lg,
    backgroundColor: 'rgba(255, 255, 255, 0.6)',
  },
});
