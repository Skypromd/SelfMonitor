import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { useNavigation } from '@react-navigation/native';

import PrimaryButton from '../components/PrimaryButton';
import { useTranslation } from '../hooks/useTranslation';

export default function WelcomeScreen() {
  const navigation = useNavigation();
  const { t } = useTranslation();

  return (
    <View style={styles.container}>
      <Text style={styles.title}>{t('auth.welcome_title')}</Text>
      <Text style={styles.subtitle}>{t('auth.welcome_subtitle')}</Text>
      <PrimaryButton title={t('common.continue')} onPress={() => navigation.navigate('Login' as never)} />
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    padding: 24,
    justifyContent: 'center',
    backgroundColor: '#0f172a',
  },
  title: {
    fontSize: 28,
    fontWeight: '700',
    color: '#ffffff',
    marginBottom: 12,
  },
  subtitle: {
    color: '#cbd5f5',
    fontSize: 16,
    marginBottom: 24,
  },
});
