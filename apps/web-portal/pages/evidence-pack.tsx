import Link from 'next/link';
import { useEffect, useState } from 'react';
import styles from '../styles/Home.module.css';

const TXN_SERVICE_URL = process.env.NEXT_PUBLIC_TRANSACTIONS_SERVICE_URL || '/api/transactions';

type CisRecordSummary = {
  id: string;
  contractor_name: string;
  period_start: string;
  period_end: string;
  evidence_status: string;
  cis_deducted_total: number;
  has_document?: boolean;
  document_id?: string | null;
  reconciliation_status?: string | null;
};

type ManifestSummary = {
  verified_records: number;
  unverified_records: number;
  open_tasks: number;
};

type ManifestPayload = {
  schema_version: string;
  pack_tier: string;
  generated_at: string;
  summary: ManifestSummary;
  cis_records: CisRecordSummary[];
  watermark_unverified_cis: string;
  export_legal_notice: string;
  audit_summary?: { note: string };
};

type ShareToken = {
  token: string;
  expires_at: string;
};

type TxnSummary = {
  total: number;
  income_count: number;
  expense_count: number;
  cis_count: number;
  income_total_gbp: number;
  expense_total_gbp: number;
  category_totals: Record<string, number>;
};

const fmt = (iso: string) => {
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? iso : d.toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' });
};

function evidenceLabel(status: string): { label: string; color: string } {
  if (status === 'verified_with_statement') return { label: 'Verified', color: '#10b981' };
  if (status === 'self_attested_no_statement') return { label: 'Unverified', color: '#f59e0b' };
  if (status === 'pending_review') return { label: 'Pending review', color: '#3b82f6' };
  if (status === 'statement_uploaded') return { label: 'Statement uploaded', color: '#14b8a6' };
  return { label: status, color: 'var(--text-secondary)' };
}

