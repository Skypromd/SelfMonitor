import Head from 'next/head';
import Link from 'next/link';
import { useEffect, useState } from 'react';
import styles from '../styles/Home.module.css';

const API_GATEWAY_ROOT = (process.env.NEXT_PUBLIC_API_GATEWAY_URL || '/api').replace(/\/$/, '');
const FINOPS_URL = `${API_GATEWAY_ROOT}/finops`;

type Obligation = {
  obligation_id?: string;
  period_start: string;
  period_end: string;
  due_date: string;
  status: 'open' | 'fulfilled' | 'overdue' | string;
  quarter?: string;
  period_key?: string;
};

type MtdObligationsResponse = {
  obligations?: Obligation[];
  quarterly_updates?: Obligation[];
  status?: string;
  due_date?: string;
  period_start?: string;
  period_end?: string;
  quarter?: string;
};

function daysUntil(dateStr: string): number {
  const due = new Date(dateStr);
  const now = new Date();
  now.setHours(0, 0, 0, 0);
  due.setHours(0, 0, 0, 0);
  return Math.round((due.getTime() - now.getTime()) / 86_400_000);
}

function StatusPill({ status }: { status: string }) {
  const map: Record<string, { bg: string; border: string; color: string; label: string }> = {
    open: { bg: '#f59e0b15', border: '#f59e0b', color: '#f59e0b', label: 'Open' },
    fulfilled: { bg: '#22c55e15', border: '#22c55e', color: '#22c55e', label: 'Fulfilled' },
    overdue: { bg: '#ef444415', border: '#ef4444', color: '#ef4444', label: 'Overdue' },
  };
  const s = map[status] ?? { bg: '#64748b15', border: '#64748b', color: '#64748b', label: status };
  return (
    <span style={{
      padding: '2px 10px', borderRadius: 999, fontSize: '0.75rem', fontWeight: 700,
      background: s.bg, border: `1px solid ${s.border}`, color: s.color,
    }}>
      {s.label}
    </span>
  );
}

type Props = { token: string };

