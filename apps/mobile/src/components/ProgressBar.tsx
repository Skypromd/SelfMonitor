import React, { useEffect, useRef } from 'react';
import { Animated, StyleSheet, View } from 'react-native';

import { colors, radius } from '../theme';

type ProgressBarProps = {
  value: number;
  tone?: 'primary' | 'success' | 'warning';
};

const toneColor = {
  primary: colors.primary,
  success: colors.success,
  warning: colors.warning,
};

export default function ProgressBar({ value, tone = 'primary' }: ProgressBarProps) {
  const progress = useRef(new Animated.Value(0)).current;
  const clamped = Math.max(0, Math.min(1, value));

  useEffect(() => {
    Animated.timing(progress, {
      toValue: clamped,
      duration: 700,
      useNativeDriver: false,
    }).start();
  }, [clamped, progress]);

  const width = progress.interpolate({
    inputRange: [0, 1],
    outputRange: ['0%', '100%'],
  });

  return (
    <View style={styles.track}>
      <Animated.View style={[styles.fill, { width, backgroundColor: toneColor[tone] }]} />
    </View>
  );
}

const styles = StyleSheet.create({
  track: {
    height: 8,
    backgroundColor: colors.surfaceAlt,
    borderRadius: radius.sm,
    overflow: 'hidden',
  },
  fill: {
    height: '100%',
    borderRadius: radius.sm,
  },
});
