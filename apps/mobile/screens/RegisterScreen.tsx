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
import { useNavigation } from '@react-navigation/native';
import { LinearGradient } from 'expo-linear-gradient';
import { colors, spacing, fontSize, borderRadius } from '../theme';
import { useAuth } from '../context/AuthContext';

function getPasswordStrength(pw: string): { label: string; color: string; ratio: number } {
  if (pw.length === 0) return { label: '', color: colors.bgCard, ratio: 0 };
  let score = 0;
  if (pw.length >= 8) score++;
  if (/[A-Z]/.test(pw)) score++;
  if (/[0-9]/.test(pw)) score++;
  if (/[^A-Za-z0-9]/.test(pw)) score++;
  if (score <= 1) return { label: 'Weak', color: colors.expense, ratio: 0.25 };
  if (score === 2) return { label: 'Fair', color: colors.warning, ratio: 0.5 };
  if (score === 3) return { label: 'Good', color: colors.accentTeal, ratio: 0.75 };
  return { label: 'Strong', color: colors.income, ratio: 1 };
}

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

export default function RegisterScreen() {
  const navigation = useNavigation<any>();
  const { register, login } = useAuth();
  const [fullName, setFullName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState<{ text: string; type: 'error' | 'success' } | null>(null);

  const strength = getPasswordStrength(password);

  async function handleRegister() {
    if (!email || !password) {
      setMessage({ text: 'Email and password are required', type: 'error' });
      return;
    }
    if (password.length < 6) {
      setMessage({ text: 'Password must be at least 6 characters', type: 'error' });
      return;
    }
    setLoading(true);
    setMessage(null);
    try {
      await register(email, password);
      await login(email, password);
    } catch (err: any) {
      setMessage({ text: err.message || 'Registration failed', type: 'error' });
      Alert.alert('Error', err.message || 'Registration failed');
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
            <Text style={styles.headline}>Start your free trial</Text>
            <Text style={styles.subheadline}>
              Financial tools built for the self-employed
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
            <Text style={styles.label}>Full Name (optional)</Text>
            <TextInput
              style={styles.input}
              placeholder="Jane Doe"
              placeholderTextColor={colors.textMuted}
              value={fullName}
              onChangeText={setFullName}
              autoCapitalize="words"
              autoComplete="name"
            />

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
              placeholder="Create a password"
              placeholderTextColor={colors.textMuted}
              value={password}
              onChangeText={setPassword}
              secureTextEntry
              autoComplete="password-new"
            />

            {password.length > 0 && (
              <View style={styles.strengthContainer}>
                <View style={styles.strengthTrack}>
                  <Animated.View
                    style={[
                      styles.strengthFill,
                      {
                        backgroundColor: strength.color,
                        width: `${strength.ratio * 100}%`,
                      },
                    ]}
                  />
                </View>
                <Text style={[styles.strengthLabel, { color: strength.color }]}>
                  {strength.label}
                </Text>
              </View>
            )}

            {loading ? (
              <ActivityIndicator
                size="large"
                color={colors.accentTeal}
                style={styles.loader}
              />
            ) : (
              <AnimatedPressable onPress={handleRegister}>
                <LinearGradient
                  colors={[colors.gradientStart, colors.gradientEnd]}
                  start={{ x: 0, y: 0 }}
                  end={{ x: 1, y: 0 }}
                  style={styles.buttonPrimary}
                >
                  <Text style={styles.buttonText}>Start Free Trial</Text>
                </LinearGradient>
              </AnimatedPressable>
            )}
          </View>

          <View style={styles.terms}>
            <Text style={styles.termsText}>
              By signing up you agree to our{' '}
              <Text style={styles.linkText}>Terms</Text> and{' '}
              <Text style={styles.linkText}>Privacy Policy</Text>
            </Text>
          </View>

          <TouchableOpacity
            style={styles.loginLink}
            onPress={() => navigation.navigate('Login')}
          >
            <Text style={styles.loginLinkText}>
              Already have an account?{' '}
              <Text style={styles.loginLinkBold}>Log In</Text>
            </Text>
          </TouchableOpacity>
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
  headline: {
    fontSize: fontSize.lg,
    fontWeight: '600',
    color: colors.text,
    marginTop: spacing.sm,
  },
  subheadline: {
    fontSize: fontSize.sm,
    color: colors.textMuted,
    marginTop: spacing.xs,
    textAlign: 'center',
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
  strengthContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    marginTop: spacing.sm,
    gap: spacing.sm,
  },
  strengthTrack: {
    flex: 1,
    height: 4,
    backgroundColor: colors.bgElevated,
    borderRadius: 2,
    overflow: 'hidden',
  },
  strengthFill: {
    height: '100%',
    borderRadius: 2,
  },
  strengthLabel: {
    fontSize: fontSize.xs,
    fontWeight: '700',
    width: 50,
  },
  buttonPrimary: {
    borderRadius: borderRadius.md,
    padding: spacing.md,
    alignItems: 'center',
    marginTop: spacing.lg,
  },
  buttonText: {
    color: colors.text,
    fontSize: fontSize.md,
    fontWeight: '700',
  },
  loader: {
    marginTop: spacing.lg,
  },
  terms: {
    marginTop: spacing.lg,
    alignItems: 'center',
  },
  termsText: {
    fontSize: fontSize.xs,
    color: colors.textMuted,
    textAlign: 'center',
    lineHeight: 18,
  },
  linkText: {
    color: colors.accentTeal,
    textDecorationLine: 'underline',
  },
  loginLink: {
    marginTop: spacing.lg,
    alignItems: 'center',
  },
  loginLinkText: {
    fontSize: fontSize.sm,
    color: colors.textMuted,
  },
  loginLinkBold: {
    color: colors.accentTeal,
    fontWeight: '700',
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
