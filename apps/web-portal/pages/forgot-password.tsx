import Head from 'next/head';
import Link from 'next/link';
import { FormEvent, useState } from 'react';
import styles from '../styles/Home.module.css';

const AUTH_SERVICE_URL = process.env.NEXT_PUBLIC_AUTH_SERVICE_URL || '/api/auth';

type Step = 'form' | 'sent';

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState('');
  const [loading, setLoading] = useState(false);
  const [step, setStep] = useState<Step>('form');
  const [error, setError] = useState('');
  const [devToken, setDevToken] = useState('');
  const [devNote, setDevNote] = useState('');
  const [emailSent, setEmailSent] = useState(false);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError('');
    if (!email.trim()) { setError('Please enter your email address.'); return; }
    setLoading(true);
    try {
      const res = await fetch(`${AUTH_SERVICE_URL}/password-reset/request`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: email.trim() }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Request failed');
      if (data.email_sent) {
        setEmailSent(true);
      }
      if (data.dev_token) {
        setDevToken(data.dev_token as string);
        setDevNote(data.dev_note as string);
      }
      setStep('sent');
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

  return (
    <>
      <Head>
        <title>Forgot Password — SelfMonitor</title>
        <meta name="description" content="Reset your SelfMonitor password" />
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

          {step === 'form' ? (
            <>
              <h1 className={styles.title} style={{ fontSize: '1.75rem', marginBottom: '0.25rem' }}>
                Forgot your password?
              </h1>
              <p className={styles.description} style={{ marginBottom: '1.75rem' }}>
                Enter the email address linked to your account and we&apos;ll send you a reset link.
              </p>

              <form onSubmit={handleSubmit} style={{ width: '100%' }}>
                <label htmlFor="reset-email">Email address</label>
                <input
                  id="reset-email"
                  type="email"
                  placeholder="your@email.com"
                  value={email}
                  onChange={e => setEmail(e.target.value)}
                  className={styles.input}
                  required
                  autoComplete="email"
                  autoFocus
                />

                {error && (
                  <p className={styles.error} role="alert" style={{ marginTop: '0.5rem' }}>{error}</p>
                )}

                <button
                  type="submit"
                  className={styles.button}
                  disabled={loading}
                  style={{ width: '100%', marginTop: '1.25rem', height: 48 }}
                >
                  {loading ? 'Sending…' : 'Send Reset Link →'}
                </button>
              </form>

              <p style={{ marginTop: '1.5rem', color: '#94a3b8', fontSize: '0.875rem', textAlign: 'center' }}>
                <Link href="/login" style={{ color: '#475569', fontSize: '0.8rem' }}>← Back to login</Link>
              </p>
            </>
          ) : (
            <>
              {/* Success state */}
              <div style={{
                width: 56, height: 56, borderRadius: 16,
                background: 'linear-gradient(135deg,#0d9488,#0284c7)',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                fontSize: '1.75rem', marginBottom: '1.5rem',
              }}>
                📧
              </div>

              <h1 className={styles.title} style={{ fontSize: '1.75rem', marginBottom: '0.25rem' }}>
                {emailSent ? 'Check your inbox' : 'Reset link ready'}
              </h1>
              <p className={styles.description} style={{ marginBottom: '1.5rem' }}>
                {emailSent ? (
                  <>
                    We sent a password reset link to{' '}
                    <strong style={{ color: '#e2e8f0' }}>{email}</strong>.
                    Check your inbox (and spam folder). The link expires in 60 minutes.
                  </>
                ) : (
                  <>
                    If <strong style={{ color: '#e2e8f0' }}>{email}</strong> is registered,
                    use the link below to reset your password.
                  </>
                )}
              </p>

              {/* DEV / SMTP-error mode: show token on-screen */}
              {devToken && (
                <div style={{
                  padding: '1rem', borderRadius: 12, marginBottom: '1.25rem',
                  background: emailSent ? 'rgba(239,68,68,0.08)' : 'rgba(234,179,8,0.08)',
                  border: `1px solid ${emailSent ? 'rgba(239,68,68,0.3)' : 'rgba(234,179,8,0.3)'}`,
                  fontSize: '0.8rem', color: emailSent ? '#f87171' : '#fbbf24', wordBreak: 'break-all',
                }}>
                  <p style={{ fontWeight: 700, marginBottom: '0.4rem' }}>
                    {emailSent ? '⚠️ SMTP ERROR — using fallback link' : '🛠 DEV MODE — SMTP not configured'}
                  </p>
                  <p style={{ marginBottom: '0.6rem', opacity: 0.85 }}>{devNote}</p>
                  <Link
                    href={`/reset-password?token=${devToken}`}
                    style={{
                      display: 'inline-block', padding: '0.5rem 1rem',
                      background: 'rgba(251,191,36,0.2)', borderRadius: 8,
                      color: '#fbbf24', fontWeight: 600, textDecoration: 'none',
                    }}
                  >
                    Open reset link →
                  </Link>
                </div>
              )}

              <p style={{ color: '#94a3b8', fontSize: '0.875rem', textAlign: 'center' }}>
                Didn&apos;t receive it?{' '}
                <button
                  onClick={() => { setStep('form'); setDevToken(''); setDevNote(''); }}
                  style={{
                    background: 'none', border: 'none', cursor: 'pointer',
                    color: '#14b8a6', fontWeight: 600, fontSize: '0.875rem',
                  }}
                >
                  Try again
                </button>
              </p>
              <p style={{ marginTop: '0.75rem', color: '#94a3b8', fontSize: '0.875rem', textAlign: 'center' }}>
                <Link href="/login" style={{ color: '#475569', fontSize: '0.8rem' }}>← Back to login</Link>
              </p>
            </>
          )}
        </main>
      </div>
    </>
  );
}
