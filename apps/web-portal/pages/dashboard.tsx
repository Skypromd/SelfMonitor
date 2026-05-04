import Link from 'next/link';
import { useRouter } from 'next/router';
import { FormEvent, useCallback, useEffect, useState } from 'react';
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
import styles from '../styles/Home.module.css';

const API_GATEWAY_URL = process.env.NEXT_PUBLIC_API_GATEWAY_URL || '/api';
const AUTH_SERVICE_URL = process.env.NEXT_PUBLIC_AUTH_SERVICE_URL || '/api/auth';
const ANALYTICS_SERVICE_URL = process.env.NEXT_PUBLIC_ANALYTICS_SERVICE_URL || '/api/analytics';
const ADVICE_SERVICE_URL = process.env.NEXT_PUBLIC_ADVICE_SERVICE_URL || '/api/advice';
const BANKING_SERVICE_URL = process.env.NEXT_PUBLIC_BANKING_SERVICE_URL || '/api/banking';
const INTEGRATIONS_SERVICE_URL = process.env.NEXT_PUBLIC_INTEGRATIONS_SERVICE_URL || '/api/integrations';
const TXN_SERVICE_URL = process.env.NEXT_PUBLIC_TRANSACTIONS_SERVICE_URL || '/api/transactions';

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

function buildFinopsDashboardWsUrl(): string | null {
  if (typeof window === 'undefined') return null;
  let httpBase = (process.env.NEXT_PUBLIC_API_GATEWAY_URL || '').trim();
  if (!httpBase.startsWith('http')) {
    if (window.location.hostname === 'localhost') {
      httpBase = 'http://localhost:8000/api';
    } else {
      return null;
    }
  }
  const base = httpBase.replace(/\/?$/, '');
  const u = new URL(base.endsWith('/api') ? base : `${base}/api`);
  u.protocol = u.protocol === 'https:' ? 'wss:' : 'ws:';
  u.pathname = '/api/finops/ws/dashboard/live';
  u.search = '';
  u.hash = '';
  return u.toString();
}

