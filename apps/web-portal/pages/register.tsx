import Head from 'next/head';
import Link from 'next/link';
import { useRouter } from 'next/router';
import { FormEvent, useEffect, useState } from 'react';
import styles from '../styles/Home.module.css';

const AUTH_SERVICE_URL = process.env.NEXT_PUBLIC_AUTH_SERVICE_URL || 'http://localhost:8001';

const PLAN_NAMES: Record<string, string> = {
  free: 'Free',
  starter: 'Starter',
  growth: 'Growth',
  pro: 'Pro',
  business: 'Business',
};

const PLAN_PRICES: Record<string, string> = {
  free: '£0/mo',
  starter: '£9/mo',
  growth: '£12/mo',
  pro: '£15/mo',
  business: '£25/mo',
};

type RegisterPageProps = {
  onLoginSuccess: (token: string) => void;
};

type Step = 'account' | '2fa-setup' | 'done';

export default function RegisterPage({ onLoginSuccess }: RegisterPageProps) {
  const router = useRouter();
  const plan = (router.query.plan as string) || 'starter';
  const planName = PLAN_NAMES[plan] || 'Starter';
  const planPrice = PLAN_PRICES[plan] || '£9/mo';
  const isTrial = plan !== 'free';

  // Step state
  const [step, setStep] = useState<Step>('account');
  const [accessToken, setAccessToken] = useState('');

  // Step 1 — Account
  const [fullName, setFullName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  // Step 2 — 2FA
  const [mfaSecret, setMfaSecret] = useState('');
  const [mfaUri, setMfaUri] = useState('');
  const [mfaQr, setMfaQr] = useState('');
  const [totpCode, setTotpCode] = useState('');
  const [mfaLoading, setMfaLoading] = useState(false);
  const [mfaError, setMfaError] = useState('');
  const [mfaEnabled, setMfaEnabled] = useState(false);

  // Password strength
  const passwordChecks = {
    length: password.length >= 8,
    uppercase: /[A-Z]/.test(password),
    lowercase: /[a-z]/.test(password),
    digit: /\d/.test(password),
    special: /[!@#$%^&*(),.?":{}|<>]/.test(password),
  };
  const passedChecks = Object.values(passwordChecks).filter(Boolean).length;
  const strength = passedChecks <= 2 ? 'weak' : passedChecks <= 4 ? 'medium' : 'strong';

  // ── Step 1: Register + auto-login ──────────────────────────────────────────
  const handleRegister = async (e: FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      const regResponse = await fetch(`${AUTH_SERVICE_URL}/register`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password, plan }),
      });
      const regData = await regResponse.json();
      if (!regResponse.ok) throw new Error(regData.detail || 'Registration failed');

      // Auto-login
      const loginForm = new URLSearchParams();
      loginForm.append('username', email);
      loginForm.append('password', password);
      const loginResponse = await fetch(`${AUTH_SERVICE_URL}/token`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: loginForm,
      });
      const loginData = await loginResponse.json();
      if (!loginResponse.ok) throw new Error('Registered but auto-login failed. Please log in manually.');

      setAccessToken(loginData.access_token);
      setStep('2fa-setup');
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Registration failed');
    } finally {
      setLoading(false);
    }
  };

  // ── Step 2: Fetch 2FA setup data ───────────────────────────────────────────
  useEffect(() => {
    if (step !== '2fa-setup' || !accessToken) return;
    (async () => {
      try {
        const res = await fetch(`${AUTH_SERVICE_URL}/2fa/setup-json`, {
          headers: { Authorization: `Bearer ${accessToken}` },
        });
        if (!res.ok) return;
        const data = await res.json();
        setMfaSecret(data.secret);
        setMfaUri(data.provisioning_uri);
        // Fetch QR as data URL from /2fa/setup (PNG)
        const qrRes = await fetch(`${AUTH_SERVICE_URL}/2fa/setup`, {
          headers: { Authorization: `Bearer ${accessToken}` },
        });
        if (qrRes.ok) {
          const blob = await qrRes.blob();
          setMfaQr(URL.createObjectURL(blob));
        }
      } catch {
        // non-fatal — user can still skip 2FA
      }
    })();
  }, [step, accessToken]);

  // ── Step 2: Verify TOTP + enable 2FA ──────────────────────────────────────
  const handleVerify2FA = async (e: FormEvent) => {
    e.preventDefault();
    setMfaError('');
    setMfaLoading(true);
    try {
      const res = await fetch(`${AUTH_SERVICE_URL}/2fa/verify?totp_code=${totpCode}`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${accessToken}` },
      });
      if (!res.ok) {
        const d = await res.json();
        throw new Error(d.detail || 'Invalid code — please try again');
      }
      setMfaEnabled(true);
      setTimeout(() => finishRegistration(), 1500);
    } catch (err: unknown) {
      setMfaError(err instanceof Error ? err.message : 'Verification failed');
    } finally {
      setMfaLoading(false);
    }
  };

  const finishRegistration = () => {
    onLoginSuccess(accessToken);
  };

  // ── Render ─────────────────────────────────────────────────────────────────
  return (
    <>
      <Head>
        <title>Create Account — SelfMonitor</title>
      </Head>
      <div className={styles.container}>
        <main className={styles.main} style={{ maxWidth: 520 }}>

          {/* Step indicator */}
          <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '1.75rem', width: '100%' }}>
            {(['account', '2fa-setup', 'done'] as Step[]).map((s, i) => (
              <div key={s} style={{
                flex: 1, height: 4, borderRadius: 2,
                background: step === s ? '#14b8a6' :
                  (step === '2fa-setup' && i === 0) || step === 'done' ? '#0d9488' : 'rgba(255,255,255,0.1)',
                transition: 'background 0.3s',
              }} />
            ))}
          </div>

          {/* ── STEP 1: Account ─────────────────────────────────────── */}
          {step === 'account' && (
            <>
              {isTrial ? (
                <>
                  <h1 className={styles.title} style={{ fontSize: '1.75rem' }}>
                    Start your 14-day {planName} trial
                  </h1>
                  <p className={styles.description}>
                    Full {planName} access ({planPrice}) — no credit card required
                  </p>
                </>
              ) : (
                <>
                  <h1 className={styles.title} style={{ fontSize: '1.75rem' }}>
                    Create your account
                  </h1>
                  <p className={styles.description}>Get started with SelfMonitor</p>
                </>
              )}

              {isTrial && (
                <div style={{
                  width: '100%', padding: '1rem', borderRadius: 12,
                  background: 'rgba(13,148,136,0.1)', border: '1px solid rgba(13,148,136,0.3)',
                  marginBottom: '1.5rem', fontSize: '0.875rem', color: '#14b8a6', lineHeight: 1.8,
                }}>
                  <div>✓ No credit card required</div>
                  <div>✓ Full {planName} access for 14 days</div>
                  <div>✓ Downgrade or cancel anytime</div>
                </div>
              )}

              <form onSubmit={handleRegister} style={{ width: '100%' }}>
                <label htmlFor="reg-name">Full name <span style={{ color: '#64748b', fontWeight: 400 }}>(optional)</span></label>
                <input
                  id="reg-name"
                  type="text"
                  placeholder="Jane Smith"
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  className={styles.input}
                  autoComplete="name"
                />

                <label htmlFor="reg-email" style={{ marginTop: '0.75rem', display: 'block' }}>Email address</label>
                <input
                  id="reg-email"
                  type="email"
                  placeholder="your@email.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className={styles.input}
                  required
                  autoComplete="email"
                />

                <label htmlFor="reg-password" style={{ marginTop: '0.75rem', display: 'block' }}>Password</label>
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
                    autoComplete="new-password"
                  />
                  <button type="button" className={styles.passwordToggle} onClick={() => setShowPassword(!showPassword)}>
                    {showPassword ? '🙈' : '👁️'}
                  </button>
                </div>

                {password.length > 0 && (
                  <>
                    <div className={
                      strength === 'strong' ? styles.strengthStrong :
                      strength === 'medium' ? styles.strengthMedium : styles.strengthWeak
                    } style={{ height: 4, borderRadius: 2, marginTop: '0.25rem', transition: 'all 0.3s' }} />
                    <ul className={styles.requirements}>
                      {[
                        [passwordChecks.length, 'At least 8 characters'],
                        [passwordChecks.uppercase, 'Uppercase letter'],
                        [passwordChecks.lowercase, 'Lowercase letter'],
                        [passwordChecks.digit, 'Number'],
                        [passwordChecks.special, 'Special character'],
                      ].map(([ok, label]) => (
                        <li key={label as string} className={(ok as boolean) ? styles.requirementMet : styles.requirementUnmet}>
                          {(ok as boolean) ? '✓' : '✗'} {label as string}
                        </li>
                      ))}
                    </ul>
                  </>
                )}

                <button
                  type="submit"
                  className={styles.button}
                  disabled={loading || passedChecks < 5 || !email}
                  style={{ width: '100%', marginTop: '1.25rem', height: 48 }}
                >
                  {loading ? 'Creating account…' : isTrial ? `Start ${planName} Trial →` : 'Create Account →'}
                </button>
              </form>

              {error && <p className={styles.error} role="alert">{error}</p>}

              <p style={{ marginTop: '1.5rem', color: '#94a3b8', fontSize: '0.875rem' }}>
                Already have an account?{' '}
                <Link href="/" style={{ color: '#14b8a6' }}>Log in</Link>
              </p>
            </>
          )}

          {/* ── STEP 2: 2FA Setup ──────────────────────────────────── */}
          {step === '2fa-setup' && (
            <>
              <h1 className={styles.title} style={{ fontSize: '1.6rem' }}>
                Secure your account
              </h1>
              <p className={styles.description} style={{ marginBottom: '1.25rem' }}>
                Set up two-factor authentication (2FA) for extra security.
              </p>

              {mfaEnabled ? (
                <div style={{
                  padding: '1.5rem', borderRadius: 12, textAlign: 'center',
                  background: 'rgba(13,148,136,0.1)', border: '1px solid rgba(13,148,136,0.3)',
                  color: '#14b8a6', fontSize: '1.1rem',
                }}>
                  ✓ 2FA enabled! Redirecting…
                </div>
              ) : (
                <>
                  {/* Instructions */}
                  <ol style={{ color: '#94a3b8', fontSize: '0.875rem', paddingLeft: '1.25rem', lineHeight: 2, marginBottom: '1.5rem' }}>
                    <li>Install <strong style={{ color: '#e2e8f0' }}>Google Authenticator</strong> or <strong style={{ color: '#e2e8f0' }}>Authy</strong> on your phone</li>
                    <li>Scan the QR code below</li>
                    <li>Enter the 6-digit code to confirm</li>
                  </ol>

                  {/* QR Code */}
                  {mfaQr ? (
                    <div style={{ textAlign: 'center', marginBottom: '1.5rem' }}>
                      {/* eslint-disable-next-line @next/next/no-img-element */}
                      <img src={mfaQr} alt="2FA QR Code" width={180} height={180}
                        style={{ borderRadius: 12, background: '#fff', padding: 8 }} />
                      {mfaSecret && (
                        <p style={{ fontSize: '0.75rem', color: '#64748b', marginTop: '0.5rem' }}>
                          Manual key: <code style={{ color: '#94a3b8', userSelect: 'all' }}>{mfaSecret}</code>
                        </p>
                      )}
                    </div>
                  ) : (
                    <div style={{ textAlign: 'center', color: '#64748b', marginBottom: '1.5rem', fontSize: '0.875rem' }}>
                      Loading QR code…
                    </div>
                  )}

                  {/* Verify form */}
                  <form onSubmit={handleVerify2FA} style={{ width: '100%' }}>
                    <label htmlFor="totp-code">6-digit code from your app</label>
                    <input
                      id="totp-code"
                      type="text"
                      inputMode="numeric"
                      pattern="[0-9]{6}"
                      maxLength={6}
                      placeholder="123456"
                      value={totpCode}
                      onChange={(e) => setTotpCode(e.target.value.replace(/\D/g, ''))}
                      className={styles.input}
                      style={{ letterSpacing: '0.3em', fontSize: '1.25rem', textAlign: 'center' }}
                      autoComplete="one-time-code"
                    />
                    {mfaError && <p className={styles.error} role="alert" style={{ marginTop: '0.5rem' }}>{mfaError}</p>}

                    <button
                      type="submit"
                      className={styles.button}
                      disabled={mfaLoading || totpCode.length !== 6}
                      style={{ width: '100%', marginTop: '1rem', height: 48 }}
                    >
                      {mfaLoading ? 'Verifying…' : 'Enable 2FA & Continue →'}
                    </button>
                  </form>

                  <button
                    type="button"
                    onClick={finishRegistration}
                    style={{
                      marginTop: '1rem', width: '100%', background: 'transparent',
                      border: '1px solid rgba(255,255,255,0.1)', borderRadius: 10,
                      color: '#64748b', height: 44, cursor: 'pointer', fontSize: '0.875rem',
                    }}
                  >
                    Skip for now — set up 2FA in Settings
                  </button>
                </>
              )}
            </>
          )}

        </main>
      </div>
    </>
  );
}
