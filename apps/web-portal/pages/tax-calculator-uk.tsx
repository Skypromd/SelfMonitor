import Head from 'next/head';
import Link from 'next/link';
import { FormEvent, useState } from 'react';
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

export default function TaxCalculatorUkPage() {
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
      setError('Enter a valid gross income.');
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
        setError(typeof d.detail === 'string' ? d.detail : `Request failed (${res.status})`);
        return;
      }
      setData(json as ApiResult);
    } catch {
      setError('Could not reach the tax service. Is the API gateway running?');
    } finally {
      setLoading(false);
    }
  };

  const fmt = (n: number) =>
    new Intl.NumberFormat('en-GB', { style: 'currency', currency: 'GBP' }).format(n);

  return (
    <>
      <Head>
        <title>UK Self-Employed Tax Calculator (illustrative) | MyNetTax</title>
        <meta
          name="description"
          content="Free illustrative UK self-employment tax and NI estimate for sole traders. Not professional advice."
        />
      </Head>
      <div className={styles.container}>
        <main className={styles.main} style={{ maxWidth: 640 }}>
          <nav style={{ marginBottom: '1rem', fontSize: '0.88rem' }}>
            <Link href="/" className={styles.link}>
              ← Home
            </Link>
          </nav>
          <h1 className={styles.title}>UK self-employed tax estimate</h1>
          <p className={styles.description}>
            Enter your annual trading income and expenses. We use the same in-engine self-employment model as the
            signed-in app (2025/26-style bands). No account required.
          </p>

          <form className={styles.subContainer} onSubmit={onSubmit}>
            <div className={styles.grid}>
              <div>
                <label className={styles.label} htmlFor="gross">
                  Gross trading income (£/year)
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
                  Allowable expenses (£/year)
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
            <label style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: '0.75rem', fontSize: '0.9rem' }}>
              <input
                type="checkbox"
                checked={useTradingAllowance}
                onChange={(e) => setUseTradingAllowance(e.target.checked)}
              />
              Use £1,000 trading allowance (instead of listing expenses below £1,000)
            </label>
            <div style={{ marginBottom: '1rem' }}>
              <label className={styles.label} htmlFor="sl">
                Student Loan (Plan)
              </label>
              <select
                id="sl"
                className={styles.input}
                value={studentLoan}
                onChange={(e) => setStudentLoan(e.target.value)}
              >
                <option value="">None</option>
                <option value="plan_1">Plan 1</option>
                <option value="plan_2">Plan 2</option>
                <option value="plan_4">Plan 4 (Scotland)</option>
                <option value="plan_5">Plan 5</option>
                <option value="postgrad">Postgraduate</option>
              </select>
            </div>
            <button type="submit" className={styles.button} disabled={loading}>
              {loading ? 'Calculating…' : 'Calculate'}
            </button>
            {error && <p className={styles.error} style={{ marginTop: '0.75rem' }}>{error}</p>}
          </form>

          {data && (
            <section className={styles.subContainer} style={{ marginTop: '1.5rem' }}>
              <h2 style={{ marginTop: 0, fontSize: '1.15rem' }}>Results ({data.tax_year_label})</h2>
              <ul style={{ listStyle: 'none', padding: 0, margin: 0, fontSize: '0.95rem', lineHeight: 1.7 }}>
                <li>
                  <strong>Adjusted profit:</strong> {fmt(data.result.adjusted_profit)}
                </li>
                <li>
                  <strong>Personal allowance (after taper):</strong> {fmt(data.result.personal_allowance)}
                </li>
                <li>
                  <strong>Income tax:</strong> {fmt(data.result.total_income_tax)}
                </li>
                <li>
                  <strong>National Insurance (Classes 2+4):</strong> {fmt(data.result.total_ni)}
                </li>
                {data.result.student_loan_repayment > 0 && (
                  <li>
                    <strong>Student loan repayment:</strong> {fmt(data.result.student_loan_repayment)}
                  </li>
                )}
                <li>
                  <strong>Total tax + NI (+ SL):</strong> {fmt(data.result.total_tax_and_ni)}
                </li>
                <li>
                  <strong>Illustrative take-home (after tax/NI/SL):</strong> {fmt(data.result.net_take_home)}
                </li>
                <li>
                  <strong>Effective rate on gross:</strong> {data.result.effective_tax_rate_percent}%
                </li>
                <li style={{ marginTop: '0.5rem', fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
                  Payments on account (each): {fmt(data.result.payment_on_account_jan)} (Jan / Jul — illustrative)
                </li>
              </ul>
              <p style={{ fontSize: '0.82rem', color: 'var(--text-secondary)', marginTop: '1rem' }}>{data.disclaimer}</p>
              <div style={{ marginTop: '1.25rem' }}>
                <Link href="/register" className={styles.button}>
                  Want automatic MTD-ready figures? Sign up free
                </Link>
              </div>
            </section>
          )}
        </main>
      </div>
    </>
  );
}
