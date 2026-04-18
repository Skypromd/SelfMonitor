import Head from 'next/head';
import Link from 'next/link';
import { useRouter } from 'next/router';
import { FormEvent, useEffect, useState } from 'react';
import { adminSurfaceUrl } from '../lib/adminSurface';
import styles from '../styles/Home.module.css';

const AUTH_SERVICE_URL = process.env.NEXT_PUBLIC_AUTH_SERVICE_URL || '/api/auth';

const PLAN_NAMES: Record<string, string> = {
  free: 'Free', starter: 'Starter', growth: 'Growth', pro: 'Pro', business: 'Business',
};
const PLAN_PRICES: Record<string, string> = {
  free: '£0/mo',
  starter: '£15/mo ex VAT',
  growth: '£18/mo ex VAT',
  pro: '£21/mo ex VAT',
  business: '£30/mo ex VAT',
};

type RegisterPageProps = { onLoginSuccess: (token: string) => void };
type Step = 'account' | 'phone-verify' | '2fa-setup' | 'done';

const STEPS: Step[] = ['account', 'phone-verify', '2fa-setup', 'done'];
const STEP_LABELS = ['Account', 'Phone', 'Authenticator', 'Done'];

const stepIndex = (s: Step) => STEPS.indexOf(s);

export default function RegisterPage({ onLoginSuccess }: RegisterPageProps) {
  const router = useRouter();
  const plan = (router.query.plan as string) || 'starter';
  const planName = PLAN_NAMES[plan] || 'Starter';
  const planPrice = PLAN_PRICES[plan] || '£15/mo ex VAT';
  const isTrial = plan !== 'free';
  const paymentConfirmed = router.query.payment === 'success';

  const [step, setStep] = useState<Step>('account');
  const [accessToken, setAccessToken] = useState('');

  // ── Step 1: Account ────────────────────────────────────────────────────────
  const [fullName, setFullName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  // ── Step 2: Phone verification ────────────────────────────────────────────
  const [phone, setPhone] = useState('');
  const [phoneCodeSent, setPhoneCodeSent] = useState(false);
  const [devCode, setDevCode] = useState('');        // filled only in dev mode
  const [smsCode, setSmsCode] = useState('');
  const [phoneLoading, setPhoneLoading] = useState(false);
  const [phoneError, setPhoneError] = useState('');
  const [resendCountdown, setResendCountdown] = useState(0);

  useEffect(() => {
    if (resendCountdown <= 0) return;
    const t = setTimeout(() => setResendCountdown(c => c - 1), 1000);
    return () => clearTimeout(t);
  }, [resendCountdown]);

  // ── Step 3: Google Authenticator / TOTP ──────────────────────────────────
  const [mfaSecret, setMfaSecret] = useState('');
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

  // ── Step 1: Register + auto-login ─────────────────────────────────────────
  const handleRegister = async (e: FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      const regRes = await fetch(`${AUTH_SERVICE_URL}/register`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password, plan }),
      });
      const regData = await regRes.json();
      if (!regRes.ok) throw new Error(regData.detail || 'Registration failed');

      const loginForm = new URLSearchParams();
      loginForm.append('username', email);
      loginForm.append('password', password);
      const loginRes = await fetch(`${AUTH_SERVICE_URL}/token`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: loginForm,
      });
      const loginData = await loginRes.json();
      if (!loginRes.ok) throw new Error('Registered. Please log in manually.');
      setAccessToken(loginData.access_token);
      setStep('phone-verify');
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Registration failed');
    } finally {
      setLoading(false);
    }
  };

  // ── Step 2a: Send SMS code ─────────────────────────────────────────────────
  const handleSendSmsCode = async (e?: FormEvent) => {
    e?.preventDefault();
    setPhoneError('');
    setPhoneLoading(true);
    try {
      const res = await fetch(`${AUTH_SERVICE_URL}/phone/send-code`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, phone }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Failed to send SMS');
      setPhoneCodeSent(true);
      setResendCountdown(60);
      if (data.dev_code) setDevCode(data.dev_code);   // dev only
    } catch (err: unknown) {
      setPhoneError(err instanceof Error ? err.message : 'SMS sending failed');
    } finally {
      setPhoneLoading(false);
    }
  };

  // ── Step 2b: Verify SMS code ───────────────────────────────────────────────
  const handleVerifyPhone = async (e: FormEvent) => {
    e.preventDefault();
    setPhoneError('');
    setPhoneLoading(true);
    try {
      const res = await fetch(`${AUTH_SERVICE_URL}/phone/verify`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${accessToken}`,
        },
        body: JSON.stringify({ email, code: smsCode }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Verification failed');
      setStep('2fa-setup');
    } catch (err: unknown) {
      setPhoneError(err instanceof Error ? err.message : 'Verification failed');
    } finally {
      setPhoneLoading(false);
    }
  };

  // ── Step 3: Fetch QR code ──────────────────────────────────────────────────
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
        const qrRes = await fetch(`${AUTH_SERVICE_URL}/2fa/setup`, {
          headers: { Authorization: `Bearer ${accessToken}` },
        });
        if (qrRes.ok) {
          const blob = await qrRes.blob();
          setMfaQr(URL.createObjectURL(blob));
        }
      } catch { /* non-fatal */ }
    })();
  }, [step, accessToken]);

  // ── Step 3: Verify TOTP ────────────────────────────────────────────────────
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
        throw new Error(d.detail || 'Invalid code');
      }
      setMfaEnabled(true);
      setTimeout(() => onLoginSuccess(accessToken), 1500);
    } catch (err: unknown) {
      setMfaError(err instanceof Error ? err.message : 'Verification failed');
    } finally {
      setMfaLoading(false);
    }
  };

  const finishRegistration = () => onLoginSuccess(accessToken);

  const currentIdx = stepIndex(step);

  return (
    <>
      <Head><title>Create Account — MyNetTax</title></Head>
      <div className={styles.container}>
        <main className={styles.main} style={{ maxWidth: 520 }}>

          {/* ── Step indicator ─────────────────────────────────── */}
          <div style={{ width: '100%', marginBottom: '1.75rem' }}>
            <div style={{ display: 'flex', gap: '0.4rem', marginBottom: '0.5rem' }}>
              {STEPS.filter(s => s !== 'done').map((s, i) => (
                <div key={s} style={{
                  flex: 1, height: 4, borderRadius: 2, transition: 'background 0.3s',
                  background: currentIdx > i ? '#0d9488' : currentIdx === i ? '#14b8a6' : 'rgba(255,255,255,0.1)',
                }} />
              ))}
            </div>
            <div style={{ display: 'flex', gap: '0.4rem' }}>
              {STEPS.filter(s => s !== 'done').map((s, i) => (
                <div key={s} style={{
                  flex: 1, textAlign: 'center', fontSize: '0.7rem',
                  color: currentIdx >= i ? '#14b8a6' : '#475569',
                  fontWeight: currentIdx === i ? 600 : 400,
                }}>
                  {i + 1}. {STEP_LABELS[i]}
                </div>
              ))}
            </div>
          </div>

          {/* ── STEP 1: Account ─────────────────────────────────── */}
          {step === 'account' && (
            <>
              {isTrial ? (
                <>
                  <h1 className={styles.title} style={{ fontSize: '1.75rem' }}>
                    {paymentConfirmed ? `${planName} Plan Activated!` : `Start your 14-day ${planName} trial`}
                  </h1>
                  <p className={styles.description}>
                    {paymentConfirmed
                      ? <span style={{ color: '#14b8a6' }}>✓ Payment confirmed — {planName} ({planPrice})</span>
                      : <>Full {planName} access ({planPrice}) — no credit card required</>
                    }
                  </p>
                </>
              ) : (
                <>
                  <h1 className={styles.title} style={{ fontSize: '1.75rem' }}>Create your account</h1>
                  <p className={styles.description}>Get started with MyNetTax</p>
                </>
              )}

              {paymentConfirmed ? (
                <div style={{
                  width: '100%', padding: '1rem', borderRadius: 12,
                  background: 'rgba(13,148,136,0.12)', border: '1px solid rgba(13,148,136,0.45)',
                  marginBottom: '1.5rem', fontSize: '0.875rem', color: '#14b8a6', lineHeight: 1.8,
                }}>
                  <div style={{ fontWeight: 600, marginBottom: '0.25rem' }}>✓ Payment successful</div>
                  <div>✓ Your {planName} subscription is confirmed</div>
                  <div>✓ 14-day free trial starts today</div>
                  <div>✓ No charge until trial ends — cancel anytime</div>
                </div>
              ) : isTrial ? (
                <div style={{
                  width: '100%', padding: '1rem', borderRadius: 12,
                  background: 'rgba(13,148,136,0.1)', border: '1px solid rgba(13,148,136,0.3)',
                  marginBottom: '1.5rem', fontSize: '0.875rem', color: '#14b8a6', lineHeight: 1.8,
                }}>
                  <div>✓ No credit card required</div>
                  <div>✓ Full {planName} access for 14 days</div>
                  <div>✓ Downgrade or cancel anytime</div>
                </div>
              ) : null}

              <p style={{ fontSize: '0.8rem', color: '#64748b', margin: '0 0 1rem', lineHeight: 1.55 }}>
                Регистрация создаёт <strong style={{ color: '#94a3b8' }}>клиентский аккаунт</strong> (как у пользователя продукта).
                Вход для администратора платформы — отдельно:{' '}
                <a href={adminSurfaceUrl('/admin/login')} style={{ color: '#14b8a6' }}>операторский вход</a>
                {' '}(учётная запись из bootstrap в .env / Docker, не эта форма).
              </p>

              <form onSubmit={handleRegister} style={{ width: '100%' }}>
                <label htmlFor="reg-name">Full name <span style={{ color: '#64748b', fontWeight: 400 }}>(optional)</span></label>
                <input id="reg-name" type="text" placeholder="Jane Smith" value={fullName}
                  onChange={e => setFullName(e.target.value)} className={styles.input} autoComplete="name" />

                <label htmlFor="reg-email" style={{ marginTop: '0.75rem', display: 'block' }}>Email address</label>
                <input id="reg-email" type="email" placeholder="your@email.com" value={email}
                  onChange={e => setEmail(e.target.value)} className={styles.input} required autoComplete="email" />

                <label htmlFor="reg-password" style={{ marginTop: '0.75rem', display: 'block' }}>Password</label>
                <div className={styles.passwordWrapper}>
                  <input id="reg-password" type={showPassword ? 'text' : 'password'}
                    placeholder="Create a strong password" value={password}
                    onChange={e => setPassword(e.target.value)} className={styles.input}
                    style={{ paddingRight: '3rem' }} required autoComplete="new-password" />
                  <button type="button" className={styles.passwordToggle} onClick={() => setShowPassword(v => !v)}>
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
                      {([
                        [passwordChecks.length, 'At least 8 characters'],
                        [passwordChecks.uppercase, 'Uppercase letter'],
                        [passwordChecks.lowercase, 'Lowercase letter'],
                        [passwordChecks.digit, 'Number'],
                        [passwordChecks.special, 'Special character'],
                      ] as [boolean, string][]).map(([ok, label]) => (
                        <li key={label} className={ok ? styles.requirementMet : styles.requirementUnmet}>
                          {ok ? '✓' : '✗'} {label}
                        </li>
                      ))}
                    </ul>
                  </>
                )}

                <button type="submit" className={styles.button}
                  disabled={loading || passedChecks < 5 || !email}
                  style={{ width: '100%', marginTop: '1.25rem', height: 48 }}>
                  {loading ? 'Creating account…' : isTrial ? `Start ${planName} Trial →` : 'Create Account →'}
                </button>
              </form>

              {error && <p className={styles.error} role="alert">{error}</p>}

              <p style={{ marginTop: '1.5rem', color: '#94a3b8', fontSize: '0.875rem' }}>
                Already have an account?{' '}
                <Link href="/login" style={{ color: '#14b8a6' }}>Log in</Link>
              </p>
            </>
          )}

          {/* ── STEP 2: Phone Verification ──────────────────────── */}
          {step === 'phone-verify' && (
            <>
              <h1 className={styles.title} style={{ fontSize: '1.6rem' }}>Verify your phone</h1>
              <p className={styles.description} style={{ marginBottom: '1.5rem' }}>
                We&apos;ll send a 6-digit code to your mobile number to confirm your identity.
              </p>

              {!phoneCodeSent ? (
                <form onSubmit={handleSendSmsCode} style={{ width: '100%' }}>
                  <label htmlFor="phone-input">Mobile phone number</label>
                  <input
                    id="phone-input"
                    type="tel"
                    placeholder="+44 7700 900000"
                    value={phone}
                    onChange={e => setPhone(e.target.value)}
                    className={styles.input}
                    required
                    autoComplete="tel"
                    style={{ fontSize: '1.1rem', letterSpacing: '0.05em' }}
                  />
                  <p style={{ fontSize: '0.78rem', color: '#64748b', marginTop: '0.4rem' }}>
                    Include country code, e.g. +44 for UK, +48 for Poland
                  </p>
                  {phoneError && <p className={styles.error} role="alert">{phoneError}</p>}
                  <button type="submit" className={styles.button}
                    disabled={phoneLoading || phone.length < 7}
                    style={{ width: '100%', marginTop: '1.25rem', height: 48 }}>
                    {phoneLoading ? 'Sending…' : 'Send Verification Code →'}
                  </button>
                </form>
              ) : (
                <form onSubmit={handleVerifyPhone} style={{ width: '100%' }}>
                  <div style={{
                    padding: '0.875rem 1rem', borderRadius: 10, marginBottom: '1.25rem',
                    background: 'rgba(13,148,136,0.1)', border: '1px solid rgba(13,148,136,0.3)',
                    fontSize: '0.875rem', color: '#14b8a6',
                  }}>
                    ✓ Code sent to <strong>{phone}</strong>
                    {devCode && (
                      <span style={{ display: 'block', marginTop: '0.25rem', color: '#f59e0b', fontSize: '0.8rem' }}>
                        [DEV] Code: <strong>{devCode}</strong>
                      </span>
                    )}
                  </div>

                  <label htmlFor="sms-code">Enter 6-digit code</label>
                  <input
                    id="sms-code"
                    type="text"
                    inputMode="numeric"
                    pattern="[0-9]{6}"
                    maxLength={6}
                    placeholder="123456"
                    value={smsCode}
                    onChange={e => setSmsCode(e.target.value.replace(/\D/g, ''))}
                    className={styles.input}
                    style={{ letterSpacing: '0.4em', fontSize: '1.5rem', textAlign: 'center' }}
                    autoComplete="one-time-code"
                    autoFocus
                  />

                  {phoneError && <p className={styles.error} role="alert">{phoneError}</p>}

                  <button type="submit" className={styles.button}
                    disabled={phoneLoading || smsCode.length !== 6}
                    style={{ width: '100%', marginTop: '1rem', height: 48 }}>
                    {phoneLoading ? 'Verifying…' : 'Verify Code →'}
                  </button>

                  <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '0.75rem', alignItems: 'center' }}>
                    <button type="button" onClick={() => { setPhoneCodeSent(false); setSmsCode(''); setPhoneError(''); setDevCode(''); }}
                      style={{ background: 'none', border: 'none', color: '#64748b', fontSize: '0.8rem', cursor: 'pointer', padding: 0 }}>
                      ← Change number
                    </button>
                    <button type="button"
                      disabled={resendCountdown > 0}
                      onClick={() => handleSendSmsCode()}
                      style={{ background: 'none', border: 'none', fontSize: '0.8rem', cursor: resendCountdown > 0 ? 'default' : 'pointer',
                        color: resendCountdown > 0 ? '#475569' : '#14b8a6', padding: 0 }}>
                      {resendCountdown > 0 ? `Resend in ${resendCountdown}s` : 'Resend code'}
                    </button>
                  </div>
                </form>
              )}

              <button type="button" onClick={() => setStep('2fa-setup')}
                style={{
                  marginTop: '1.25rem', width: '100%', background: 'transparent',
                  border: '1px solid rgba(255,255,255,0.1)', borderRadius: 10,
                  color: '#475569', height: 40, cursor: 'pointer', fontSize: '0.8rem',
                }}>
                Skip phone verification — add later in Settings
              </button>
            </>
          )}

          {/* ── STEP 3: Google Authenticator ────────────────────── */}
          {step === '2fa-setup' && (
            <>
              <h1 className={styles.title} style={{ fontSize: '1.6rem' }}>Set up Authenticator app</h1>
              <p className={styles.description} style={{ marginBottom: '1.25rem' }}>
                Protect your account with Google Authenticator or Authy (TOTP 2FA).
              </p>

              {mfaEnabled ? (
                <div style={{
                  padding: '1.5rem', borderRadius: 12, textAlign: 'center',
                  background: 'rgba(13,148,136,0.1)', border: '1px solid rgba(13,148,136,0.3)',
                  color: '#14b8a6', fontSize: '1.1rem',
                }}>
                  ✓ Authenticator enabled! Redirecting…
                </div>
              ) : (
                <>
                  <ol style={{ color: '#94a3b8', fontSize: '0.875rem', paddingLeft: '1.25rem', lineHeight: 2, marginBottom: '1.5rem' }}>
                    <li>Install <strong style={{ color: '#e2e8f0' }}>Google Authenticator</strong> or <strong style={{ color: '#e2e8f0' }}>Authy</strong></li>
                    <li>Scan the QR code below with the app</li>
                    <li>Enter the 6-digit rotating code to confirm</li>
                  </ol>

                  {mfaQr ? (
                    <div style={{ textAlign: 'center', marginBottom: '1.5rem' }}>
                      {/* eslint-disable-next-line @next/next/no-img-element */}
                      <img src={mfaQr} alt="2FA QR Code" width={180} height={180}
                        style={{ borderRadius: 12, background: '#fff', padding: 8 }} />
                      {mfaSecret && (
                        <p style={{ fontSize: '0.73rem', color: '#64748b', marginTop: '0.5rem' }}>
                          Manual key: <code style={{ color: '#94a3b8', userSelect: 'all', wordBreak: 'break-all' }}>{mfaSecret}</code>
                        </p>
                      )}
                    </div>
                  ) : (
                    <div style={{ textAlign: 'center', color: '#64748b', marginBottom: '1.5rem', fontSize: '0.875rem' }}>
                      Loading QR code…
                    </div>
                  )}

                  <form onSubmit={handleVerify2FA} style={{ width: '100%' }}>
                    <label htmlFor="totp-code">6-digit code from your app</label>
                    <input id="totp-code" type="text" inputMode="numeric" pattern="[0-9]{6}"
                      maxLength={6} placeholder="123456" value={totpCode}
                      onChange={e => setTotpCode(e.target.value.replace(/\D/g, ''))}
                      className={styles.input}
                      style={{ letterSpacing: '0.3em', fontSize: '1.25rem', textAlign: 'center' }}
                      autoComplete="one-time-code" />
                    {mfaError && <p className={styles.error} role="alert" style={{ marginTop: '0.5rem' }}>{mfaError}</p>}
                    <button type="submit" className={styles.button}
                      disabled={mfaLoading || totpCode.length !== 6}
                      style={{ width: '100%', marginTop: '1rem', height: 48 }}>
                      {mfaLoading ? 'Verifying…' : 'Enable Authenticator & Finish →'}
                    </button>
                  </form>

                  <button type="button" onClick={finishRegistration}
                    style={{
                      marginTop: '1rem', width: '100%', background: 'transparent',
                      border: '1px solid rgba(255,255,255,0.1)', borderRadius: 10,
                      color: '#64748b', height: 44, cursor: 'pointer', fontSize: '0.875rem',
                    }}>
                    Skip for now — set up Authenticator in Settings
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
