import Head from 'next/head';
import Link from 'next/link';
import { useCallback, useEffect, useState } from 'react';
import styles from '../styles/Home.module.css';

const BILLING_URL = process.env.NEXT_PUBLIC_BILLING_SERVICE_URL || '/api/billing';

type Props = {
  token: string;
  user?: { email?: string; is_admin?: boolean };
};

type SubscriptionInfo = {
  email: string;
  plan: string;
  status: string;
  current_period_end?: number | null;
};

export default function MySubscriptionPage({ token, user }: Props) {
  const email = user?.email?.trim() || '';
  const [data, setData] = useState<SubscriptionInfo | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const load = useCallback(async () => {
    if (!email) {
      setLoading(false);
      setError('No email in session.');
      return;
    }
    setLoading(true);
    setError('');
    try {
      const res = await fetch(`${BILLING_URL}/subscription/${encodeURIComponent(email)}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) {
        throw new Error(`Subscription lookup failed (${res.status})`);
      }
      setData(await res.json());
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load subscription');
      setData(null);
    } finally {
      setLoading(false);
    }
  }, [email, token]);

  useEffect(() => {
    void load();
  }, [load]);

  return (
    <>
      <Head>
        <title>My subscription — MyNetTax</title>
      </Head>
      <div className={styles.pageContainer}>
        <div className={styles.pageHeader}>
          <p className={styles.pageEyebrow}>Billing</p>
          <h1 className={styles.pageTitle}>My subscription</h1>
          <p className={styles.pageLead}>
            Your current plan and status. Platform revenue tools for operators live under the admin console, not here.
          </p>
        </div>

        {loading && <p style={{ color: 'var(--lp-text-muted)' }}>Loading…</p>}
        {error && !loading && (
          <p style={{ color: '#f87171' }}>{error}</p>
        )}
        {data && !loading && (
          <div
            style={{
              border: '1px solid var(--lp-border)',
              borderRadius: 12,
              padding: '1.25rem 1.5rem',
              maxWidth: 480,
              background: 'var(--lp-bg-card)',
            }}
          >
            <p style={{ margin: '0 0 0.5rem', fontSize: 13, color: 'var(--lp-text-muted)' }}>Plan</p>
            <p style={{ margin: '0 0 1rem', fontSize: 22, fontWeight: 700 }}>{data.plan}</p>
            <p style={{ margin: '0 0 0.5rem', fontSize: 13, color: 'var(--lp-text-muted)' }}>Status</p>
            <p style={{ margin: '0 0 1rem', fontSize: 16 }}>{data.status}</p>
            {data.current_period_end ? (
              <p style={{ margin: 0, fontSize: 13, color: 'var(--lp-text-muted)' }}>
                Current period ends:{' '}
                {new Date(data.current_period_end * 1000).toLocaleDateString()}
              </p>
            ) : null}
            <div style={{ marginTop: '1.25rem' }}>
              <Link href="/marketplace" style={{ color: 'var(--lp-accent-teal)', fontWeight: 600 }}>
                Compare plans &amp; upgrades
              </Link>
              {user?.is_admin ? (
                <p style={{ marginTop: 12, marginBottom: 0, fontSize: 13 }}>
                  <Link href="/billing" style={{ color: 'var(--lp-text-muted)' }}>
                    Open platform billing (operator)
                  </Link>
                </p>
              ) : null}
            </div>
          </div>
        )}
      </div>
    </>
  );
}

