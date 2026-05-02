import { useState, type FormEvent } from 'react';
import { MtdDraftWorkflowStrip, type MtdDraftLatest } from '../components/MtdDraftWorkflow';
import { downloadAccountantTaxSummaryPdf, type AccountantPdfCalc } from '../lib/taxAccountantPdf';
import { transactionsBearerHeaders, useTransactionsBusinessScope } from '../lib/transactionsBusinessScope';
import styles from '../styles/Home.module.css';

const TAX_ENGINE_URL = process.env.NEXT_PUBLIC_TAX_ENGINE_URL || '/api/tax';
const TXN_SERVICE_URL = process.env.NEXT_PUBLIC_TRANSACTIONS_SERVICE_URL || '/api/transactions';
const INTEGRATIONS_API = process.env.NEXT_PUBLIC_INTEGRATIONS_SERVICE_URL || '/api/integrations';

type Props = { token: string };

type TaxBand = { label: string; rate: string; amount: number; taxable: number };

type TaxCalcResult = {
  user_id: string;
  start_date: string;
  end_date: string;
  total_income: number;
  total_expenses: number;
  taxable_profit: number;
  personal_allowance_used: number;
  pa_taper_reduction: number;
  taxable_amount_after_allowance: number;
  basic_rate_tax: number;
  higher_rate_tax: number;
  additional_rate_tax: number;
  estimated_income_tax_due: number;
  estimated_class2_nic_due: number;
  estimated_class4_nic_due: number;
  estimated_tax_due: number;
  estimated_effective_tax_rate: number;
  payment_on_account_jan: number;
  payment_on_account_jul: number;
  cis_hmrc_submit_requires_unverified_ack?: boolean;
  cis_tax_credit_self_attested_gbp?: number;
  cis_tax_credit_verified_gbp?: number;
  mtd_obligation: {
    reporting_required: boolean;
    tax_year_start: string;
    tax_year_end: string;
    next_deadline: string | null;
    policy_code: string;
    qualifying_income_estimate?: number;
    quarterly_updates: { quarter: string; due_date: string; status: string }[];
  };
  summary_by_category: { category: string; total_amount: number; taxable_amount: number }[];
};

type SubmitResult = {
  submission_id: string;
  message: string;
  submission_mode: string;
};

type Step = 'draft' | 'review' | 'confirm' | 'submitted';

const TAX_YEARS = [
  { label: '2025/26', start: '2025-04-06', end: '2026-04-05' },
  { label: '2024/25', start: '2024-04-06', end: '2025-04-05' },
  { label: '2023/24', start: '2023-04-06', end: '2024-04-05' },
];

const fmt = (n: number) =>
  n < 0
    ? `-£${Math.abs(n).toLocaleString('en-GB', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
    : `£${n.toLocaleString('en-GB', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

const pct = (n: number) => `${(n * 100).toFixed(1)}%`;

function formatApiDetail(detail: unknown): string {
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail)) {
    return detail
      .map((e) => {
        if (e && typeof e === 'object' && 'msg' in e) return String((e as { msg: string }).msg);
        return JSON.stringify(e);
      })
      .join('; ');
  }
  if (detail && typeof detail === 'object' && 'message' in detail) {
    return String((detail as { message: string }).message);
  }
  return 'Request failed';
}

