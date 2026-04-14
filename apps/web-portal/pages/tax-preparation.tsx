import { useEffect, useState } from 'react';
import { useRouter } from 'next/router';
import Link from 'next/link';
import styles from '../styles/Home.module.css';

const TAX_SERVICE_URL = process.env.NEXT_PUBLIC_TAX_ENGINE_URL || '/api/tax';
const TXN_SERVICE_URL = process.env.NEXT_PUBLIC_TRANSACTIONS_SERVICE_URL || '/api/transactions';

type Props = { token: string };

const TAX_YEARS = [
  { label: '2025/26', start: '2025-04-06', end: '2026-04-05', deadline: '31 Jan 2027' },
  { label: '2024/25', start: '2024-04-06', end: '2025-04-05', deadline: '31 Jan 2026' },
  { label: '2023/24', start: '2023-04-06', end: '2024-04-05', deadline: '31 Jan 2025' },
];

type Txn = {
  id: string;
  date: string;
  description: string;
  amount: number;
  category: string | null;
  reconciliation_status: string | null;
  provider_transaction_id: string;
};

type TaxCalc = {
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
  payment_on_account_jan: number;
  payment_on_account_jul: number;
  summary_by_category: { category: string; total_amount: number; taxable_amount: number }[];
  mtd_obligation: {
    reporting_required: boolean;
    qualifying_income_estimate: number;
    next_deadline: string | null;
    quarterly_updates: { quarter: string; due_date: string; status: string }[];
  };
};

const CATEGORY_LABELS: Record<string, string> = {
  transport: 'Transport & Travel', travel: 'Travel', fuel: 'Fuel & Mileage',
  mileage: 'Mileage', subscriptions: 'Subscriptions', office_supplies: 'Office Supplies',
  office: 'Office', stationery: 'Stationery', professional_fees: 'Professional Fees',
  legal: 'Legal', accounting: 'Accounting', advertising: 'Advertising & Marketing',
  marketing: 'Marketing', promotion: 'Promotion', insurance: 'Insurance',
  utilities: 'Utilities', rent: 'Rent & Premises', premises: 'Premises',
  home_office: 'Home Office', phone: 'Phone & Internet', internet: 'Internet',
  communication: 'Communications', training: 'Training & Education', education: 'Education',
  courses: 'Courses', equipment: 'Equipment', tools: 'Tools', hardware: 'Hardware',
  software: 'Software', bank_charges: 'Bank Charges', financial_charges: 'Financial Charges',
  clothing: 'Clothing/Uniform', uniform: 'Uniform', repairs: 'Repairs & Maintenance',
  maintenance: 'Maintenance', staff_costs: 'Staff Costs', wages: 'Wages',
  cost_of_goods: 'Cost of Goods', materials: 'Materials', stock: 'Stock',
  pension: 'Pension Contributions',
};