function ProfitPulseStrip({ token }: { token: string }) {
  const [data, setData] = useState<ProfitPulseData | null>(null);
  const [error, setError] = useState('');

  const load = useCallback(async () => {
    try {
      const response = await fetch(
        `${ANALYTICS_SERVICE_URL}/insights/profit-pulse?include_tax_estimate=1`,
        { headers: { Authorization: `Bearer ${token}` } },
      );
      if (!response.ok) {
        throw new Error('Profit pulse unavailable');
      }
      const json = (await response.json()) as ProfitPulseData;
      setData(json);
      setError('');
    } catch (err: unknown) {
      const details = err instanceof Error ? err.message : 'Profit pulse unavailable';
      setError(details);
    }
  }, [token]);

  useEffect(() => {
    void load();
    const id = setInterval(() => void load(), 120000);
    return () => clearInterval(id);
  }, [load]);

  useEffect(() => {
    const wsUrl = buildFinopsDashboardWsUrl();
    if (!wsUrl || !token) return undefined;
    let ws: WebSocket | null = null;
    try {
      ws = new WebSocket(wsUrl);
      ws.onopen = () => {
        ws?.send(`Bearer ${token}`);
      };
      ws.onmessage = (ev) => {
        try {
          const msg = JSON.parse(String(ev.data)) as { type?: string };
          if (msg.type === 'transactions_updated') void load();
        } catch {
          /* ignore */
        }
      };
    } catch {
      /* ignore */
    }
    return () => {
      ws?.close();
    };
  }, [token, load]);

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
          <Tooltip formatter={(value) => formatGbp(typeof value === 'number' ? value : 0)} />
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


type TaxReserveData = {
  net_tax_due_gbp: number;
  income_tax_gbp: number;
  class4_nic_gbp: number;
  profit_gbp: number;
  cis_deductions_verified_gbp?: number;
  cis_deductions_unverified_gbp?: number;
  confidence: 'low' | 'medium' | 'high';
};

const RESERVE_STORAGE_KEY = 'mnt_tax_reserve_prev';

function explainReserveChange(prev: TaxReserveData, curr: TaxReserveData): string | null {
  const delta = curr.net_tax_due_gbp - prev.net_tax_due_gbp;
  if (Math.abs(delta) < 1) return null;
  const dir = delta > 0 ? 'up' : 'down';
  const reasons: string[] = [];
  const profitDelta = curr.profit_gbp - prev.profit_gbp;
  if (Math.abs(profitDelta) >= 1) reasons.push(`profit ${profitDelta > 0 ? 'increased' : 'decreased'} by £${Math.abs(Math.round(profitDelta)).toLocaleString('en-GB')}`);
  const expDelta = (prev.income_tax_gbp + prev.class4_nic_gbp) - (curr.income_tax_gbp + curr.class4_nic_gbp);
  if (reasons.length === 0 && Math.abs(expDelta) >= 1) reasons.push('tax band or NIC calculation changed');
  const cisPrev = (prev.cis_deductions_verified_gbp ?? 0);
  const cisCurr = (curr.cis_deductions_verified_gbp ?? 0);
  const cisDelta = cisCurr - cisPrev;
  if (Math.abs(cisDelta) >= 1) reasons.push(`CIS verified credits ${cisDelta > 0 ? 'increased' : 'decreased'} by £${Math.abs(Math.round(cisDelta)).toLocaleString('en-GB')}`);
  const why = reasons.length > 0 ? ` — ${reasons.join('; ')}` : '';
  return `Reserve ${dir} £${Math.abs(Math.round(delta)).toLocaleString('en-GB')}${why}.`;
}

function TaxReserveWidget({ token }: { token: string }) {
  const [reserve, setReserve] = useState<TaxReserveData | null>(null);
  const [changeNote, setChangeNote] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      try {
        const r = await fetch(`${TXN_SERVICE_URL}/transactions/tax-reserve`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (!r.ok || cancelled) return;
        const data = (await r.json()) as TaxReserveData;
        setReserve(data);
        // Compare with previous stored value
        try {
          const stored = localStorage.getItem(RESERVE_STORAGE_KEY);
          if (stored) {
            const prev = JSON.parse(stored) as TaxReserveData;
            setChangeNote(explainReserveChange(prev, data));
          }
          localStorage.setItem(RESERVE_STORAGE_KEY, JSON.stringify(data));
        } catch { /* storage unavailable */ }
      } catch { /* ignore */ }
    })();
    return () => { cancelled = true; };
  }, [token]);

  if (!reserve) return null;

  const fmt = (n: number) => `£${Math.round(n).toLocaleString('en-GB')}`;
  const confColor = reserve.confidence === 'high' ? '#22c55e' : reserve.confidence === 'medium' ? '#f59e0b' : '#94a3b8';

  // Weekly reserve suggestion: split remaining balance over weeks until next SA payment date
  const weeklyReserve = (() => {
    const now = new Date();
    const year = now.getFullYear();
    // HMRC SA dates: 31 Jan, 31 Jul — find the next one
    const candidates = [new Date(year, 0, 31), new Date(year, 6, 31), new Date(year + 1, 0, 31)];
    const target = candidates.find(d => d > now) ?? candidates[candidates.length - 1];
    const weeksLeft = Math.max(1, Math.ceil((target.getTime() - now.getTime()) / (7 * 86_400_000)));
    const weeklyAmount = reserve.net_tax_due_gbp / weeksLeft;
    return { weeklyAmount, target, weeksLeft };
  })();

  return (
    <div className={styles.subContainer} style={{
      border: '1px solid rgba(239,68,68,0.25)',
      background: 'rgba(239,68,68,0.04)',
      marginBottom: '1.25rem',
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '0.5rem', marginBottom: '0.6rem' }}>
        <h2 style={{ margin: 0, fontSize: '1rem' }}>Tax Reserve Estimate</h2>
        <span style={{ fontSize: '0.72rem', fontWeight: 700, color: confColor, textTransform: 'uppercase' }}>
          {reserve.confidence} confidence
        </span>
      </div>
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '1.5rem', alignItems: 'center' }}>
        <div>
          <div style={{ fontSize: '1.8rem', fontWeight: 800, color: '#ef4444', lineHeight: 1 }}>
            {fmt(reserve.net_tax_due_gbp)}
          </div>
          <div style={{ fontSize: '0.75rem', color: 'var(--lp-muted)', marginTop: 2 }}>est. tax to set aside</div>
        </div>
        <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap', fontSize: '0.82rem', color: 'var(--lp-muted)' }}>
          <span>Profit: <strong style={{ color: 'var(--text-primary)' }}>{fmt(reserve.profit_gbp)}</strong></span>
          <span>Income tax: <strong style={{ color: 'var(--text-primary)' }}>{fmt(reserve.income_tax_gbp)}</strong></span>
          <span>Class 4 NIC: <strong style={{ color: 'var(--text-primary)' }}>{fmt(reserve.class4_nic_gbp)}</strong></span>
        </div>
      </div>
      <div style={{ marginTop: '0.75rem', display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
        {changeNote && (
          <div style={{
            padding: '0.4rem 0.85rem', borderRadius: 8,
            background: 'rgba(245,158,11,0.07)', border: '1px solid rgba(245,158,11,0.25)',
            fontSize: '0.78rem', color: '#92400e',
          }}>
            ↕ {changeNote}
          </div>
        )}
        <div style={{
          padding: '0.45rem 0.85rem', borderRadius: 8,
          background: 'rgba(239,68,68,0.06)', border: '1px solid rgba(239,68,68,0.2)',
          fontSize: '0.8rem', color: '#b91c1c',
        }}>
          Save <strong>{fmt(weeklyReserve.weeklyAmount)}/week</strong> to reach your reserve by{' '}
          {weeklyReserve.target.toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' })}{' '}
          <span style={{ opacity: 0.7 }}>({weeklyReserve.weeksLeft} weeks left)</span>
        </div>
        <Link href="/tax-readiness" style={{
          padding: '0.4rem 1rem', borderRadius: 8, border: '1px solid rgba(239,68,68,0.35)',
          color: '#ef4444', fontSize: '0.82rem', fontWeight: 600, textDecoration: 'none',
          display: 'inline-block',
        }}>
          View full breakdown →
        </Link>
      </div>
    </div>
  );
}

type SyncQuota = { daily_limit: number; remaining: number; last_sync_at?: string | null };

function fmtRelative(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diff / 60_000);
  if (mins < 2) return 'just now';
  if (mins < 60) return `${mins} min ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  const days = Math.floor(hrs / 24);
  return `${days}d ago`;
}

function BankSyncStatus({ token }: { token: string }) {
  const [quota, setQuota] = useState<SyncQuota | null>(null);

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      try {
        const r = await fetch(`${BANKING_SERVICE_URL}/connections/sync-quota`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (!r.ok || cancelled) return;
        const d = (await r.json()) as SyncQuota;
        if (typeof d.daily_limit === 'number') setQuota(d);
      } catch { /* ignore */ }
    })();
    return () => { cancelled = true; };
  }, [token]);

  if (!quota) return null;

  const used = quota.daily_limit - quota.remaining;
  const pct = quota.daily_limit > 0 ? Math.round((used / quota.daily_limit) * 100) : 0;
  const barColor = quota.remaining === 0 ? '#ef4444' : quota.remaining <= 1 ? '#f59e0b' : '#22c55e';

  return (
    <div className={styles.subContainer} style={{ marginBottom: '1.25rem' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '0.5rem', marginBottom: '0.6rem' }}>
        <h2 style={{ margin: 0, fontSize: '1rem' }}>Bank Sync</h2>
        <Link href="/connect-bank" style={{
          padding: '0.35rem 0.85rem', borderRadius: 8,
          background: 'var(--lp-accent-teal)', color: '#fff',
          fontWeight: 700, fontSize: '0.8rem', textDecoration: 'none',
        }}>
          Sync now →
        </Link>
      </div>
      <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap', alignItems: 'center', fontSize: '0.85rem', color: 'var(--lp-muted)', marginBottom: '0.5rem' }}>
        <span>
          Today: <strong style={{ color: barColor }}>{quota.remaining}</strong> sync{quota.remaining !== 1 ? 's' : ''} remaining
          {' '}/ {quota.daily_limit} daily limit
        </span>
        <span style={{ color: 'var(--text-secondary)' }}>Used {used} of {quota.daily_limit} ({pct}%)</span>
      </div>
      <div style={{ height: 6, borderRadius: 999, background: 'var(--lp-border)', overflow: 'hidden' }}>
        <div style={{ height: '100%', width: `${pct}%`, background: barColor, borderRadius: 999, transition: 'width 0.4s ease' }} />
      </div>
      {quota.last_sync_at && (
        <p style={{ fontSize: '0.75rem', color: 'var(--lp-muted)', margin: '0.35rem 0 0' }}>
          Last sync: <strong>{fmtRelative(quota.last_sync_at)}</strong>{' '}
          <span style={{ opacity: 0.6 }}>
            ({new Date(quota.last_sync_at).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' })})
          </span>
        </p>
      )}
      {!quota.last_sync_at && (
        <p style={{ fontSize: '0.75rem', color: 'var(--lp-muted)', margin: '0.35rem 0 0' }}>
          No sync recorded yet — press Sync now to import transactions.
        </p>
      )}
      {quota.remaining === 0 && (
        <p style={{ fontSize: '0.75rem', color: '#ef4444', margin: '0.2rem 0 0' }}>
          Daily limit reached — resets at midnight UTC.
        </p>
      )}
    </div>
  );
}

type LatestSubmission = {
  submission_id: string;
  status: string;
  submitted_at: string;
  provider_reference: string | null;
  submission_mode: string | null;
};

function SubmissionStatus({ token }: { token: string }) {
  const [sub, setSub] = useState<LatestSubmission | null>(null);
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      try {
        const r = await fetch(`${INTEGRATIONS_SERVICE_URL}/submissions/latest`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (!r.ok || cancelled) return;
        const d = (await r.json()) as { submission: LatestSubmission | null };
        if (!cancelled) { setSub(d.submission); setLoaded(true); }
      } catch { setLoaded(true); }
    })();
    return () => { cancelled = true; };
  }, [token]);

  if (!loaded) return null;

  const statusColor = (s: string) =>
    s === 'completed' ? '#22c55e' : s === 'failed' ? '#ef4444' : s === 'pending' ? '#f59e0b' : '#94a3b8';

  return (
    <div className={styles.subContainer} style={{ marginBottom: '1.25rem' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '0.5rem', marginBottom: '0.4rem' }}>
        <h2 style={{ margin: 0, fontSize: '1rem' }}>Last HMRC Submission</h2>
        <Link href="/tax-preparation" style={{
          padding: '0.3rem 0.75rem', borderRadius: 8,
          border: '1px solid var(--lp-border)', color: 'var(--lp-muted)',
          fontWeight: 600, fontSize: '0.78rem', textDecoration: 'none',
        }}>
          Submit return →
        </Link>
      </div>
      {sub ? (
        <div style={{ fontSize: '0.82rem', color: 'var(--lp-muted)', display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
          <div style={{ display: 'flex', gap: '0.6rem', alignItems: 'center', flexWrap: 'wrap' }}>
            <span style={{
              padding: '0.15rem 0.55rem', borderRadius: 999, fontWeight: 700, fontSize: '0.7rem',
              textTransform: 'capitalize', background: `${statusColor(sub.status)}22`,
              border: `1px solid ${statusColor(sub.status)}55`, color: statusColor(sub.status),
            }}>
              {sub.status}
            </span>
            <span>{fmtRelative(sub.submitted_at)}</span>
            <span style={{ opacity: 0.6 }}>
              ({new Date(sub.submitted_at).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' })})
            </span>
          </div>
          {sub.provider_reference && (
            <span>HMRC ref: <strong style={{ fontFamily: 'monospace' }}>{sub.provider_reference}</strong></span>
          )}
          {sub.submission_mode && (
            <span>Mode: {sub.submission_mode.replace(/_/g, ' ')}</span>
          )}
        </div>
      ) : (
        <p style={{ fontSize: '0.82rem', color: 'var(--lp-muted)', margin: 0 }}>
          No submission on record — use the{' '}
          <Link href="/tax-preparation" style={{ color: 'var(--lp-accent-teal)' }}>MTD Submission</Link> page to file your first return.
        </p>
      )}
    </div>
  );
}

function ActionCenter({ token }: { token: string }) {  const [advice, setAdvice] = useState<AdviceItem | null>(null);
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

type MortgageProgressStep = { id: string; title: string; detail: string; status: 'completed' | 'current' | 'upcoming'; done: boolean };
type MortgageProgressResult = { steps: MortgageProgressStep[]; estimated_timeline_note: string | null; disclaimer: string };

function MortgageReadinessCard({ token }: { token: string }) {
  const [data, setData] = useState<MortgageProgressResult | null>(null);
  const [planGated, setPlanGated] = useState(false);

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      try {
        const r = await fetch(`${ANALYTICS_SERVICE_URL}/mortgage/progress-tracker`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
          body: JSON.stringify({ credit_focus: 'unknown', include_backend_signals: false }),
        });
        if (r.status === 403) { if (!cancelled) setPlanGated(true); return; }
        if (!r.ok) return;
        const j = await r.json() as MortgageProgressResult;
        if (!cancelled) setData(j);
      } catch { /* no-op */ }
    })();
    return () => { cancelled = true; };
  }, [token]);

  const stepDots = data?.steps.slice(0, 5) ?? [];
  const completedCount = stepDots.filter(s => s.done).length;
  const totalCount = stepDots.length || 1;
  const pct = Math.round((completedCount / totalCount) * 100);

  return (
    <div className={styles.subContainer} style={{ marginBottom: '1.25rem' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '0.5rem', marginBottom: '0.75rem' }}>
        <h2 style={{ margin: 0, fontSize: '1rem' }}>Road to Mortgage</h2>
        <Link href="/mortgage" style={{ padding: '0.35rem 0.85rem', borderRadius: 8, background: 'var(--lp-accent-teal)', color: '#fff', fontWeight: 700, fontSize: '0.8rem', textDecoration: 'none' }}>
          Open plan →
        </Link>
      </div>
      {planGated ? (
        <p style={{ fontSize: '0.82rem', color: 'var(--lp-muted)' }}>
          Mortgage readiness requires Pro or Business plan.{' '}
          <Link href="/my-subscription" style={{ color: 'var(--accent)' }}>Upgrade</Link>
        </p>
      ) : !data ? (
        <p style={{ fontSize: '0.82rem', color: 'var(--lp-muted)' }}>Loading milestones…</p>
      ) : (
        <>
          <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center', marginBottom: '0.75rem' }}>
            <div style={{ flex: 1, height: 6, borderRadius: 999, background: 'var(--lp-border)', overflow: 'hidden' }}>
              <div style={{ height: '100%', width: `${pct}%`, background: '#0d9488', borderRadius: 999, transition: 'width 0.4s' }} />
            </div>
            <span style={{ fontSize: '0.8rem', fontWeight: 700, color: '#0d9488', whiteSpace: 'nowrap' }}>{completedCount}/{totalCount} done</span>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.4rem' }}>
            {stepDots.map(step => (
              <div key={step.id} style={{ display: 'flex', gap: '0.6rem', alignItems: 'flex-start', fontSize: '0.82rem' }}>
                <span style={{ marginTop: 2, color: step.done ? '#22c55e' : step.status === 'current' ? '#818cf8' : 'var(--lp-muted)' }}>
                  {step.done ? '✓' : step.status === 'current' ? '●' : '○'}
                </span>
                <div>
                  <span style={{ fontWeight: 600, color: step.done ? '#22c55e' : step.status === 'current' ? '#818cf8' : 'var(--text-primary)' }}>{step.title}</span>
                  {step.status === 'current' && <span style={{ marginLeft: 6, fontSize: '0.72rem', color: '#818cf8' }}>← next step</span>}
                  <div style={{ fontSize: '0.75rem', color: 'var(--lp-muted)' }}>{step.detail}</div>
                </div>
              </div>
            ))}
          </div>
          {data.estimated_timeline_note && (
            <p style={{ fontSize: '0.75rem', color: 'var(--lp-muted)', marginTop: '0.75rem', marginBottom: 0 }}>{data.estimated_timeline_note}</p>
          )}
          <p style={{ fontSize: '0.7rem', color: 'var(--lp-muted)', marginTop: '0.5rem', marginBottom: 0 }}>
            Informational only — not financial or mortgage advice.
          </p>
        </>
      )}
    </div>
  );
}

export default function DashboardPage({ token }: DashboardPageProps) {
  return (
    <div className={styles.pageContainer}>
      <TrialBanner token={token} />
      <MtdComplianceBanner token={token} />
      <h1>Financial Dashboard</h1>
      <p>Your financial overview</p>
      <CisTasksStrip token={token} />
      <TaxReserveWidget token={token} />
      <BankSyncStatus token={token} />
      <SubmissionStatus token={token} />
      <ProfitPulseStrip token={token} />
      <MortgageReadinessCard token={token} />
      <ActionCenter token={token} />
      <CashFlowChart token={token} />
      <TaxCalculator token={token} />
    </div>
  );
}
