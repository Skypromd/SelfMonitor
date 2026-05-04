import Head from 'next/head';
import Link from 'next/link';
import { useEffect, useMemo, useState } from 'react';
import styles from '../styles/Home.module.css';

const API_GATEWAY_ROOT = (process.env.NEXT_PUBLIC_API_GATEWAY_URL || '/api').replace(/\/$/, '');
const FINOPS_URL = `${API_GATEWAY_ROOT}/finops`;
const TXN_URL = `${API_GATEWAY_ROOT}/transactions`;

function parseJwtClaims(jwt: string): Record<string, unknown> {
  try {
    const part = jwt.split('.')[1];
    if (!part) return {};
    return JSON.parse(atob(part.replace(/-/g, '+').replace(/_/g, '/'))) as Record<string, unknown>;
  } catch {
    return {};
  }
}

// ── New enriched types ──────────────────────────────────────────────────────
type BlockerDetail = {
  id: string;
  label: string;
  count: number;
  severity: 'blocking' | 'attention' | 'info';
  estimated_minutes: number;
  impact_points: number;
  action_label: string;
  action_route: string;
};

type TaxReserve = {
  income_gbp: number;
  expenses_gbp: number;
  profit_gbp: number;
  income_tax_gbp: number;
  class4_nic_gbp: number;
  total_tax_estimated_gbp: number;
  cis_deductions_verified_gbp: number;
  cis_deductions_unverified_gbp: number;
  net_tax_due_gbp: number;
  confidence: 'low' | 'medium' | 'high';
  disclaimer: string;
};

function fmt(n: number) {
  return `£${Math.round(n).toLocaleString('en-GB')}`;
}

function SeverityBadge({ severity }: { severity: BlockerDetail['severity'] }) {
  const map = {
    blocking: { bg: '#ef444420', border: '#ef4444', color: '#ef4444', label: 'Blocking' },
    attention: { bg: '#f59e0b20', border: '#f59e0b', color: '#f59e0b', label: 'Attention' },
    info: { bg: '#0891b220', border: '#0891b2', color: '#0891b2', label: 'Info' },
  };
  const s = map[severity];
  return (
    <span style={{
      padding: '2px 7px', borderRadius: 999, fontSize: '0.7rem', fontWeight: 700,
      background: s.bg, border: `1px solid ${s.border}`, color: s.color,
    }}>
      {s.label}
    </span>
  );
}

type ReadinessData = {
  uncategorized_count: number;
  missing_business_pct: number;
  unmatched_receipts: number;
  cis_unverified: number;
  score: number;
  blockers: BlockerDetail[];
  today_list: BlockerDetail[];
};

type MtdStatus = {
  quarter?: string;
  status?: string;
  due_date?: string;
  period_start?: string;
  period_end?: string;
};

type Props = { token: string };

