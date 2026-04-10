import React, { useState, useRef } from 'react';
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
  Animated,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { LinearGradient } from 'expo-linear-gradient';
import { colors, spacing, fontSize, borderRadius } from '../theme';
import { useAuth } from '../context/AuthContext';

function AnimatedPressable({
  onPress,
  style,
  children,
  disabled,
}: {
  onPress: () => void;
  style?: any;
  children: React.ReactNode;
  disabled?: boolean;
}) {
  const scale = useRef(new Animated.Value(1)).current;

  return (
    <Animated.View style={[{ transform: [{ scale }] }, style]}>
      <TouchableOpacity
        onPress={onPress}
        onPressIn={() =>
          Animated.spring(scale, { toValue: 0.97, useNativeDriver: true }).start()
        }
        onPressOut={() =>
          Animated.spring(scale, { toValue: 1, friction: 3, useNativeDriver: true }).start()
        }
        activeOpacity={0.9}
        disabled={disabled}
      >
        {children}
      </TouchableOpacity>
    </Animated.View>
  );
}

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
        <ScrollView
          contentContainerStyle={styles.scroll}
          keyboardShouldPersistTaps="handled"
          showsVerticalScrollIndicator={false}
        >
          {/* Brand */}
          <View style={styles.brandSection}>
            <View style={styles.logoCircle}>
              <Text style={styles.logoEmoji}>💎</Text>
            </View>
            <Text style={styles.brandName}>SelfMonitor</Text>
            <Text style={styles.tagline}>
              Financial Dashboard for the Self-Employed
            </Text>
          </View>

          {message && (
            <View
              style={[
                styles.messageBox,
                message.type === 'error' ? styles.errorBox : styles.successBox,
              ]}
            >
              <Text
                style={[
                  styles.messageText,
                  message.type === 'error' ? styles.errorText : styles.successText,
                ]}
              >
                {message.text}
              </Text>
            </View>
          )}

          {/* Form Card */}
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
              <ActivityIndicator
                size="large"
                color={colors.accentTeal}
                style={styles.loader}
              />
            ) : (
              <View style={styles.buttonRow}>
                <AnimatedPressable onPress={handleLogin} style={styles.buttonFlex}>
                  <LinearGradient
                    colors={[colors.gradientStart, colors.gradientEnd]}
                    start={{ x: 0, y: 0 }}
                    end={{ x: 1, y: 0 }}
                    style={styles.buttonPrimary}
                  >
                    <Text style={styles.buttonText}>Login</Text>
                  </LinearGradient>
                </AnimatedPressable>
                <AnimatedPressable onPress={handleRegister} style={styles.buttonFlex}>
                  <View style={styles.buttonSecondary}>
                    <Text style={styles.buttonSecondaryText}>Register</Text>
                  </View>
                </AnimatedPressable>
              </View>
            )}
          </View>

          <View style={styles.footer}>
            <Text style={styles.footerText}>
              Secure login powered by SelfMonitor
            </Text>
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
  brandSection: {
    alignItems: 'center',
    marginBottom: spacing.xl,
  },
  logoCircle: {
    width: 72,
    height: 72,
    borderRadius: 36,
    backgroundColor: colors.accentTealBg,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: spacing.md,
  },
  logoEmoji: {
    fontSize: 32,
  },
  brandName: {
    fontSize: fontSize.xxl,
    fontWeight: '800',
    color: colors.accentTeal,
    letterSpacing: -0.5,
  },
  tagline: {
    fontSize: fontSize.sm,
    color: colors.textMuted,
    textAlign: 'center',
    marginTop: spacing.sm,
  },
  card: {
    backgroundColor: colors.bgCard,
    borderRadius: borderRadius.xl,
    padding: spacing.lg,
    borderWidth: 1,
    borderColor: colors.border,
  },
  label: {
    fontSize: fontSize.xs,
    color: colors.textMuted,
    marginBottom: spacing.xs,
    marginTop: spacing.md,
    textTransform: 'uppercase',
    letterSpacing: 0.5,
  },
  input: {
    backgroundColor: colors.bgElevated,
    borderRadius: borderRadius.sm,
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
  buttonFlex: {
    flex: 1,
  },
  buttonPrimary: {
    borderRadius: borderRadius.md,
    padding: spacing.md,
    alignItems: 'center',
  },
  buttonSecondary: {
    backgroundColor: 'transparent',
    borderRadius: borderRadius.md,
    padding: spacing.md,
    alignItems: 'center',
    borderWidth: 1,
    borderColor: colors.accentTeal,
  },
  buttonText: {
    color: colors.text,
    fontSize: fontSize.md,
    fontWeight: '700',
  },
  buttonSecondaryText: {
    color: colors.accentTeal,
    fontSize: fontSize.md,
    fontWeight: '700',
  },
  loader: {
    marginTop: spacing.lg,
  },
  footer: {
    marginTop: spacing.xl,
    alignItems: 'center',
  },
  footerText: {
    fontSize: fontSize.xs,
    color: colors.textMuted,
  },
  messageBox: {
    borderRadius: borderRadius.md,
    padding: spacing.md,
    marginBottom: spacing.md,
  },
  errorBox: {
    backgroundColor: colors.expenseBg,
  },
  successBox: {
    backgroundColor: colors.incomeBg,
  },
  messageText: {
    fontSize: fontSize.sm,
  },
  errorText: {
    color: colors.expense,
  },
  successText: {
    color: colors.income,
  },
});
