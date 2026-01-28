import React, { useState } from 'react';
import { View, Text, TextInput, StyleSheet } from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';

import PrimaryButton from '../components/PrimaryButton';
import Card from '../components/Card';
import { useAuth } from '../context/AuthContext';
import { apiRequest } from '../services/api';
import { useTranslation } from '../hooks/useTranslation';
import { colors, spacing } from '../theme';

export default function LoginScreen() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const { signIn } = useAuth();
  const { t } = useTranslation();

  const handleLogin = async () => {
    setError('');
    setMessage('');
    try {
      const formData = new URLSearchParams();
      formData.append('username', email);
      formData.append('password', password);
      const response = await apiRequest('/auth/token', {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: formData.toString(),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || 'Login failed');
      await signIn(data.access_token);
    } catch (err: any) {
      setError(err.message);
    }
  };

  const handleRegister = async () => {
    setError('');
    setMessage('');
    try {
      const formData = new URLSearchParams();
      formData.append('username', email);
      formData.append('password', password);
      const response = await apiRequest('/auth/register', {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: formData.toString(),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || 'Registration failed');
      setMessage(t('auth.register_success'));
    } catch (err: any) {
      setError(err.message);
    }
  };

  return (
    <LinearGradient colors={['#eff6ff', '#f8fafc']} style={styles.container}>
      <Card>
        <Text style={styles.title}>{t('auth.login_title')}</Text>
        <TextInput
          placeholder={t('auth.email_placeholder')}
          value={email}
          onChangeText={setEmail}
          autoCapitalize="none"
          keyboardType="email-address"
          style={styles.input}
        />
        <TextInput
          placeholder={t('auth.password_placeholder')}
          value={password}
          onChangeText={setPassword}
          secureTextEntry
          style={styles.input}
        />
        <PrimaryButton title={t('auth.login_button')} onPress={handleLogin} />
        <View style={{ height: spacing.md }} />
        <PrimaryButton title={t('auth.register_button')} onPress={handleRegister} variant="secondary" />
        {message ? <Text style={styles.message}>{message}</Text> : null}
        {error ? <Text style={styles.error}>{error}</Text> : null}
      </Card>
    </LinearGradient>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    padding: spacing.xxl,
    justifyContent: 'center',
  },
  title: {
    fontSize: 24,
    fontWeight: '700',
    color: colors.textPrimary,
    marginBottom: spacing.lg,
  },
  input: {
    backgroundColor: colors.surface,
    borderRadius: 12,
    padding: spacing.md,
    borderWidth: 1,
    borderColor: colors.border,
    marginBottom: spacing.md,
  },
  message: {
    marginTop: spacing.md,
    color: colors.success,
  },
  error: {
    marginTop: spacing.md,
    color: colors.danger,
  },
});