export default function TaxReadinessPage({ token }: Props) {
  const [readiness, setReadiness] = useState<ReadinessData | null>(null);
  const [mtdStatus, setMtdStatus] = useState<MtdStatus | null>(null);
  const [reserve, setReserve] = useState<TaxReserve | null>(null);
  const [reserveChangeNote, setReserveChangeNote] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!token) return;
    setLoading(true);
    setError('');
    const headers = { Authorization: `Bearer ${token}` };

    const fetchAll = async () => {
      try {
        const [rdRes, mtdRes, resRes] = await Promise.allSettled([
          fetch(`${TXN_URL}/transactions/readiness`, { headers }),
          fetch(`${FINOPS_URL}/mtd/status`, { headers }),
          fetch(`${TXN_URL}/transactions/tax-reserve`, { headers }),
        ]);
        if (rdRes.status === 'fulfilled' && rdRes.value.ok)
          setReadiness((await rdRes.value.json()) as ReadinessData);
        if (mtdRes.status === 'fulfilled' && mtdRes.value.ok)
          setMtdStatus((await mtdRes.value.json()) as MtdStatus);
        if (resRes.status === 'fulfilled' && resRes.value.ok) {
          const resData = (await resRes.value.json()) as TaxReserve;
          setReserve(resData);
          try {
            const stored = localStorage.getItem('mnt_tax_reserve_prev');
            if (stored) {
              const prev = JSON.parse(stored) as TaxReserve;
              const delta = resData.net_tax_due_gbp - prev.net_tax_due_gbp;
              if (Math.abs(delta) >= 1) {
                const dir = delta > 0 ? 'up' : 'down';
                const reasons: string[] = [];
                const profitDelta = resData.profit_gbp - prev.profit_gbp;
                if (Math.abs(profitDelta) >= 1) reasons.push(`profit ${profitDelta > 0 ? 'increased' : 'decreased'} by £${Math.abs(Math.round(profitDelta)).toLocaleString('en-GB')}`);
                const cisDelta = (resData.cis_deductions_verified_gbp ?? 0) - (prev.cis_deductions_verified_gbp ?? 0);
                if (Math.abs(cisDelta) >= 1) reasons.push(`CIS verified credits ${cisDelta > 0 ? 'increased' : 'decreased'} by £${Math.abs(Math.round(cisDelta)).toLocaleString('en-GB')}`);
                const why = reasons.length > 0 ? ` — ${reasons.join('; ')}` : '';
                setReserveChangeNote(`Reserve ${dir} £${Math.abs(Math.round(delta)).toLocaleString('en-GB')}${why}.`);
              }
            }
            localStorage.setItem('mnt_tax_reserve_prev', JSON.stringify(resData));
          } catch { /* storage unavailable */ }
        }
      } catch {
        setError('Failed to load readiness data.');
      } finally {
        setLoading(false);
      }
    };

    void fetchAll();
  }, [token]);

  const score = readiness?.score ?? null;
  const blockers = readiness?.blockers ?? [];
  const todayList = readiness?.today_list ?? [];
  const totalMinutes = todayList.reduce((s, b) => s + b.estimated_minutes, 0);

  const hmrcDirect = useMemo(() => {
    const claims = parseJwtClaims(token);
    return claims.hmrc_direct_submission === true;
  }, [token]);

  const scoreColor =
    score === null ? '#64748b' : score >= 80 ? '#22c55e' : score >= 50 ? '#f59e0b' : '#ef4444';
  const scoreLabel =
    score === null ? '—' : score >= 80 ? 'Ready' : score >= 50 ? 'In Progress' : 'Needs Attention';
  const statusColor = (st?: string) =>
    !st ? '#64748b' : st === 'overdue' ? '#ef4444' : st === 'fulfilled' ? '#22c55e' : '#f59e0b';
  const confidenceColor = (c?: string) =>
    c === 'high' ? '#22c55e' : c === 'medium' ? '#f59e0b' : '#94a3b8';

  return (
    <>
      <Head>
        <title>Tax Readiness — MyNetTax</title>
      </Head>
      <div className={styles.pageContainer}>
        <div className={styles.pageHeader}>
          <p className={styles.pageEyebrow}>Quarter Readiness</p>
          <h1 className={styles.pageTitle}>Tax Readiness Console</h1>
          <p className={styles.pageLead}>
            Fix blockers before your MTD submission deadline. Every resolved item improves your score.
          </p>
        </div>

        {loading && (
          <p style={{ color: 'var(--lp-muted)', fontSize: '0.9rem', padding: '2rem 0' }}>Loading…</p>
        )}
        {error && <p className={styles.error}>{error}</p>}

        {!loading && (
          <>
            {/* ── Score + MTD Status + Reserve row ── */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: '1rem', marginBottom: '1.5rem' }}>

              {/* Score card */}
              <div className={styles.subContainer} style={{ display: 'flex', alignItems: 'center', gap: '1.25rem' }}>
                <div style={{ textAlign: 'center', minWidth: 72 }}>
                  <div style={{ fontSize: '2.8rem', fontWeight: 800, color: scoreColor, lineHeight: 1 }}>
                    {score ?? '—'}
                  </div>
                  <div style={{ fontSize: '0.7rem', color: 'var(--lp-muted)', marginTop: 2 }}>/ 100</div>
                </div>
                <div style={{ flex: 1 }}>
                  <div style={{
                    display: 'inline-block', padding: '0.2rem 0.75rem', borderRadius: 999,
                    background: `${scoreColor}22`, border: `1px solid ${scoreColor}55`,
                    color: scoreColor, fontSize: '0.78rem', fontWeight: 700, marginBottom: '0.4rem',
                  }}>
                    {scoreLabel}
                  </div>
                  <div style={{ height: 8, borderRadius: 999, background: 'var(--lp-border)', overflow: 'hidden', marginBottom: 6 }}>
                    <div style={{ height: '100%', width: `${score ?? 0}%`, background: scoreColor, borderRadius: 999, transition: 'width 0.6s ease' }} />
                  </div>
                  <p style={{ color: 'var(--lp-muted)', fontSize: '0.82rem', margin: 0 }}>
                    {blockers.length === 0
                      ? 'All clear — records ready for submission.'
                      : `${blockers.length} blocker${blockers.length > 1 ? 's' : ''} to resolve`}
                  </p>
                </div>
              </div>

              {/* MTD Status card */}
              <div className={styles.subContainer}>
                <div style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--lp-muted)', marginBottom: '0.5rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                  MTD Obligation
                </div>
                {mtdStatus ? (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '0.35rem', fontSize: '0.88rem' }}>
                    {mtdStatus.quarter && (
                      <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                        <span style={{ color: 'var(--lp-muted)' }}>Quarter</span>
                        <strong style={{ color: 'var(--text-primary)' }}>{mtdStatus.quarter}</strong>
                      </div>
                    )}
                    {mtdStatus.status && (
                      <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                        <span style={{ color: 'var(--lp-muted)' }}>Status</span>
                        <strong style={{ color: statusColor(mtdStatus.status), textTransform: 'capitalize' }}>{mtdStatus.status}</strong>
                      </div>
                    )}
                    {mtdStatus.due_date && (
                      <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                        <span style={{ color: 'var(--lp-muted)' }}>Due</span>
                        <strong style={{ color: 'var(--text-primary)' }}>
                          {new Date(mtdStatus.due_date).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' })}
                        </strong>
                      </div>
                    )}
                  </div>
                ) : (
                  <p style={{ color: 'var(--lp-muted)', fontSize: '0.85rem', margin: 0 }}>
                    No obligation data — <Link href="/tax-preparation" style={{ color: 'var(--lp-accent-teal)' }}>connect HMRC →</Link>
                  </p>
                )}
                <Link href="/obligations" style={{ display: 'block', marginTop: '0.75rem', fontSize: '0.78rem', color: 'var(--lp-accent-teal)', textDecoration: 'none', fontWeight: 600 }}>
                  View all deadlines →
                </Link>
              </div>

              {/* Tax Reserve card */}
              {reserve && (
                <div className={styles.subContainer}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '0.5rem' }}>
                    <div style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--lp-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                      Tax Reserve (est.)
                    </div>
                    <span style={{ fontSize: '0.7rem', color: confidenceColor(reserve.confidence), fontWeight: 600 }}>
                      {reserve.confidence} confidence
                    </span>
                  </div>
                  <div style={{ fontSize: '1.7rem', fontWeight: 800, color: '#ef4444', marginBottom: '0.4rem' }}>
                    {fmt(reserve.net_tax_due_gbp)}
                  </div>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem', fontSize: '0.8rem', color: 'var(--lp-muted)' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                      <span>Income tax</span><span>{fmt(reserve.income_tax_gbp)}</span>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                      <span>Class 4 NIC</span><span>{fmt(reserve.class4_nic_gbp)}</span>
                    </div>
                    {reserve.cis_deductions_verified_gbp > 0 && (
                      <div style={{ display: 'flex', justifyContent: 'space-between', color: '#22c55e' }}>
                        <span>CIS withheld (verified)</span><span>−{fmt(reserve.cis_deductions_verified_gbp)}</span>
                      </div>
                    )}
                    {reserve.cis_deductions_unverified_gbp > 0 && (
                      <div style={{ display: 'flex', justifyContent: 'space-between', color: '#f59e0b' }}>
                        <span>CIS unverified</span><span>{fmt(reserve.cis_deductions_unverified_gbp)}</span>
                      </div>
                    )}
                  </div>
                  <p style={{ fontSize: '0.68rem', color: 'var(--lp-muted)', marginTop: '0.5rem', lineHeight: 1.4 }}>
                    {reserve.disclaimer}
                  </p>
                  {reserveChangeNote && (
                    <div style={{ marginTop: '0.5rem', padding: '0.35rem 0.7rem', borderRadius: 7, background: 'rgba(245,158,11,0.07)', border: '1px solid rgba(245,158,11,0.25)', fontSize: '0.75rem', color: '#92400e' }}>
                      ↕ {reserveChangeNote}
                    </div>
                  )}
                </div>
              )}

              {/* HMRC Mode card */}
              <div className={styles.subContainer}>
                <div style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--lp-muted)', marginBottom: '0.75rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                  HMRC Submission Mode
                </div>
                {hmrcDirect ? (
                  <div>
                    <span style={{
                      display: 'inline-block', padding: '0.3rem 0.9rem', borderRadius: 999,
                      background: '#0d948822', border: '1px solid #0d9488', color: '#0d9488',
                      fontWeight: 700, fontSize: '0.8rem', marginBottom: '0.6rem',
                    }}>
                      Direct HMRC Submission
                    </span>
                    <p style={{ margin: 0, fontSize: '0.82rem', color: 'var(--lp-muted)', lineHeight: 1.5 }}>
                      Your Pro/Business account submits figures directly to HMRC MTD via OAuth. Full fraud-prevention headers required.
                    </p>
                  </div>
                ) : (
                  <div>
                    <span style={{
                      display: 'inline-block', padding: '0.3rem 0.9rem', borderRadius: 999,
                      background: '#6366f122', border: '1px solid #6366f1', color: '#6366f1',
                      fontWeight: 700, fontSize: '0.8rem', marginBottom: '0.6rem',
                    }}>
                      Guided MTD Workflow
                    </span>
                    <p style={{ margin: 0, fontSize: '0.82rem', color: 'var(--lp-muted)', lineHeight: 1.5 }}>
                      Your figures are prepared and reviewed here. An accountant or agent submits to HMRC on your behalf.
                    </p>
                  </div>
                )}
                <Link href="/settings" style={{ display: 'block', marginTop: '0.75rem', fontSize: '0.78rem', color: 'var(--lp-accent-teal)', textDecoration: 'none', fontWeight: 600 }}>
                  HMRC Connection Settings →
                </Link>
              </div>
            </div>

            {/* ── Today List ── */}
            {todayList.length > 0 && (
              <div className={styles.subContainer} style={{ marginBottom: '1.5rem', borderLeft: '3px solid #0d9488' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.85rem', flexWrap: 'wrap', gap: '0.5rem' }}>
                  <div>
                    <h2 style={{ margin: 0, fontSize: '1rem', fontWeight: 700 }}>
                      Fix in {totalMinutes} minute{totalMinutes !== 1 ? 's' : ''} — Today&apos;s List
                    </h2>
                    <p style={{ margin: '0.2rem 0 0', fontSize: '0.82rem', color: 'var(--lp-muted)' }}>
                      Top {todayList.length} priority actions to raise your score
                    </p>
                  </div>
                  <Link href="/transactions" style={{
                    padding: '0.45rem 1.1rem', borderRadius: 8,
                    background: '#0d9488', color: '#fff', fontWeight: 700, fontSize: '0.82rem', textDecoration: 'none',
                  }}>
                    Start fixing →
                  </Link>
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.6rem' }}>
                  {todayList.map((b, i) => (
                    <div key={b.id} style={{
                      display: 'flex', alignItems: 'center', gap: '0.75rem',
                      padding: '0.7rem 0.9rem', borderRadius: 10,
                      border: '1px solid var(--lp-border)', background: 'var(--lp-bg-elevated)',
                      flexWrap: 'wrap',
                    }}>
                      <div style={{
                        width: 28, height: 28, borderRadius: '50%', background: 'var(--lp-border)',
                        display: 'flex', alignItems: 'center', justifyContent: 'center',
                        fontWeight: 800, fontSize: '0.78rem', color: 'var(--lp-muted)', flexShrink: 0,
                      }}>
                        {i + 1}
                      </div>
                      <div style={{ flex: 1, minWidth: 140 }}>
                        <div style={{ fontWeight: 600, fontSize: '0.88rem', color: 'var(--text-primary)', marginBottom: 2 }}>
                          {b.label}
                        </div>
                        <div style={{ fontSize: '0.75rem', color: 'var(--lp-muted)', display: 'flex', gap: '0.75rem', flexWrap: 'wrap', alignItems: 'center' }}>
                          <span>⏱ ~{b.estimated_minutes} min</span>
                          <span>+{b.impact_points}pts to score</span>
                          <SeverityBadge severity={b.severity} />
                        </div>
                      </div>
                      <Link href={b.action_route} style={{
                        padding: '0.3rem 0.85rem', borderRadius: 7,
                        border: '1px solid var(--lp-border)', color: 'var(--text-primary)',
                        fontSize: '0.8rem', fontWeight: 600, textDecoration: 'none', whiteSpace: 'nowrap',
                      }}>
                        {b.action_label} →
                      </Link>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* ── All Blockers ── */}
            {blockers.length > 0 ? (
              <div className={styles.subContainer} style={{ marginBottom: '1.5rem' }}>
                <h2 style={{ margin: '0 0 1rem', fontSize: '1rem', fontWeight: 700 }}>All Blockers</h2>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.65rem' }}>
                  {blockers.map((b) => {
                    const c = b.severity === 'blocking' ? '#ef4444' : b.severity === 'attention' ? '#f59e0b' : '#0891b2';
                    return (
                      <div key={b.id} style={{
                        display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '0.65rem',
                        padding: '0.8rem 1rem', borderRadius: 10,
                        border: `1px solid ${c}33`, background: `${c}0a`,
                      }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.65rem' }}>
                          <div style={{
                            width: 34, height: 34, borderRadius: 8, background: `${c}22`,
                            display: 'flex', alignItems: 'center', justifyContent: 'center',
                            fontWeight: 800, fontSize: '0.9rem', color: c, flexShrink: 0,
                          }}>
                            {b.count}
                          </div>
                          <div>
                            <div style={{ fontWeight: 600, fontSize: '0.88rem', color: 'var(--text-primary)' }}>{b.label}</div>
                            <div style={{ fontSize: '0.74rem', color: 'var(--lp-muted)', marginTop: 2, display: 'flex', gap: '0.6rem', flexWrap: 'wrap', alignItems: 'center' }}>
                              <span>⏱ ~{b.estimated_minutes} min</span>
                              <span>+{b.impact_points}pts</span>
                              <SeverityBadge severity={b.severity} />
                            </div>
                          </div>
                        </div>
                        <Link href={b.action_route} style={{
                          padding: '0.3rem 0.85rem', borderRadius: 7,
                          border: `1px solid ${c}`, color: c,
                          fontSize: '0.8rem', fontWeight: 600, textDecoration: 'none',
                          background: `${c}14`, whiteSpace: 'nowrap',
                        }}>
                          {b.action_label} →
                        </Link>
                      </div>
                    );
                  })}
                </div>
              </div>
            ) : (
              !loading && score !== null && (
                <div className={styles.subContainer} style={{ textAlign: 'center', padding: '2rem', color: '#22c55e', fontWeight: 600, marginBottom: '1.5rem' }}>
                  ✓ No blockers — your records are clean and ready for submission.
                </div>
              )
            )}

            {/* ── CTAs ── */}
            <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap' }}>
              <Link href="/tax-preparation" style={{
                padding: '0.6rem 1.4rem', borderRadius: 10,
                background: 'var(--lp-accent-teal)', color: '#fff',
                fontWeight: 700, fontSize: '0.9rem', textDecoration: 'none',
              }}>
                Go to MTD Submission →
              </Link>
              <Link href="/obligations" style={{
                padding: '0.6rem 1.4rem', borderRadius: 10,
                border: '1px solid var(--lp-border)', color: 'var(--lp-muted)',
                fontWeight: 600, fontSize: '0.9rem', textDecoration: 'none',
              }}>
                View Deadlines
              </Link>
              <Link href="/transactions" style={{
                padding: '0.6rem 1.4rem', borderRadius: 10,
                border: '1px solid var(--lp-border)', color: 'var(--lp-muted)',
                fontWeight: 600, fontSize: '0.9rem', textDecoration: 'none',
              }}>
                Review Transactions
              </Link>
            </div>
          </>
        )}
      </div>
    </>
  );
}
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
