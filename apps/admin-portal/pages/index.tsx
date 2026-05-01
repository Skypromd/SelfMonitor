import { type FormEvent, useState } from 'react';
import styles from '../styles/Admin.module.css';

const AUTH_SERVICE_BASE_URL =
  process.env.NEXT_PUBLIC_AUTH_SERVICE_URL || 'http://localhost:8001';

export default function LoginPage() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      const response = await fetch(`${AUTH_SERVICE_BASE_URL}/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || 'Login failed');
      }

      const token: string = data.access_token ?? data.token ?? '';
      const user = data.user ?? { email, is_admin: data.is_admin ?? false };

      if (!user.is_admin) {
        setError('Access denied — this portal is for administrators only.');
        setLoading(false);
        return;
      }

      sessionStorage.setItem('authToken', token);
      sessionStorage.setItem('adminUser', JSON.stringify(user));
      window.location.replace('/dashboard');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unexpected error. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      style={{
        minHeight: '100vh',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        background: 'var(--lp-bg)',
        padding: '1.5rem',
      }}
    >
      <div
        style={{
          width: '100%',
          maxWidth: 420,
          background: 'var(--lp-bg-elevated)',
          border: '1px solid var(--lp-border)',
          borderRadius: 16,
          padding: '2.5rem',
          boxShadow: '0 12px 40px rgba(0,0,0,0.4)',
        }}
      >
        <div style={{ marginBottom: '2rem', textAlign: 'center' }}>
          <p
            style={{
              fontSize: '0.75rem',
              fontWeight: 600,
              letterSpacing: '0.12em',
              textTransform: 'uppercase',
              color: '#14b8a6',
              margin: '0 0 0.4rem',
            }}
          >
            SelfMonitor
          </p>
          <h1
            style={{
              fontSize: '1.75rem',
              fontWeight: 700,
              color: 'var(--lp-text)',
              letterSpacing: '-0.03em',
              margin: '0 0 0.5rem',
            }}
          >
            Owner Console
          </h1>
          <p style={{ color: 'var(--lp-text-muted)', fontSize: '0.9rem', margin: 0 }}>
            Restricted access — administrators only
          </p>
        </div>

        <form onSubmit={handleSubmit}>
          <input
            className={styles.input}
            type="email"
            placeholder="admin@example.com"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            autoComplete="email"
          />
          <input
            className={styles.input}
            type="password"
            placeholder="Password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            autoComplete="current-password"
          />
          <button
            className={styles.button}
            type="submit"
            disabled={loading}
            style={{ width: '100%', marginTop: '0.25rem' }}
          >
            {loading ? 'Signing in…' : 'Sign In'}
          </button>
        </form>

        {error && (
          <div
            style={{
              marginTop: '1rem',
              background: 'rgba(239,68,68,0.1)',
              border: '1px solid rgba(239,68,68,0.3)',
              borderRadius: 10,
              padding: '0.85rem 1rem',
              color: '#fca5a5',
              fontSize: '0.875rem',
            }}
          >
            {error}
          </div>
        )}

        <p
          style={{
            marginTop: '1.5rem',
            textAlign: 'center',
            fontSize: '0.78rem',
            color: '#475569',
          }}
        >
          🔒 Secure admin portal — do not share this URL
        </p>
      </div>
    </div>
  );
}
