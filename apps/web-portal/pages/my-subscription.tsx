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
  account_credit_balance_gbp?: number;
  accountant_consult_sessions_available?: number;
};

type ConsultAddon = {
  name: string;
  amount_pence: number;
  sla_note?: string;
};

export default function MySubscriptionPage({ token, user }: Props) {
  const email = user?.email?.trim() || '';
  const [data, setData] = useState<SubscriptionInfo | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [consultAddon, setConsultAddon] = useState<ConsultAddon | null>(null);
  const [checkoutLoading, setCheckoutLoading] = useState(false);

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

  useEffect(() => {
    void fetch(`${BILLING_URL}/addons`)
      .then((r) => (r.ok ? r.json() : null))
      .then((j) => {
        const a = j?.accountant_cis_consult;
        if (a?.name && typeof a.amount_pence === 'number') {
          setConsultAddon({
            name: a.name,
            amount_pence: a.amount_pence,
            sla_note: typeof a.sla_note === 'string' ? a.sla_note : undefined,
          });
        }
      })
      .catch(() => {});
  }, []);

  const startConsultCheckout = async () => {
    if (!email) return;
    setCheckoutLoading(true);
    setError('');
    try {
      const res = await fetch(`${BILLING_URL}/checkout/session`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ product: 'accountant_cis_consult', email }),
      });
      const payload = await res.json().catch(() => ({}));
      if (!res.ok) {
        throw new Error(typeof payload.detail === 'string' ? payload.detail : `Checkout failed (${res.status})`);
      }
      if (payload.checkout_url) {
        window.location.href = payload.checkout_url as string;
        return;
      }
      throw new Error('No checkout URL returned');
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Checkout failed');
    } finally {
      setCheckoutLoading(false);
    }
  };

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
            {(data.account_credit_balance_gbp ?? 0) > 0 ? (
              <p style={{ margin: '1rem 0 0', fontSize: 13, color: 'var(--lp-text-muted)' }}>
                Account credit: £{Number(data.account_credit_balance_gbp).toFixed(2)}
              </p>
            ) : null}
            {(data.accountant_consult_sessions_available ?? 0) > 0 ? (
              <p style={{ margin: '0.75rem 0 0', fontSize: 13, color: 'var(--lp-text-muted)' }}>
                CIS accountant review sessions available:{' '}
                <strong style={{ color: 'var(--lp-text)' }}>{data.accountant_consult_sessions_available}</strong>
              </p>
            ) : null}
            <div
              style={{
                marginTop: '1.5rem',
                paddingTop: '1.25rem',
                borderTop: '1px solid var(--lp-border)',
              }}
            >
              <p style={{ margin: '0 0 0.5rem', fontSize: 13, color: 'var(--lp-text-muted)' }}>
                Optional add-on
              </p>
              <p style={{ margin: '0 0 0.75rem', fontSize: 15, fontWeight: 600 }}>
                {consultAddon?.name ?? 'CIS accountant review (1 session)'}
              </p>
              {consultAddon?.sla_note ? (
                <p style={{ margin: '0 0 1rem', fontSize: 12, color: 'var(--lp-text-muted)', lineHeight: 1.5 }}>
                  {consultAddon.sla_note}
                </p>
              ) : (
                <p style={{ margin: '0 0 1rem', fontSize: 12, color: 'var(--lp-text-muted)', lineHeight: 1.5 }}>
                  Paid review of your CIS evidence or self-attested figures. Scheduling via support after purchase.
                </p>
              )}
              <button
                type="button"
                className={styles.button}
                style={{
                  border: 'none',
                  cursor: checkoutLoading ? 'wait' : 'pointer',
                  opacity: checkoutLoading ? 0.7 : 1,
                  padding: '0.65rem 1.25rem',
                  fontSize: 14,
                }}
                disabled={checkoutLoading || !email}
                onClick={() => void startConsultCheckout()}
              >
                {checkoutLoading
                  ? 'Opening checkout…'
                  : consultAddon
                    ? `Buy — £${(consultAddon.amount_pence / 100).toFixed(2)}`
                    : 'Buy session'}
              </button>
            </div>
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

