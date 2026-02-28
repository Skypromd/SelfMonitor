import Head from 'next/head';
import Link from 'next/link';
import { useRouter } from 'next/router';
import { FormEvent, useState } from 'react';
import styles from '../styles/Home.module.css';

const API_GATEWAY_URL = process.env.NEXT_PUBLIC_API_GATEWAY_URL || 'http://localhost:8000/api';
const AUTH_SERVICE_URL = process.env.NEXT_PUBLIC_AUTH_SERVICE_URL || 'http://localhost:8001';

const PLAN_NAMES: Record<string, string> = {
  free: 'Free',
  starter: 'Starter',
  pro: 'Pro',
  business: 'Business',
};

const PLAN_PRICES: Record<string, string> = {
  free: '£0/mo',
  starter: '£9/mo',
  pro: '£19/mo',
  business: '£39/mo',
};

type RegisterPageProps = {
  onLoginSuccess: (token: string) => void;
};

export default function RegisterPage({ onLoginSuccess }: RegisterPageProps) {
  const router = useRouter();
  const plan = (router.query.plan as string) || 'free';
  const planName = PLAN_NAMES[plan] || 'Free';
  const planPrice = PLAN_PRICES[plan] || '£0/mo';
  const isTrial = plan !== 'free';

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  // Password strength checks (same as login page)
  const passwordChecks = {
    length: password.length >= 8,
    uppercase: /[A-Z]/.test(password),
    lowercase: /[a-z]/.test(password),
    digit: /\d/.test(password),
    special: /[!@#$%^&*(),.?":{}|<>]/.test(password),
  };
  const passedChecks = Object.values(passwordChecks).filter(Boolean).length;
  const strength = passedChecks <= 2 ? 'weak' : passedChecks <= 4 ? 'medium' : 'strong';

  const handleRegister = async (e: FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      // 1. Register with plan
      const regResponse = await fetch(`${AUTH_SERVICE_URL}/register`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password, plan }),
      });
      const regData = await regResponse.json();
      if (!regResponse.ok) {
        throw new Error(regData.detail || 'Registration failed');
      }

      // 2. Auto-login
      const loginForm = new URLSearchParams();
      loginForm.append('username', email);
      loginForm.append('password', password);
      const loginResponse = await fetch(`${AUTH_SERVICE_URL}/token`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: loginForm,
      });
      const loginData = await loginResponse.json();
      if (!loginResponse.ok) {
        throw new Error('Registered but login failed. Please log in manually.');
      }

      onLoginSuccess(loginData.access_token);
    } catch (err: unknown) {
      const details = err instanceof Error ? err.message : 'Registration failed';
      setError(details);
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      <Head>
        <title>Start Your {planName} Trial — SelfMonitor</title>
      </Head>
      <div className={styles.container}>
        <main className={styles.main} style={{ maxWidth: 520 }}>
          {isTrial ? (
            <>
              <h1 className={styles.title} style={{ fontSize: '1.75rem' }}>
                🎉 Start your 14-day {planName} trial
              </h1>
              <p className={styles.description}>
                Full {planName} access ({planPrice}) — no credit card required
              </p>
            </>
          ) : (
            <>
              <h1 className={styles.title} style={{ fontSize: '1.75rem' }}>
                Create your free account
              </h1>
              <p className={styles.description}>
                Get started with SelfMonitor — free forever
              </p>
            </>
          )}

          {isTrial && (
            <div style={{
              width: '100%',
              padding: '1rem',
              borderRadius: 12,
              background: 'rgba(13,148,136,0.1)',
              border: '1px solid rgba(13,148,136,0.3)',
              marginBottom: '1.5rem',
              fontSize: '0.9rem',
              color: '#14b8a6',
            }}>
              <div>✓ No credit card required</div>
              <div>✓ Full {planName} access for 14 days</div>
              <div>✓ Downgrade to Free anytime</div>
              <div>✓ Cancel anytime — no commitments</div>
            </div>
          )}

          <form onSubmit={handleRegister} style={{ width: '100%' }}>
            <label htmlFor="reg-email">Email</label>
            <input
              id="reg-email"
              type="email"
              placeholder="your@email.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className={styles.input}
              required
            />

            <label htmlFor="reg-password">Password</label>
            <div className={styles.passwordWrapper}>
              <input
                id="reg-password"
                type={showPassword ? 'text' : 'password'}
                placeholder="Create a strong password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className={styles.input}
                style={{ paddingRight: '3rem' }}
                required
              />
              <button
                type="button"
                className={styles.passwordToggle}
                onClick={() => setShowPassword(!showPassword)}
              >
                {showPassword ? '🙈' : '👁️'}
              </button>
            </div>

            {password.length > 0 && (
              <>
                <div className={
                  strength === 'strong' ? styles.strengthStrong :
                  strength === 'medium' ? styles.strengthMedium :
                  styles.strengthWeak
                } style={{ height: 4, borderRadius: 2, marginTop: '0.25rem', transition: 'all 0.3s' }} />
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
                    {passwordChecks.special ? '✓' : '✗'} Special character
                  </li>
                </ul>
              </>
            )}

            <button
              type="submit"
              className={styles.button}
              disabled={loading || passedChecks < 5 || !email}
              style={{ width: '100%', marginTop: '1rem', height: 48 }}
            >
              {loading ? 'Creating account...' : isTrial ? `Start ${planName} Trial` : 'Create Free Account'}
            </button>
          </form>

          {error && <p className={styles.error} role="alert">{error}</p>}

          <p style={{ marginTop: '1.5rem', color: '#94a3b8', fontSize: '0.9rem' }}>
            Already have an account? <Link href="/" style={{ color: '#14b8a6' }}>Log in</Link>
          </p>
        </main>
      </div>
    </>
  );
}
