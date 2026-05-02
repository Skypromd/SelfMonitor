import Link from 'next/link';
import { useCallback, useEffect, useState } from 'react';
import styles from '../../styles/Home.module.css';

const BANKING_SERVICE_URL =
  process.env.NEXT_PUBLIC_BANKING_SERVICE_URL || '/api/banking';

const PREFERRED_PROVIDER_ID =
  (process.env.NEXT_PUBLIC_OPEN_BANKING_PROVIDER || 'saltedge').trim().toLowerCase();

type BankingProviderRow = {
  id: string;
  display_name: string;
  configured: 'true' | 'false';
  logo_url?: string;
};

type ConnectBankPageProps = {
  token: string;
};

const UK_BANKS_INFO: { name: string; domain: string }[] = [
  { name: 'Barclays', domain: 'barclays.co.uk' },
  { name: 'HSBC UK', domain: 'hsbc.co.uk' },
  { name: 'Lloyds Bank', domain: 'lloydsbank.co.uk' },
  { name: 'NatWest', domain: 'natwest.com' },
  { name: 'Santander UK', domain: 'santander.co.uk' },
  { name: 'Nationwide', domain: 'nationwide.co.uk' },
  { name: 'TSB', domain: 'tsb.co.uk' },
  { name: 'Metro Bank', domain: 'metrobankonline.co.uk' },
  { name: 'Monzo', domain: 'monzo.com' },
  { name: 'Starling Bank', domain: 'starlingbank.com' },
  { name: 'Revolut', domain: 'revolut.com' },
  { name: 'Co-operative Bank', domain: 'co-operativebank.co.uk' },
  { name: 'Virgin Money', domain: 'virginmoney.com' },
  { name: 'First Direct', domain: 'firstdirect.com' },
];

function faviconUrl(domain: string) {
  return `https://www.google.com/s2/favicons?domain=${encodeURIComponent(domain)}&sz=32`;
}