export default function ObligationsPage({ token }: Props) {
  const [obligations, setObligations] = useState<Obligation[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!token) return;
    setLoading(true);
    setError('');

    fetch(`${FINOPS_URL}/mtd/obligations`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then(async (r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        const data = (await r.json()) as MtdObligationsResponse;
        // Normalise: accept obligations array, quarterly_updates array, or single object
        if (Array.isArray(data.obligations)) {
          setObligations(data.obligations);
        } else if (Array.isArray(data.quarterly_updates)) {
          setObligations(data.quarterly_updates);
        } else if (data.period_start && data.period_end && data.due_date) {
          setObligations([
            {
              period_start: data.period_start,
              period_end: data.period_end,
              due_date: data.due_date,
              status: data.status ?? 'open',
              quarter: data.quarter,
            },
          ]);
        } else {
          setObligations([]);
        }
      })
      .catch(() => {
        // Fallback: try /mtd/status
        fetch(`${FINOPS_URL}/mtd/status`, {
          headers: { Authorization: `Bearer ${token}` },
        })
          .then(async (r2) => {
            if (!r2.ok) {
              setError('No obligation data available.');
              return;
            }
            const d2 = (await r2.json()) as MtdObligationsResponse;
            if (d2.period_start && d2.period_end && d2.due_date) {
              setObligations([
                {
                  period_start: d2.period_start,
                  period_end: d2.period_end,
                  due_date: d2.due_date,
                  status: d2.status ?? 'open',
                  quarter: d2.quarter,
                },
              ]);
            } else {
              setObligations([]);
            }
          })
          .catch(() => setError('Failed to load obligations.'));
      })
      .finally(() => setLoading(false));
  }, [token]);

  const fmtDate = (s: string) =>
    new Date(s).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' });

  return (
    <>
      <Head>
        <title>Deadlines &amp; Obligations — MyNetTax</title>
      </Head>
      <div className={styles.pageContainer}>
        <div className={styles.pageHeader}>
          <p className={styles.pageEyebrow}>MTD ITSA</p>
          <h1 className={styles.pageTitle}>Deadlines &amp; Obligations</h1>
          <p className={styles.pageLead}>
            Your upcoming HMRC filing obligations. Stay ahead of every deadline to avoid penalties.
          </p>
        </div>

        {loading && (
          <p style={{ color: 'var(--lp-muted)', fontSize: '0.9rem', padding: '2rem 0' }}>Loading…</p>
        )}
        {error && <p style={{ color: '#ef4444', fontSize: '0.88rem', marginBottom: '1rem' }}>{error}</p>}

        {!loading && !error && obligations.length === 0 && (
          <div className={styles.subContainer} style={{ textAlign: 'center', padding: '2rem' }}>
            <p style={{ color: 'var(--lp-muted)', fontSize: '0.9rem', margin: '0 0 1rem' }}>
              No obligations found. Connect your HMRC account to see your filing deadlines.
            </p>
            <Link href="/tax-preparation" style={{
              padding: '0.55rem 1.4rem', borderRadius: 10,
              background: 'var(--lp-accent-teal)', color: '#fff',
              fontWeight: 700, fontSize: '0.88rem', textDecoration: 'none',
            }}>
              Connect HMRC →
            </Link>
          </div>
        )}

        {!loading && obligations.length > 0 && (
          <>
            {/* Summary strip */}
            <div style={{
              display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
              gap: '0.75rem', marginBottom: '1.5rem',
            }}>
              {[
                { label: 'Total obligations', value: String(obligations.length), color: 'var(--text-primary)' },
                {
                  label: 'Open / Overdue',
                  value: String(obligations.filter(o => o.status === 'open' || o.status === 'overdue').length),
                  color: '#f59e0b',
                },
                {
                  label: 'Fulfilled',
                  value: String(obligations.filter(o => o.status === 'fulfilled').length),
                  color: '#22c55e',
                },
              ].map(({ label, value, color }) => (
                <div key={label} className={styles.subContainer} style={{ padding: '0.85rem 1rem' }}>
                  <div style={{ fontSize: '1.5rem', fontWeight: 800, color }}>{value}</div>
                  <div style={{ fontSize: '0.75rem', color: 'var(--lp-muted)', marginTop: 2 }}>{label}</div>
                </div>
              ))}
            </div>

            {/* Obligations table */}
            <div className={styles.subContainer} style={{ padding: 0, overflow: 'hidden' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.88rem' }}>
                <thead>
                  <tr style={{ background: 'var(--lp-bg-elevated)', borderBottom: '1px solid var(--lp-border)' }}>
                    {['Quarter / Period', 'Period', 'Due date', 'Days left', 'Status', ''].map((h) => (
                      <th key={h} style={{
                        padding: '0.7rem 1rem', textAlign: 'left',
                        fontWeight: 700, fontSize: '0.75rem', color: 'var(--lp-muted)',
                        textTransform: 'uppercase', letterSpacing: '0.05em', whiteSpace: 'nowrap',
                      }}>
                        {h}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {obligations.map((ob, i) => {
                    const days = daysUntil(ob.due_date);
                    const daysColor =
                      ob.status === 'fulfilled' ? '#22c55e' :
                      days < 0 ? '#ef4444' :
                      days <= 14 ? '#f59e0b' : 'var(--text-primary)';
                    const daysLabel =
                      ob.status === 'fulfilled' ? 'Done' :
                      days < 0 ? `${Math.abs(days)}d overdue` :
                      days === 0 ? 'Due today' :
                      `${days}d`;
                    return (
                      <tr
                        key={ob.obligation_id ?? `${ob.period_start}-${i}`}
                        style={{
                          borderBottom: '1px solid var(--lp-border)',
                          background: i % 2 === 0 ? 'transparent' : 'var(--lp-bg-elevated)',
                        }}
                      >
                        <td style={{ padding: '0.8rem 1rem', fontWeight: 600, color: 'var(--text-primary)' }}>
                          {ob.quarter ?? ob.period_key ?? `Q${i + 1}`}
                        </td>
                        <td style={{ padding: '0.8rem 1rem', color: 'var(--lp-muted)', whiteSpace: 'nowrap' }}>
                          {fmtDate(ob.period_start)} – {fmtDate(ob.period_end)}
                        </td>
                        <td style={{ padding: '0.8rem 1rem', color: 'var(--text-primary)', whiteSpace: 'nowrap' }}>
                          {fmtDate(ob.due_date)}
                        </td>
                        <td style={{ padding: '0.8rem 1rem', fontWeight: 700, color: daysColor, whiteSpace: 'nowrap' }}>
                          {daysLabel}
                        </td>
                        <td style={{ padding: '0.8rem 1rem' }}>
                          <StatusPill status={ob.status} />
                        </td>
                        <td style={{ padding: '0.8rem 1rem' }}>
                          {ob.status !== 'fulfilled' && (
                            <Link href="/tax-readiness" style={{
                              fontSize: '0.78rem', fontWeight: 600,
                              color: 'var(--lp-accent-teal)', textDecoration: 'none',
                            }}>
                              Check readiness →
                            </Link>
                          )}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>

            {/* CTAs */}
            <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap', marginTop: '1.5rem' }}>
              <Link href="/tax-readiness" style={{
                padding: '0.6rem 1.4rem', borderRadius: 10,
                background: 'var(--lp-accent-teal)', color: '#fff',
                fontWeight: 700, fontSize: '0.9rem', textDecoration: 'none',
              }}>
                Check Tax Readiness →
              </Link>
              <Link href="/tax-preparation" style={{
                padding: '0.6rem 1.4rem', borderRadius: 10,
                border: '1px solid var(--lp-border)', color: 'var(--lp-muted)',
                fontWeight: 600, fontSize: '0.9rem', textDecoration: 'none',
              }}>
                Go to MTD Submission
              </Link>
            </div>
          </>
        )}
      </div>
    </>
  );
}
