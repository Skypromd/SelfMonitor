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
  const [attempt, setAttempt] = useState(0);

  const MAX_ATTEMPTS = 3;

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
      if (typeof window !== 'undefined') sessionStorage.removeItem('bankingProviderId');
      return;
    }

    const exchange = async (tryNum: number) => {
      setAttempt(tryNum);
      setMessage(tryNum > 1 ? `Retrying… (attempt ${tryNum} of ${MAX_ATTEMPTS})` : 'Connecting to your bank…');
      try {
        const providerId =
          (typeof window !== 'undefined' && sessionStorage.getItem('bankingProviderId')) || '';
        const qsBase = connectionId
          ? `connection_id=${encodeURIComponent(connectionId)}`
          : `code=${encodeURIComponent(code)}`;
        const qs = providerId ? `${qsBase}&provider_id=${encodeURIComponent(providerId)}` : qsBase;
        const res = await fetch(`${BANKING_SERVICE_URL}/connections/callback?${qs}`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || 'Exchange failed');

        setConnId(data.connection_id);
        setMessage(data.message || 'Bank connected successfully!');
        setStatus('success');
        sessionStorage.removeItem('bankingToken');
        sessionStorage.removeItem('bankingProviderId');

        // Redirect after short delay
        setTimeout(() => void router.replace('/transactions'), 2500);
      } catch (err) {
        if (tryNum < MAX_ATTEMPTS) {
          const delay = 1500 * tryNum; // 1.5 s, 3 s
          setMessage(`Attempt ${tryNum} failed — retrying in ${delay / 1000}s…`);
          setTimeout(() => void exchange(tryNum + 1), delay);
        } else {
          setStatus('error');
          setMessage(err instanceof Error ? err.message : 'Connection failed');
          if (typeof window !== 'undefined') sessionStorage.removeItem('bankingProviderId');
        }
      }
    };

    void exchange(1);
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
            {attempt > 1 && (
              <p style={{ fontSize: '0.8rem', color: '#f59e0b', marginTop: '0.35rem' }}>
                Attempt {attempt} of {MAX_ATTEMPTS}
              </p>
            )}
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
            <p style={{ fontSize: '0.8rem', color: 'var(--lp-muted)', marginTop: '0.25rem' }}>
              Failed after {MAX_ATTEMPTS} attempts. Check your connection and try again.
            </p>
            <div style={{ display: 'flex', gap: '0.75rem', justifyContent: 'center', marginTop: '1.5rem', flexWrap: 'wrap' }}>
              <button
                onClick={() => void router.replace('/connect-bank')}
                style={{ padding: '0.65rem 1.5rem', background: 'var(--lp-accent-teal)', color: '#fff', border: 'none', borderRadius: 10, fontWeight: 600, cursor: 'pointer' }}
              >
                Try again →
              </button>
              <button
                onClick={() => void router.replace('/transactions')}
                style={{ padding: '0.65rem 1.5rem', background: 'transparent', color: 'var(--lp-muted)', border: '1px solid var(--lp-border)', borderRadius: 10, fontWeight: 500, cursor: 'pointer' }}
              >
                Back to Transactions
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
