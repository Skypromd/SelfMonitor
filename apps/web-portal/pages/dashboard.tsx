import Link from 'next/link';
import { useRouter } from 'next/router';
import { FormEvent, useEffect, useState } from 'react';
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { useTranslation } from '../hooks/useTranslation';
import styles from '../styles/Home.module.css';

const API_GATEWAY_URL = process.env.NEXT_PUBLIC_API_GATEWAY_URL || '/api';
const AUTH_SERVICE_URL = process.env.NEXT_PUBLIC_AUTH_SERVICE_URL || '/api/auth';
const ANALYTICS_SERVICE_URL = process.env.NEXT_PUBLIC_ANALYTICS_SERVICE_URL || '/api/analytics';
const ADVICE_SERVICE_URL = process.env.NEXT_PUBLIC_ADVICE_SERVICE_URL || '/api/advice';

type DashboardPageProps = {
  token: string;
};

type ForecastPoint = {
  date: string;
  balance: number;
};

type TaxResult = {
  start_date: string;
  end_date: string;
  total_income: number;
  total_expenses: number;
  estimated_tax_due: number;
};

type AdviceItem = {
  headline: string;
  details: string;
};

function TaxCalculator({ token }: { token: string }) {
  const [result, setResult] = useState<TaxResult | null>(null);
  const [error, setError] = useState('');
  const [startDate, setStartDate] = useState('2023-01-01');
  const [endDate, setEndDate] = useState('2023-12-31');

  const handleCalculate = async (e: FormEvent) => {
    e.preventDefault();
    setError('');
    setResult(null);

    try {
      const response = await fetch(`${API_GATEWAY_URL}/tax/calculate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({ start_date: startDate, end_date: endDate, jurisdiction: 'UK' }),
      });
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.detail || 'Failed to calculate tax');
      }
      setResult(data);
    } catch (err: unknown) {
      const details = err instanceof Error ? err.message : 'Failed to calculate tax';
      setError(details);
    }
  };

  return (
    <div className={styles.subContainer}>
      <h2>Tax Estimator (UK)</h2>
      <form onSubmit={handleCalculate}>
        <div className={styles.dateInputs}>
          <input type="date" value={startDate} onChange={(e) => setStartDate(e.target.value)} className={styles.input} />
          <input type="date" value={endDate} onChange={(e) => setEndDate(e.target.value)} className={styles.input} />
        </div>
        <button type="submit" className={styles.button}>
          Calculate Tax
        </button>
      </form>
      {error && <p className={styles.error}>{error}</p>}
      {result && (
        <div className={styles.resultsContainer}>
          <h3>
            Estimated Tax for {result.start_date} to {result.end_date}
          </h3>
          <div className={styles.resultItem}>
            <span>Total Income:</span> <span className={styles.positive}>£{result.total_income.toFixed(2)}</span>
          </div>
          <div className={styles.resultItem}>
            <span>Deductible Expenses:</span> <span className={styles.negative}>£{result.total_expenses.toFixed(2)}</span>
          </div>
          <div className={styles.resultItemMain}>
            <span>Estimated Tax Due:</span> <span>£{result.estimated_tax_due.toFixed(2)}</span>
          </div>
        </div>
      )}
    </div>
  );
}

type ProfitPulseWeek = {
  week_start: string;
  week_end: string;
  income_gbp: number;
  expenses_gbp: number;
  profit_gbp: number;
};

type ProfitPulseData = {
  as_of: string;
  profit_today_gbp: number;
  profit_week_gbp: number;
  profit_tax_year_to_date_gbp: number;
  weekly: ProfitPulseWeek[];
  yoy_week_profit_delta_gbp: number;
  prior_year_same_week_profit_gbp: number;
  disclaimer: string;
  estimated_tax_due_ytd_gbp?: number | null;
};

function formatGbp(n: number): string {
  const abs = Math.abs(n).toFixed(2);
  if (n < 0) return `-£${abs}`;
  return `£${abs}`;
}

function ProfitPulseStrip({ token }: { token: string }) {
  const [data, setData] = useState<ProfitPulseData | null>(null);
  const [error, setError] = useState('');

  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      try {
        const response = await fetch(
          `${ANALYTICS_SERVICE_URL}/insights/profit-pulse?include_tax_estimate=1`,
          { headers: { Authorization: `Bearer ${token}` } },
        );
        if (!response.ok) {
          throw new Error('Profit pulse unavailable');
        }
        const json = (await response.json()) as ProfitPulseData;
        if (!cancelled) {
          setData(json);
          setError('');
        }
      } catch (err: unknown) {
        if (!cancelled) {
          const details = err instanceof Error ? err.message : 'Profit pulse unavailable';
          setError(details);
        }
      }
    };
    void load();
    const id = setInterval(() => void load(), 55000);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, [token]);

  if (error) {
    return (
      <p className={styles.info} style={{ marginBottom: '1rem' }}>
        Profit snapshot unavailable — connect a bank and ensure analytics is enabled.
      </p>
    );
  }
  if (!data) {
    return <p className={styles.info}>Loading profit snapshot…</p>;
  }

  const chartRows = data.weekly.map((w) => ({
    label: w.week_start.slice(5),
    profit: w.profit_gbp,
    income: w.income_gbp,
    expenses: w.expenses_gbp,
  }));

  return (
    <div className={styles.subContainer}>
      <h2>Profit pulse</h2>
      <p style={{ fontSize: '0.88rem', color: 'rgba(15,23,42,0.65)', marginBottom: '1rem' }}>
        {data.disclaimer}
      </p>
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))',
          gap: '0.75rem',
          marginBottom: '1.25rem',
        }}
      >
        <div style={{ padding: '0.75rem', borderRadius: 10, background: 'rgba(13,148,136,0.08)', border: '1px solid rgba(13,148,136,0.25)' }}>
          <div style={{ fontSize: '0.75rem', fontWeight: 600, color: 'rgba(15,23,42,0.55)' }}>Profit today</div>
          <div style={{ fontSize: '1.35rem', fontWeight: 800 }}>{formatGbp(data.profit_today_gbp)}</div>
        </div>
        <div style={{ padding: '0.75rem', borderRadius: 10, background: 'rgba(59,130,246,0.06)', border: '1px solid rgba(59,130,246,0.2)' }}>
          <div style={{ fontSize: '0.75rem', fontWeight: 600, color: 'rgba(15,23,42,0.55)' }}>Profit this week</div>
          <div style={{ fontSize: '1.35rem', fontWeight: 800 }}>{formatGbp(data.profit_week_gbp)}</div>
        </div>
        <div style={{ padding: '0.75rem', borderRadius: 10, background: 'rgba(245,158,11,0.08)', border: '1px solid rgba(245,158,11,0.25)' }}>
          <div style={{ fontSize: '0.75rem', fontWeight: 600, color: 'rgba(15,23,42,0.55)' }}>Tax year profit (bank)</div>
          <div style={{ fontSize: '1.35rem', fontWeight: 800 }}>{formatGbp(data.profit_tax_year_to_date_gbp)}</div>
        </div>
        {typeof data.estimated_tax_due_ytd_gbp === 'number' && (
          <div style={{ padding: '0.75rem', borderRadius: 10, background: 'rgba(239,68,68,0.06)', border: '1px solid rgba(239,68,68,0.2)' }}>
            <div style={{ fontSize: '0.75rem', fontWeight: 600, color: 'rgba(15,23,42,0.55)' }}>Est. tax due (YTD)</div>
            <div style={{ fontSize: '1.35rem', fontWeight: 800 }}>{formatGbp(data.estimated_tax_due_ytd_gbp)}</div>
          </div>
        )}
        <div style={{ padding: '0.75rem', borderRadius: 10, background: 'rgba(15,23,42,0.04)', border: '1px solid rgba(15,23,42,0.08)' }}>
          <div style={{ fontSize: '0.75rem', fontWeight: 600, color: 'rgba(15,23,42,0.55)' }}>vs same week last year</div>
          <div style={{ fontSize: '1.35rem', fontWeight: 800 }}>{formatGbp(data.yoy_week_profit_delta_gbp)}</div>
          <div style={{ fontSize: '0.72rem', marginTop: '0.25rem', color: 'rgba(15,23,42,0.45)' }}>
            Prior year week: {formatGbp(data.prior_year_same_week_profit_gbp)}
          </div>
        </div>
      </div>
      <h3 style={{ fontSize: '1rem', marginBottom: '0.5rem' }}>Weekly profit (last 8 weeks)</h3>
      <ResponsiveContainer width="100%" height={280}>
        <BarChart data={chartRows}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="label" tick={{ fontSize: 11 }} />
          <YAxis tick={{ fontSize: 11 }} />
          <Tooltip formatter={(value: number) => formatGbp(value)} />
          <Legend />
          <Bar dataKey="profit" fill="var(--lp-accent-teal, #0d9488)" name="Net profit" radius={[4, 4, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

function CashFlowChart({ token }: { token: string }) {
  const [data, setData] = useState<ForecastPoint[]>([]);
  const [error, setError] = useState('');

  useEffect(() => {
    const fetchForecast = async () => {
      try {
        const response = await fetch(`${ANALYTICS_SERVICE_URL}/forecast/cash-flow`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
          body: JSON.stringify({ days_to_forecast: 30 }),
        });
        if (!response.ok) {
          throw new Error('Failed to fetch cash flow forecast');
        }
        const result = await response.json();
        setData(result.forecast);
      } catch (err: unknown) {
        const details = err instanceof Error ? err.message : 'Failed to fetch cash flow forecast';
        setError(details);
      }
    };

    fetchForecast();
  }, [token]);

  if (error) {
    return <p className={styles.info}>Cash flow forecast unavailable — connect a bank account to enable forecasting.</p>;
  }
  if (!data.length) {
    return <p>No transaction data yet — add transactions to generate a forecast.</p>;
  }

  return (
    <div className={styles.subContainer}>
      <h2>Cash Flow Forecast (Next 30 Days)</h2>
      <ResponsiveContainer width="100%" height={300}>
        <LineChart data={data}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="date" />
          <YAxis />
          <Tooltip />
          <Legend />
          <Line type="monotone" dataKey="balance" stroke="#8884d8" activeDot={{ r: 8 }} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

type TrialSubscription = {
  plan: string;
  status: string;
  trial_end?: string;
};

type MtdQuarterRow = { quarter: string; due_date: string; status: string };

type MtdObligationSummary = {
  reporting_required: boolean;
  next_deadline: string | null;
  quarterly_updates?: MtdQuarterRow[];
};

function ukTaxYearBounds(now: Date): { start: string; end: string } {
  const m = now.getMonth();
  const day = now.getDate();
  const y = m > 3 || (m === 3 && day >= 6) ? now.getFullYear() : now.getFullYear() - 1;
  return { start: `${y}-04-06`, end: `${y + 1}-04-05` };
}

function formatShortUk(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' });
}

function MtdComplianceBanner({ token }: { token: string }) {
  const [mtd, setMtd] = useState<MtdObligationSummary | null>(null);

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      try {
        const { start, end } = ukTaxYearBounds(new Date());
        const res = await fetch(`${API_GATEWAY_URL}/tax/calculate`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
          body: JSON.stringify({ start_date: start, end_date: end, jurisdiction: 'UK' }),
        });
        const data = (await res.json().catch(() => null)) as { mtd_obligation?: MtdObligationSummary } | null;
        if (!res.ok || !data?.mtd_obligation || typeof data.mtd_obligation.reporting_required !== 'boolean') {
          return;
        }
        if (!cancelled) setMtd(data.mtd_obligation);
      } catch {
        /* ignore */
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [token]);

  if (!mtd?.reporting_required) return null;

  const hot = mtd.quarterly_updates?.find((q) => q.status === 'overdue' || q.status === 'due_now');
  const isCritical = hot?.status === 'overdue';
  const isDue = hot?.status === 'due_now';

  let body: string;
  if (hot?.status === 'overdue') {
    body = `${hot.quarter} update was due ${formatShortUk(hot.due_date)}. Prepare figures in Tax preparation, then submit only after you confirm in the MTD workflow.`;
  } else if (hot?.status === 'due_now') {
    body = `${hot.quarter} period has ended; filing deadline ${formatShortUk(hot.due_date)}. Review in Tax preparation before submitting.`;
  } else if (mtd.next_deadline) {
    const days = Math.ceil((new Date(mtd.next_deadline).getTime() - Date.now()) / (1000 * 60 * 60 * 24));
    body = `Next quarterly filing deadline ${formatShortUk(mtd.next_deadline)}${days >= 0 ? ` (${days} day${days === 1 ? '' : 's'})` : ''}.`;
  } else {
    body = 'Quarterly MTD updates may apply based on your income. Review dates in Tax preparation.';
  }

  const border = isCritical ? 'rgba(239,68,68,0.45)' : isDue ? 'rgba(245,158,11,0.45)' : 'rgba(13,148,136,0.35)';
  const bg = isCritical ? 'rgba(239,68,68,0.08)' : isDue ? 'rgba(245,158,11,0.08)' : 'rgba(13,148,136,0.1)';

  return (
    <div
      style={{
        width: '100%',
        padding: '0.85rem 1.15rem',
        borderRadius: 10,
        background: bg,
        border: `1px solid ${border}`,
        marginBottom: '1.5rem',
      }}
    >
      <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'flex-start', justifyContent: 'space-between', gap: '1rem' }}>
        <div>
          <h2 style={{ margin: '0 0 0.35rem', fontSize: '1rem', color: 'var(--text-primary)' }}>
            Making Tax Digital (Income Tax)
          </h2>
          <p style={{ margin: 0, color: 'var(--lp-muted)', fontSize: '0.88rem', lineHeight: 1.55, maxWidth: 640 }}>
            {body}
          </p>
        </div>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem', alignItems: 'center' }}>
          <Link
            href="/tax-preparation"
            style={{
              padding: '0.5rem 1rem',
              borderRadius: 10,
              border: '1px solid rgba(13,148,136,0.45)',
              color: 'var(--lp-accent-teal)',
              fontWeight: 700,
              fontSize: '0.88rem',
              textDecoration: 'none',
              whiteSpace: 'nowrap',
            }}
          >
            Tax preparation
          </Link>
          <Link
            href="/submission"
            style={{
              padding: '0.5rem 1rem',
              borderRadius: 10,
              background: 'var(--lp-accent-teal)',
              color: '#fff',
              fontWeight: 700,
              fontSize: '0.88rem',
              textDecoration: 'none',
              whiteSpace: 'nowrap',
            }}
          >
            MTD workflow
          </Link>
        </div>
      </div>
    </div>
  );
}

function TrialBanner({ token }: { token: string }) {
  const [sub, setSub] = useState<TrialSubscription | null>(null);

  useEffect(() => {
    const fetchSub = async () => {
      try {
        const response = await fetch(`${AUTH_SERVICE_URL}/subscription/me`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (response.ok) {
          setSub(await response.json());
        }
      } catch {
        // silently ignore
      }
    };
    fetchSub();
  }, [token]);

  if (!sub || sub.status !== 'trialing') return null;

  const daysRemaining = sub.trial_end
    ? Math.max(0, Math.ceil((new Date(sub.trial_end).getTime() - Date.now()) / (1000 * 60 * 60 * 24)))
    : 0;

  const planName = sub.plan.charAt(0).toUpperCase() + sub.plan.slice(1);

  return (
    <div style={{
      width: '100%',
      padding: '0.75rem 1.25rem',
      borderRadius: 10,
      background: 'rgba(13,148,136,0.15)',
      border: '1px solid rgba(13,148,136,0.3)',
      marginBottom: '1.5rem',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      gap: '1rem',
    }}>
      <span style={{ color: '#14b8a6', fontWeight: 600 }}>
        🎉 {planName} trial — {daysRemaining} day{daysRemaining !== 1 ? 's' : ''} remaining
      </span>
      <Link href="/billing" style={{
        color: '#fff',
        background: 'var(--lp-accent-teal)',
        padding: '0.4rem 1rem',
        borderRadius: 8,
        fontWeight: 600,
        fontSize: '0.85rem',
        textDecoration: 'none',
      }}>
        Upgrade Now
      </Link>
    </div>
  );
}

type CisTaskRow = {
  id: string;
  status: string;
  suspect_reason: string | null;
  suspected_transaction_id: string | null;
};

function CisTasksStrip({ token }: { token: string }) {
  const [openCount, setOpenCount] = useState<number | null>(null);
  const [dueReminders, setDueReminders] = useState<number | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      try {
        const [tasksRes, dueRes] = await Promise.all([
          fetch(`${API_GATEWAY_URL}/transactions/cis/tasks?status=open`, {
            headers: { Authorization: `Bearer ${token}` },
          }),
          fetch(`${API_GATEWAY_URL}/transactions/cis/reminders/due`, {
            headers: { Authorization: `Bearer ${token}` },
          }),
        ]);
        if (cancelled) return;
        if (tasksRes.ok) {
          const rows = (await tasksRes.json()) as CisTaskRow[];
          setOpenCount(rows.length);
        } else {
          setError(true);
        }
        if (dueRes.ok) {
          const rows = (await dueRes.json()) as CisTaskRow[];
          setDueReminders(rows.length);
        }
      } catch {
        if (!cancelled) setError(true);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [token]);

  if (error || openCount === null || dueReminders === null) {
    return null;
  }
  if (openCount === 0 && dueReminders === 0) {
    return null;
  }

  return (
    <div
      className={styles.subContainer}
      style={{
        border: '1px solid rgba(245,158,11,0.35)',
        background: 'rgba(245,158,11,0.07)',
        marginBottom: '1.25rem',
      }}
    >
      <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', justifyContent: 'space-between', gap: '0.75rem' }}>
        <div>
          <h2 style={{ margin: '0 0 0.35rem', fontSize: '1rem' }}>To review — CIS</h2>
          <p style={{ margin: 0, color: 'var(--lp-muted)', fontSize: '0.88rem', lineHeight: 1.5 }}>
            {openCount > 0 && (
              <span>
                <strong>{openCount}</strong> open task{openCount !== 1 ? 's' : ''} on transactions
                {dueReminders > 0 ? '; ' : '.'}
              </span>
            )}
            {dueReminders > 0 && (
              <span>
                <strong>{dueReminders}</strong> reminder{dueReminders !== 1 ? 's' : ''} due.
              </span>
            )}
          </p>
        </div>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem', alignItems: 'center' }}>
          <Link
            href="/cis-refund-tracker"
            style={{
              padding: '0.5rem 1rem',
              borderRadius: 10,
              border: '1px solid rgba(245,158,11,0.5)',
              color: 'var(--lp-accent-teal)',
              fontWeight: 700,
              fontSize: '0.88rem',
              textDecoration: 'none',
              whiteSpace: 'nowrap',
            }}
          >
            CIS refund tracker
          </Link>
          <Link
            href="/transactions"
            style={{
              padding: '0.5rem 1rem',
              borderRadius: 10,
              background: 'var(--lp-accent-teal)',
              color: '#fff',
              fontWeight: 700,
              fontSize: '0.88rem',
              textDecoration: 'none',
              whiteSpace: 'nowrap',
            }}
          >
            Open Transactions
          </Link>
        </div>
      </div>
    </div>
  );
}

function ActionCenter({ token }: { token: string }) {
  const [advice, setAdvice] = useState<AdviceItem | null>(null);
  const router = useRouter();

  useEffect(() => {
    const fetchAdvice = async () => {
      try {
        const response = await fetch(`${ADVICE_SERVICE_URL}/generate`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
          body: JSON.stringify({ topic: 'income_protection' }),
        });
        if (!response.ok) {
          return;
        }
        setAdvice(await response.json());
      } catch (err) {
        console.error(err);
      }
    };

    fetchAdvice();
  }, [token]);

  if (!advice) {
    return null;
  }

  return (
    <div className={`${styles.subContainer} ${styles.actionableAdviceCard}`}>
      <div className={styles.adviceTextContent}>
        <h3>{advice.headline}</h3>
        <p>{advice.details}</p>
      </div>
      <div className={styles.advicePartnerList}>
        <h4>What&apos;s Next?</h4>
        <p>Explore our marketplace of trusted partners to get help with insurance, accounting, and more.</p>
        <button onClick={() => router.push('/marketplace')} className={styles.button}>
          Explore Partner Services
        </button>
      </div>
    </div>
  );
}

export default function DashboardPage({ token }: DashboardPageProps) {
  const { t } = useTranslation();

  return (
    <div className={styles.pageContainer}>
      <TrialBanner token={token} />
      <MtdComplianceBanner token={token} />
      <h1>{t('dashboard.title')}</h1>
      <p>{t('dashboard.description')}</p>
      <CisTasksStrip token={token} />
      <ProfitPulseStrip token={token} />
      <ActionCenter token={token} />
      <CashFlowChart token={token} />
      <TaxCalculator token={token} />
    </div>
  );
}
