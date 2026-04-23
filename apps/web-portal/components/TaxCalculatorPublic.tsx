import Link from 'next/link';
import { FormEvent, useState } from 'react';
import type { TaxCalculatorPublicCopy } from '../lib/taxCalculatorSeoCopy';
import styles from '../styles/Home.module.css';

const API_BASE = process.env.NEXT_PUBLIC_API_GATEWAY_URL || '/api';

type ApiResult = {
  result: {
    gross_trading_income: number;
    allowable_expenses_used: number;
    trading_allowance_used: number;
    adjusted_profit: number;
    personal_allowance: number;
    taxable_income: number;
    total_income_tax: number;
    total_ni: number;
    total_tax_and_ni: number;
    student_loan_repayment: number;
    net_take_home: number;
    effective_tax_rate_percent: number;
    payment_on_account_jan: number;
    payment_on_account_jul: number;
  };
  disclaimer: string;
  tax_year_label: string;
};

type LangLink = { href: string; label: string };

type Props = {
  copy: TaxCalculatorPublicCopy;
  langLinks: LangLink[];
};

export default function TaxCalculatorPublic({ copy, langLinks }: Props) {
  const [gross, setGross] = useState('45000');
  const [expenses, setExpenses] = useState('3000');
  const [useTradingAllowance, setUseTradingAllowance] = useState(false);
  const [studentLoan, setStudentLoan] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [data, setData] = useState<ApiResult | null>(null);

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError('');
    setData(null);
    const gi = parseFloat(gross);
    const ex = parseFloat(expenses || '0');
    if (Number.isNaN(gi) || gi < 0) {
      setError(copy.errors.invalidGross);
      return;
    }
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/tax/public/self-employed-estimate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          gross_trading_income: gi,
          allowable_expenses: Number.isNaN(ex) ? 0 : ex,
          use_trading_allowance: useTradingAllowance,
          student_loan_plan: studentLoan || null,
        }),
      });
      const json = await res.json().catch(() => ({}));
      if (!res.ok) {
        const d = json as { detail?: string };
        setError(typeof d.detail === 'string' ? d.detail : copy.errors.requestFailed(res.status));
        return;
      }
      setData(json as ApiResult);
    } catch {
      setError(copy.errors.network);
    } finally {
      setLoading(false);
    }
  };

  const fmt = (n: number) =>
    new Intl.NumberFormat('en-GB', { style: 'currency', currency: 'GBP' }).format(n);

  return (
    <div className={styles.container} lang={copy.htmlLang}>
      <main className={styles.main} style={{ maxWidth: 640 }}>
        <nav style={{ marginBottom: '1rem', fontSize: '0.88rem' }}>
          <Link href="/" className={styles.link} locale={false}>
            {copy.navHome}
          </Link>
        </nav>
        <h1 className={styles.title}>{copy.h1}</h1>
        <p className={styles.description}>{copy.intro}</p>

        {langLinks.length > 0 && (
          <nav
            aria-label={copy.langSwitcher}
            style={{
              marginBottom: '1.25rem',
              fontSize: '0.82rem',
              display: 'flex',
              flexWrap: 'wrap',
              gap: '0.5rem 0.75rem',
              alignItems: 'center',
            }}
          >
            <span style={{ color: 'var(--text-secondary)' }}>{copy.langSwitcher}:</span>
            {langLinks.map((l) => (
              <Link key={l.href} href={l.href} className={styles.link} locale={false}>
                {l.label}
              </Link>
            ))}
          </nav>
        )}

        <form className={styles.subContainer} onSubmit={onSubmit}>
          <div className={styles.grid}>
            <div>
              <label className={styles.label} htmlFor="gross">
                {copy.grossLabel}
              </label>
              <input
                id="gross"
                className={styles.input}
                type="number"
                min={0}
                step={100}
                value={gross}
                onChange={(e) => setGross(e.target.value)}
                required
              />
            </div>
            <div>
              <label className={styles.label} htmlFor="expenses">
                {copy.expensesLabel}
              </label>
              <input
                id="expenses"
                className={styles.input}
                type="number"
                min={0}
                step={100}
                value={expenses}
                onChange={(e) => setExpenses(e.target.value)}
                disabled={useTradingAllowance}
              />
            </div>
          </div>
          <label
            style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: '0.75rem', fontSize: '0.9rem' }}
          >
            <input
              type="checkbox"
              checked={useTradingAllowance}
              onChange={(e) => setUseTradingAllowance(e.target.checked)}
            />
            {copy.tradingAllowanceLabel}
          </label>
          <div style={{ marginBottom: '1rem' }}>
            <label className={styles.label} htmlFor="sl">
              {copy.studentLoanLabel}
            </label>
            <select
              id="sl"
              className={styles.input}
              value={studentLoan}
              onChange={(e) => setStudentLoan(e.target.value)}
            >
              <option value="">{copy.studentLoanNone}</option>
              <option value="plan_1">Plan 1</option>
              <option value="plan_2">Plan 2</option>
              <option value="plan_4">Plan 4 (Scotland)</option>
              <option value="plan_5">Plan 5</option>
              <option value="postgrad">Postgraduate</option>
            </select>
          </div>
          <button type="submit" className={styles.button} disabled={loading}>
            {loading ? copy.calculating : copy.calculate}
          </button>
          {error && <p className={styles.error} style={{ marginTop: '0.75rem' }}>{error}</p>}
        </form>

        {data && (
          <section className={styles.subContainer} style={{ marginTop: '1.5rem' }}>
            <h2 style={{ marginTop: 0, fontSize: '1.15rem' }}>
              {copy.resultsTitle} ({data.tax_year_label})
            </h2>
            <ul style={{ listStyle: 'none', padding: 0, margin: 0, fontSize: '0.95rem', lineHeight: 1.7 }}>
              <li>
                <strong>{copy.resultAdjustedProfit}</strong> {fmt(data.result.adjusted_profit)}
              </li>
              <li>
                <strong>{copy.resultPersonalAllowance}</strong> {fmt(data.result.personal_allowance)}
              </li>
              <li>
                <strong>{copy.resultIncomeTax}</strong> {fmt(data.result.total_income_tax)}
              </li>
              <li>
                <strong>{copy.resultNi}</strong> {fmt(data.result.total_ni)}
              </li>
              {data.result.student_loan_repayment > 0 && (
                <li>
                  <strong>{copy.resultStudentLoan}</strong> {fmt(data.result.student_loan_repayment)}
                </li>
              )}
              <li>
                <strong>{copy.resultTotalTaxNi}</strong> {fmt(data.result.total_tax_and_ni)}
              </li>
              <li>
                <strong>{copy.resultTakeHome}</strong> {fmt(data.result.net_take_home)}
              </li>
              <li>
                <strong>{copy.resultEffectiveRate}</strong> {data.result.effective_tax_rate_percent}%
              </li>
              <li style={{ marginTop: '0.5rem', fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
                {copy.resultPaymentsOnAccount} {fmt(data.result.payment_on_account_jan)}
              </li>
            </ul>
            <p style={{ fontSize: '0.82rem', color: 'var(--text-secondary)', marginTop: '1rem' }}>{data.disclaimer}</p>
            <div style={{ marginTop: '1.25rem' }}>
              <Link href="/register" className={styles.button} locale={false}>
                {copy.ctaRegister}
              </Link>
            </div>
          </section>
        )}
      </main>
    </div>
  );
}
