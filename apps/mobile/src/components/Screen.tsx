import React from 'react';
import { ScrollView, StyleSheet, Text, View, ViewStyle } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { colors, spacing } from '../theme';
import { useNetworkStatus } from '../hooks/useNetworkStatus';
import { useTranslation } from '../hooks/useTranslation';

type ScreenProps = {
  children: React.ReactNode;
  style?: ViewStyle;
  showOfflineBanner?: boolean;
};

export default function Screen({ children, style, showOfflineBanner = true }: ScreenProps) {
  const { isOffline } = useNetworkStatus();
  const { t } = useTranslation();

  return (
    <SafeAreaView style={styles.safe}>
      <ScrollView contentContainerStyle={[styles.content, style]}>
        {showOfflineBanner && isOffline ? (
          <View style={styles.banner}>
            <Text style={styles.bannerTitle}>{t('common.offline_title')}</Text>
            <Text style={styles.bannerSubtitle}>{t('common.offline_subtitle')}</Text>
          </View>
        ) : null}
        {children}
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: {
    flex: 1,
    backgroundColor: colors.background,
  },
  content: {
    padding: spacing.lg,
  },
  banner: {
    backgroundColor: '#fef3c7',
    borderRadius: 16,
    padding: spacing.md,
    borderWidth: 1,
    borderColor: '#fde68a',
    marginBottom: spacing.lg,
  },
  bannerTitle: {
    color: '#92400e',
    fontWeight: '700',
    marginBottom: spacing.xs,
  },
  bannerSubtitle: {
    color: '#92400e',
    fontSize: 12,
  },
});
