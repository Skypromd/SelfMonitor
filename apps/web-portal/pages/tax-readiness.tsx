import Head from 'next/head';
import Link from 'next/link';
import { useEffect, useState } from 'react';
import styles from '../styles/Home.module.css';

const API_GATEWAY_ROOT = (process.env.NEXT_PUBLIC_API_GATEWAY_URL || '/api').replace(/\/$/, '');
const FINOPS_URL = `${API_GATEWAY_ROOT}/finops`;
const TXN_URL = `${API_GATEWAY_ROOT}/transactions`;

type ReadinessData = {
  uncategorized_count: number;
  missing_business_pct: number;
  unmatched_receipts: number;
  cis_unverified: number;
  score: number;
};

type MtdStatus = {
  quarter?: string;
  status?: string;
  due_date?: string;
  period_start?: string;
  period_end?: string;
};

type Blocker = {
  label: string;
  count: number;
  action: string;
  href: string;
  color: string;
};

type Props = { token: string };

export default function TaxReadinessPage({ token }: Props) {
  const [readiness, setReadiness] = useState<ReadinessData | null>(null);
  const [mtdStatus, setMtdStatus] = useState<MtdStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!token) return;
    setLoading(true);
    setError('');

    const headers = { Authorization: `Bearer ${token}` };

    const fetchAll = async () => {
      try {
        const [rdRes, mtdRes] = await Promise.allSettled([
          fetch(`${TXN_URL}/transactions/readiness`, { headers }),
          fetch(`${FINOPS_URL}/mtd/status`, { headers }),
        ]);

        if (rdRes.status === 'fulfilled' && rdRes.value.ok) {
          setReadiness((await rdRes.value.json()) as ReadinessData);
        }
        if (mtdRes.status === 'fulfilled' && mtdRes.value.ok) {
          setMtdStatus((await mtdRes.value.json()) as MtdStatus);
        }
      } catch {
        setError('Failed to load readiness data.');
      } finally {
        setLoading(false);
      }
    };

    void fetchAll();
  }, [token]);

  const blockers: Blocker[] = readiness
    ? [
        {
          label: 'Uncategorised transactions',
          count: readiness.uncategorized_count,
          action: 'Categorise now',
          href: '/transactions',
          color: '#f59e0b',
        },
        {
          label: 'Expenses without business %',
          count: readiness.missing_business_pct,
          action: 'Set business use',
          href: '/transactions',
          color: '#ef4444',
        },
        {
          label: 'Unmatched receipts',
          count: readiness.unmatched_receipts,
          action: 'Match receipts',
          href: '/transactions',
          color: '#8b5cf6',
        },
        {
          label: 'CIS records unverified',
          count: readiness.cis_unverified,
          action: 'Verify CIS',
          href: '/transactions',
          color: '#0891b2',
        },
      ].filter((b) => b.count > 0)
    : [];

  const score = readiness?.score ?? null;

  const scoreColor =
    score === null ? '#64748b' : score >= 80 ? '#22c55e' : score >= 50 ? '#f59e0b' : '#ef4444';

  const scoreLabel =
    score === null ? '—' : score >= 80 ? 'Ready' : score >= 50 ? 'In Progress' : 'Needs Attention';

  return (
    <>
      <Head>
        <title>Tax Readiness — MyNetTax</title>
      </Head>
      <div className={styles.pageContainer}>
        {/* Header */}
        <div className={styles.pageHeader}>
          <p className={styles.pageEyebrow}>Quarter Readiness</p>
          <h1 className={styles.pageTitle}>Tax Readiness</h1>
          <p className={styles.pageLead}>
            Fix blockers before your MTD submission deadline. Every resolved item improves your readiness score.
          </p>
        </div>

        {loading && (
          <p style={{ color: 'var(--lp-muted)', fontSize: '0.9rem', padding: '2rem 0' }}>Loading…</p>
        )}

        {error && <p className={styles.error}>{error}</p>}

        {!loading && (
          <>
            {/* Score card */}
            <div
              className={styles.subContainer}
              style={{ display: 'flex', alignItems: 'center', gap: '2rem', flexWrap: 'wrap', marginBottom: '1.5rem' }}
            >
              <div style={{ textAlign: 'center', minWidth: 100 }}>
                <div
                  style={{
                    fontSize: '3rem',
                    fontWeight: 800,
                    color: scoreColor,
                    lineHeight: 1,
                  }}
                >
                  {score ?? '—'}
                </div>
                <div style={{ fontSize: '0.75rem', color: 'var(--lp-muted)', marginTop: 4 }}>/ 100</div>
              </div>
              <div>
                <div
                  style={{
                    display: 'inline-block',
                    padding: '0.25rem 0.85rem',
                    borderRadius: 999,
                    background: `${scoreColor}22`,
                    border: `1px solid ${scoreColor}55`,
                    color: scoreColor,
                    fontSize: '0.82rem',
                    fontWeight: 700,
                    marginBottom: '0.4rem',
                  }}
                >
                  {scoreLabel}
                </div>
                <p style={{ color: 'var(--lp-muted)', fontSize: '0.88rem', margin: 0 }}>
                  {blockers.length === 0
                    ? 'All clear — your records are ready for MTD submission.'
                    : `${blockers.length} blocker${blockers.length > 1 ? 's' : ''} found. Resolve them to increase your score.`}
                </p>
              </div>

              {/* Score bar */}
              <div style={{ flex: 1, minWidth: 180 }}>
                <div
                  style={{
                    height: 10,
                    borderRadius: 999,
                    background: 'var(--lp-border)',
                    overflow: 'hidden',
                  }}
                >
                  <div
                    style={{
                      height: '100%',
                      width: `${score ?? 0}%`,
                      background: scoreColor,
                      borderRadius: 999,
                      transition: 'width 0.6s ease',
                    }}
                  />
                </div>
              </div>
            </div>

            {/* MTD status */}
            {mtdStatus && (
              <div className={styles.subContainer} style={{ marginBottom: '1.5rem' }}>
                <h2 style={{ margin: '0 0 0.6rem', fontSize: '1rem' }}>MTD Obligation Status</h2>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '1rem', fontSize: '0.88rem', color: 'var(--lp-muted)' }}>
                  {mtdStatus.quarter && (
                    <span>
                      Quarter: <strong style={{ color: 'var(--text-primary)' }}>{mtdStatus.quarter}</strong>
                    </span>
                  )}
                  {mtdStatus.status && (
                    <span>
                      Status:{' '}
                      <strong
                        style={{
                          color:
                            mtdStatus.status === 'overdue'
                              ? '#ef4444'
                              : mtdStatus.status === 'fulfilled'
                              ? '#22c55e'
                              : '#f59e0b',
                        }}
                      >
                        {mtdStatus.status}
                      </strong>
                    </span>
                  )}
                  {mtdStatus.due_date && (
                    <span>
                      Due:{' '}
                      <strong style={{ color: 'var(--text-primary)' }}>
                        {new Date(mtdStatus.due_date).toLocaleDateString('en-GB', {
                          day: 'numeric',
                          month: 'short',
                          year: 'numeric',
                        })}
                      </strong>
                    </span>
                  )}
                </div>
              </div>
            )}

            {/* Blockers list */}
            {blockers.length > 0 ? (
              <div className={styles.subContainer} style={{ marginBottom: '1.5rem' }}>
                <h2 style={{ margin: '0 0 1rem', fontSize: '1rem' }}>Fix-Now Actions</h2>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                  {blockers.map((b) => (
                    <div
                      key={b.label}
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'space-between',
                        flexWrap: 'wrap',
                        gap: '0.75rem',
                        padding: '0.85rem 1rem',
                        borderRadius: 10,
                        border: `1px solid ${b.color}44`,
                        background: `${b.color}0e`,
                      }}
                    >
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                        <div
                          style={{
                            width: 32,
                            height: 32,
                            borderRadius: 8,
                            background: `${b.color}22`,
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            fontWeight: 800,
                            fontSize: '0.95rem',
                            color: b.color,
                          }}
                        >
                          {b.count}
                        </div>
                        <span style={{ fontSize: '0.9rem', color: 'var(--text-primary)' }}>{b.label}</span>
                      </div>
                      <Link
                        href={b.href}
                        style={{
                          padding: '0.3rem 0.9rem',
                          borderRadius: 8,
                          border: `1px solid ${b.color}`,
                          color: b.color,
                          fontSize: '0.82rem',
                          fontWeight: 600,
                          textDecoration: 'none',
                          background: `${b.color}14`,
                        }}
                      >
                        {b.action} →
                      </Link>
                    </div>
                  ))}
                </div>
              </div>
            ) : (
              !loading && score !== null && (
                <div
                  className={styles.subContainer}
                  style={{ textAlign: 'center', padding: '2rem', color: '#22c55e', fontWeight: 600 }}
                >
                  ✓ No blockers — your records are clean and ready for submission.
                </div>
              )
            )}

            {/* CTA */}
            <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap' }}>
              <Link
                href="/tax-preparation"
                style={{
                  padding: '0.6rem 1.4rem',
                  borderRadius: 10,
                  background: 'var(--lp-accent-teal)',
                  color: '#fff',
                  fontWeight: 700,
                  fontSize: '0.9rem',
                  textDecoration: 'none',
                }}
              >
                Go to MTD Submission →
              </Link>
              <Link
                href="/transactions"
                style={{
                  padding: '0.6rem 1.4rem',
                  borderRadius: 10,
                  border: '1px solid var(--lp-border)',
                  color: 'var(--lp-muted)',
                  fontWeight: 600,
                  fontSize: '0.9rem',
                  textDecoration: 'none',
                  background: 'transparent',
                }}
              >
                Review Transactions
              </Link>
            </div>
          </>
        )}
      </div>
    </>
  );
}
