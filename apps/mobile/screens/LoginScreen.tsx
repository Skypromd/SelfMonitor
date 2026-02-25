import React, { useState } from 'react';
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  StyleSheet,
  ActivityIndicator,
  Alert,
  KeyboardAvoidingView,
  Platform,
  ScrollView,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { colors, spacing, fontSize } from '../theme';
import { useAuth } from '../context/AuthContext';

export default function LoginScreen() {
  const { login, register } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState<{ text: string; type: 'success' | 'error' } | null>(null);

  async function handleLogin() {
    if (!email || !password) {
      setMessage({ text: 'Please enter email and password', type: 'error' });
      return;
    }
    setLoading(true);
    setMessage(null);
    try {
      await login(email, password);
    } catch (err: any) {
      setMessage({ text: err.message || 'Login failed', type: 'error' });
      Alert.alert('Login Error', err.message || 'Login failed');
    } finally {
      setLoading(false);
    }
  }

  async function handleRegister() {
    if (!email || !password) {
      setMessage({ text: 'Please enter email and password', type: 'error' });
      return;
    }
    setLoading(true);
    setMessage(null);
    try {
      const registeredEmail = await register(email, password);
      setMessage({ text: `Registered ${registeredEmail}. You can now log in.`, type: 'success' });
    } catch (err: any) {
      setMessage({ text: err.message || 'Registration failed', type: 'error' });
      Alert.alert('Registration Error', err.message || 'Registration failed');
    } finally {
      setLoading(false);
    }
  }

  return (
    <SafeAreaView style={styles.container}>
      <KeyboardAvoidingView
        behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
        style={styles.flex}
      >
        <ScrollView contentContainerStyle={styles.scroll} keyboardShouldPersistTaps="handled">
          <Text style={styles.title}>SelfMonitor</Text>
          <Text style={styles.subtitle}>Financial Dashboard for the Self-Employed</Text>

          {message && (
            <View style={[styles.messageBox, message.type === 'error' ? styles.errorBox : styles.successBox]}>
              <Text style={[styles.messageText, message.type === 'error' ? styles.errorText : styles.successText]}>
                {message.text}
              </Text>
            </View>
          )}

          <View style={styles.card}>
            <Text style={styles.label}>Email</Text>
            <TextInput
              style={styles.input}
              placeholder="you@example.com"
              placeholderTextColor={colors.textMuted}
              value={email}
              onChangeText={setEmail}
              autoCapitalize="none"
              keyboardType="email-address"
              autoComplete="email"
            />

            <Text style={styles.label}>Password</Text>
            <TextInput
              style={styles.input}
              placeholder="Enter your password"
              placeholderTextColor={colors.textMuted}
              value={password}
              onChangeText={setPassword}
              secureTextEntry
              autoComplete="password"
            />

            {loading ? (
              <ActivityIndicator size="large" color={colors.accentTeal} style={styles.loader} />
            ) : (
              <View style={styles.buttonRow}>
                <TouchableOpacity style={styles.buttonPrimary} onPress={handleLogin}>
                  <Text style={styles.buttonText}>Login</Text>
                </TouchableOpacity>
                <TouchableOpacity style={styles.buttonSecondary} onPress={handleRegister}>
                  <Text style={styles.buttonSecondaryText}>Register</Text>
                </TouchableOpacity>
              </View>
            )}
          </View>
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.bg,
  },
  flex: {
    flex: 1,
  },
  scroll: {
    flexGrow: 1,
    justifyContent: 'center',
    padding: spacing.lg,
  },
  title: {
    fontSize: fontSize.xxl,
    fontWeight: '700',
    color: colors.accentTealLight,
    textAlign: 'center',
    marginBottom: spacing.xs,
  },
  subtitle: {
    fontSize: fontSize.sm,
    color: colors.textMuted,
    textAlign: 'center',
    marginBottom: spacing.xl,
  },
  card: {
    backgroundColor: colors.bgElevated,
    borderRadius: 12,
    padding: spacing.lg,
    borderWidth: 1,
    borderColor: colors.border,
  },
  label: {
    fontSize: fontSize.sm,
    color: colors.textMuted,
    marginBottom: spacing.xs,
    marginTop: spacing.md,
  },
  input: {
    backgroundColor: colors.bgCard,
    borderRadius: 8,
    padding: spacing.md,
    color: colors.text,
    fontSize: fontSize.md,
    borderWidth: 1,
    borderColor: colors.border,
  },
  buttonRow: {
    flexDirection: 'row',
    gap: spacing.md,
    marginTop: spacing.lg,
  },
  buttonPrimary: {
    flex: 1,
    backgroundColor: colors.accentTeal,
    borderRadius: 8,
    padding: spacing.md,
    alignItems: 'center',
  },
  buttonSecondary: {
    flex: 1,
    backgroundColor: 'transparent',
    borderRadius: 8,
    padding: spacing.md,
    alignItems: 'center',
    borderWidth: 1,
    borderColor: colors.accentTeal,
  },
  buttonText: {
    color: colors.text,
    fontSize: fontSize.md,
    fontWeight: '600',
  },
  buttonSecondaryText: {
    color: colors.accentTealLight,
    fontSize: fontSize.md,
    fontWeight: '600',
  },
  loader: {
    marginTop: spacing.lg,
  },
  messageBox: {
    borderRadius: 8,
    padding: spacing.md,
    marginBottom: spacing.md,
  },
  errorBox: {
    backgroundColor: colors.errorBg,
  },
  successBox: {
    backgroundColor: colors.successBg,
  },
  messageText: {
    fontSize: fontSize.sm,
  },
  errorText: {
    color: colors.error,
  },
  successText: {
    color: colors.success,
  },
});