function escapeSubmissionCsvField(value: string): string {
  if (/[",\n\r]/.test(value)) {
    return `"${value.replace(/"/g, '""')}"`;
  }
  return value;
}

function downloadSubmissionCsv(filename: string, lines: string[]): void {
  const blob = new Blob([`\uFEFF${lines.join('\n')}`], { type: 'text/csv;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

function buildSubmissionSummaryLines(yearLabel: string, calc: TaxCalcResult): string[] {
  const mtd = calc.mtd_obligation;
  const lines: string[] = [
    'field,value',
    `tax_year,${escapeSubmissionCsvField(yearLabel)}`,
    `period_start,${escapeSubmissionCsvField(calc.start_date)}`,
    `period_end,${escapeSubmissionCsvField(calc.end_date)}`,
    `disclaimer,${escapeSubmissionCsvField('MyNetTax export for accountant review. Not an HMRC submission file.')}`,
    `total_income,${calc.total_income}`,
    `total_expenses,${calc.total_expenses}`,
    `taxable_profit,${calc.taxable_profit}`,
    `personal_allowance_used,${calc.personal_allowance_used}`,
    `pa_taper_reduction,${calc.pa_taper_reduction}`,
    `taxable_amount_after_allowance,${calc.taxable_amount_after_allowance}`,
    `basic_rate_tax,${calc.basic_rate_tax}`,
    `higher_rate_tax,${calc.higher_rate_tax}`,
    `additional_rate_tax,${calc.additional_rate_tax}`,
    `estimated_income_tax_due,${calc.estimated_income_tax_due}`,
    `estimated_class2_nic_due,${calc.estimated_class2_nic_due}`,
    `estimated_class4_nic_due,${calc.estimated_class4_nic_due}`,
    `estimated_tax_due,${calc.estimated_tax_due}`,
    `payment_on_account_jan,${calc.payment_on_account_jan}`,
    `payment_on_account_jul,${calc.payment_on_account_jul}`,
    `cis_tax_credit_verified_gbp,${calc.cis_tax_credit_verified_gbp ?? 0}`,
    `cis_tax_credit_self_attested_gbp,${calc.cis_tax_credit_self_attested_gbp ?? 0}`,
    `mtd_reporting_required,${mtd.reporting_required}`,
    `mtd_qualifying_income_estimate,${mtd.qualifying_income_estimate ?? ''}`,
    `mtd_next_deadline,${escapeSubmissionCsvField(mtd.next_deadline ?? '')}`,
  ];
  lines.push('');
  lines.push('category,total_amount,taxable_amount');
  for (const row of calc.summary_by_category) {
    lines.push(
      [escapeSubmissionCsvField(row.category), String(row.total_amount), String(row.taxable_amount)].join(','),
    );
  }
  if (mtd.quarterly_updates?.length) {
    lines.push('');
    lines.push('mtd_quarter,due_date,status');
    for (const q of mtd.quarterly_updates) {
      lines.push(
        [escapeSubmissionCsvField(q.quarter), escapeSubmissionCsvField(q.due_date), escapeSubmissionCsvField(q.status)].join(
          ',',
        ),
      );
    }
  }
  return lines;
}

type SubmissionTxnRow = {
  id: string;
  date: string;
  description: string;
  amount: number;
  category?: string | null;
  reconciliation_status?: string | null;
  provider_transaction_id: string;
};

function buildSubmissionTransactionLines(rows: SubmissionTxnRow[]): string[] {
  const header =
    'date,amount_gbp,flow,description,category,reconciliation_status,transaction_id,provider_transaction_id';
  const lines = [header];
  for (const t of rows) {
    const flow = t.amount >= 0 ? 'INCOME' : 'EXPENSE';
    lines.push(
      [
        escapeSubmissionCsvField(t.date),
        String(t.amount),
        flow,
        escapeSubmissionCsvField(t.description),
        escapeSubmissionCsvField(t.category ?? ''),
        escapeSubmissionCsvField(t.reconciliation_status ?? ''),
        escapeSubmissionCsvField(t.id),
        escapeSubmissionCsvField(t.provider_transaction_id ?? ''),
      ].join(','),
    );
  }
  return lines;
}

function buildSubmissionBookkeepingLines(rows: SubmissionTxnRow[]): string[] {
  const header = 'Date,Description,Income_gbp,Expense_gbp,Category';
  const lines = [header];
  for (const t of rows) {
    const income = t.amount > 0 ? String(t.amount) : '';
    const expense = t.amount < 0 ? String(Math.abs(t.amount)) : '';
    lines.push(
      [
        escapeSubmissionCsvField(t.date),
        escapeSubmissionCsvField(t.description),
        income,
        expense,
        escapeSubmissionCsvField(t.category ?? ''),
      ].join(','),
    );
  }
  return lines;
}

function StatusPill({ status }: { status: string }) {
  const map: Record<string, string> = {
    overdue: '#ef4444',
    due_now: '#f59e0b',
    upcoming: '#0d9488',
  };
  return (
    <span
      style={{
        background: map[status] ?? '#64748b',
        color: '#fff',
        borderRadius: 999,
        padding: '2px 10px',
        fontSize: '0.72rem',
        fontWeight: 600,
        textTransform: 'capitalize',
      }}
    >
      {status.replace('_', ' ')}
    </span>
  );
}

export default function SubmissionPage({ token }: Props) {
  const { businesses, loadError, selectedBusinessId, setSelectedBusinessId } = useTransactionsBusinessScope(
    token,
    TXN_SERVICE_URL,
  );
  const [step, setStep] = useState<Step>('draft');
  const [yearIdx, setYearIdx] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [calc, setCalc] = useState<TaxCalcResult | null>(null);
  const [submitResult, setSubmitResult] = useState<SubmitResult | null>(null);
  const [unverifiedCisSubmitAck, setUnverifiedCisSubmitAck] = useState(false);
  const [txExportBusy, setTxExportBusy] = useState(false);
  const [pdfBusy, setPdfBusy] = useState(false);
  const [mtdDraft, setMtdDraft] = useState<MtdDraftLatest | null>(null);

  const year = TAX_YEARS[yearIdx];

  const requiresUnverifiedCisAck = Boolean(calc?.cis_hmrc_submit_requires_unverified_ack);

  const refreshMtdDraft = async (c: TaxCalcResult | null) => {
    if (!c?.mtd_obligation?.reporting_required) {
      setMtdDraft(null);
      return;
    }
    try {
      const dr = await fetch(
        `${INTEGRATIONS_API}/integrations/hmrc/mtd/quarterly-update/draft/latest`,
        { headers: { Authorization: `Bearer ${token}` } },
      );
      if (dr.ok) setMtdDraft((await dr.json()) as MtdDraftLatest);
      else setMtdDraft(null);
    } catch {
      setMtdDraft(null);
    }
  };

  const handleCalculate = async (e: FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    setMtdDraft(null);
    try {
      const res = await fetch(`${TAX_ENGINE_URL}/calculate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({ start_date: year.start, end_date: year.end, jurisdiction: 'UK' }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(formatApiDetail(data.detail) || 'Calculation failed');
      setCalc(data);
      setUnverifiedCisSubmitAck(false);
      setStep('review');
      void refreshMtdDraft(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unexpected error');
    } finally {
      setLoading(false);
    }
  };

  const exportSummaryCsv = () => {
    if (!calc) return;
    downloadSubmissionCsv(
      `submission-tax-summary-${year.label.replace(/\//g, '-')}-${new Date().toISOString().slice(0, 10)}.csv`,
      buildSubmissionSummaryLines(year.label, calc),
    );
  };

  const exportTransactionsCsv = async () => {
    if (!calc) return;
    setTxExportBusy(true);
    try {
      const res = await fetch(`${TXN_SERVICE_URL}/transactions/me`, {
        headers: transactionsBearerHeaders(token, selectedBusinessId),
      });
      if (!res.ok) throw new Error('Could not load transactions');
      const all = (await res.json()) as SubmissionTxnRow[];
      const start = new Date(year.start);
      const end = new Date(year.end);
      const filtered = all.filter((t) => {
        const d = new Date(t.date);
        return d >= start && d <= end;
      });
      downloadSubmissionCsv(
        `submission-transactions-${year.label.replace(/\//g, '-')}-${new Date().toISOString().slice(0, 10)}.csv`,
        buildSubmissionTransactionLines(filtered),
      );
    } catch {
      setError('Could not export transactions CSV.');
    } finally {
      setTxExportBusy(false);
    }
  };

  const exportBookkeepingCsv = async () => {
    if (!calc) return;
    setTxExportBusy(true);
    try {
      const res = await fetch(`${TXN_SERVICE_URL}/transactions/me`, {
        headers: transactionsBearerHeaders(token, selectedBusinessId),
      });
      if (!res.ok) throw new Error('Could not load transactions');
      const all = (await res.json()) as SubmissionTxnRow[];
      const start = new Date(year.start);
      const end = new Date(year.end);
      const filtered = all.filter((t) => {
        const d = new Date(t.date);
        return d >= start && d <= end;
      });
      downloadSubmissionCsv(
        `submission-bookkeeping-${year.label.replace(/\//g, '-')}-${new Date().toISOString().slice(0, 10)}.csv`,
        buildSubmissionBookkeepingLines(filtered),
      );
    } catch {
      setError('Could not export bookkeeping CSV.');
    } finally {
      setTxExportBusy(false);
    }
  };

  const exportSummaryPdf = async () => {
    if (!calc) return;
    setPdfBusy(true);
    try {
      await downloadAccountantTaxSummaryPdf({
        yearLabel: year.label,
        periodStart: calc.start_date,
        periodEnd: calc.end_date,
        calc: calc as AccountantPdfCalc,
        filename: `submission-tax-summary-${year.label.replace(/\//g, '-')}-${new Date().toISOString().slice(0, 10)}.pdf`,
      });
    } catch {
      setError('Could not generate PDF.');
    } finally {
      setPdfBusy(false);
    }
  };

  const handleSubmit = async () => {
    if (!calc) return;
    if (requiresUnverifiedCisAck && !unverifiedCisSubmitAck) {
      setError(
        'Self-attested CIS credits without matching statements are included. Confirm the declaration below or upload CIS evidence before submitting.',
      );
      return;
    }
    setLoading(true);
    setError('');
    try {
      let sessionId: string | undefined;
      if (typeof window !== 'undefined' && typeof sessionStorage !== 'undefined') {
        const k = 'hmrc_fraud_session_v1';
        sessionId = sessionStorage.getItem(k) ?? undefined;
        if (!sessionId && typeof crypto !== 'undefined' && 'randomUUID' in crypto) {
          sessionId = crypto.randomUUID();
          sessionStorage.setItem(k, sessionId);
        }
      }
      const hmrcFraudClientContext =
        typeof window !== 'undefined'
          ? {
              client_type: 'web' as const,
              user_agent: navigator.userAgent,
              timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
              locale: navigator.language,
              request_timestamp_utc: new Date().toISOString(),
              session_id: sessionId,
            }
          : undefined;
      const res = await fetch(`${TAX_ENGINE_URL}/calculate-and-submit`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({
          start_date: year.start,
          end_date: year.end,
          jurisdiction: 'UK',
          unverified_cis_submit_acknowledged: requiresUnverifiedCisAck ? unverifiedCisSubmitAck : false,
          hmrc_fraud_client_context: hmrcFraudClientContext,
        }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(formatApiDetail(data.detail) || 'Submission failed');
      setSubmitResult(data);
      setStep('submitted');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unexpected error');
    } finally {
      setLoading(false);
    }
  };

  const bands: TaxBand[] = calc
    ? [
        {
          label: 'Basic rate',
          rate: '20%',
          taxable: Math.min(calc.taxable_amount_after_allowance, 37700),
          amount: calc.basic_rate_tax,
        },
        {
          label: 'Higher rate',
          rate: '40%',
          taxable: Math.max(Math.min(calc.taxable_amount_after_allowance - 37700, 87440), 0),
          amount: calc.higher_rate_tax,
        },
        {
          label: 'Additional rate',
          rate: '45%',
          taxable: Math.max(calc.taxable_amount_after_allowance - 125140 + 12570, 0),
          amount: calc.additional_rate_tax,
        },
      ]
    : [];

  return (
    <div className={styles.pageContainer}>
      {/* Header */}
      <div style={{ marginBottom: '2rem' }}>
        <p style={{ color: 'var(--lp-accent-teal)', fontWeight: 600, fontSize: '0.8rem', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: '0.4rem' }}>
          HMRC Self Assessment
        </p>
        <h1 style={{ fontSize: 'clamp(1.5rem, 3vw, 2rem)', fontWeight: 800, margin: 0 }}>
          Tax Return
        </h1>
        <p style={{ color: 'var(--lp-muted)', marginTop: '0.5rem' }}>
          Draft → Review → Confirm your Self Assessment submission
        </p>
        {(businesses.length > 0 || loadError) && (
          <div style={{ marginTop: '0.75rem', display: 'flex', flexWrap: 'wrap', gap: '0.5rem', alignItems: 'center' }}>
            {businesses.length > 0 ? (
              <>
                <span style={{ fontSize: '0.82rem', color: 'var(--lp-muted)', fontWeight: 600 }}>Business</span>
                <select
                  onChange={(e) => setSelectedBusinessId(e.target.value)}
                  style={{
                    padding: '6px 10px',
                    borderRadius: 8,
                    border: '1px solid var(--lp-border)',
                    background: 'var(--lp-bg-elevated)',
                    fontSize: '0.85rem',
                  }}
                  value={selectedBusinessId ?? businesses[0]?.id ?? ''}
                >
                  {businesses.map((b) => (
                    <option key={b.id} value={b.id}>
                      {b.display_name}
                    </option>
                  ))}
                </select>
              </>
            ) : null}
            {loadError ? (
              <span style={{ fontSize: '0.8rem', color: 'rgb(248,113,113)' }}>{loadError}</span>
            ) : null}
          </div>
        )}
      </div>

      {/* Step indicator */}
      <div style={{ display: 'flex', gap: '0', marginBottom: '2rem', background: 'var(--lp-bg-elevated)', borderRadius: 12, padding: '4px', width: 'fit-content', border: '1px solid var(--lp-border)' }}>
        {(['draft', 'review', 'confirm'] as const).map((s, i) => (
          <button
            key={s}
            onClick={() => step !== 'submitted' && setStep(s)}
            style={{
              padding: '0.5rem 1.25rem',
              borderRadius: 9,
              border: 'none',
              cursor: step === 'submitted' || (s !== 'draft' && !calc) ? 'default' : 'pointer',
              background: step === s ? 'var(--lp-accent-teal)' : 'transparent',
              color: step === s ? '#fff' : 'var(--lp-muted)',
              fontWeight: 600,
              fontSize: '0.85rem',
              transition: 'all 0.15s',
            }}
          >
            {i + 1}. {s.charAt(0).toUpperCase() + s.slice(1)}
          </button>
        ))}
      </div>

      {/* STEP 1: DRAFT */}
      {step === 'draft' && (
        <div style={{ maxWidth: 520 }}>
          <div style={{ background: 'var(--lp-bg-elevated)', border: '1px solid var(--lp-border)', borderRadius: 16, padding: '2rem' }}>
            <h2 style={{ marginTop: 0, fontSize: '1.1rem' }}>Select Tax Year</h2>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem', marginBottom: '1.5rem' }}>
              {TAX_YEARS.map((y, i) => (
                <label key={y.label} style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', padding: '0.9rem 1.1rem', border: `2px solid ${yearIdx === i ? 'var(--lp-accent-teal)' : 'var(--lp-border)'}`, borderRadius: 10, cursor: 'pointer', background: yearIdx === i ? 'rgba(13,148,136,0.07)' : 'transparent', transition: 'all 0.15s' }}>
                  <input type="radio" checked={yearIdx === i} onChange={() => setYearIdx(i)} style={{ accentColor: 'var(--lp-accent-teal)' }} />
                  <div>
                    <div style={{ fontWeight: 700 }}>{y.label}</div>
                    <div style={{ fontSize: '0.8rem', color: 'var(--lp-muted)' }}>{y.start} → {y.end}</div>
                  </div>
                </label>
              ))}
            </div>

            <div style={{ background: 'rgba(245,158,11,0.1)', border: '1px solid rgba(245,158,11,0.3)', borderRadius: 10, padding: '0.85rem 1rem', marginBottom: '1.5rem', fontSize: '0.85rem' }}>
              <strong>⚠️ Note:</strong> This will fetch your real transactions and calculate your tax liability for the selected period.
            </div>

            <form onSubmit={handleCalculate}>
              <button
                type="submit"
                disabled={loading}
                style={{ width: '100%', padding: '0.9rem', background: 'var(--lp-accent-teal)', color: '#fff', border: 'none', borderRadius: 10, fontWeight: 700, fontSize: '1rem', cursor: loading ? 'wait' : 'pointer', opacity: loading ? 0.7 : 1 }}
              >
                {loading ? 'Calculating…' : 'Calculate Tax Return →'}
              </button>
            </form>
            {error && <p style={{ color: '#ef4444', marginTop: '0.75rem', fontSize: '0.875rem' }}>{error}</p>}
          </div>
        </div>
      )}

      {/* STEP 2: REVIEW */}
      {step === 'review' && calc && (
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 340px', gap: '1.5rem', alignItems: 'start' }}>
          {/* Main breakdown */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>

            {/* Income & Expenses */}
            <section style={{ background: 'var(--lp-bg-elevated)', border: '1px solid var(--lp-border)', borderRadius: 16, padding: '1.5rem' }}>
              <h2 style={{ marginTop: 0, fontSize: '1rem', fontWeight: 700, marginBottom: '1rem' }}>📊 Income & Expenses</h2>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.9rem' }}>
                <tbody>
                  <Row label="Gross trading income" value={fmt(calc.total_income)} />
                  <Row label="Allowable expenses" value={`−${fmt(calc.total_expenses)}`} muted />
                  <Row label="Net profit" value={fmt(calc.taxable_profit)} bold />
                  {calc.pa_taper_reduction > 0 && (
                    <Row label="Personal allowance taper (income > £100k)" value={`−${fmt(calc.pa_taper_reduction)}`} warn />
                  )}
                  <Row label="Personal allowance" value={`−${fmt(calc.personal_allowance_used)}`} muted />
                  <Row label="Taxable income" value={fmt(calc.taxable_amount_after_allowance)} bold accent />
                </tbody>
              </table>
            </section>

            {/* Income Tax Bands — SA100 mapping */}
            <section style={{ background: 'var(--lp-bg-elevated)', border: '1px solid var(--lp-border)', borderRadius: 16, padding: '1.5rem' }}>
              <h2 style={{ marginTop: 0, fontSize: '1rem', fontWeight: 700, marginBottom: '1rem' }}>💷 Income Tax (SA100 Box 15–17)</h2>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.9rem' }}>
                <thead>
                  <tr style={{ color: 'var(--lp-muted)', fontSize: '0.78rem' }}>
                    <th style={{ textAlign: 'left', paddingBottom: 8, fontWeight: 600 }}>Band</th>
                    <th style={{ textAlign: 'right', paddingBottom: 8, fontWeight: 600 }}>Rate</th>
                    <th style={{ textAlign: 'right', paddingBottom: 8, fontWeight: 600 }}>Taxable</th>
                    <th style={{ textAlign: 'right', paddingBottom: 8, fontWeight: 600 }}>Tax</th>
                  </tr>
                </thead>
                <tbody>
                  {bands.map((b) => (
                    <tr key={b.label} style={{ borderTop: '1px solid var(--lp-border)' }}>
                      <td style={{ padding: '0.6rem 0' }}>{b.label}</td>
                      <td style={{ textAlign: 'right', color: 'var(--lp-muted)' }}>{b.rate}</td>
                      <td style={{ textAlign: 'right', color: 'var(--lp-muted)' }}>{fmt(b.taxable)}</td>
                      <td style={{ textAlign: 'right', fontWeight: 600, color: b.amount > 0 ? '#ef4444' : 'var(--lp-muted)' }}>{fmt(b.amount)}</td>
                    </tr>
                  ))}
                  <tr style={{ borderTop: '2px solid var(--lp-border)' }}>
                    <td colSpan={3} style={{ padding: '0.6rem 0', fontWeight: 700 }}>Total Income Tax</td>
                    <td style={{ textAlign: 'right', fontWeight: 700, color: '#ef4444' }}>{fmt(calc.estimated_income_tax_due)}</td>
                  </tr>
                </tbody>
              </table>
            </section>

            {/* National Insurance */}
            <section style={{ background: 'var(--lp-bg-elevated)', border: '1px solid var(--lp-border)', borderRadius: 16, padding: '1.5rem' }}>
              <h2 style={{ marginTop: 0, fontSize: '1rem', fontWeight: 700, marginBottom: '1rem' }}>🏛️ National Insurance</h2>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.9rem' }}>
                <tbody>
                  <Row label="Class 2 NI (£3.45/week × 52)" value={fmt(calc.estimated_class2_nic_due)} />
                  <Row label="Class 4 NI main rate (6% on £12,570–£50,270)" value={fmt(calc.estimated_class4_nic_due)} />
                  <Row label="Total NI" value={fmt(calc.estimated_class2_nic_due + calc.estimated_class4_nic_due)} bold />
                </tbody>
              </table>
            </section>

            {/* Expense categories */}
            {calc.summary_by_category.length > 0 && (
              <section style={{ background: 'var(--lp-bg-elevated)', border: '1px solid var(--lp-border)', borderRadius: 16, padding: '1.5rem' }}>
                <h2 style={{ marginTop: 0, fontSize: '1rem', fontWeight: 700, marginBottom: '1rem' }}>📂 Expenses by Category (SA103F)</h2>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: '0.5rem' }}>
                  {calc.summary_by_category
                    .filter((c) => c.total_amount < 0)
                    .sort((a, b) => a.total_amount - b.total_amount)
                    .map((c) => (
                      <div key={c.category} style={{ display: 'flex', justifyContent: 'space-between', padding: '0.5rem 0.75rem', background: 'rgba(255,255,255,0.03)', borderRadius: 8, fontSize: '0.85rem' }}>
                        <span style={{ color: 'var(--lp-muted)', textTransform: 'capitalize' }}>{c.category.replace(/_/g, ' ')}</span>
                        <span style={{ fontWeight: 600 }}>{fmt(Math.abs(c.total_amount))}</span>
                      </div>
                    ))}
                </div>
              </section>
            )}

            {/* MTD Quarterly obligations */}
            {calc.mtd_obligation.reporting_required && calc.mtd_obligation.quarterly_updates.length > 0 && (
              <section style={{ background: 'var(--lp-bg-elevated)', border: '1px solid var(--lp-border)', borderRadius: 16, padding: '1.5rem' }}>
                <h2 style={{ marginTop: 0, fontSize: '1rem', fontWeight: 700, marginBottom: '1rem' }}>📅 MTD Quarterly Updates Required</h2>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                  {calc.mtd_obligation.quarterly_updates.map((q) => (
                    <div key={q.quarter} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '0.6rem 0.75rem', background: 'rgba(255,255,255,0.03)', borderRadius: 8 }}>
                      <span style={{ fontWeight: 600 }}>{q.quarter}</span>
                      <span style={{ color: 'var(--lp-muted)', fontSize: '0.85rem' }}>Due {q.due_date}</span>
                      <StatusPill status={q.status} />
                    </div>
                  ))}
                </div>
                <MtdDraftWorkflowStrip reportingRequired={calc.mtd_obligation.reporting_required} mtdDraft={mtdDraft} />
              </section>
            )}
          </div>

          {/* Summary sidebar */}
          <div style={{ position: 'sticky', top: '1rem', display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            <div style={{ background: 'var(--lp-bg-elevated)', border: '1px solid var(--lp-border)', borderRadius: 16, padding: '1.5rem' }}>
              <p style={{ color: 'var(--lp-muted)', fontSize: '0.8rem', margin: '0 0 0.25rem' }}>Tax year {year.label}</p>
              <p style={{ color: 'var(--lp-muted)', fontSize: '0.75rem', margin: '0 0 1rem' }}>Effective rate: {pct(calc.estimated_effective_tax_rate)}</p>

              <div style={{ marginBottom: '1rem' }}>
                <p style={{ color: 'var(--lp-muted)', fontSize: '0.78rem', margin: '0 0 0.2rem' }}>Total tax + NI due</p>
                <p style={{ fontSize: '2rem', fontWeight: 800, color: '#ef4444', margin: 0 }}>{fmt(calc.estimated_tax_due)}</p>
              </div>

              <div style={{ borderTop: '1px solid var(--lp-border)', paddingTop: '1rem', display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                <MiniRow label="Income Tax" value={fmt(calc.estimated_income_tax_due)} />
                <MiniRow label="Class 2 NI" value={fmt(calc.estimated_class2_nic_due)} />
                <MiniRow label="Class 4 NI" value={fmt(calc.estimated_class4_nic_due)} />
              </div>
            </div>

            {/* Payment on Account */}
            <div style={{ background: 'rgba(245,158,11,0.08)', border: '1px solid rgba(245,158,11,0.25)', borderRadius: 16, padding: '1.25rem' }}>
              <p style={{ fontWeight: 700, fontSize: '0.9rem', margin: '0 0 0.75rem' }}>💰 Payments on Account</p>
              <MiniRow label="31 Jan payment" value={fmt(calc.payment_on_account_jan)} />
              <MiniRow label="31 Jul payment" value={fmt(calc.payment_on_account_jul)} />
              <p style={{ color: 'var(--lp-muted)', fontSize: '0.75rem', marginTop: '0.5rem', marginBottom: 0 }}>Each = 50% of prior year tax</p>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
              <button
                type="button"
                onClick={exportSummaryCsv}
                disabled={txExportBusy || pdfBusy}
                style={{
                  width: '100%',
                  padding: '0.65rem',
                  background: 'var(--lp-bg-elevated)',
                  color: 'var(--lp-muted)',
                  border: '1px solid var(--lp-border)',
                  borderRadius: 10,
                  fontWeight: 600,
                  fontSize: '0.88rem',
                  cursor: txExportBusy || pdfBusy ? 'wait' : 'pointer',
                }}
              >
                Export summary CSV
              </button>
              <button
                type="button"
                onClick={() => void exportSummaryPdf()}
                disabled={txExportBusy || pdfBusy}
                style={{
                  width: '100%',
                  padding: '0.65rem',
                  background: 'rgba(13,148,136,0.12)',
                  color: 'var(--lp-accent-teal)',
                  border: '1px solid var(--lp-accent-teal)',
                  borderRadius: 10,
                  fontWeight: 600,
                  fontSize: '0.88rem',
                  cursor: txExportBusy || pdfBusy ? 'wait' : 'pointer',
                }}
              >
                {pdfBusy ? 'Preparing PDF…' : 'Export summary PDF'}
              </button>
              <button
                type="button"
                onClick={() => void exportTransactionsCsv()}
                disabled={txExportBusy || pdfBusy}
                style={{
                  width: '100%',
                  padding: '0.65rem',
                  background: 'var(--lp-bg-elevated)',
                  color: 'var(--lp-muted)',
                  border: '1px solid var(--lp-border)',
                  borderRadius: 10,
                  fontWeight: 600,
                  fontSize: '0.88rem',
                  cursor: txExportBusy || pdfBusy ? 'wait' : 'pointer',
                }}
              >
                {txExportBusy ? 'Preparing…' : 'Export transactions CSV'}
              </button>
              <button
                type="button"
                onClick={() => void exportBookkeepingCsv()}
                disabled={txExportBusy || pdfBusy}
                style={{
                  width: '100%',
                  padding: '0.65rem',
                  background: 'var(--lp-bg-elevated)',
                  color: 'var(--lp-muted)',
                  border: '1px solid var(--lp-border)',
                  borderRadius: 10,
                  fontWeight: 600,
                  fontSize: '0.88rem',
                  cursor: txExportBusy || pdfBusy ? 'wait' : 'pointer',
                }}
                title="Income and expense in separate columns. Not an HMRC submission file."
              >
                Bookkeeping CSV
              </button>
            </div>

            <button
              onClick={() => setStep('confirm')}
              style={{ width: '100%', padding: '0.9rem', background: 'var(--lp-accent-teal)', color: '#fff', border: 'none', borderRadius: 10, fontWeight: 700, fontSize: '1rem', cursor: 'pointer' }}
            >
              Proceed to Confirm →
            </button>
            <button
              onClick={() => setStep('draft')}
              style={{ width: '100%', padding: '0.75rem', background: 'transparent', color: 'var(--lp-muted)', border: '1px solid var(--lp-border)', borderRadius: 10, fontWeight: 600, cursor: 'pointer' }}
            >
              ← Back
            </button>
          </div>
        </div>
      )}

      {/* STEP 3: CONFIRM */}
      {step === 'confirm' && calc && (
        <div style={{ maxWidth: 560 }}>
          <div style={{ background: 'var(--lp-bg-elevated)', border: '1px solid var(--lp-border)', borderRadius: 16, padding: '2rem' }}>
            <h2 style={{ marginTop: 0 }}>Final Declaration</h2>
            <MtdDraftWorkflowStrip reportingRequired={calc.mtd_obligation.reporting_required} mtdDraft={mtdDraft} />

            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.6rem', marginBottom: '1.5rem' }}>
              <MiniRow label="Tax period" value={`${calc.start_date} → ${calc.end_date}`} />
              <MiniRow label="Total income" value={fmt(calc.total_income)} />
              <MiniRow label="Total expenses" value={fmt(calc.total_expenses)} />
              <MiniRow label="Taxable profit" value={fmt(calc.taxable_profit)} />
              <MiniRow label="Income Tax due" value={fmt(calc.estimated_income_tax_due)} />
              <MiniRow label="NI (Class 2+4)" value={fmt(calc.estimated_class2_nic_due + calc.estimated_class4_nic_due)} />
              <MiniRow label="Total tax & NI" value={fmt(calc.estimated_tax_due)} bold />
            </div>

            <div style={{ background: 'rgba(13,148,136,0.08)', border: '1px solid rgba(13,148,136,0.3)', borderRadius: 10, padding: '1rem', marginBottom: '1.5rem', fontSize: '0.85rem', lineHeight: 1.6 }}>
              <strong>Declaration:</strong> I declare that the information I have given on this return is correct and complete to the best of my knowledge and belief. I understand that I may face financial penalties and/or prosecution if I give false information.
            </div>

            {requiresUnverifiedCisAck && (
              <div
                style={{
                  background: 'rgba(245,158,11,0.1)',
                  border: '1px solid rgba(245,158,11,0.45)',
                  borderRadius: 10,
                  padding: '1rem',
                  marginBottom: '1.25rem',
                  fontSize: '0.85rem',
                  lineHeight: 1.55,
                }}
              >
                <strong>CIS credits (unverified):</strong> This return includes self-attested Construction Industry Scheme
                deductions that are not backed by CIS statements in MyNetTax. HMRC may challenge these figures. You may
                upload statements later and adjust figures before any submission. If you continue, you accept responsibility
                for these amounts as entered.
                <div style={{ marginTop: '0.75rem' }}>
                  <label style={{ display: 'flex', gap: '0.5rem', alignItems: 'flex-start', cursor: 'pointer' }}>
                    <input
                      checked={unverifiedCisSubmitAck}
                      onChange={(e) => setUnverifiedCisSubmitAck(e.target.checked)}
                      type="checkbox"
                      style={{ marginTop: 3 }}
                    />
                    <span>
                      I understand and accept responsibility for including unverified self-attested CIS credits in this
                      submission.
                    </span>
                  </label>
                </div>
              </div>
            )}

            {error && <p style={{ color: '#ef4444', marginBottom: '1rem', fontSize: '0.875rem' }}>{error}</p>}

            <div style={{ display: 'flex', gap: '0.75rem' }}>
              <button
                onClick={handleSubmit}
                disabled={loading || (requiresUnverifiedCisAck && !unverifiedCisSubmitAck)}
                style={{ flex: 1, padding: '0.9rem', background: '#0d9488', color: '#fff', border: 'none', borderRadius: 10, fontWeight: 700, fontSize: '1rem', cursor: loading ? 'wait' : 'pointer', opacity: loading ? 0.7 : 1 }}
              >
                {loading ? 'Submitting to HMRC…' : 'Confirm & Submit to HMRC'}
              </button>
              <button
                onClick={() => setStep('review')}
                style={{ padding: '0.9rem 1.25rem', background: 'transparent', color: 'var(--lp-muted)', border: '1px solid var(--lp-border)', borderRadius: 10, cursor: 'pointer' }}
              >
                ←
              </button>
            </div>
          </div>
        </div>
      )}

      {/* STEP 4: SUBMITTED */}
      {step === 'submitted' && submitResult && (
        <div style={{ maxWidth: 520 }}>
          <div style={{ background: 'rgba(13,148,136,0.07)', border: '2px solid rgba(13,148,136,0.4)', borderRadius: 16, padding: '2.5rem', textAlign: 'center' }}>
            <div style={{ fontSize: '3rem', marginBottom: '1rem' }}>✅</div>
            <h2 style={{ marginTop: 0, color: '#0d9488' }}>Submitted to HMRC</h2>
            <p style={{ color: 'var(--lp-muted)', marginBottom: '1.5rem' }}>Your Self Assessment has been submitted successfully.</p>

            <div style={{ background: 'var(--lp-bg-elevated)', border: '1px solid var(--lp-border)', borderRadius: 12, padding: '1.25rem', textAlign: 'left', marginBottom: '1.5rem' }}>
              <div style={{ fontSize: '0.8rem', color: 'var(--lp-muted)', marginBottom: '0.25rem' }}>HMRC Reference</div>
              <div style={{ fontFamily: 'monospace', fontSize: '1rem', fontWeight: 700 }}>{submitResult.submission_id}</div>
              <div style={{ fontSize: '0.8rem', color: 'var(--lp-muted)', marginTop: '0.75rem', marginBottom: '0.25rem' }}>Mode</div>
              <div style={{ fontSize: '0.9rem' }}>{submitResult.submission_mode?.replace(/_/g, ' ')}</div>
            </div>

            <button
              onClick={() => {
                setStep('draft');
                setCalc(null);
                setSubmitResult(null);
                setMtdDraft(null);
              }}
              style={{ padding: '0.75rem 2rem', background: 'var(--lp-accent-teal)', color: '#fff', border: 'none', borderRadius: 10, fontWeight: 600, cursor: 'pointer' }}
            >
              Start New Return
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

function Row({
  label, value, bold, muted, accent, warn,
}: {
  label: string; value: string; bold?: boolean; muted?: boolean; accent?: boolean; warn?: boolean;
}) {
  return (
    <tr style={{ borderTop: '1px solid var(--lp-border)' }}>
      <td style={{ padding: '0.55rem 0', color: muted ? 'var(--lp-muted)' : 'inherit', fontSize: '0.88rem' }}>{label}</td>
      <td style={{
        textAlign: 'right',
        padding: '0.55rem 0',
        fontWeight: bold ? 700 : 400,
        color: accent ? 'var(--lp-accent-teal)' : warn ? '#f59e0b' : muted ? 'var(--lp-muted)' : 'inherit',
        fontSize: '0.88rem',
      }}>
        {value}
      </td>
    </tr>
  );
}

function MiniRow({ label, value, bold }: { label: string; value: string; bold?: boolean }) {
  return (
    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.85rem', padding: '0.2rem 0' }}>
      <span style={{ color: 'var(--lp-muted)' }}>{label}</span>
      <span style={{ fontWeight: bold ? 700 : 500 }}>{value}</span>
    </div>
  );
}
