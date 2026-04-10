import React, { useState, useRef } from 'react';
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  Alert,
  Animated,
  Share,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { colors, spacing, fontSize, borderRadius } from '../theme';

function AnimatedPressable({
  onPress,
  style,
  children,
}: {
  onPress: () => void;
  style?: object;
  children: React.ReactNode;
}) {
  const scale = useRef(new Animated.Value(1)).current;
  return (
    <Animated.View style={[{ transform: [{ scale }] }, style]}>
      <TouchableOpacity
        onPress={onPress}
        onPressIn={() =>
          Animated.spring(scale, { toValue: 0.96, useNativeDriver: true }).start()
        }
        onPressOut={() =>
          Animated.spring(scale, { toValue: 1, friction: 3, useNativeDriver: true }).start()
        }
        activeOpacity={0.9}
      >
        {children}
      </TouchableOpacity>
    </Animated.View>
  );
}

export default function ReferralsScreen() {
  const [code] = useState('ABCD1234');
  const invited = 3;
  const earned = 75;

  const copyCode = () => {
    Alert.alert('Copied!', `Referral code "${code}" copied to clipboard`);
  };

  const shareCode = async () => {
    try {
      await Share.share({
        message: `Join SelfMonitor with my referral code ${code} and we both get £25! https://selfmonitor.app/refer/${code}`,
      });
    } catch {
      Alert.alert('Error', 'Could not share referral code');
    }
  };

  return (
    <SafeAreaView style={styles.container} edges={['top']}>
      <View style={styles.content}>
        <Text style={styles.title}>🎁 Referrals</Text>
        <Text style={styles.subtitle}>
          Invite a friend → you both get £25
        </Text>

        <TouchableOpacity
          style={styles.codeCard}
          onPress={copyCode}
          activeOpacity={0.8}
        >
          <Text style={styles.codeLabel}>Your Referral Code</Text>
          <Text style={styles.codeValue}>{code}</Text>
          <Text style={styles.codeTap}>Tap to copy</Text>
        </TouchableOpacity>

        <AnimatedPressable onPress={shareCode}>
          <View style={styles.shareButton}>
            <Text style={styles.shareButtonText}>Share Code</Text>
          </View>
        </AnimatedPressable>

        <View style={styles.statsCard}>
          <View style={styles.statRow}>
            <Text style={styles.statLabel}>Friends invited</Text>
            <Text style={styles.statValue}>{invited}</Text>
          </View>
          <View style={[styles.statRow, { borderBottomWidth: 0 }]}>
            <Text style={styles.statLabel}>Total earned</Text>
            <Text style={[styles.statValue, { color: colors.income }]}>
              £{earned}
            </Text>
          </View>
        </View>
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.bg,
  },
  content: {
    padding: spacing.lg,
  },
  title: {
    fontSize: fontSize.xl,
    fontWeight: '800',
    color: colors.text,
    marginBottom: spacing.xs,
  },
  subtitle: {
    fontSize: fontSize.md,
    color: colors.textSecondary,
    marginBottom: spacing.xl,
  },
  codeCard: {
    backgroundColor: colors.bgCard,
    borderRadius: borderRadius.xl,
    padding: spacing.xl,
    alignItems: 'center',
    borderWidth: 2,
    borderColor: colors.accentTeal,
    marginBottom: spacing.lg,
  },
  codeLabel: {
    fontSize: fontSize.xs,
    color: colors.textMuted,
    textTransform: 'uppercase',
    letterSpacing: 1,
    marginBottom: spacing.sm,
  },
  codeValue: {
    fontSize: fontSize.hero,
    fontWeight: '800',
    color: colors.accentTeal,
    letterSpacing: 4,
  },
  codeTap: {
    fontSize: fontSize.xs,
    color: colors.textMuted,
    marginTop: spacing.sm,
  },
  shareButton: {
    backgroundColor: colors.accentTeal,
    borderRadius: borderRadius.md,
    padding: spacing.md,
    alignItems: 'center',
    marginBottom: spacing.xl,
  },
  shareButtonText: {
    color: colors.textInverse,
    fontSize: fontSize.md,
    fontWeight: '700',
  },
  statsCard: {
    backgroundColor: colors.bgCard,
    borderRadius: borderRadius.lg,
    padding: spacing.lg,
    borderWidth: 1,
    borderColor: colors.border,
  },
  statRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    paddingVertical: spacing.md,
    borderBottomWidth: 1,
    borderBottomColor: colors.border,
  },
  statLabel: {
    fontSize: fontSize.md,
    color: colors.textSecondary,
  },
  statValue: {
    fontSize: fontSize.md,
    fontWeight: '700',
    color: colors.text,
  },
});
