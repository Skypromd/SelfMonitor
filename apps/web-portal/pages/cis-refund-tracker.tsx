import Link from 'next/link';
import { useCallback, useEffect, useState } from 'react';
import styles from '../styles/Home.module.css';

const TXN_SERVICE_URL = process.env.NEXT_PUBLIC_TRANSACTIONS_SERVICE_URL || '/api/transactions';

type TrackerTotals = {
  verified_cis_withheld_gbp: number;
  unverified_cis_withheld_gbp: number;
  combined_cis_withheld_gbp: number;
  missing_obligation_buckets: number;
  open_tasks: number;
  estimate_note: string;
};

type ContractorRow = {
  contractor_key: string;
  display_name: string;
  status: string;
  cis_withheld_gbp: number;
  net_paid_declared_gbp: number;
  reconciliation_worst: string;
  bank_net_observed_gbp: number | null;
  open_payment_count: number;
  record_ids: string[];
};

type MonthBlock = {
  tax_month_label: string;
  tax_year_start: number;
  tax_month: number;
  contractors: ContractorRow[];
};

type TrackerPayload = {
  schema_version: string;
  totals: TrackerTotals;
  by_tax_month: MonthBlock[];
  open_tasks_preview: { task_id: string; amount_gbp: number | null; description: string | null }[];
  reminder_policy: { hard_interval_hours: number; soft_max_sends_per_7_days: number; snooze_days_allowed: number[] };
};

