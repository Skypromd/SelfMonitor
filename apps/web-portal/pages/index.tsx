import { FormEvent, useMemo, useState } from 'react';
import { useTranslation } from '../hooks/useTranslation';
import styles from '../styles/Home.module.css';

const AUTH_SERVICE_URL = process.env.NEXT_PUBLIC_AUTH_SERVICE_URL || 'http://localhost:8001';

type IndexPageProps = {
  onLoginSuccess: (newToken: string) => void;
};

function getPasswordChecks(password: string) {
  return {
    length: password.length >= 8,
    uppercase: /[A-Z]/.test(password),
    lowercase: /[a-z]/.test(password),
    digit: /\d/.test(password),
    special: /[!@#$%^&*()_+\-=[\]{};':"\\|,.<>/?`~]/.test(password),
  };
}

function getStrength(checks: ReturnType<typeof getPasswordChecks>) {
  const passed = Object.values(checks).filter(Boolean).length;
  if (passed >= 5) return 'strong';
  if (passed >= 3) return 'medium';
  return 'weak';
}

const FEATURES = [
  {
    icon: '🧾',
    title: 'Smart Invoicing',
    desc: 'Create professional invoices with line items, VAT support, PDF export and one-click send. Track paid, overdue and draft invoices in one place.',
  },
  {
    icon: '📊',
    title: 'Transaction Analytics',
    desc: 'Automatically categorise income and expenses via AI. Visualise spending patterns, cash flow and profit trends with interactive charts.',
  },
  {
    icon: '📅',
    title: 'Tax Calendar',
    desc: 'Never miss a HMRC deadline. Built-in reminders for Self Assessment (Jan 31), Payment on Account, VAT returns and P60 filing dates.',
  },
  {
    icon: '🤖',
    title: 'AI Tax Assistant',
    desc: 'Ask anything about UK self-employment tax, NI thresholds, Trading Allowance or expense deductions — get instant, context-aware answers.',
  },
  {
    icon: '💷',
    title: 'Cash Flow Forecasting',
    desc: 'Predict your financial position 30, 60 and 90 days ahead based on recurring income, upcoming invoices and projected expenses.',
  },
  {
    icon: '🔒',
    title: 'Bank-Grade Security',
    desc: 'Two-factor authentication (TOTP), device session management, account lockdown, full security event log and encrypted data at rest.',
  },
  {
    icon: '📂',
    title: 'Document Storage',
    desc: 'Upload and organise receipts, contracts and tax documents. Instantly retrievable for Self Assessment or accountant review.',
  },
  {
    icon: '🌍',
    title: 'Multi-Currency Support',
    desc: 'Invoice clients in GBP, EUR, USD, PLN, RON, UAH and more. Real-time rate conversion for accurate profit tracking across currencies.',
  },
  {
    icon: '🎁',
    title: 'Referral Programme',
    desc: 'Earn rewards by referring other freelancers. Share your unique code, track conversions and see your earnings on a live leaderboard.',
  },
  {
    icon: '🏪',
    title: 'Partner Marketplace',
    desc: 'Access vetted accountants, legal advisors, insurance providers and fintech tools — all integrated with your financial data.',
  },
  {
    icon: '📈',
    title: 'Business Intelligence',
    desc: 'Executive-level dashboards: revenue trends, top clients, expense breakdowns and actionable recommendations powered by ML models.',
  },
  {
    icon: '✅',
    title: 'Compliance Engine',
    desc: 'Automated HMRC MTD compliance checks, audit trail logging, consent management and GDPR-ready data controls.',
  },
];

const ADVANTAGES = [
  { icon: '⚡', text: 'Built specifically for UK sole traders & freelancers — not a generic accounting tool' },
  { icon: '🧠', text: 'AI-powered categorisation reduces manual bookkeeping by up to 90%' },
  { icon: '📱', text: 'Available on web and mobile (iOS & Android via Expo) — manage finances anywhere' },
  { icon: '💰', text: 'Save hundreds on accountancy fees with automated tax calculations and reminders' },
  { icon: '🔗', text: 'Open Banking connector for automatic transaction import (no manual CSV uploads)' },
  { icon: '🛡️', text: 'SOC 2-aligned security practices with MFA, audit logs and encrypted storage' },
];

export default function HomePage({ onLoginSuccess }: IndexPageProps) {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [isRegistering, setIsRegistering] = useState(false);
  const [totpRequired, setTotpRequired] = useState(false);
  const [totpCode, setTotpCode] = useState('');
  const [loading, setLoading] = useState(false);
  const { t } = useTranslation();

  const passwordChecks = useMemo(() => getPasswordChecks(password), [password]);
  const strength = useMemo(() => getStrength(passwordChecks), [passwordChecks]);

  const clearFeedback = () => {
    setMessage('');
    setError('');
  };

  const formatErrorMessage = (detail: string): string => {
    if (/locked/i.test(detail)) {
      return 'Account temporarily locked. Please try again later.';
    }
    if (/password must/i.test(detail)) {
      const missing: string[] = [];
      if (!passwordChecks.length) missing.push('at least 8 characters');
      if (!passwordChecks.uppercase) missing.push('an uppercase letter');
      if (!passwordChecks.lowercase) missing.push('a lowercase letter');
      if (!passwordChecks.digit) missing.push('a number');
      if (!passwordChecks.special) missing.push('a special character');
      return missing.length
        ? `Password must contain: ${missing.join(', ')}.`
        : detail;
    }
    return detail;
  };

  const handleRegister = async (e: FormEvent) => {
    e.preventDefault();
    clearFeedback();
    if (!email.trim() || !password.trim()) {
      setError('Please enter your email and password.');
      return;
    }
    setLoading(true);

    try {
      const response = await fetch(`${AUTH_SERVICE_URL}/register`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: email.trim(), password }),
      });
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.detail || 'Registration failed');
      }
      setMessage(`User ${data.email} registered successfully! You can now log in.`);
      setIsRegistering(false);
    } catch (err: unknown) {
      if (err instanceof TypeError && err.message === 'Failed to fetch') {
        setError('Connection failed. Please try again.');
      } else {
        const details = err instanceof Error ? err.message : 'Registration failed';
        setError(formatErrorMessage(details));
      }
    } finally {
      setLoading(false);
    }
  };

  const handleLogin = async (e: FormEvent, totpOverride?: string) => {
    e.preventDefault();
    clearFeedback();
    if (!email.trim() || !password.trim()) {
      setError('Please enter your email and password.');
      return;
    }
    setLoading(true);

    try {
      const formData = new URLSearchParams();
      formData.append('username', email.trim());
      formData.append('password', password);

      const code = totpOverride || totpCode;
      if (code) {
        formData.append('scope', `totp:${code}`);
      }

      const response = await fetch(`${AUTH_SERVICE_URL}/token`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: formData.toString(),
      });
      const data = await response.json();

      if (response.status === 403 && data.detail === '2FA_REQUIRED') {
        setTotpRequired(true);
        setTotpCode('');
        setLoading(false);
        return;
      }

      if (!response.ok) {
        throw new Error(data.detail || 'Login failed');
      }

      onLoginSuccess(data.access_token);
    } catch (err: unknown) {
      if (err instanceof TypeError && err.message === 'Failed to fetch') {
        setError('Connection failed. Please try again.');
      } else {
        const details = err instanceof Error ? err.message : 'Login failed';
        setError(formatErrorMessage(details));
      }
    } finally {
      setLoading(false);
    }
  };

  const handleTotpSubmit = (e: FormEvent) => {
    handleLogin(e);
  };

  const handleBackToLogin = () => {
    setTotpRequired(false);
    setTotpCode('');
    clearFeedback();
  };

  const strengthClass =
    strength === 'strong'
      ? styles.strengthStrong
      : strength === 'medium'
      ? styles.strengthMedium
      : styles.strengthWeak;

  const strengthLabel =
    strength === 'strong' ? 'Strong' : strength === 'medium' ? 'Medium' : 'Weak';

  return (
    <div className={styles.landingRoot}>
      {/* ── LEFT PANEL — product description ── */}
      <div className={styles.landingLeft}>
        <div className={styles.landingBrand}>
          <span className={styles.landingLogo}>SM</span>
          <span className={styles.landingBrandName}>SelfMonitor</span>
        </div>

        <h1 className={styles.landingHero}>
          Your complete financial hub<br />
          <span className={styles.landingHeroAccent}>for UK self-employed</span>
        </h1>
        <p className={styles.landingSubtitle}>
          Invoicing · Tax Deadlines · AI Advice · Cash Flow · Documents · Analytics
          — everything in one platform, designed for freelancers and sole traders.
        </p>

        <div className={styles.landingFeatureGrid}>
          {FEATURES.map((f) => (
            <div key={f.title} className={styles.landingFeatureCard}>
              <span className={styles.landingFeatureIcon}>{f.icon}</span>
              <div>
                <div className={styles.landingFeatureTitle}>{f.title}</div>
                <div className={styles.landingFeatureDesc}>{f.desc}</div>
              </div>
            </div>
          ))}
        </div>

        <h2 className={styles.landingAdvTitle}>Why SelfMonitor?</h2>
        <ul className={styles.landingAdvList}>
          {ADVANTAGES.map((a) => (
            <li key={a.text} className={styles.landingAdvItem}>
              <span className={styles.landingAdvIcon}>{a.icon}</span>
              <span>{a.text}</span>
            </li>
          ))}
        </ul>

        <p className={styles.landingFooter}>
          Trusted by <strong>2,400+</strong> freelancers across the UK &nbsp;·&nbsp;
          HMRC MTD ready &nbsp;·&nbsp; GDPR compliant
        </p>
      </div>

      {/* ── RIGHT PANEL — auth form ── */}
      <div className={styles.landingRight}>
        <main className={styles.main}>
          <h1 className={styles.title}>{t('login.title')}</h1>
          <p className={styles.description}>{t('login.description')}</p>
          <div className={styles.formContainer}>
          {totpRequired ? (
            <form onSubmit={handleTotpSubmit}>
              <div className={styles.totpSection}>
                <p>Enter your 6-digit code from authenticator app</p>
              </div>
              <input
                id="totp-input"
                type="text"
                inputMode="numeric"
                pattern="[0-9]*"
                maxLength={6}
                placeholder="000000"
                value={totpCode}
                onChange={(e) => setTotpCode(e.target.value.replace(/\D/g, '').slice(0, 6))}
                className={`${styles.input} ${styles.totpInput}`}
                aria-label="Two-factor authentication code"
                autoFocus
              />
              <div className={styles.buttonGroup}>
                <button
                  type="button"
                  onClick={handleBackToLogin}
                  className={styles.button}
                  style={{ background: 'transparent', border: '1px solid var(--lp-border)', color: 'var(--lp-text-muted)' }}
                >
                  Back
                </button>
                <button
                  type="submit"
                  className={styles.button}
                  disabled={totpCode.length !== 6 || loading}
                  aria-label="Verify TOTP code"
                >
                  {loading ? 'Verifying...' : 'Verify'}
                </button>
              </div>
            </form>
          ) : (
            <form>
              <label htmlFor="email-input">Email</label>
              <input
                id="email-input"
                type="email"
                placeholder="Email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className={styles.input}
                aria-label="Email address"
              />
              <label htmlFor="password-input">Password</label>
              <div className={styles.passwordWrapper}>
                <input
                  id="password-input"
                  type={showPassword ? 'text' : 'password'}
                  placeholder="Password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className={styles.input}
                  aria-label="Password"
                  style={{ paddingRight: '3rem' }}
                />
                <button
                  type="button"
                  className={styles.passwordToggle}
                  onClick={() => setShowPassword(!showPassword)}
                  aria-label={showPassword ? 'Hide password' : 'Show password'}
                >
                  {showPassword ? '🙈' : '👁️'}
                </button>
              </div>

              {isRegistering && password.length > 0 && (
                <>
                  <div className={strengthClass} style={{ height: 4, borderRadius: 2, marginTop: '0.5rem', transition: 'all 0.3s' }} />
                  <div className={styles.strengthLabel} style={{ color: strength === 'strong' ? '#14b8a6' : strength === 'medium' ? '#d97706' : '#ef4444' }}>
                    {strengthLabel}
                  </div>
                  <ul className={styles.requirements}>
                    <li className={passwordChecks.length ? styles.requirementMet : styles.requirementUnmet}>
                      {passwordChecks.length ? '✓' : '✗'} At least 8 characters
                    </li>
                    <li className={passwordChecks.uppercase ? styles.requirementMet : styles.requirementUnmet}>
                      {passwordChecks.uppercase ? '✓' : '✗'} Uppercase letter
                    </li>
                    <li className={passwordChecks.lowercase ? styles.requirementMet : styles.requirementUnmet}>
                      {passwordChecks.lowercase ? '✓' : '✗'} Lowercase letter
                    </li>
                    <li className={passwordChecks.digit ? styles.requirementMet : styles.requirementUnmet}>
                      {passwordChecks.digit ? '✓' : '✗'} Number
                    </li>
                    <li className={passwordChecks.special ? styles.requirementMet : styles.requirementUnmet}>
                      {passwordChecks.special ? '✓' : '✗'} Special character (!@#$%...)
                    </li>
                  </ul>
                </>
              )}

              <div className={styles.buttonGroup}>
                <button
                  type="button"
                  onClick={(e) => {
                    if (!isRegistering) {
                      setIsRegistering(true);
                      clearFeedback();
                    } else {
                      handleRegister(e);
                    }
                  }}
                  className={styles.button}
                  disabled={loading}
                  aria-label="Register a new account"
                  style={isRegistering ? {} : { background: 'transparent', border: '1px solid var(--lp-border)', color: 'var(--lp-text-muted)' }}
                >
                  {loading && isRegistering ? 'Registering...' : t('login.register_button')}
                </button>
                <button
                  type="button"
                  onClick={(e) => {
                    if (isRegistering) {
                      setIsRegistering(false);
                      clearFeedback();
                    } else {
                      handleLogin(e);
                    }
                  }}
                  className={styles.button}
                  disabled={loading}
                  aria-label="Log in to your account"
                  style={!isRegistering ? {} : { background: 'transparent', border: '1px solid var(--lp-border)', color: 'var(--lp-text-muted)' }}
                >
                  {loading && !isRegistering ? 'Logging in...' : t('login.login_button')}
                </button>
              </div>
            </form>
          )}
        </div>
          {message && <p className={styles.message} role="alert">{message}</p>}
          {error && <p className={styles.error} role="alert">{error}</p>}
        </main>
      </div>
    </div>
  );
}
