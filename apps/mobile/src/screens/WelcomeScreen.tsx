import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { useNavigation } from '@react-navigation/native';
import { LinearGradient } from 'expo-linear-gradient';

import PrimaryButton from '../components/PrimaryButton';
import { useTranslation } from '../hooks/useTranslation';
import { colors, spacing } from '../theme';

export default function WelcomeScreen() {
  const navigation = useNavigation();
  const { t } = useTranslation();

  return (
    <LinearGradient colors={['#0f172a', '#1e293b']} style={styles.container}>
      <View style={styles.card}>
        <Text style={styles.title}>{t('auth.welcome_title')}</Text>
        <Text style={styles.subtitle}>{t('auth.welcome_subtitle')}</Text>
        <PrimaryButton title={t('common.continue')} onPress={() => navigation.navigate('Login' as never)} />
      </View>
    </LinearGradient>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    justifyContent: 'center',
    padding: spacing.xxl,
  },
  card: {
    backgroundColor: 'rgba(15, 23, 42, 0.7)',
    borderRadius: 20,
    padding: spacing.xxl,
    borderWidth: 1,
    borderColor: 'rgba(148, 163, 184, 0.3)',
  },
  title: {
    fontSize: 28,
    fontWeight: '700',
    color: colors.surface,
    marginBottom: spacing.md,
  },
  subtitle: {
    color: '#cbd5f5',
    fontSize: 16,
    marginBottom: spacing.xl,
  },
});