const fmt = (n: number) =>
  `£${Math.abs(n).toLocaleString('en-GB', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

function statusColor(st: string): string {
  if (st === 'VERIFIED') return '#10b981';
  if (st === 'UNVERIFIED') return '#f59e0b';
  if (st === 'MISSING') return '#ef4444';
  return 'var(--text-secondary)';
}

export default function CisRefundTrackerPage({ token }: { token: string }) {
  const [data, setData] = useState<TrackerPayload | null>(null);
  const [err, setErr] = useState('');
  const [filter, setFilter] = useState<'all' | 'problems' | 'unverified' | 'missing'>('all');

  const load = useCallback(async () => {
    setErr('');
    const r = await fetch(`${TXN_SERVICE_URL}/cis/refund-tracker`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    const j = await r.json().catch(() => ({}));
    if (!r.ok) {
      setErr((j as { detail?: string }).detail || 'Could not load CIS refund tracker');
      setData(null);
      return;
    }
    setData(j as TrackerPayload);
  }, [token]);

  useEffect(() => {
    void load();
  }, [load]);

  return (
    <div className={styles.container} style={{ maxWidth: 960, margin: '0 auto', padding: '24px 16px' }}>
      <h1 style={{ fontSize: '1.35rem', marginBottom: 8 }}>CIS refund tracker</h1>
      <p style={{ color: 'var(--text-secondary)', fontSize: '0.88rem', lineHeight: 1.5, marginBottom: 20 }}>
        UK tax months (6th–5th), verified vs unverified withheld, and open CIS tasks.{' '}
        <Link href="/transactions" style={{ color: 'var(--accent)' }}>Resolve tasks on Transactions</Link>
        {' · '}
        <Link href="/tax-preparation" style={{ color: 'var(--accent)' }}>Tax preparation</Link>
      </p>

      {err && <p className={styles.error}>{err}</p>}

      {data && (
        <>
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))',
              gap: 12,
              marginBottom: 20,
            }}
          >
            <div style={{ background: 'var(--card-bg)', borderRadius: 10, padding: 14, border: '1px solid var(--border)' }}>
              <div style={{ fontSize: '0.72rem', color: 'var(--text-tertiary)' }}>Verified withheld</div>
              <div style={{ fontWeight: 700, fontSize: '1.1rem' }}>{fmt(data.totals.verified_cis_withheld_gbp)}</div>
            </div>
            <div style={{ background: 'var(--card-bg)', borderRadius: 10, padding: 14, border: '1px solid var(--border)' }}>
              <div style={{ fontSize: '0.72rem', color: 'var(--text-tertiary)' }}>Unverified withheld</div>
              <div style={{ fontWeight: 700, fontSize: '1.1rem', color: '#f59e0b' }}>
                {fmt(data.totals.unverified_cis_withheld_gbp)}
              </div>
            </div>
            <div style={{ background: 'var(--card-bg)', borderRadius: 10, padding: 14, border: '1px solid var(--border)' }}>
              <div style={{ fontSize: '0.72rem', color: 'var(--text-tertiary)' }}>Missing buckets</div>
              <div style={{ fontWeight: 700, fontSize: '1.1rem' }}>{data.totals.missing_obligation_buckets}</div>
            </div>
            <div style={{ background: 'var(--card-bg)', borderRadius: 10, padding: 14, border: '1px solid var(--border)' }}>
              <div style={{ fontSize: '0.72rem', color: 'var(--text-tertiary)' }}>Open tasks</div>
              <div style={{ fontWeight: 700, fontSize: '1.1rem' }}>{data.totals.open_tasks}</div>
            </div>
          </div>

          <p style={{ fontSize: '0.78rem', color: 'var(--text-tertiary)', lineHeight: 1.45, marginBottom: 16 }}>
            {data.totals.estimate_note}
          </p>

          <p style={{ fontSize: '0.75rem', color: 'var(--text-tertiary)', marginBottom: 20 }}>
            Reminders: hard gap {data.reminder_policy.hard_interval_hours}h; max{' '}
            {data.reminder_policy.soft_max_sends_per_7_days} push/email per 7 days per task (then in-app only). Snooze:{' '}
            {data.reminder_policy.snooze_days_allowed.join(', ')} days.
          </p>

          {data.by_tax_month.length === 0 && (
            <p style={{ color: 'var(--text-secondary)' }}>No CIS periods or tasks yet.</p>
          )}

          {/* ── Pill filters ── */}
          {data.by_tax_month.length > 0 && (
            <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap', marginBottom: 16 }}>
              {(
                [
                  { key: 'all', label: 'All' },
                  { key: 'problems', label: '⚠ Problems' },
                  { key: 'unverified', label: 'Unverified' },
                  { key: 'missing', label: 'Missing' },
                ] as { key: typeof filter; label: string }[]
              ).map(({ key, label }) => (
                <button
                  key={key}
                  type="button"
                  onClick={() => setFilter(key)}
                  style={{
                    padding: '0.3rem 0.9rem', borderRadius: 999, fontSize: '0.8rem', fontWeight: 600,
                    cursor: 'pointer', border: '1px solid',
                    borderColor: filter === key ? 'var(--accent, #0d9488)' : 'var(--border)',
                    background: filter === key ? 'rgba(13,148,136,0.12)' : 'transparent',
                    color: filter === key ? 'var(--accent, #0d9488)' : 'var(--text-secondary)',
                    transition: 'all 0.15s',
                  }}
                >
                  {label}
                </button>
              ))}
            </div>
          )}

          {data.by_tax_month.map((block) => {
            const filteredContractors = block.contractors.filter((c) => {
              if (filter === 'all') return true;
              if (filter === 'unverified') return c.status === 'UNVERIFIED';
              if (filter === 'missing') return c.status === 'MISSING';
              if (filter === 'problems')
                return (
                  c.status === 'UNVERIFIED' ||
                  c.status === 'MISSING' ||
                  c.reconciliation_worst === 'needs_review' ||
                  c.open_payment_count > 0
                );
              return true;
            });
            if (filteredContractors.length === 0) return null;
            return (
            <section key={`${block.tax_year_start}-${block.tax_month}`} style={{ marginBottom: 24 }}>
              <h2 style={{ fontSize: '1rem', marginBottom: 10 }}>{block.tax_month_label}</h2>
              <div style={{ overflowX: 'auto' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.82rem' }}>
                  <thead>
                    <tr style={{ textAlign: 'left', color: 'var(--text-tertiary)' }}>
                      <th style={{ padding: '8px 6px', borderBottom: '1px solid var(--border)' }}>Contractor</th>
                      <th style={{ padding: '8px 6px', borderBottom: '1px solid var(--border)' }}>Status</th>
                      <th style={{ padding: '8px 6px', borderBottom: '1px solid var(--border)' }}>CIS withheld</th>
                      <th style={{ padding: '8px 6px', borderBottom: '1px solid var(--border)' }}>Bank / review</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredContractors.map((c) => (
                      <tr key={c.contractor_key}>
                        <td style={{ padding: '10px 6px', borderBottom: '1px solid var(--border)' }}>
                          {c.display_name}
                          {c.open_payment_count > 0 && (
                            <span style={{ color: 'var(--text-tertiary)', fontSize: '0.72rem' }}>
                              {' '}
                              · {c.open_payment_count} open payment(s)
                            </span>
                          )}
                        </td>
                        <td style={{ padding: '10px 6px', borderBottom: '1px solid var(--border)', color: statusColor(c.status) }}>
                          {c.status}
                        </td>
                        <td style={{ padding: '10px 6px', borderBottom: '1px solid var(--border)' }}>{fmt(c.cis_withheld_gbp)}</td>
                        <td style={{ padding: '10px 6px', borderBottom: '1px solid var(--border)' }}>
                          {c.reconciliation_worst === 'needs_review' && (
                            <span style={{ color: '#f97316', fontWeight: 600 }}>Needs review</span>
                          )}
                          {c.reconciliation_worst === 'ok' && <span style={{ color: '#10b981' }}>Statement ↔ bank OK</span>}
                          {c.reconciliation_worst === 'pending' && <span style={{ color: 'var(--text-tertiary)' }}>Pending match</span>}
                          {c.reconciliation_worst === 'not_applicable' && <span style={{ color: 'var(--text-tertiary)' }}>—</span>}
                          {c.bank_net_observed_gbp != null && c.reconciliation_worst !== 'not_applicable' && (
                            <span style={{ color: 'var(--text-tertiary)', display: 'block', fontSize: '0.72rem' }}>
                              Bank net {fmt(c.bank_net_observed_gbp)} vs declared {fmt(c.net_paid_declared_gbp)}
                            </span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>
            );
          })}

          {data.open_tasks_preview.length > 0 && (
            <section>
              <h2 style={{ fontSize: '1rem', marginBottom: 8 }}>Recent open tasks</h2>
              <ul style={{ paddingLeft: 18, fontSize: '0.82rem', color: 'var(--text-secondary)' }}>
                {data.open_tasks_preview.map((t) => (
                  <li key={t.task_id} style={{ marginBottom: 6 }}>
                    {t.description || 'CIS suspect'} {t.amount_gbp != null ? `· ${fmt(t.amount_gbp)}` : ''}
                  </li>
                ))}
              </ul>
            </section>
          )}
        </>
      )}
    </div>
  );
}