export default function ConnectBankPage({ token }: ConnectBankPageProps) {
  const [providers, setProviders] = useState<BankingProviderRow[]>([]);
  const [loadError, setLoadError] = useState('');
  const [connectingId, setConnectingId] = useState('');
  const [flowError, setFlowError] = useState('');
  const [lastConnectedId, setLastConnectedId] = useState('');
  const [syncQuota, setSyncQuota] = useState<{ daily_limit: number; remaining: number } | null>(null);
  const [statementExportBusy, setStatementExportBusy] = useState(false);
  const [statementExportError, setStatementExportError] = useState('');

  const loadProviders = useCallback(async () => {
    setLoadError('');
    try {
      const res = await fetch(`${BANKING_SERVICE_URL}/providers`);
      if (!res.ok) throw new Error('Could not load providers');
      const raw = (await res.json()) as BankingProviderRow[];
      const data = Array.isArray(raw) ? raw : [];
      const pref = data.filter((p) => p.id === PREFERRED_PROVIDER_ID);
      const rest = data.filter((p) => p.id !== PREFERRED_PROVIDER_ID);
      rest.sort((a, b) => a.id.localeCompare(b.id));
      setProviders([...pref, ...rest]);
    } catch {
      setLoadError('Unable to load Open Banking providers. Try again later.');
    }
  }, []);

  useEffect(() => {
    void loadProviders();
  }, [loadProviders]);

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      try {
        const res = await fetch(`${BANKING_SERVICE_URL}/connections/sync-quota`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (!res.ok) return;
        const data = (await res.json()) as { daily_limit: number; remaining: number };
        if (!cancelled && typeof data.daily_limit === 'number') setSyncQuota(data);
      } catch {
        /* ignore */
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [token]);

  const startConnect = async (providerId: string) => {
    setFlowError('');
    setLastConnectedId(providerId);
    setConnectingId(providerId);
    try {
      const callbackUrl =
        typeof window !== 'undefined'
          ? `${window.location.origin}/connect-bank/callback`
          : 'http://localhost:3000/connect-bank/callback';

      const response = await fetch(`${BANKING_SERVICE_URL}/connections/initiate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({ provider_id: providerId, redirect_uri: callbackUrl }),
      });
      if (!response.ok) {
        const body = await response.json().catch(() => ({}));
        throw new Error(typeof body.detail === 'string' ? body.detail : 'Failed to start connection');
      }
      const data = (await response.json()) as { consent_url: string };
      if (typeof window !== 'undefined') {
        sessionStorage.setItem('bankingToken', token);
        sessionStorage.setItem('bankingProviderId', providerId);
      }
      window.location.href = data.consent_url;
    } catch (err) {
      setConnectingId('');
      setFlowError(err instanceof Error ? err.message : 'Connection failed');
    }
  };

  const downloadStatementCsv = async (days: number) => {
    setStatementExportError('');
    setStatementExportBusy(true);
    try {
      const params = new URLSearchParams({ days: String(days) });
      const res = await fetch(`${BANKING_SERVICE_URL}/exports/statement-csv?${params.toString()}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(typeof (body as { detail?: string }).detail === 'string' ? (body as { detail: string }).detail : 'Export failed');
      }
      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const anchor = document.createElement('a');
      anchor.href = url;
      anchor.download = `bank-statement-${days}d.csv`;
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      setStatementExportError(err instanceof Error ? err.message : 'Export failed');
    } finally {
      setStatementExportBusy(false);
    }
  };

  return (
    <div className={styles.pageContainer}>
      <h1>Connect your bank</h1>
      <p style={{ color: 'var(--lp-muted)', maxWidth: 640 }}>
        Production flow uses <strong>Salt Edge</strong> (UK Open Banking). You pick your bank inside Salt Edge Connect
        after pressing Connect. Imports run only when you sync — nothing happens in the background without your action.
      </p>
      <p style={{ marginBottom: '0.5rem' }}>
        <Link href="/transactions" style={{ color: 'var(--lp-accent-teal)', fontWeight: 600 }}>
          ← Back to Transactions
        </Link>
      </p>

      {syncQuota && (
        <p style={{ color: 'var(--lp-muted)', fontSize: '0.9rem', marginBottom: '1.25rem' }}>
          {syncQuota.daily_limit <= 0
            ? 'Manual bank sync is not included in your current plan (UTC daily limits).'
            : `Manual syncs left today (UTC): ${syncQuota.remaining} of ${syncQuota.daily_limit}`}
        </p>
      )}

      <div className={styles.subContainer} style={{ marginBottom: '1.5rem' }}>
        <h2 style={{ marginTop: 0 }}>Providers</h2>
        {loadError && <p className={styles.error}>{loadError}</p>}
        {flowError && (
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', flexWrap: 'wrap', marginBottom: '0.5rem' }}>
            <p className={styles.error} style={{ margin: 0 }}>{flowError}</p>
            {lastConnectedId && (
              <button
                type="button"
                onClick={() => void startConnect(lastConnectedId)}
                style={{
                  padding: '0.3rem 0.85rem', borderRadius: 8, border: 'none',
                  background: 'var(--lp-accent-teal)', color: '#fff', fontWeight: 600,
                  fontSize: '0.82rem', cursor: 'pointer', whiteSpace: 'nowrap',
                }}
              >
                Try again →
              </button>
            )}
          </div>
        )}
        {!loadError && providers.length === 0 && <p className={styles.emptyState}>No providers registered.</p>}
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))',
            gap: '0.75rem',
          }}
        >
          {providers.map((p) => (
            <div
              key={p.id}
              style={{
                border: '1px solid var(--lp-border)',
                borderRadius: 12,
                padding: '1rem',
                background: 'var(--lp-bg-elevated)',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.65rem', marginBottom: '0.35rem' }}>
                {p.logo_url ? (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img src={p.logo_url} alt="" width={28} height={28} style={{ borderRadius: 6 }} />
                ) : null}
                <div style={{ flex: 1 }}>
                  <div style={{ fontWeight: 700 }}>{p.display_name}</div>
                  {p.id === PREFERRED_PROVIDER_ID ? (
                    <div style={{ fontSize: '0.72rem', color: 'var(--lp-accent-teal)', fontWeight: 600 }}>
                      Recommended
                    </div>
                  ) : null}
                </div>
              </div>
              <div style={{ fontSize: '0.78rem', color: 'var(--lp-muted)', marginBottom: '0.75rem' }}>
                {p.id}
                {p.configured === 'false' && (
                  <span style={{ display: 'block', marginTop: 4, color: '#ca8a04' }}>
                    Not configured in this environment
                  </span>
                )}
              </div>
              <button
                type="button"
                disabled={connectingId !== '' || p.configured === 'false'}
                onClick={() => void startConnect(p.id)}
                style={{
                  width: '100%',
                  padding: '0.55rem 1rem',
                  borderRadius: 8,
                  border: 'none',
                  background: 'var(--lp-accent-teal)',
                  color: '#fff',
                  fontWeight: 600,
                  cursor: connectingId !== '' || p.configured === 'false' ? 'not-allowed' : 'pointer',
                  opacity: p.configured === 'false' ? 0.55 : 1,
                }}
              >
                {connectingId === p.id ? 'Redirecting…' : 'Connect'}
              </button>
            </div>
          ))}
        </div>
      </div>

      <div className={styles.subContainer}>
        <h2 style={{ marginTop: 0 }}>Statement-style export (CSV)</h2>
        <p style={{ color: 'var(--lp-muted)', fontSize: '0.9rem', marginBottom: '0.75rem', maxWidth: 720 }}>
          Download transactions already stored in MyNetTax (from your last manual bank sync). This is not a bank PDF
          statement; lenders may ask for originals. Default window is about six months (180 days).
        </p>
        {statementExportError && <p className={styles.error}>{statementExportError}</p>}
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem', alignItems: 'center' }}>
          <button
            type="button"
            className={styles.button}
            disabled={statementExportBusy}
            onClick={() => void downloadStatementCsv(180)}
          >
            {statementExportBusy ? 'Preparing…' : 'Download last ~6 months (180 days)'}
          </button>
          <button
            type="button"
            className={styles.button}
            disabled={statementExportBusy}
            onClick={() => void downloadStatementCsv(90)}
          >
            Last 90 days
          </button>
        </div>
      </div>

      <div className={styles.subContainer}>
        <h2 style={{ marginTop: 0 }}>UK banks & brands (via Open Banking)</h2>
        <p style={{ color: 'var(--lp-muted)', fontSize: '0.9rem', marginBottom: '1rem' }}>
          Coverage depends on Salt Edge and your account type. You will choose the institution on the Salt Edge screen.
          Typical UK brands:
        </p>
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fill, minmax(160px, 1fr))',
            gap: '0.5rem',
          }}
        >
          {UK_BANKS_INFO.map((b) => (
            <div
              key={b.name}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '0.45rem',
                color: 'var(--lp-muted)',
                fontSize: '0.85rem',
              }}
            >
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img src={faviconUrl(b.domain)} alt="" width={20} height={20} style={{ borderRadius: 4 }} />
              <span>{b.name}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
