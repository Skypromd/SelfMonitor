import Head from 'next/head';
import Link from 'next/link';
import { useRouter } from 'next/router';
import { FormEvent, useState } from 'react';
import styles from '../styles/Home.module.css';

const AUTH_SERVICE_URL = process.env.NEXT_PUBLIC_AUTH_SERVICE_URL || 'http://localhost:8001';

type LoginPageProps = { onLoginSuccess: (token: string) => void };

export default function LoginPage({ onLoginSuccess }: LoginPageProps) {
  const router = useRouter();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [totpRequired, setTotpRequired] = useState(false);
  const [totpCode, setTotpCode] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleLogin = async (e: FormEvent, totpOverride?: string) => {
    e.preventDefault();
    setError('');
    if (!email.trim() || !password.trim()) { setError('Please enter your email and password.'); return; }
    setLoading(true);
    try {
      const formData = new URLSearchParams();
      formData.append('username', email.trim());
      formData.append('password', password);
      const code = totpOverride || totpCode;
      if (code) formData.append('scope', `totp:${code}`);

      const res = await fetch(`${AUTH_SERVICE_URL}/token`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: formData.toString(),
      });
      const data = await res.json();

      if (res.status === 403 && data.detail === '2FA_REQUIRED') {
        setTotpRequired(true);
        setTotpCode('');
        setLoading(false);
        return;
      }
      if (!res.ok) throw new Error(data.detail || 'Login failed');
      onLoginSuccess(data.access_token);
    } catch (err: unknown) {
      if (err instanceof TypeError && err.message === 'Failed to fetch') {
        setError('Connection failed. Please try again.');
      } else {
        setError(err instanceof Error ? err.message : 'Login failed');
      }
    } finally {
      setLoading(false);
    }
  };

  // Plan CTA from query — e.g. /login?next=dashboard
  const next = (router.query.next as string) || '/dashboard';
  void next; // used by _app.tsx router.push

  return (
    <>
      <Head>
        <title>Log In — SelfMonitor</title>
        <meta name="description" content="Log in to your SelfMonitor account" />
      </Head>
      <div className={styles.container}>
        <main className={styles.main} style={{ maxWidth: 440 }}>

          {/* Brand */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', marginBottom: '2rem' }}>
            <span style={{
              width: 36, height: 36, borderRadius: 10, background: 'linear-gradient(135deg,#0d9488,#0284c7)',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              fontSize: '0.75rem', fontWeight: 800, color: '#fff',
            }}>SM</span>
            <span style={{ fontWeight: 700, fontSize: '1.15rem', color: '#f1f5f9' }}>SelfMonitor</span>
          </div>

          {!totpRequired ? (
            <>
              <h1 className={styles.title} style={{ fontSize: '1.75rem', marginBottom: '0.25rem' }}>Welcome back</h1>
              <p className={styles.description} style={{ marginBottom: '1.75rem' }}>Log in to your account</p>

              <form onSubmit={handleLogin} style={{ width: '100%' }}>
                <label htmlFor="login-email">Email address</label>
                <input id="login-email" type="email" placeholder="your@email.com"
                  value={email} onChange={e => setEmail(e.target.value)}
                  className={styles.input} required autoComplete="email" />

                <label htmlFor="login-password" style={{ marginTop: '0.75rem', display: 'block' }}>Password</label>
                <div className={styles.passwordWrapper}>
                  <input id="login-password" type={showPassword ? 'text' : 'password'}
                    placeholder="Your password" value={password}
                    onChange={e => setPassword(e.target.value)}
                    className={styles.input} style={{ paddingRight: '3rem' }}
                    required autoComplete="current-password" />
                  <button type="button" className={styles.passwordToggle}
                    onClick={() => setShowPassword(v => !v)} aria-label="Toggle password">
                    {showPassword ? '🙈' : '👁️'}
                  </button>
                </div>

                {error && <p className={styles.error} role="alert" style={{ marginTop: '0.5rem' }}>{error}</p>}

                <button type="submit" className={styles.button}
                  disabled={loading} style={{ width: '100%', marginTop: '1.25rem', height: 48 }}>
                  {loading ? 'Logging in…' : 'Log In →'}
                </button>
              </form>

              {/* Divider */}
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', margin: '1.5rem 0', width: '100%' }}>
                <div style={{ flex: 1, height: 1, background: 'rgba(255,255,255,0.1)' }} />
                <span style={{ fontSize: '0.75rem', color: '#475569' }}>or</span>
                <div style={{ flex: 1, height: 1, background: 'rgba(255,255,255,0.1)' }} />
              </div>

              <p style={{ color: '#94a3b8', fontSize: '0.875rem', textAlign: 'center' }}>
                Don&apos;t have an account?{' '}
                <Link href="/register" style={{ color: '#14b8a6', fontWeight: 600 }}>Start free trial →</Link>
              </p>
              <p style={{ marginTop: '0.5rem', color: '#94a3b8', fontSize: '0.875rem', textAlign: 'center' }}>
                <Link href="/" style={{ color: '#475569', fontSize: '0.8rem' }}>← Back to homepage</Link>
              </p>
            </>
          ) : (
            /* ── 2FA step ── */
            <>
              <h1 className={styles.title} style={{ fontSize: '1.6rem' }}>Two-factor authentication</h1>
              <p className={styles.description} style={{ marginBottom: '1.5rem' }}>
                Enter the 6-digit code from your authenticator app.
              </p>

              <div style={{
                padding: '0.875rem 1rem', borderRadius: 10, marginBottom: '1.25rem',
                background: 'rgba(13,148,136,0.1)', border: '1px solid rgba(13,148,136,0.3)',
                fontSize: '0.85rem', color: '#14b8a6',
              }}>
                🔐 Logging in as <strong>{email}</strong>
              </div>

              <form onSubmit={e => handleLogin(e)} style={{ width: '100%' }}>
                <label htmlFor="totp-input">Authenticator code</label>
                <input id="totp-input" type="text" inputMode="numeric" pattern="[0-9]*"
                  maxLength={6} placeholder="000000" value={totpCode}
                  onChange={e => setTotpCode(e.target.value.replace(/\D/g, '').slice(0, 6))}
                  className={styles.input}
                  style={{ letterSpacing: '0.4em', fontSize: '1.5rem', textAlign: 'center' }}
                  autoComplete="one-time-code" autoFocus />

                {error && <p className={styles.error} role="alert">{error}</p>}

                <div style={{ display: 'flex', gap: '0.75rem', marginTop: '1rem' }}>
                  <button type="button" onClick={() => { setTotpRequired(false); setTotpCode(''); setError(''); }}
                    className={styles.button}
                    style={{ flex: 1, background: 'transparent', border: '1px solid var(--lp-border)', color: '#94a3b8', height: 48 }}>
                    ← Back
                  </button>
                  <button type="submit" className={styles.button}
                    disabled={totpCode.length !== 6 || loading}
                    style={{ flex: 2, height: 48 }}>
                    {loading ? 'Verifying…' : 'Verify →'}
                  </button>
                </div>
              </form>
            </>
          )}

        </main>
      </div>
    </>
  );
}
