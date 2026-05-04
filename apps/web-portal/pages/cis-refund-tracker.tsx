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
  if (st === 'MISMATCH') return '#f97316';
  if (st === 'NOT_CIS') return '#94a3b8';
  return 'var(--text-secondary)';
}

function statusBg(st: string): string {
  if (st === 'VERIFIED') return 'rgba(16,185,129,0.12)';
  if (st === 'UNVERIFIED') return 'rgba(245,158,11,0.12)';
  if (st === 'MISSING') return 'rgba(239,68,68,0.1)';
  if (st === 'MISMATCH') return 'rgba(249,115,22,0.12)';
  if (st === 'NOT_CIS') return 'rgba(148,163,184,0.12)';
  return 'rgba(148,163,184,0.08)';
}

function statusLabel(st: string): string {
  if (st === 'VERIFIED') return 'Matched';
  if (st === 'UNVERIFIED') return 'Unverified';
  if (st === 'MISSING') return 'Missing';
  if (st === 'MISMATCH') return 'Mismatch';
  if (st === 'NOT_CIS') return 'Not CIS';
  return st;
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

type ContractorGroup = {
  contractor_key: string;
  display_name: string;
  total_cis_withheld: number;
  worst_status: string;
  months: Array<{ month_label: string; row: ContractorRow }>;
};

export default function CisRefundTrackerPage({ token }: { token: string }) {
  const [data, setData] = useState<TrackerPayload | null>(null);
  const [err, setErr] = useState('');
  const [filter, setFilter] = useState<'all' | 'problems' | 'unverified' | 'missing' | 'mismatch' | 'not_cis'>('all');
  const [groupBy, setGroupBy] = useState<'month' | 'contractor'>('month');

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

  // Auto-match state: keyed by first record_id of the row
  type AutoMatchCandidate = { transaction_id: string; date: string; description: string; amount: number; delta_gbp: number; within_tolerance: boolean };
  type AutoMatchResult = { net_paid_total: number; tolerance_gbp: number; candidates: AutoMatchCandidate[]; auto_applied: boolean; reconciliation_status: string | null; bank_net_observed_gbp: number | null };
  const [matchResults, setMatchResults] = useState<Record<string, AutoMatchResult>>({});
  const [matchLoading, setMatchLoading] = useState<Record<string, boolean>>({});

  const runAutoMatch = async (recordId: string) => {
    setMatchLoading(prev => ({ ...prev, [recordId]: true }));
    try {
      const r = await fetch(`${TXN_SERVICE_URL}/cis/records/${recordId}/auto-match`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
      });
      const j = await r.json().catch(() => ({}));
      if (r.ok) setMatchResults(prev => ({ ...prev, [recordId]: j as AutoMatchResult }));
    } finally {
      setMatchLoading(prev => ({ ...prev, [recordId]: false }));
    }
  };

  // Snooze state
  const [snoozeLoading, setSnoozeLoading] = useState<Record<string, boolean>>({});
  const [snoozeDone_, setSnoozeDone_] = useState<Record<string, boolean>>({});
  type ReminderLogEntry = { at: string; task_id: string; action: string; days?: number };
  const [reminderLog, setReminderLog] = useState<ReminderLogEntry[]>([]);

  const snoozeTask = async (taskId: string, days: number) => {
    setSnoozeLoading(prev => ({ ...prev, [taskId]: true }));
    try {
      const r = await fetch(`${TXN_SERVICE_URL}/cis/tasks/${taskId}/snooze-reminder`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
        body: JSON.stringify({ days }),
      });
      if (r.ok) {
        setSnoozeDone_(prev => ({ ...prev, [taskId]: true }));
        setReminderLog(prev => [{ at: new Date().toLocaleTimeString('en-GB'), task_id: taskId, action: 'snoozed', days }, ...prev.slice(0, 19)]);
      }
    } finally {
      setSnoozeLoading(prev => ({ ...prev, [taskId]: false }));
    }
  };

  const openUploadForContractor = (contractorName: string, periodStart?: string, periodEnd?: string) => {
    setSaveOk(false);
    setUploadErr('');
    setOcr(null);
    setForm(prev => ({
      ...prev,
      contractor_name: contractorName,
      period_start: periodStart ?? prev.period_start,
      period_end: periodEnd ?? prev.period_end,
    }));
    setUploadOpen(true);
  };

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
            {uploadErr && (
              <div style={{ marginBottom: '0.75rem', display: 'flex', alignItems: 'center', gap: '0.65rem', flexWrap: 'wrap' }}>
                <p style={{ color: '#ef4444', margin: 0, fontSize: '0.85rem' }}>{uploadErr}</p>
                <button
                  type="button"
                  onClick={() => { setUploadErr(''); setOcr(null); if (fileInputRef.current) { fileInputRef.current.value = ''; fileInputRef.current.click(); } }}
                  style={{
                    padding: '0.25rem 0.75rem', borderRadius: 8, border: 'none',
                    background: 'var(--lp-accent-teal)', color: '#fff', fontWeight: 600,
                    fontSize: '0.78rem', cursor: 'pointer', whiteSpace: 'nowrap',
                  }}
                >
                  Try again →
                </button>
              </div>
            )}
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
                {uploading && (
                  <p style={{ fontSize: '0.82rem', color: 'var(--text-tertiary)', marginTop: 6 }}>
                    Analysing document… this may take a few seconds.
                  </p>
                )}
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

          {/* ── Pill filters + group-by toggle ── */}
          {data.by_tax_month.length > 0 && (
            <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap', marginBottom: 16, alignItems: 'center' }}>
              {(
                [
                  { key: 'all', label: 'All' },
                  { key: 'problems', label: '⚠ Problems' },
                  { key: 'unverified', label: 'Unverified' },
                  { key: 'missing', label: 'Missing' },
                  { key: 'mismatch', label: 'Mismatch' },
                  { key: 'not_cis', label: 'Not CIS' },
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
              <div style={{ marginLeft: 'auto', display: 'flex', gap: '0.4rem' }}>
                {(['month', 'contractor'] as const).map((g) => (
                  <button
                    key={g}
                    type="button"
                    onClick={() => setGroupBy(g)}
                    style={{
                      padding: '0.25rem 0.8rem', borderRadius: 999, fontSize: '0.78rem', fontWeight: 600,
                      cursor: 'pointer', border: '1px solid',
                      borderColor: groupBy === g ? '#6366f1' : 'var(--border)',
                      background: groupBy === g ? 'rgba(99,102,241,0.12)' : 'transparent',
                      color: groupBy === g ? '#6366f1' : 'var(--text-secondary)',
                    }}
                  >
                    {g === 'month' ? '📅 By month' : '🏢 By contractor'}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Helper: row-level action buttons */}
          {(() => {
            const rowActions = (c: ContractorRow, monthLabel?: string) => (
              <>
                {c.status === 'MISSING' && (
                  <button
                    type="button"
                    onClick={() => openUploadForContractor(c.display_name, monthLabel)}
                    style={{ padding: '0.25rem 0.7rem', borderRadius: 6, background: 'rgba(239,68,68,0.1)', color: '#ef4444', border: '1px solid rgba(239,68,68,0.3)', fontSize: '0.75rem', fontWeight: 700, cursor: 'pointer' }}
                  >
                    Upload statement
                  </button>
                )}
                {c.status === 'UNVERIFIED' && (
                  <button
                    type="button"
                    onClick={() => openUploadForContractor(c.display_name, monthLabel)}
                    style={{ padding: '0.25rem 0.7rem', borderRadius: 6, background: 'rgba(245,158,11,0.1)', color: '#f59e0b', border: '1px solid rgba(245,158,11,0.3)', fontSize: '0.75rem', fontWeight: 700, cursor: 'pointer' }}
                  >
                    Add statement
                  </button>
                )}
                {c.status === 'MISMATCH' && (
                  <span style={{ color: '#f97316', fontWeight: 600 }}>Review bank match</span>
                )}
                {c.status === 'NOT_CIS' && (
                  <span style={{ color: '#94a3b8' }}>No CIS action</span>
                )}
                {c.status === 'VERIFIED' && c.reconciliation_worst === 'needs_review' && (
                  <span style={{ color: '#f97316' }}>Review bank match</span>
                )}
                {c.status === 'VERIFIED' && c.reconciliation_worst !== 'needs_review' && (
                  <span style={{ color: '#10b981' }}>✓ No action needed</span>
                )}
                {/* Bank reconciliation panel — shown when bank match is needed */}
                {(c.reconciliation_worst === 'needs_review' || c.reconciliation_worst === 'pending') && c.record_ids.length > 0 && (() => {
                  const rid = c.record_ids[0];
                  const result = matchResults[rid];
                  const loading = matchLoading[rid];
                  return (
                    <div style={{ marginTop: 8, padding: '0.7rem 1rem', borderRadius: 8, background: 'rgba(249,115,22,0.06)', border: '1px solid rgba(249,115,22,0.25)', fontSize: '0.78rem' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: result ? 8 : 0 }}>
                        <span style={{ fontWeight: 700, color: '#f97316' }}>Bank match</span>
                        {c.bank_net_observed_gbp != null && (
                          <span style={{ color: '#94a3b8' }}>
                            Bank: {fmt(c.bank_net_observed_gbp)} vs declared: {fmt(c.net_paid_declared_gbp)}
                            {' '}({c.reconciliation_worst === 'needs_review' ? '⚠ outside tolerance' : '⏳ unmatched'})
                          </span>
                        )}
                        <button
                          type="button"
                          onClick={() => runAutoMatch(rid)}
                          disabled={loading}
                          style={{ marginLeft: 'auto', padding: '0.2rem 0.65rem', borderRadius: 6, background: loading ? '#374151' : 'rgba(249,115,22,0.15)', color: '#f97316', border: '1px solid rgba(249,115,22,0.4)', fontSize: '0.73rem', fontWeight: 700, cursor: loading ? 'default' : 'pointer' }}
                        >
                          {loading ? 'Searching…' : result ? 'Re-run auto-match' : 'Auto-match'}
                        </button>
                      </div>
                      {result && (
                        <div>
                          {result.auto_applied && (
                            <div style={{ color: '#10b981', fontWeight: 700, marginBottom: 4 }}>
                              ✓ Match applied — status: {result.reconciliation_status}
                              {result.bank_net_observed_gbp != null && ` (bank net: ${fmt(result.bank_net_observed_gbp)})`}
                            </div>
                          )}
                          {!result.auto_applied && result.candidates.length === 0 && (
                            <div style={{ color: '#ef4444', marginBottom: 4 }}>No bank transactions found within ±{fmt(result.tolerance_gbp)} of {fmt(result.net_paid_total)}</div>
                          )}
                          {!result.auto_applied && result.candidates.length > 1 && (
                            <div style={{ color: '#f59e0b', marginBottom: 4 }}>Multiple candidates found — select one below</div>
                          )}
                          {result.candidates.length > 0 && (
                            <table style={{ width: '100%', borderCollapse: 'collapse', marginTop: 4 }}>
                              <thead>
                                <tr style={{ color: '#94a3b8', fontWeight: 600, fontSize: '0.7rem' }}>
                                  <th style={{ textAlign: 'left', paddingBottom: 4 }}>Date</th>
                                  <th style={{ textAlign: 'left', paddingBottom: 4 }}>Description</th>
                                  <th style={{ textAlign: 'right', paddingBottom: 4 }}>Amount</th>
                                  <th style={{ textAlign: 'right', paddingBottom: 4 }}>Delta</th>
                                  <th style={{ textAlign: 'center', paddingBottom: 4 }}>Match</th>
                                </tr>
                              </thead>
                              <tbody>
                                {result.candidates.map(cand => (
                                  <tr key={cand.transaction_id} style={{ borderTop: '1px solid rgba(255,255,255,0.05)' }}>
                                    <td style={{ padding: '3px 0', whiteSpace: 'nowrap' }}>{cand.date}</td>
                                    <td style={{ padding: '3px 8px', color: '#94a3b8', maxWidth: 200, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{cand.description}</td>
                                    <td style={{ textAlign: 'right', whiteSpace: 'nowrap' }}>{fmt(cand.amount)}</td>
                                    <td style={{ textAlign: 'right', color: cand.within_tolerance ? '#10b981' : '#ef4444', whiteSpace: 'nowrap' }}>±{fmt(cand.delta_gbp)}</td>
                                    <td style={{ textAlign: 'center' }}>
                                      {cand.within_tolerance ? (
                                        <span style={{ color: '#10b981', fontWeight: 700 }}>✓</span>
                                      ) : (
                                        <span style={{ color: '#ef4444' }}>✗</span>
                                      )}
                                    </td>
                                  </tr>
                                ))}
                              </tbody>
                            </table>
                          )}
                        </div>
                      )}
                    </div>
                  );
                })()}
              </>
            );

            const passesFilter = (c: ContractorRow) => {
              if (filter === 'all') return true;
              if (filter === 'unverified') return c.status === 'UNVERIFIED';
              if (filter === 'missing') return c.status === 'MISSING';
              if (filter === 'mismatch') return c.status === 'MISMATCH' || c.reconciliation_worst === 'needs_review';
              if (filter === 'not_cis') return c.status === 'NOT_CIS';
              if (filter === 'problems')
                return (
                  c.status === 'UNVERIFIED' ||
                  c.status === 'MISSING' ||
                  c.status === 'MISMATCH' ||
                  c.reconciliation_worst === 'needs_review' ||
                  c.open_payment_count > 0
                );
              return true;
            };

            const statusRank = (st: string) => ({ MISSING: 0, MISMATCH: 1, UNVERIFIED: 2, NOT_CIS: 3, VERIFIED: 4 }[st] ?? 5);

            if (groupBy === 'month') {
              return data.by_tax_month.map((block) => {
                const filtered = block.contractors.filter(passesFilter);
                if (filtered.length === 0) return null;
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
                          {filtered.map((c) => (
                            <tr key={c.contractor_key}>
                              <td style={{ padding: '10px 6px', borderBottom: '1px solid var(--border)' }}>
                                {c.display_name}
                                {c.open_payment_count > 0 && (
                                  <span style={{ color: 'var(--text-tertiary)', fontSize: '0.72rem' }}>
                                    {' '}· {c.open_payment_count} open payment(s)
                                  </span>
                                )}
                              </td>
                              <td style={{ padding: '10px 6px', borderBottom: '1px solid var(--border)' }}>
                                <span style={{ padding: '0.15rem 0.55rem', borderRadius: 999, fontWeight: 700, fontSize: '0.7rem', textTransform: 'uppercase', background: statusBg(c.status), color: statusColor(c.status) }}>
                                  {statusLabel(c.status)}
                                </span>
                              </td>
                              <td style={{ padding: '10px 6px', borderBottom: '1px solid var(--border)', fontWeight: 600 }}>{fmt(c.cis_withheld_gbp)}</td>
                              <td style={{ padding: '10px 6px', borderBottom: '1px solid var(--border)' }}>
                                {c.reconciliation_worst === 'needs_review' && <span style={{ color: '#f97316', fontWeight: 600, fontSize: '0.8rem' }}>⚠ Mismatch</span>}
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
                                {rowActions(c, block.tax_month_label)}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </section>
                );
              });
            }

            // By contractor grouping
            const groupMap = new Map<string, ContractorGroup>();
            for (const block of data.by_tax_month) {
              for (const row of block.contractors) {
                if (!passesFilter(row)) continue;
                const existing = groupMap.get(row.contractor_key);
                if (existing) {
                  existing.total_cis_withheld += row.cis_withheld_gbp;
                  if (statusRank(row.status) < statusRank(existing.worst_status)) {
                    existing.worst_status = row.status;
                  }
                  existing.months.push({ month_label: block.tax_month_label, row });
                } else {
                  groupMap.set(row.contractor_key, {
                    contractor_key: row.contractor_key,
                    display_name: row.display_name,
                    total_cis_withheld: row.cis_withheld_gbp,
                    worst_status: row.status,
                    months: [{ month_label: block.tax_month_label, row }],
                  });
                }
              }
            }
            const groups = Array.from(groupMap.values()).sort((a, b) => statusRank(a.worst_status) - statusRank(b.worst_status));
            if (groups.length === 0) return <p style={{ color: 'var(--text-secondary)' }}>No contractors match this filter.</p>;

            return groups.map((g) => (
              <section key={g.contractor_key} style={{ marginBottom: 24, background: 'var(--card-bg)', border: '1px solid var(--border)', borderRadius: 12, overflow: 'hidden' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', padding: '0.85rem 1rem', borderBottom: '1px solid var(--border)' }}>
                  <span style={{ fontWeight: 700, fontSize: '0.95rem', flex: 1 }}>{g.display_name}</span>
                  <span style={{ padding: '0.15rem 0.6rem', borderRadius: 999, fontWeight: 700, fontSize: '0.7rem', textTransform: 'uppercase', background: statusBg(g.worst_status), color: statusColor(g.worst_status) }}>
                    {statusLabel(g.worst_status)}
                  </span>
                  <span style={{ fontWeight: 700, fontSize: '0.9rem' }}>{fmt(g.total_cis_withheld)}</span>
                  <span style={{ fontSize: '0.75rem', color: 'var(--text-tertiary)' }}>{g.months.length} month{g.months.length !== 1 ? 's' : ''}</span>
                </div>
                <div style={{ overflowX: 'auto' }}>
                  <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.82rem' }}>
                    <thead>
                      <tr style={{ textAlign: 'left', color: 'var(--text-tertiary)' }}>
                        <th style={{ padding: '7px 12px', borderBottom: '1px solid var(--border)', fontWeight: 600 }}>Tax month</th>
                        <th style={{ padding: '7px 12px', borderBottom: '1px solid var(--border)', fontWeight: 600 }}>Status</th>
                        <th style={{ padding: '7px 12px', borderBottom: '1px solid var(--border)', fontWeight: 600 }}>CIS withheld</th>
                        <th style={{ padding: '7px 12px', borderBottom: '1px solid var(--border)', fontWeight: 600 }}>Reconciliation</th>
                        <th style={{ padding: '7px 12px', borderBottom: '1px solid var(--border)', fontWeight: 600 }}>Next action</th>
                      </tr>
                    </thead>
                    <tbody>
                      {g.months.map(({ month_label, row: c }) => (
                        <tr key={month_label + c.contractor_key}>
                          <td style={{ padding: '9px 12px', borderBottom: '1px solid var(--border)', fontSize: '0.8rem', color: 'var(--text-secondary)' }}>{month_label}</td>
                          <td style={{ padding: '9px 12px', borderBottom: '1px solid var(--border)' }}>
                            <span style={{ padding: '0.12rem 0.5rem', borderRadius: 999, fontWeight: 700, fontSize: '0.68rem', textTransform: 'uppercase', background: statusBg(c.status), color: statusColor(c.status) }}>
                              {statusLabel(c.status)}
                            </span>
                          </td>
                          <td style={{ padding: '9px 12px', borderBottom: '1px solid var(--border)', fontWeight: 600 }}>{fmt(c.cis_withheld_gbp)}</td>
                          <td style={{ padding: '9px 12px', borderBottom: '1px solid var(--border)' }}>
                            {c.reconciliation_worst === 'needs_review' && <span style={{ color: '#f97316', fontWeight: 600, fontSize: '0.8rem' }}>⚠ Mismatch</span>}
                            {c.reconciliation_worst === 'ok' && <span style={{ color: '#10b981', fontSize: '0.8rem' }}>✓ Matched</span>}
                            {(c.reconciliation_worst === 'pending') && <span style={{ color: 'var(--text-tertiary)', fontSize: '0.8rem' }}>Pending</span>}
                            {(c.reconciliation_worst === 'not_applicable' || !c.reconciliation_worst) && <span style={{ color: 'var(--text-tertiary)', fontSize: '0.8rem' }}>—</span>}
                          </td>
                          <td style={{ padding: '9px 12px', borderBottom: '1px solid var(--border)', fontSize: '0.78rem' }}>
                            {rowActions(c, month_label)}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </section>
            ));
          })()}

          {data.open_tasks_preview.length > 0 && (
            <section style={{ background: 'var(--lp-bg-elevated, rgba(255,255,255,0.03))', border: '1px solid var(--lp-border, rgba(255,255,255,0.08))', borderRadius: 14, padding: '1.2rem 1.5rem' }}>
              <h2 style={{ fontSize: '1rem', marginBottom: 12, marginTop: 0 }}>🔔 Open CIS Tasks</h2>
              {data.open_tasks_preview.map((t) => {
                const snoozing = snoozeLoading[t.task_id];
                const snoozeDone = snoozeDone_[t.task_id];
                return (
                  <div key={t.task_id} style={{ display: 'flex', alignItems: 'center', gap: '0.7rem', marginBottom: 10, fontSize: '0.84rem', padding: '0.5rem 0', borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                    <span style={{ flex: 1, color: 'var(--text-secondary)' }}>
                      {t.description || 'CIS suspect'} {t.amount_gbp != null ? `· ${fmt(t.amount_gbp)}` : ''}
                    </span>
                    {snoozeDone ? (
                      <span style={{ color: '#94a3b8', fontSize: '0.75rem' }}>✓ Snoozed</span>
                    ) : (
                      <div style={{ display: 'flex', gap: '0.35rem' }}>
                        {(data.reminder_policy.snooze_days_allowed ?? [7, 14, 30]).map((days) => (
                          <button
                            key={days}
                            type="button"
                            disabled={snoozing}
                            onClick={() => snoozeTask(t.task_id, days)}
                            style={{ padding: '0.18rem 0.55rem', borderRadius: 6, background: 'rgba(148,163,184,0.1)', color: '#94a3b8', border: '1px solid rgba(148,163,184,0.2)', fontSize: '0.7rem', fontWeight: 600, cursor: snoozing ? 'default' : 'pointer' }}
                          >
                            {snoozing ? '…' : `Snooze ${days}d`}
                          </button>
                        ))}
                      </div>
                    )}
                  </div>
                );
              })}
              {reminderLog.length > 0 && (
                <div style={{ marginTop: 12, paddingTop: 10, borderTop: '1px solid rgba(255,255,255,0.06)' }}>
                  <div style={{ fontSize: '0.75rem', fontWeight: 700, color: '#94a3b8', marginBottom: 6 }}>REMINDER LOG</div>
                  {reminderLog.map((entry, i) => (
                    <div key={i} style={{ fontSize: '0.75rem', color: '#94a3b8', marginBottom: 3 }}>
                      {entry.at} — {entry.action} task {entry.task_id.slice(0, 8)}…{entry.days != null ? ` (${entry.days}d snooze)` : ''}
                    </div>
                  ))}
                </div>
              )}
            </section>
          )}
        </>
      )}
    </div>
  );
}
