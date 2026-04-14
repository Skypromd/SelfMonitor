import Head from 'next/head';
import Link from 'next/link';
import { useRouter } from 'next/router';
import { FormEvent, useEffect, useState } from 'react';
import styles from '../styles/Home.module.css';

const AUTH_SERVICE_URL = process.env.NEXT_PUBLIC_AUTH_SERVICE_URL || '/api/auth';

type Step = 'form' | 'success' | 'invalid';

export default function ResetPasswordPage() {
  const router = useRouter();
  const [token, setToken] = useState('');
  const [password, setNewPassword] = useState('');
  const [confirm, setConfirm] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [step, setStep] = useState<Step>('form');
  const [error, setError] = useState('');

  useEffect(() => {
    if (!router.isReady) return;
    const t = router.query.token as string;
    if (!t) { setStep('invalid'); return; }
    setToken(t);
  }, [router.isReady, router.query.token]);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError('');
    if (password.length < 8) { setError('Password must be at least 8 characters.'); return; }
    if (password !== confirm) { setError('Passwords do not match.'); return; }
    setLoading(true);
    try {
      const res = await fetch(`${AUTH_SERVICE_URL}/password-reset/confirm`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ token, new_password: password }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Reset failed');
      setStep('success');
    } catch (err: unknown) {
      if (err instanceof TypeError && err.message === 'Failed to fetch') {
        setError('Connection failed. Please try again.');
      } else {
        setError(err instanceof Error ? err.message : 'Something went wrong');
      }
    } finally {
      setLoading(false);
    }
  };

  // Strength indicator
  const strength = (() => {
    let score = 0;
    if (password.length >= 8) score++;
    if (/[A-Z]/.test(password)) score++;
    if (/[a-z]/.test(password)) score++;
    if (/\d/.test(password)) score++;
    if (/[!@#$%^&*(),.?":{}|<>]/.test(password)) score++;
    return score;
  })();
  const strengthLabel = ['', 'Very weak', 'Weak', 'Fair', 'Good', 'Strong'][strength];
  const strengthColor = ['', '#ef4444', '#f97316', '#eab308', '#22c55e', '#14b8a6'][strength];

  return (
    <>
      <Head>
        <title>Reset Password — SelfMonitor</title>
        <meta name="description" content="Set a new password for your SelfMonitor account" />
      </Head>
      <div className={styles.container}>
        <main className={styles.main} style={{ maxWidth: 440 }}>

          {/* Brand */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', marginBottom: '2rem' }}>
            <span style={{
              width: 36, height: 36, borderRadius: 10,
              background: 'linear-gradient(135deg,#0d9488,#0284c7)',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              fontSize: '0.75rem', fontWeight: 800, color: '#fff',
            }}>SM</span>
            <span style={{ fontWeight: 700, fontSize: '1.15rem', color: '#f1f5f9' }}>SelfMonitor</span>
          </div>

          {step === 'invalid' && (
            <>
              <div style={{ fontSize: '2rem', marginBottom: '1rem' }}>⚠️</div>
              <h1 className={styles.title} style={{ fontSize: '1.6rem', marginBottom: '0.5rem' }}>
                Invalid reset link
              </h1>
              <p className={styles.description} style={{ marginBottom: '1.5rem' }}>
                This password reset link is missing or malformed. Please request a new one.
              </p>
              <Link href="/forgot-password" className={styles.button}
                style={{ display: 'block', textAlign: 'center', padding: '0.75rem 1.5rem' }}>
                Request new link →
              </Link>
            </>
          )}

          {step === 'form' && (
            <>
              <h1 className={styles.title} style={{ fontSize: '1.75rem', marginBottom: '0.25rem' }}>
                Set new password
              </h1>
              <p className={styles.description} style={{ marginBottom: '1.75rem' }}>
                Choose a strong password for your account.
              </p>

              <form onSubmit={handleSubmit} style={{ width: '100%' }}>
                <label htmlFor="new-password">New password</label>
                <div className={styles.passwordWrapper}>
                  <input
                    id="new-password"
                    type={showPassword ? 'text' : 'password'}
                    placeholder="At least 8 characters"
                    value={password}
                    onChange={e => setNewPassword(e.target.value)}
                    className={styles.input}
                    style={{ paddingRight: '3rem' }}
                    required
                    autoComplete="new-password"
                    autoFocus
                  />
                  <button type="button" className={styles.passwordToggle}
                    onClick={() => setShowPassword(v => !v)} aria-label="Toggle password">
                    {showPassword ? '🙈' : '👁️'}
                  </button>
                </div>

                {/* Strength bar */}
                {password.length > 0 && (
                  <div style={{ marginTop: '0.4rem' }}>
                    <div style={{ display: 'flex', gap: 4, marginBottom: '0.25rem' }}>
                      {[1, 2, 3, 4, 5].map(i => (
                        <div key={i} style={{
                          flex: 1, height: 4, borderRadius: 2,
                          background: i <= strength ? strengthColor : 'rgba(255,255,255,0.1)',
                          transition: 'background 0.2s',
                        }} />
                      ))}
                    </div>
                    <span style={{ fontSize: '0.75rem', color: strengthColor }}>{strengthLabel}</span>
                  </div>
                )}

                <label htmlFor="confirm-password" style={{ marginTop: '0.75rem', display: 'block' }}>
                  Confirm new password
                </label>
                <input
                  id="confirm-password"
                  type={showPassword ? 'text' : 'password'}
                  placeholder="Repeat password"
                  value={confirm}
                  onChange={e => setConfirm(e.target.value)}
                  className={styles.input}
                  required
                  autoComplete="new-password"
                />
                {confirm.length > 0 && password !== confirm && (
                  <p style={{ fontSize: '0.75rem', color: '#ef4444', marginTop: '0.25rem' }}>
                    Passwords do not match
                  </p>
                )}
                {confirm.length > 0 && password === confirm && (
                  <p style={{ fontSize: '0.75rem', color: '#22c55e', marginTop: '0.25rem' }}>
                    ✓ Passwords match
                  </p>
                )}

                {error && (
                  <p className={styles.error} role="alert" style={{ marginTop: '0.5rem' }}>{error}</p>
                )}

                <button
                  type="submit"
                  className={styles.button}
                  disabled={loading || password !== confirm || strength < 3}
                  style={{ width: '100%', marginTop: '1.25rem', height: 48 }}
                >
                  {loading ? 'Saving…' : 'Set New Password →'}
                </button>
              </form>

              <p style={{ marginTop: '1.5rem', color: '#94a3b8', fontSize: '0.875rem', textAlign: 'center' }}>
                <Link href="/login" style={{ color: '#475569', fontSize: '0.8rem' }}>← Back to login</Link>
              </p>
            </>
          )}

          {step === 'success' && (
            <>
              <div style={{
                width: 56, height: 56, borderRadius: 16,
                background: 'linear-gradient(135deg,#0d9488,#22c55e)',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                fontSize: '1.75rem', marginBottom: '1.5rem',
              }}>
                ✅
              </div>
              <h1 className={styles.title} style={{ fontSize: '1.75rem', marginBottom: '0.25rem' }}>
                Password updated!
              </h1>
              <p className={styles.description} style={{ marginBottom: '2rem' }}>
                Your password has been changed successfully. You can now log in with your new password.
              </p>
              <Link href="/login" className={styles.button}
                style={{ display: 'block', textAlign: 'center', padding: '0.75rem 1.5rem' }}>
                Go to Login →
              </Link>
            </>
          )}
        </main>
      </div>
    </>
  );
}
