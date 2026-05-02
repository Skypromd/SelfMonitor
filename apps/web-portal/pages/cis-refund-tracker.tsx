import Link from 'next/link';
import { useCallback, useEffect, useRef, useState } from 'react';
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

type OcrResult = {
  document_id: string;
  filename: string | null;
  contractor_name: string | null;
  period_start: string | null;
  period_end: string | null;
  gross_total: number | null;
  materials_total: number;
  cis_deducted_total: number | null;
  net_paid_total: number | null;
  ocr_confidence: 'low' | 'medium' | 'high';
  needs_review: boolean;
  note?: string;
};

export default function CisRefundTrackerPage({ token }: { token: string }) {
  const [data, setData] = useState<TrackerPayload | null>(null);
  const [err, setErr] = useState('');
  const [filter, setFilter] = useState<'all' | 'problems' | 'unverified' | 'missing'>('all');

  // Upload state
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [uploadOpen, setUploadOpen] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [uploadErr, setUploadErr] = useState('');
  const [ocr, setOcr] = useState<OcrResult | null>(null);
  const [form, setForm] = useState({
    contractor_name: '',
    period_start: '',
    period_end: '',
    gross_total: '',
    materials_total: '0',
    cis_deducted_total: '',
    net_paid_total: '',
  });
  const [saving, setSaving] = useState(false);
  const [saveOk, setSaveOk] = useState(false);

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

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploadErr('');
    setOcr(null);
    setSaveOk(false);
    setUploading(true);
    try {
      const fd = new FormData();
      fd.append('file', file);
      const r = await fetch(`${TXN_SERVICE_URL}/cis/statements/upload`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
        body: fd,
      });
      const j = await r.json().catch(() => ({}));
      if (!r.ok) {
        setUploadErr((j as { detail?: string }).detail || 'Upload failed');
        return;
      }
      const result = j as OcrResult;
      setOcr(result);
      setForm({
        contractor_name: result.contractor_name ?? '',
        period_start: result.period_start ?? '',
        period_end: result.period_end ?? '',
        gross_total: result.gross_total != null ? String(result.gross_total) : '',
        materials_total: String(result.materials_total ?? 0),
        cis_deducted_total: result.cis_deducted_total != null ? String(result.cis_deducted_total) : '',
        net_paid_total: result.net_paid_total != null ? String(result.net_paid_total) : '',
      });
    } catch {
      setUploadErr('Upload failed. Please try again.');
    } finally {
      setUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!ocr) return;
    setSaving(true);
    setSaveOk(false);
    try {
      const body = {
        contractor_name: form.contractor_name,
        period_start: form.period_start,
        period_end: form.period_end,
        gross_total: parseFloat(form.gross_total) || 0,
        materials_total: parseFloat(form.materials_total) || 0,
        cis_deducted_total: parseFloat(form.cis_deducted_total) || 0,
        net_paid_total: parseFloat(form.net_paid_total) || 0,
        evidence_status: ocr.needs_review ? 'pending_review' : 'statement_uploaded',
        document_id: ocr.document_id,
        source: 'statement_upload',
        report_status: 'draft',
      };
      const r = await fetch(`${TXN_SERVICE_URL}/cis/records`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify(body),
      });
      const j = await r.json().catch(() => ({}));
      if (!r.ok) {
        setUploadErr((j as { detail?: string }).detail || 'Could not save CIS record');
        return;
      }
      setSaveOk(true);
      setOcr(null);
      setForm({ contractor_name: '', period_start: '', period_end: '', gross_total: '', materials_total: '0', cis_deducted_total: '', net_paid_total: '' });
      void load();
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className={styles.container} style={{ maxWidth: 960, margin: '0 auto', padding: '24px 16px' }}>
      <h1 style={{ fontSize: '1.35rem', marginBottom: 8 }}>CIS refund tracker</h1>
      <p style={{ color: 'var(--text-secondary)', fontSize: '0.88rem', lineHeight: 1.5, marginBottom: 20 }}>
        UK tax months (6th–5th), verified vs unverified withheld, and open CIS tasks.{' '}
        <Link href="/transactions" style={{ color: 'var(--accent)' }}>Resolve tasks on Transactions</Link>
        {' · '}
        <Link href="/tax-preparation" style={{ color: 'var(--accent)' }}>Tax preparation</Link>
      </p>

      {/* ── Upload CIS Statement ── */}
      <div style={{ marginBottom: 20, borderRadius: 10, border: '1px solid var(--border)', overflow: 'hidden' }}>
        <button
          type="button"
          onClick={() => { setUploadOpen((v) => !v); setSaveOk(false); setUploadErr(''); }}
          style={{
            width: '100%', textAlign: 'left', padding: '0.75rem 1rem',
            background: uploadOpen ? 'rgba(13,148,136,0.08)' : 'var(--card-bg)',
            border: 'none', cursor: 'pointer', fontWeight: 600,
            fontSize: '0.9rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center',
          }}
        >
          <span>Upload CIS statement (PDF or photo)</span>
          <span style={{ fontSize: '0.75rem', color: 'var(--text-tertiary)' }}>{uploadOpen ? '▲ Hide' : '▼ Show'}</span>
        </button>
        {uploadOpen && (
          <div style={{ padding: '1rem', borderTop: '1px solid var(--border)' }}>
            {saveOk && (
              <p style={{ color: '#10b981', fontWeight: 600, marginBottom: '0.75rem' }}>
                CIS record saved successfully.
              </p>
            )}
            {uploadErr && <p style={{ color: '#ef4444', marginBottom: '0.75rem', fontSize: '0.85rem' }}>{uploadErr}</p>}
            {!ocr && (
              <label style={{ display: 'block' }}>
                <span style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', display: 'block', marginBottom: 8 }}>
                  Select a PDF or image of a CIS300 deduction statement. Fields will be pre-filled from the document.
                </span>
                <input
                  ref={fileInputRef}
                  type="file"
                  accept="application/pdf,image/*"
                  onChange={handleFileChange}
                  style={{ fontSize: '0.85rem' }}
                />
                {uploading && <p style={{ fontSize: '0.82rem', color: 'var(--text-tertiary)', marginTop: 6 }}>Analysing document…</p>}
              </label>
            )}
            {ocr && (
              <form onSubmit={handleSave}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.75rem' }}>
                  <span style={{
                    padding: '0.2rem 0.6rem', borderRadius: 999, fontSize: '0.72rem', fontWeight: 700,
                    background: ocr.ocr_confidence === 'high' ? 'rgba(16,185,129,0.15)' : ocr.ocr_confidence === 'medium' ? 'rgba(245,158,11,0.15)' : 'rgba(239,68,68,0.12)',
                    color: ocr.ocr_confidence === 'high' ? '#10b981' : ocr.ocr_confidence === 'medium' ? '#f59e0b' : '#ef4444',
                    textTransform: 'uppercase',
                  }}>
                    OCR confidence: {ocr.ocr_confidence}
                  </span>
                  {ocr.needs_review && (
                    <span style={{ fontSize: '0.78rem', color: '#f59e0b' }}>
                      ⚠ Please review all fields before saving
                    </span>
                  )}
                </div>
                {ocr.note && <p style={{ fontSize: '0.78rem', color: 'var(--text-tertiary)', marginBottom: '0.75rem' }}>{ocr.note}</p>}
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '0.65rem', marginBottom: '0.85rem' }}>
                  {(
                    [
                      { key: 'contractor_name', label: 'Contractor name', type: 'text', required: true },
                      { key: 'period_start', label: 'Period start (YYYY-MM-DD)', type: 'date', required: true },
                      { key: 'period_end', label: 'Period end (YYYY-MM-DD)', type: 'date', required: true },
                      { key: 'gross_total', label: 'Gross total (£)', type: 'number', required: true },
                      { key: 'materials_total', label: 'Materials total (£)', type: 'number', required: false },
                      { key: 'cis_deducted_total', label: 'CIS deducted (£)', type: 'number', required: true },
                      { key: 'net_paid_total', label: 'Net paid (£)', type: 'number', required: true },
                    ] as { key: keyof typeof form; label: string; type: string; required: boolean }[]
                  ).map(({ key, label, type, required }) => (
                    <label key={key} style={{ display: 'flex', flexDirection: 'column', gap: 3, fontSize: '0.82rem' }}>
                      <span style={{ color: 'var(--text-secondary)', fontWeight: 600 }}>{label}{required && ' *'}</span>
                      <input
                        type={type}
                        value={form[key]}
                        onChange={(e) => setForm((f) => ({ ...f, [key]: e.target.value }))}
                        required={required}
                        step={type === 'number' ? '0.01' : undefined}
                        min={type === 'number' ? '0' : undefined}
                        style={{
                          padding: '0.4rem 0.6rem', borderRadius: 6,
                          border: '1px solid var(--border)', fontSize: '0.82rem',
                          background: 'var(--card-bg)', color: 'var(--text-primary)',
                        }}
                      />
                    </label>
                  ))}
                </div>
                <div style={{ display: 'flex', gap: '0.5rem' }}>
                  <button
                    type="submit"
                    disabled={saving}
                    style={{
                      padding: '0.45rem 1.1rem', borderRadius: 8,
                      background: 'var(--lp-accent-teal, #0d9488)', color: '#fff',
                      fontWeight: 700, fontSize: '0.85rem', border: 'none', cursor: saving ? 'not-allowed' : 'pointer',
                      opacity: saving ? 0.7 : 1,
                    }}
                  >
                    {saving ? 'Saving…' : 'Save CIS record'}
                  </button>
                  <button
                    type="button"
                    onClick={() => { setOcr(null); setUploadErr(''); }}
                    style={{ padding: '0.45rem 1rem', borderRadius: 8, border: '1px solid var(--border)', background: 'transparent', cursor: 'pointer', fontSize: '0.85rem' }}
                  >
                    Cancel
                  </button>
                </div>
              </form>
            )}
          </div>
        )}
      </div>

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

          {/* ── Refund Estimate Banner ── */}
          {data.totals.verified_cis_withheld_gbp > 0 && (
            <div style={{
              display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: 12,
              marginBottom: 20, padding: '1rem', borderRadius: 12,
              background: 'rgba(16,185,129,0.07)', border: '1px solid rgba(16,185,129,0.25)',
            }}>
              <div>
                <div style={{ fontSize: '0.72rem', color: '#10b981', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 4 }}>
                  Estimated CIS refund
                </div>
                <div style={{ fontWeight: 800, fontSize: '1.5rem', color: '#10b981' }}>
                  {fmt(data.totals.verified_cis_withheld_gbp)}
                </div>
                <div style={{ fontSize: '0.72rem', color: 'var(--text-tertiary)', marginTop: 3 }}>
                  From verified statements only
                </div>
              </div>
              {data.totals.unverified_cis_withheld_gbp > 0 && (
                <div>
                  <div style={{ fontSize: '0.72rem', color: '#f59e0b', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 4 }}>
                    Pending verification
                  </div>
                  <div style={{ fontWeight: 800, fontSize: '1.5rem', color: '#f59e0b' }}>
                    {fmt(data.totals.unverified_cis_withheld_gbp)}
                  </div>
                  <div style={{ fontSize: '0.72rem', color: 'var(--text-tertiary)', marginTop: 3 }}>
                    Upload statements to confirm
                  </div>
                </div>
              )}
              <div>
                <div style={{ fontSize: '0.72rem', color: 'var(--text-tertiary)', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 4 }}>
                  Total withheld
                </div>
                <div style={{ fontWeight: 800, fontSize: '1.5rem' }}>
                  {fmt(data.totals.verified_cis_withheld_gbp + data.totals.unverified_cis_withheld_gbp)}
                </div>
                <div style={{ fontSize: '0.72rem', color: 'var(--text-tertiary)', marginTop: 3 }}>
                  Verified + unverified
                </div>
              </div>
            </div>
          )}

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
                      <th style={{ padding: '8px 6px', borderBottom: '1px solid var(--border)' }}>Reconciliation</th>
                      <th style={{ padding: '8px 6px', borderBottom: '1px solid var(--border)' }}>Next action</th>
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
                        <td style={{ padding: '10px 6px', borderBottom: '1px solid var(--border)' }}>
                          <span style={{
                            padding: '0.15rem 0.55rem', borderRadius: 999, fontWeight: 700, fontSize: '0.7rem',
                            textTransform: 'uppercase',
                            background: c.status === 'VERIFIED' ? 'rgba(16,185,129,0.12)' : c.status === 'UNVERIFIED' ? 'rgba(245,158,11,0.12)' : 'rgba(239,68,68,0.1)',
                            color: statusColor(c.status),
                          }}>
                            {c.status === 'VERIFIED' ? 'Matched' : c.status === 'UNVERIFIED' ? 'Unverified' : c.status === 'MISSING' ? 'Missing' : c.status}
                          </span>
                        </td>
                        <td style={{ padding: '10px 6px', borderBottom: '1px solid var(--border)', fontWeight: 600 }}>{fmt(c.cis_withheld_gbp)}</td>
                        <td style={{ padding: '10px 6px', borderBottom: '1px solid var(--border)' }}>
                          {c.reconciliation_worst === 'needs_review' && (
                            <span style={{ color: '#f97316', fontWeight: 600, fontSize: '0.8rem' }}>⚠ Mismatch</span>
                          )}
                          {c.reconciliation_worst === 'ok' && <span style={{ color: '#10b981', fontSize: '0.8rem' }}>✓ Matched</span>}
                          {c.reconciliation_worst === 'pending' && <span style={{ color: 'var(--text-tertiary)', fontSize: '0.8rem' }}>Pending</span>}
                          {(c.reconciliation_worst === 'not_applicable' || !c.reconciliation_worst) && <span style={{ color: 'var(--text-tertiary)', fontSize: '0.8rem' }}>—</span>}
                          {c.bank_net_observed_gbp != null && c.reconciliation_worst === 'needs_review' && (
                            <span style={{ color: 'var(--text-tertiary)', display: 'block', fontSize: '0.7rem' }}>
                              Bank {fmt(c.bank_net_observed_gbp)} vs {fmt(c.net_paid_declared_gbp)}
                            </span>
                          )}
                        </td>
                        <td style={{ padding: '10px 6px', borderBottom: '1px solid var(--border)', fontSize: '0.78rem' }}>
                          {c.status === 'MISSING' && (
                            <button
                              type="button"
                              onClick={() => setUploadOpen(true)}
                              style={{ padding: '0.25rem 0.7rem', borderRadius: 6, background: 'rgba(239,68,68,0.1)', color: '#ef4444', border: '1px solid rgba(239,68,68,0.3)', fontSize: '0.75rem', fontWeight: 700, cursor: 'pointer' }}
                            >
                              Upload statement
                            </button>
                          )}
                          {c.status === 'UNVERIFIED' && (
                            <button
                              type="button"
                              onClick={() => setUploadOpen(true)}
                              style={{ padding: '0.25rem 0.7rem', borderRadius: 6, background: 'rgba(245,158,11,0.1)', color: '#f59e0b', border: '1px solid rgba(245,158,11,0.3)', fontSize: '0.75rem', fontWeight: 700, cursor: 'pointer' }}
                            >
                              Add statement
                            </button>
                          )}
                          {c.status === 'VERIFIED' && c.reconciliation_worst === 'needs_review' && (
                            <span style={{ color: '#f97316' }}>Review bank match</span>
                          )}
                          {c.status === 'VERIFIED' && c.reconciliation_worst !== 'needs_review' && (
                            <span style={{ color: '#10b981' }}>✓ No action needed</span>
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
