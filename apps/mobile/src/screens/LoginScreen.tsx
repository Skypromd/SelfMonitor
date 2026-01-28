import React, { useState } from 'react';
import { View, Text, TextInput, StyleSheet } from 'react-native';

import PrimaryButton from '../components/PrimaryButton';
import { useAuth } from '../context/AuthContext';
import { apiRequest } from '../services/api';
import { useTranslation } from '../hooks/useTranslation';

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
    <View style={styles.container}>
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
      <View style={{ height: 12 }} />
      <PrimaryButton title={t('auth.register_button')} onPress={handleRegister} />
      {message ? <Text style={styles.message}>{message}</Text> : null}
      {error ? <Text style={styles.error}>{error}</Text> : null}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    padding: 24,
    justifyContent: 'center',
    backgroundColor: '#f8fafc',
  },
  title: {
    fontSize: 24,
    fontWeight: '700',
    color: '#0f172a',
    marginBottom: 16,
  },
  input: {
    backgroundColor: '#ffffff',
    borderRadius: 12,
    padding: 12,
    borderWidth: 1,
    borderColor: '#e2e8f0',
    marginBottom: 12,
  },
  message: {
    marginTop: 12,
    color: '#16a34a',
  },
  error: {
    marginTop: 12,
    color: '#dc2626',
  },
});
