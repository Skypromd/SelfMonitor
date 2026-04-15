/**
 * Open Banking callback: TrueLayer ?code=… | Salt Edge ?connection_id=…
 * Completes the flow via banking-connector, then redirects to /transactions.
 */
import { useRouter } from 'next/router';
import { useEffect, useState } from 'react';

const BANKING_SERVICE_URL =
  process.env.NEXT_PUBLIC_BANKING_SERVICE_URL || '/api/banking';

export default function BankCallbackPage() {
  const router = useRouter();
  const [status, setStatus] = useState<'loading' | 'success' | 'error'>('loading');
  const [message, setMessage] = useState('Connecting to your bank…');
  const [connId, setConnId] = useState('');

  useEffect(() => {
    if (!router.isReady) return;

    const code = typeof router.query.code === 'string' ? router.query.code : '';
    const connectionId =
      typeof router.query.connection_id === 'string' ? router.query.connection_id : '';
    const error = typeof router.query.error === 'string' ? router.query.error : '';

    if (error) {
      setStatus('error');
      setMessage(`Bank declined: ${error}`);
      return;
    }

    if (!code && !connectionId) {
      setStatus('error');
      setMessage('No authorisation data received from bank (missing code or connection_id).');
      return;
    }

    const token =
      (typeof window !== 'undefined' && sessionStorage.getItem('bankingToken')) ||
      (typeof window !== 'undefined' && sessionStorage.getItem('authToken')) ||
      '';

    if (!token) {
      setStatus('error');
      setMessage('Session expired. Please log in again.');
      return;
    }

    const exchange = async () => {
      try {
        const qs = connectionId
          ? `connection_id=${encodeURIComponent(connectionId)}`
          : `code=${encodeURIComponent(code)}`;
        const res = await fetch(`${BANKING_SERVICE_URL}/connections/callback?${qs}`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || 'Exchange failed');

        setConnId(data.connection_id);
        setMessage(data.message || 'Bank connected successfully!');
        setStatus('success');
        sessionStorage.removeItem('bankingToken');

        // Redirect after short delay
        setTimeout(() => void router.replace('/transactions'), 2500);
      } catch (err) {
        setStatus('error');
        setMessage(err instanceof Error ? err.message : 'Connection failed');
      }
    };

    void exchange();
  }, [router.isReady, router.query, router]);

  return (
    <div
      style={{
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        background: 'var(--lp-bg)',
        fontFamily: 'Inter, sans-serif',
        padding: '2rem',
      }}
    >
      <div
        style={{
          background: 'var(--lp-bg-elevated)',
          border: '1px solid var(--lp-border)',
          borderRadius: 20,
          padding: '3rem',
          maxWidth: 460,
          width: '100%',
          textAlign: 'center',
        }}
      >
        {status === 'loading' && (
          <>
            <div style={{ fontSize: '2.5rem', marginBottom: '1rem', animation: 'spin 1.2s linear infinite', display: 'inline-block' }}>⏳</div>
            <h2 style={{ marginTop: 0 }}>Connecting…</h2>
            <p style={{ color: 'var(--lp-muted)' }}>{message}</p>
          </>
        )}

        {status === 'success' && (
          <>
            <div style={{ fontSize: '2.5rem', marginBottom: '1rem' }}>✅</div>
            <h2 style={{ marginTop: 0, color: '#0d9488' }}>Bank Connected!</h2>
            <p style={{ color: 'var(--lp-muted)' }}>{message}</p>
            {connId && (
              <p style={{ fontFamily: 'monospace', fontSize: '0.8rem', color: 'var(--lp-muted)', marginTop: '0.5rem' }}>
                Connection ID: {connId}
              </p>
            )}
            <p style={{ color: 'var(--lp-muted)', fontSize: '0.85rem', marginTop: '1rem' }}>
              Redirecting to transactions…
            </p>
          </>
        )}

        {status === 'error' && (
          <>
            <div style={{ fontSize: '2.5rem', marginBottom: '1rem' }}>❌</div>
            <h2 style={{ marginTop: 0, color: '#ef4444' }}>Connection Failed</h2>
            <p style={{ color: 'var(--lp-muted)' }}>{message}</p>
            <button
              onClick={() => void router.replace('/transactions')}
              style={{ marginTop: '1.5rem', padding: '0.75rem 2rem', background: 'var(--lp-accent-teal)', color: '#fff', border: 'none', borderRadius: 10, fontWeight: 600, cursor: 'pointer' }}
            >
              Back to Transactions
            </button>
          </>
        )}
      </div>
    </div>
  );
}
