import Head from 'next/head';
import Link from 'next/link';
import { useRouter } from 'next/router';
import { useCallback, useEffect, useMemo, useState } from 'react';
import styles from '../../../styles/Home.module.css';

function browserApiPrefix(): string {
  const raw = process.env.NEXT_PUBLIC_API_GATEWAY_URL || '/api';
  if (/^https?:\/\//i.test(raw)) {
    return raw.replace(/\/$/, '');
  }
  return raw.startsWith('/') ? raw.replace(/\/$/, '') : '/api';
}

const API_P = browserApiPrefix();
const AUTH_SERVICE_BASE_URL =
  process.env.NEXT_PUBLIC_AUTH_SERVICE_URL || `${API_P}/auth`;

type Props = {
  token: string;
  user?: { email?: string; is_admin?: boolean };
};

type UserDetail = {
  email: string;
  is_active: boolean;
  is_admin: boolean;
  is_two_factor_enabled: boolean;
  plan: string;
  subscription_status: string;
  trial_end: string | null;
};

export default function AdminUserDetailPage({ token, user: _viewer }: Props) {
  const router = useRouter();
  const raw = router.query.email;
  const emailFromRoute = typeof raw === 'string' ? decodeURIComponent(raw) : '';
  const [detail, setDetail] = useState<UserDetail | null>(null);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  const authHeaders = useMemo(
    () => ({ Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' }),
    [token],
  );

  const load = useCallback(async () => {
    if (!emailFromRoute || !token) return;
    setError('');
    try {
      const res = await fetch(
        `${AUTH_SERVICE_BASE_URL}/admin/users/${encodeURIComponent(emailFromRoute)}`,
        { headers: authHeaders },
      );
      if (!res.ok) {
        throw new Error(`Load failed (${res.status})`);
      }
      setDetail(await res.json());
    } catch (e) {
      setDetail(null);
      setError(e instanceof Error ? e.message : 'Failed to load user');
    }
  }, [emailFromRoute, token, authHeaders]);

  useEffect(() => {
    if (!router.isReady) return;
    void load();
  }, [router.isReady, load]);

  const deactivate = async () => {
    if (!emailFromRoute || !detail?.is_active) return;
    if (!window.confirm(`Deactivate ${emailFromRoute}?`)) return;
    setBusy(true);
    try {
      const res = await fetch(
        `${AUTH_SERVICE_BASE_URL}/users/${encodeURIComponent(emailFromRoute)}/deactivate`,
        { method: 'POST', headers: authHeaders },
      );
      if (!res.ok) throw new Error(`Deactivate failed (${res.status})`);
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Deactivate failed');
    } finally {
      setBusy(false);
    }
  };

  return (
    <>
      <Head>
        <title>{emailFromRoute ? `${emailFromRoute} — User` : 'User'} — Admin</title>
      </Head>
      <div className={styles.pageContainerWide}>
        <p className={styles.pageEyebrow}>
          <Link href="/admin/users">← Users</Link>
        </p>
        <div className={styles.pageHeader}>
          <h1 className={styles.pageTitle}>{emailFromRoute || 'User'}</h1>
          <p className={styles.pageLead}>Auth profile and subscription snapshot.</p>
        </div>
        {error && <p style={{ color: '#f87171' }}>{error}</p>}
        {detail && (
          <div
            style={{
              border: '1px solid var(--lp-border)',
              borderRadius: 12,
              padding: '1.25rem 1.5rem',
              maxWidth: 560,
              background: 'var(--lp-bg-card)',
            }}
          >
            <p><strong>Plan:</strong> {detail.plan}</p>
            <p><strong>Subscription status:</strong> {detail.subscription_status}</p>
            <p><strong>Active:</strong> {detail.is_active ? 'Yes' : 'No'}</p>
            <p><strong>Platform admin:</strong> {detail.is_admin ? 'Yes' : 'No'}</p>
            <p><strong>2FA:</strong> {detail.is_two_factor_enabled ? 'Enabled' : 'Off'}</p>
            {detail.trial_end ? <p><strong>Trial ends:</strong> {detail.trial_end}</p> : null}
            {detail.is_active ? (
              <button
                type="button"
                className={styles.button}
                disabled={busy}
                onClick={() => void deactivate()}
                style={{ marginTop: 16 }}
              >
                {busy ? 'Working…' : 'Deactivate user'}
              </button>
            ) : null}
          </div>
        )}
      </div>
    </>
  );
}