const fmt = (n: number) =>
  `£${Math.abs(n).toLocaleString('en-GB', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

const pct = (n: number) => `${(n * 100).toFixed(1)}%`;

function Pill({ label, color }: { label: string; color: string }) {
  return (
    <span style={{
      background: color, color: '#fff', borderRadius: 999, padding: '2px 10px',
      fontSize: '0.72rem', fontWeight: 600,
    }}>{label}</span>
  );
}

function WarningBox({ children }: { children: React.ReactNode }) {
  return (
    <div style={{
      background: 'rgba(245,158,11,0.1)', border: '1px solid rgba(245,158,11,0.4)',
      borderRadius: 10, padding: '12px 16px', marginBottom: 12, display: 'flex',
      gap: 10, alignItems: 'flex-start',
    }}>
      <span style={{ fontSize: 18, lineHeight: 1.4 }}>⚠️</span>
      <div style={{ fontSize: '0.88rem', color: 'var(--text-secondary)', lineHeight: 1.5 }}>{children}</div>
    </div>
  );
}

function SectionCard({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div style={{
      background: 'var(--card-bg)', border: '1px solid var(--border)', borderRadius: 12,
      padding: '20px 24px', marginBottom: 20,
    }}>
      <h3 style={{ margin: '0 0 16px', fontSize: '1rem', fontWeight: 700, color: 'var(--text-primary)' }}>
        {title}
      </h3>
      {children}
    </div>
  );
}

function Row({ label, value, bold, accent }: { label: string; value: string; bold?: boolean; accent?: string }) {
  return (
    <div style={{
      display: 'flex', justifyContent: 'space-between', padding: '7px 0',
      borderBottom: '1px solid var(--border-light)', fontSize: '0.88rem',
    }}>
      <span style={{ color: 'var(--text-secondary)' }}>{label}</span>
      <span style={{ fontWeight: bold ? 700 : 500, color: accent ?? 'var(--text-primary)' }}>{value}</span>
    </div>
  );
}

export default function TaxPreparationPage({ token }: Props) {
  const router = useRouter();
  const [yearIdx, setYearIdx] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [txns, setTxns] = useState<Txn[]>([]);
  const [unmatchedCount, setUnmatchedCount] = useState(0);
  const [calc, setCalc] = useState<TaxCalc | null>(null);
  const [ready, setReady] = useState(false);

  const year = TAX_YEARS[yearIdx];

  const load = async (yIdx: number) => {
    const y = TAX_YEARS[yIdx];
    setLoading(true);
    setError('');
    setCalc(null);
    setReady(false);
    try {
      const [txnRes, unmatchedRes, calcRes] = await Promise.all([
        fetch(`${TXN_SERVICE_URL}/transactions/me`, {
          headers: { Authorization: `Bearer ${token}` },
        }),
        fetch(`${TXN_SERVICE_URL}/transactions/receipt-drafts/unmatched?limit=1`, {
          headers: { Authorization: `Bearer ${token}` },
        }),
        fetch(`${TAX_SERVICE_URL}/calculate`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
          body: JSON.stringify({ start_date: y.start, end_date: y.end, jurisdiction: 'UK' }),
        }),
      ]);

      if (!txnRes.ok && !calcRes.ok) {
        throw new Error('Failed to load tax data. Please try again.');
      }

      const allTxns: Txn[] = txnRes.ok ? await txnRes.json() : [];
      const start = new Date(y.start);
      const end = new Date(y.end);
      const filtered = allTxns.filter(t => {
        const d = new Date(t.date);
        return d >= start && d <= end;
      });
      setTxns(filtered);

      if (unmatchedRes.ok) {
        const u = await unmatchedRes.json();
        setUnmatchedCount(u.total ?? 0);
      }

      if (!calcRes.ok) {
        const err = await calcRes.json().catch(() => ({}));
        throw new Error((err as any).detail ?? 'Tax calculation failed');
      }
      const calcData: TaxCalc = await calcRes.json();
      setCalc(calcData);
      setReady(true);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Unexpected error');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void load(yearIdx);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleYearChange = (idx: number) => {
    setYearIdx(idx);
    void load(idx);
  };

  // Derived data
  const incomeTxns = txns.filter(t => t.amount > 0);
  const expenseTxns = txns.filter(t => t.amount < 0 && !t.provider_transaction_id.startsWith('receipt-draft-'));
  const draftTxns = txns.filter(t => t.provider_transaction_id.startsWith('receipt-draft-'));
  const uncategorised = txns.filter(t => !t.category && t.amount < 0 && !t.provider_transaction_id.startsWith('receipt-draft-'));

  // Group expenses by category
  const expenseByCategory: Record<string, number> = {};
  expenseTxns.forEach(t => {
    const cat = t.category ?? 'uncategorised';
    expenseByCategory[cat] = (expenseByCategory[cat] ?? 0) + Math.abs(t.amount);
  });
  const sortedExpenseCategories = Object.entries(expenseByCategory).sort(([, a], [, b]) => b - a);

  const totalIncome = incomeTxns.reduce((s, t) => s + t.amount, 0);
  const totalExpenses = expenseTxns.reduce((s, t) => s + Math.abs(t.amount), 0);

  const warnings: string[] = [];
  if (unmatchedCount > 0)
    warnings.push(`${unmatchedCount} receipt${unmatchedCount !== 1 ? 's' : ''} not yet matched to a bank transaction. Match them in Documents to claim deductions accurately.`);
  if (uncategorised.length > 0)
    warnings.push(`${uncategorised.length} transaction${uncategorised.length !== 1 ? 's' : ''} have no category. Categorise them in Transactions to include them as deductible expenses.`);
  if (draftTxns.filter(t => t.reconciliation_status === 'open').length > 0)
    warnings.push(`${draftTxns.filter(t => t.reconciliation_status === 'open').length} receipt draft${draftTxns.filter(t => t.reconciliation_status === 'open').length !== 1 ? 's' : ''} pending bank reconciliation.`);

  const totalTaxDue = calc ? calc.estimated_tax_due : 0;

  return (
    <div className={styles.pageContainer} style={{ padding: '24px 0' }}>
      {/* Header */}
      <div style={{ marginBottom: 24 }}>
        <h1 style={{ fontSize: '1.6rem', fontWeight: 800, margin: 0, color: 'var(--text-primary)' }}>
          Tax Return Preparation
        </h1>
        <p style={{ margin: '6px 0 0', color: 'var(--text-secondary)', fontSize: '0.9rem' }}>
          Review your income, expenses, and tax liability before submitting to HMRC
        </p>
      </div>

      {/* Tax Year Selector */}
      <div style={{ display: 'flex', gap: 10, marginBottom: 24, flexWrap: 'wrap', alignItems: 'center' }}>
        {TAX_YEARS.map((y, i) => (
          <button
            key={y.label}
            onClick={() => handleYearChange(i)}
            style={{
              padding: '8px 20px', borderRadius: 999, border: 'none', cursor: 'pointer',
              fontWeight: 600, fontSize: '0.88rem',
              background: i === yearIdx ? 'var(--accent)' : 'var(--card-bg)',
              color: i === yearIdx ? '#fff' : 'var(--text-secondary)',
              outline: i === yearIdx ? 'none' : '1px solid var(--border)',
              transition: 'all 0.15s',
            }}
          >
            {y.label}
          </button>
        ))}
        <span style={{ marginLeft: 'auto', fontSize: '0.82rem', color: 'var(--text-tertiary)' }}>
          SA100 deadline: <strong style={{ color: 'var(--text-secondary)' }}>{TAX_YEARS[yearIdx].deadline}</strong>
        </span>
      </div>

      {/* Loading */}
      {loading && (
        <div style={{ textAlign: 'center', padding: '60px 0', color: 'var(--text-secondary)' }}>
          <div style={{ fontSize: '2rem', marginBottom: 12 }}>⏳</div>
          Loading your tax data...
        </div>
      )}

      {/* Error */}
      {!loading && error && (
        <div style={{
          background: 'rgba(239,68,68,0.1)', border: '1px solid rgba(239,68,68,0.3)',
          borderRadius: 10, padding: '14px 18px', marginBottom: 20, color: 'var(--danger)',
        }}>
          {error}
          <button onClick={() => load(yearIdx)} style={{
            marginLeft: 12, padding: '4px 12px', borderRadius: 6, border: '1px solid var(--danger)',
            background: 'transparent', color: 'var(--danger)', cursor: 'pointer', fontSize: '0.82rem',
          }}>Retry</button>
        </div>
      )}

      {!loading && ready && calc && (
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 340px', gap: 24, alignItems: 'start' }}>

          {/* LEFT COLUMN */}
          <div>
            {/* Warnings */}
            {warnings.length > 0 && (
              <div style={{ marginBottom: 20 }}>
                {warnings.map((w, i) => <WarningBox key={i}>{w}</WarningBox>)}
              </div>
            )}

            {/* Income Summary */}
            <SectionCard title="Income">
              <Row label="Gross trading income" value={fmt(totalIncome)} bold />
              <Row label={`Transactions (${incomeTxns.length})`} value={`${incomeTxns.length} payments received`} />
            </SectionCard>

            {/* Expenses by Category */}
            <SectionCard title={`Allowable Expenses  (${sortedExpenseCategories.length} categories)`}>
              {sortedExpenseCategories.length === 0 ? (
                <p style={{ color: 'var(--text-tertiary)', fontSize: '0.88rem', margin: 0 }}>
                  No categorised expenses for this tax year.{' '}
                  <Link href="/transactions" style={{ color: 'var(--accent)' }}>Categorise transactions</Link>
                </p>
              ) : (
                <>
                  {sortedExpenseCategories.map(([cat, total]) => (
                    <div key={cat} style={{ display: 'flex', justifyContent: 'space-between', padding: '7px 0', borderBottom: '1px solid var(--border-light)', fontSize: '0.88rem' }}>
                      <span style={{ color: 'var(--text-secondary)' }}>{CATEGORY_LABELS[cat] ?? cat}</span>
                      <span style={{ fontWeight: 600, color: 'var(--text-primary)' }}>{fmt(total)}</span>
                    </div>
                  ))}
                  <div style={{ display: 'flex', justifyContent: 'space-between', padding: '10px 0 0', fontSize: '0.92rem', fontWeight: 700, color: 'var(--text-primary)' }}>
                    <span>Total Expenses</span>
                    <span>{fmt(totalExpenses)}</span>
                  </div>
                </>
              )}
            </SectionCard>

            {/* Receipt Drafts */}
            {draftTxns.length > 0 && (
              <SectionCard title={`Receipt Drafts (${draftTxns.length})`}>
                <p style={{ margin: '0 0 12px', fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
                  Receipts scanned via OCR — match to bank transactions to confirm deductibility.
                </p>
                {draftTxns.slice(0, 5).map(t => (
                  <div key={t.id} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '7px 0', borderBottom: '1px solid var(--border-light)', fontSize: '0.85rem' }}>
                    <div>
                      <span style={{ color: 'var(--text-primary)', fontWeight: 500 }}>{t.description.replace('Receipt draft: ', '')}</span>
                      <span style={{ color: 'var(--text-tertiary)', marginLeft: 8 }}>{t.date}</span>
                    </div>
                    <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
                      <span style={{ fontWeight: 600 }}>{fmt(Math.abs(t.amount))}</span>
                      <Pill label={t.reconciliation_status ?? 'open'} color={t.reconciliation_status === 'reconciled' ? '#0d9488' : '#f59e0b'} />
                    </div>
                  </div>
                ))}
                {draftTxns.length > 5 && (
                  <p style={{ margin: '8px 0 0', fontSize: '0.82rem', color: 'var(--text-tertiary)' }}>
                    +{draftTxns.length - 5} more —{' '}
                    <Link href="/documents" style={{ color: 'var(--accent)' }}>review in Documents</Link>
                  </p>
                )}
              </SectionCard>
            )}

            {/* Tax Breakdown */}
            <SectionCard title="Tax Calculation (2025/26 rates)">
              <Row label="Gross trading income" value={fmt(calc.total_income)} />
              <Row label="Less: allowable expenses" value={`- ${fmt(calc.total_expenses)}`} />
              <Row label="Net profit" value={fmt(calc.taxable_profit)} bold />
              <div style={{ height: 8 }} />
              <Row label="Personal allowance" value={`- ${fmt(calc.personal_allowance_used)}`} />
              {calc.pa_taper_reduction > 0 && (
                <Row label="PA taper (income > £100k)" value={`- ${fmt(calc.pa_taper_reduction)}`} accent="var(--danger)" />
              )}
              <Row label="Taxable profit" value={fmt(calc.taxable_amount_after_allowance)} bold />
              <div style={{ height: 8 }} />
              <Row label="Basic rate tax (20%)" value={fmt(calc.basic_rate_tax)} />
              <Row label="Higher rate tax (40%)" value={fmt(calc.higher_rate_tax)} />
              <Row label="Additional rate tax (45%)" value={fmt(calc.additional_rate_tax)} />
              <Row label="Income tax" value={fmt(calc.estimated_income_tax_due)} bold />
              <div style={{ height: 8 }} />
              <Row label="Class 2 NI (£3.45/wk)" value={fmt(calc.estimated_class2_nic_due)} />
              <Row label="Class 4 NI (6%/2%)" value={fmt(calc.estimated_class4_nic_due)} />
            </SectionCard>

            {/* MTD Obligations */}
            {calc.mtd_obligation.reporting_required && (
              <SectionCard title="MTD ITSA Obligations">
                <p style={{ margin: '0 0 12px', fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
                  Your income estimate of {fmt(calc.mtd_obligation.qualifying_income_estimate)} exceeds the MTD ITSA threshold. Quarterly updates are required.
                </p>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: 10 }}>
                  {calc.mtd_obligation.quarterly_updates.map(q => (
                    <div key={q.quarter} style={{
                      background: 'var(--bg-elevated)', borderRadius: 8, padding: '10px 14px',
                      border: `1px solid ${q.status === 'overdue' ? 'rgba(239,68,68,0.4)' : q.status === 'due_now' ? 'rgba(245,158,11,0.4)' : 'var(--border)'}`,
                    }}>
                      <div style={{ fontWeight: 700, fontSize: '0.88rem', marginBottom: 4 }}>{q.quarter}</div>
                      <div style={{ fontSize: '0.8rem', color: 'var(--text-tertiary)' }}>Due {q.due_date}</div>
                      <div style={{ marginTop: 6 }}>
                        <Pill label={q.status.replace('_', ' ')} color={q.status === 'overdue' ? '#ef4444' : q.status === 'due_now' ? '#f59e0b' : '#0d9488'} />
                      </div>
                    </div>
                  ))}
                </div>
              </SectionCard>
            )}
          </div>

          {/* RIGHT COLUMN — sticky summary */}
          <div style={{ position: 'sticky', top: 24 }}>
            <div style={{
              background: 'var(--card-bg)', border: '1px solid var(--border)', borderRadius: 14,
              padding: '24px', boxShadow: '0 4px 24px rgba(0,0,0,0.06)',
            }}>
              <h3 style={{ margin: '0 0 20px', fontSize: '1rem', fontWeight: 700 }}>Summary</h3>

              <div style={{ marginBottom: 20 }}>
                <div style={{ fontSize: '0.78rem', color: 'var(--text-tertiary)', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 4 }}>
                  Tax Year
                </div>
                <div style={{ fontWeight: 700, fontSize: '1.1rem' }}>{year.label}</div>
              </div>

              <div style={{ background: 'var(--bg-elevated)', borderRadius: 10, padding: '16px', marginBottom: 16 }}>
                <div style={{ fontSize: '0.78rem', color: 'var(--text-tertiary)', marginBottom: 4 }}>Total Tax &amp; NI Due</div>
                <div style={{ fontSize: '2rem', fontWeight: 800, color: totalTaxDue > 0 ? 'var(--danger)' : 'var(--income)' }}>
                  {fmt(totalTaxDue)}
                </div>
                {calc.estimated_income_tax_due > 0 && (
                  <div style={{ fontSize: '0.78rem', color: 'var(--text-tertiary)', marginTop: 4 }}>
                    Inc. tax {fmt(calc.estimated_income_tax_due)} + NI {fmt(calc.estimated_class2_nic_due + calc.estimated_class4_nic_due)}
                  </div>
                )}
              </div>

              {(calc.payment_on_account_jan > 0) && (
                <div style={{ marginBottom: 16 }}>
                  <div style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 8 }}>
                    Payments on Account
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.85rem', padding: '5px 0', borderBottom: '1px solid var(--border-light)' }}>
                    <span style={{ color: 'var(--text-secondary)' }}>31 Jan {parseInt(year.label.split('/')[1]) + 2000 + 1}</span>
                    <span style={{ fontWeight: 600 }}>{fmt(calc.payment_on_account_jan)}</span>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.85rem', padding: '5px 0' }}>
                    <span style={{ color: 'var(--text-secondary)' }}>31 Jul {parseInt(year.label.split('/')[1]) + 2000 + 1}</span>
                    <span style={{ fontWeight: 600 }}>{fmt(calc.payment_on_account_jul)}</span>
                  </div>
                </div>
              )}

              <div style={{ marginBottom: 20 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.85rem', padding: '6px 0', borderBottom: '1px solid var(--border-light)' }}>
                  <span style={{ color: 'var(--text-secondary)' }}>Income</span>
                  <span style={{ fontWeight: 600, color: 'var(--income)' }}>{fmt(calc.total_income)}</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.85rem', padding: '6px 0', borderBottom: '1px solid var(--border-light)' }}>
                  <span style={{ color: 'var(--text-secondary)' }}>Expenses</span>
                  <span style={{ fontWeight: 600 }}>- {fmt(calc.total_expenses)}</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.85rem', padding: '6px 0' }}>
                  <span style={{ color: 'var(--text-secondary)' }}>Net profit</span>
                  <span style={{ fontWeight: 700 }}>{fmt(calc.taxable_profit)}</span>
                </div>
              </div>

              {warnings.length > 0 && (
                <div style={{
                  background: 'rgba(245,158,11,0.08)', border: '1px solid rgba(245,158,11,0.3)',
                  borderRadius: 8, padding: '10px 12px', marginBottom: 16, fontSize: '0.8rem',
                  color: 'var(--warning)', lineHeight: 1.5,
                }}>
                  ⚠️ {warnings.length} issue{warnings.length !== 1 ? 's' : ''} to resolve before submitting
                </div>
              )}

              <button
                onClick={() => void router.push(`/submission?year=${encodeURIComponent(year.label)}`)}
                style={{
                  width: '100%', padding: '14px', borderRadius: 10, border: 'none',
                  background: 'var(--accent)', color: '#fff', fontWeight: 700,
                  fontSize: '0.95rem', cursor: 'pointer', transition: 'opacity 0.15s',
                }}
                onMouseOver={e => (e.currentTarget.style.opacity = '0.88')}
                onMouseOut={e => (e.currentTarget.style.opacity = '1')}
              >
                Proceed to HMRC Submission
              </button>
              <p style={{ margin: '10px 0 0', fontSize: '0.75rem', color: 'var(--text-tertiary)', textAlign: 'center', lineHeight: 1.4 }}>
                You will review and confirm before anything is sent to HMRC
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