export default function EvidencePackPage({ token }: { token: string }) {
  const [manifest, setManifest] = useState<ManifestPayload | null>(null);
  const [err, setErr] = useState('');
  const [loading, setLoading] = useState(true);
  const [downloading, setDownloading] = useState(false);
  const [shareToken, setShareToken] = useState<ShareToken | null>(null);
  const [generating, setGenerating] = useState(false);
  const [shareErr, setShareErr] = useState('');
  const [copied, setCopied] = useState(false);
  const [txnSummary, setTxnSummary] = useState<TxnSummary | null>(null);

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      try {
        const [manifestRes, txnRes] = await Promise.all([
          fetch(`${TXN_SERVICE_URL}/cis/evidence-pack/manifest`, {
            headers: { Authorization: `Bearer ${token}` },
          }),
          fetch(`${TXN_SERVICE_URL}/transactions/me`, {
            headers: { Authorization: `Bearer ${token}` },
          }),
        ]);
        if (cancelled) return;

        const j = await manifestRes.json().catch(() => ({}));
        if (manifestRes.status === 403) {
          setErr((j as { detail?: string }).detail || 'Evidence pack requires Growth plan or higher.');
        } else if (!manifestRes.ok) {
          setErr((j as { detail?: string }).detail || 'Could not load evidence pack.');
        } else {
          setManifest((j as { manifest: ManifestPayload }).manifest);
        }

        if (txnRes.ok) {
          const txns = (await txnRes.json().catch(() => [])) as Array<{ amount: number; category?: string | null }>;
          const income = txns.filter((t) => t.amount > 0);
          const expense = txns.filter((t) => t.amount < 0);
          const cis = txns.filter((t) => t.category === 'cis_income' || t.category === 'cis' || t.category === 'cis_payment');
          const catTotals: Record<string, number> = {};
          for (const t of txns) {
            if (t.amount < 0 && t.category) {
              catTotals[t.category] = (catTotals[t.category] ?? 0) + Math.abs(t.amount);
            }
          }
          if (!cancelled) setTxnSummary({
            total: txns.length,
            income_count: income.length,
            expense_count: expense.length,
            cis_count: cis.length,
            income_total_gbp: income.reduce((s, t) => s + t.amount, 0),
            expense_total_gbp: expense.reduce((s, t) => s + Math.abs(t.amount), 0),
            category_totals: catTotals,
          });
        }
      } catch {
        if (!cancelled) setErr('Failed to load evidence pack.');
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => { cancelled = true; };
  }, [token]);

  const handleDownload = async () => {
    setDownloading(true);
    try {
      const r = await fetch(`${TXN_SERVICE_URL}/cis/evidence-pack/zip`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!r.ok) {
        const j = await r.json().catch(() => ({}));
        setErr((j as { detail?: string }).detail || 'Download failed.');
        return;
      }
      const blob = await r.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'mynettax-cis-evidence-pack.zip';
      a.click();
      URL.revokeObjectURL(url);
    } finally {
      setDownloading(false);
    }
  };

  const handleGenerateShareLink = async () => {
    setGenerating(true);
    setShareErr('');
    try {
      const r = await fetch(`${TXN_SERVICE_URL}/cis/evidence-pack/share-token`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
      });
      const j = await r.json().catch(() => ({}));
      if (!r.ok) {
        setShareErr((j as { detail?: string }).detail || 'Could not generate share link.');
        return;
      }
      setShareToken(j as ShareToken);
    } finally {
      setGenerating(false);
    }
  };

  const shareUrl = shareToken
    ? `${TXN_SERVICE_URL}/cis/evidence-pack/shared-zip?token=${shareToken.token}`
    : '';

  const handleCopy = () => {
    void navigator.clipboard.writeText(shareUrl).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  };

  const daysUntilExpiry = shareToken
    ? Math.max(0, Math.ceil((new Date(shareToken.expires_at).getTime() - Date.now()) / (1000 * 60 * 60 * 24)))
    : 0;

  return (
    <div className={styles.container} style={{ maxWidth: 960, margin: '0 auto', padding: '24px 16px' }}>
      <h1 style={{ fontSize: '1.35rem', marginBottom: 8 }}>Evidence Pack</h1>
      <p style={{ color: 'var(--text-secondary)', fontSize: '0.88rem', lineHeight: 1.5, marginBottom: 20 }}>
        Quarter evidence bundle: CIS records, reconciliation status, and accountant share link.{' '}
        <Link href="/cis-refund-tracker" style={{ color: 'var(--accent)' }}>CIS refund tracker</Link>
        {' · '}
        <Link href="/tax-preparation" style={{ color: 'var(--accent)' }}>Tax preparation</Link>
      </p>

      {loading && <p style={{ color: 'var(--text-secondary)', fontSize: '0.88rem' }}>Loading evidence pack…</p>}
      {err && (
        <div style={{ padding: '1rem', borderRadius: 10, background: 'rgba(239,68,68,0.08)', border: '1px solid rgba(239,68,68,0.25)', marginBottom: 20 }}>
          <p style={{ color: '#ef4444', margin: 0, fontWeight: 600 }}>{err}</p>
          {err.includes('plan') && (
            <p style={{ margin: '0.5rem 0 0', fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
              <Link href="/my-subscription" style={{ color: 'var(--accent)' }}>Upgrade your plan</Link> to unlock the Evidence Pack.
            </p>
          )}
        </div>
      )}

      {manifest && (
        <>
          {/* Summary cards */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))', gap: 12, marginBottom: 20 }}>
            <div style={{ background: 'var(--card-bg)', borderRadius: 10, padding: 14, border: '1px solid var(--border)' }}>
              <div style={{ fontSize: '0.72rem', color: 'var(--text-tertiary)' }}>Verified records</div>
              <div style={{ fontWeight: 700, fontSize: '1.2rem', color: '#10b981' }}>{manifest.summary.verified_records}</div>
            </div>
            <div style={{ background: 'var(--card-bg)', borderRadius: 10, padding: 14, border: '1px solid var(--border)' }}>
              <div style={{ fontSize: '0.72rem', color: 'var(--text-tertiary)' }}>Unverified records</div>
              <div style={{ fontWeight: 700, fontSize: '1.2rem', color: manifest.summary.unverified_records > 0 ? '#f59e0b' : 'var(--text-primary)' }}>
                {manifest.summary.unverified_records}
              </div>
            </div>
            <div style={{ background: 'var(--card-bg)', borderRadius: 10, padding: 14, border: '1px solid var(--border)' }}>
              <div style={{ fontSize: '0.72rem', color: 'var(--text-tertiary)' }}>Open tasks</div>
              <div style={{ fontWeight: 700, fontSize: '1.2rem', color: manifest.summary.open_tasks > 0 ? '#ef4444' : 'var(--text-primary)' }}>
                {manifest.summary.open_tasks}
              </div>
            </div>
            <div style={{ background: 'var(--card-bg)', borderRadius: 10, padding: 14, border: '1px solid var(--border)' }}>
              <div style={{ fontSize: '0.72rem', color: 'var(--text-tertiary)' }}>Pack tier</div>
              <div style={{ fontWeight: 700, fontSize: '1rem', textTransform: 'capitalize' }}>{manifest.pack_tier}</div>
            </div>
          </div>

          {manifest.summary.unverified_records > 0 && (
            <div style={{ padding: '0.75rem 1rem', borderRadius: 10, background: 'rgba(245,158,11,0.1)', border: '1px solid rgba(245,158,11,0.35)', marginBottom: 16, fontSize: '0.82rem', color: 'rgba(15,23,42,0.75)' }}>
              <strong>Unverified CIS watermark:</strong> {manifest.watermark_unverified_cis}
            </div>
          )}

          {/* Download + Share actions */}
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.75rem', marginBottom: 24 }}>
            <button
              type="button"
              onClick={handleDownload}
              disabled={downloading}
              style={{
                padding: '0.55rem 1.25rem', borderRadius: 8,
                background: 'var(--lp-accent-teal, #0d9488)', color: '#fff',
                fontWeight: 700, fontSize: '0.88rem', border: 'none',
                cursor: downloading ? 'not-allowed' : 'pointer', opacity: downloading ? 0.7 : 1,
              }}
            >
              {downloading ? 'Preparing ZIP…' : 'Download ZIP'}
            </button>
            <button
              type="button"
              onClick={handleGenerateShareLink}
              disabled={generating}
              style={{
                padding: '0.55rem 1.25rem', borderRadius: 8,
                border: '1px solid var(--lp-accent-teal, #0d9488)',
                color: 'var(--lp-accent-teal, #0d9488)',
                fontWeight: 700, fontSize: '0.88rem', background: 'transparent',
                cursor: generating ? 'not-allowed' : 'pointer', opacity: generating ? 0.7 : 1,
              }}
            >
              {generating ? 'Generating…' : 'Generate accountant share link'}
            </button>
          </div>

          {shareErr && <p style={{ color: '#ef4444', fontSize: '0.85rem', marginBottom: 12 }}>{shareErr}</p>}

          {shareToken && (
            <div style={{ padding: '0.85rem 1rem', borderRadius: 10, background: 'rgba(13,148,136,0.08)', border: '1px solid rgba(13,148,136,0.3)', marginBottom: 24 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '0.5rem', marginBottom: 8 }}>
                <span style={{ fontWeight: 700, fontSize: '0.88rem' }}>Accountant share link</span>
                <span style={{ fontSize: '0.75rem', color: 'var(--text-tertiary)' }}>
                  Expires {fmt(shareToken.expires_at)} ({daysUntilExpiry} day{daysUntilExpiry !== 1 ? 's' : ''})
                </span>
              </div>
              <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center', flexWrap: 'wrap' }}>
                <code style={{ fontSize: '0.75rem', wordBreak: 'break-all', flex: 1, color: 'var(--text-secondary)', background: 'var(--card-bg)', padding: '0.3rem 0.5rem', borderRadius: 6 }}>
                  {shareUrl}
                </code>
                <button
                  type="button"
                  onClick={handleCopy}
                  style={{ padding: '0.35rem 0.85rem', borderRadius: 6, border: '1px solid var(--border)', background: copied ? '#10b981' : 'var(--card-bg)', color: copied ? '#fff' : 'var(--text-primary)', fontWeight: 600, fontSize: '0.78rem', cursor: 'pointer', whiteSpace: 'nowrap' }}
                >
                  {copied ? 'Copied!' : 'Copy link'}
                </button>
              </div>
              <p style={{ margin: '0.5rem 0 0', fontSize: '0.72rem', color: 'var(--text-tertiary)' }}>
                Your accountant can download the ZIP directly using this link — no login required. The link expires automatically.
              </p>
            </div>
          )}

          {/* CIS records table */}
          {manifest.cis_records.length === 0 ? (
            <p style={{ color: 'var(--text-secondary)', fontSize: '0.88rem' }}>
              No CIS records yet.{' '}
              <Link href="/cis-refund-tracker" style={{ color: 'var(--accent)' }}>Upload a statement</Link> to get started.
            </p>
          ) : (
            <section>
              <h2 style={{ fontSize: '1rem', marginBottom: 10 }}>CIS records ({manifest.cis_records.length})</h2>
              <div style={{ overflowX: 'auto' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.82rem' }}>
                  <thead>
                    <tr style={{ textAlign: 'left', color: 'var(--text-tertiary)' }}>
                      <th style={{ padding: '8px 6px', borderBottom: '1px solid var(--border)' }}>Contractor</th>
                      <th style={{ padding: '8px 6px', borderBottom: '1px solid var(--border)' }}>Period</th>
                      <th style={{ padding: '8px 6px', borderBottom: '1px solid var(--border)' }}>CIS deducted</th>
                      <th style={{ padding: '8px 6px', borderBottom: '1px solid var(--border)' }}>Status</th>
                      <th style={{ padding: '8px 6px', borderBottom: '1px solid var(--border)' }}>Document</th>
                    </tr>
                  </thead>
                  <tbody>
                    {manifest.cis_records.map((r) => {
                      const ev = evidenceLabel(r.evidence_status);
                      return (
                        <tr key={r.id}>
                          <td style={{ padding: '10px 6px', borderBottom: '1px solid var(--border)' }}>{r.contractor_name}</td>
                          <td style={{ padding: '10px 6px', borderBottom: '1px solid var(--border)', whiteSpace: 'nowrap' }}>
                            {fmt(r.period_start)} – {fmt(r.period_end)}
                          </td>
                          <td style={{ padding: '10px 6px', borderBottom: '1px solid var(--border)' }}>
                            £{r.cis_deducted_total.toLocaleString('en-GB', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                          </td>
                          <td style={{ padding: '10px 6px', borderBottom: '1px solid var(--border)', color: ev.color, fontWeight: 600 }}>
                            {ev.label}
                          </td>
                          <td style={{ padding: '10px 6px', borderBottom: '1px solid var(--border)' }}>
                            {(r.has_document ?? !!r.document_id) ? (
                              <span style={{ color: '#10b981', fontSize: '0.78rem' }}>✓ Uploaded</span>
                            ) : (
                              <Link href="/cis-refund-tracker" style={{ color: '#f59e0b', fontSize: '0.78rem' }}>Upload statement</Link>
                            )}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </section>
          )}

          <p style={{ fontSize: '0.72rem', color: 'var(--text-tertiary)', marginTop: 24, lineHeight: 1.55 }}>
            {manifest.export_legal_notice}
          </p>

          {/* Transaction Summary */}
          {txnSummary && txnSummary.total > 0 && (
            <section style={{ marginTop: 28 }}>
              <h2 style={{ fontSize: '1rem', marginBottom: 12 }}>Transaction Summary</h2>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))', gap: 10, marginBottom: 16 }}>
                {[
                  { label: 'Total transactions', value: txnSummary.total.toString(), color: 'var(--text-primary)' },
                  { label: 'Income transactions', value: txnSummary.income_count.toString(), color: '#10b981' },
                  { label: 'Expense transactions', value: txnSummary.expense_count.toString(), color: '#ef4444' },
                  { label: 'CIS payments', value: txnSummary.cis_count.toString(), color: '#3b82f6' },
                ].map(({ label, value, color }) => (
                  <div key={label} style={{ background: 'var(--card-bg)', borderRadius: 10, padding: '0.85rem', border: '1px solid var(--border)' }}>
                    <div style={{ fontSize: '0.72rem', color: 'var(--text-tertiary)' }}>{label}</div>
                    <div style={{ fontWeight: 700, fontSize: '1.1rem', color }}>{value}</div>
                  </div>
                ))}
              </div>
              <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
                <div style={{ flex: 1, minWidth: 140, background: 'rgba(16,185,129,0.07)', borderRadius: 10, padding: '0.85rem', border: '1px solid rgba(16,185,129,0.2)' }}>
                  <div style={{ fontSize: '0.72rem', color: '#10b981', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.05em' }}>Total income</div>
                  <div style={{ fontWeight: 800, fontSize: '1.25rem', color: '#10b981' }}>
                    £{txnSummary.income_total_gbp.toLocaleString('en-GB', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                  </div>
                </div>
                <div style={{ flex: 1, minWidth: 140, background: 'rgba(239,68,68,0.07)', borderRadius: 10, padding: '0.85rem', border: '1px solid rgba(239,68,68,0.2)' }}>
                  <div style={{ fontSize: '0.72rem', color: '#ef4444', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.05em' }}>Total expenses</div>
                  <div style={{ fontWeight: 800, fontSize: '1.25rem', color: '#ef4444' }}>
                    £{txnSummary.expense_total_gbp.toLocaleString('en-GB', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                  </div>
                </div>
              </div>
            </section>
          )}

          {/* Category Breakdown */}
          {txnSummary && Object.keys(txnSummary.category_totals).length > 0 && (
            <section style={{ marginTop: 24 }}>
              <h2 style={{ fontSize: '1rem', marginBottom: 10 }}>Expense Category Breakdown</h2>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: 8 }}>
                {Object.entries(txnSummary.category_totals)
                  .sort(([, a], [, b]) => b - a)
                  .map(([cat, total]) => (
                    <div key={cat} style={{ display: 'flex', justifyContent: 'space-between', padding: '0.55rem 0.75rem', background: 'var(--card-bg)', borderRadius: 8, border: '1px solid var(--border)', fontSize: '0.82rem' }}>
                      <span style={{ color: 'var(--text-secondary)', textTransform: 'capitalize' }}>{cat.replace(/_/g, ' ')}</span>
                      <span style={{ fontWeight: 600 }}>£{total.toLocaleString('en-GB', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span>
                    </div>
                  ))}
              </div>
              <p style={{ fontSize: '0.72rem', color: 'var(--text-tertiary)', marginTop: 8 }}>
                Expense categories from your transaction history. For the full tax calculation visit{' '}
                <Link href="/tax-preparation" style={{ color: 'var(--accent)' }}>Tax preparation</Link>.
              </p>
            </section>
          )}

          <p style={{ fontSize: '0.68rem', color: 'var(--text-tertiary)', marginTop: 12 }}>
            Pack generated: {fmt(manifest.generated_at)}
          </p>
        </>
      )}
    </div>
  );
}
