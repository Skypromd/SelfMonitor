import Head from 'next/head';
import { useRouter } from 'next/router';
import { useCallback, useEffect, useState } from 'react';
import {
    Bar,
    BarChart,
    CartesianGrid,
    Cell,
    Legend,
    Line,
    LineChart,
    Pie,
    PieChart,
    ResponsiveContainer,
    Tooltip,
    XAxis, YAxis,
} from 'recharts';
import bStyles from '../styles/Billing.module.css';
import styles from '../styles/Home.module.css';

const BILLING_URL =
  process.env.NEXT_PUBLIC_BILLING_SERVICE_URL || 'http://localhost:8016';

// ── Types ─────────────────────────────────────────────────────────────────────
interface Overview {
  mrr: number; arr: number;
  active_subscriptions: number; total_subscriptions: number;
  cancelled_subscriptions: number; churn_rate: number;
  total_invoiced: number; revenue_collected: number;
  revenue_outstanding: number; revenue_overdue: number;
  collection_rate: number;
}
interface RevenuePoint { month: string; collected: number; outstanding: number; total: number; invoices: number }
interface PlanData    { plan: string; name: string; active: number; trialing: number; cancelled: number; total: number; mrr: number }
interface InvStatusData { status: string; count: number; total: number }
interface Invoice {
  id: string; invoice_number: string; user_email: string; plan: string;
  amount: number; status: string; period_start: string; due_date: string;
  paid_at: string | null; sent_at: string | null; created_at: string;
}
interface Sub {
  id: number; email: string; plan: string; status: string;
  created_at: number; current_period_end: number | null;
}

const PLAN_AMOUNT_GBP: Record<string, number> = {
  free: 0, starter: 9, growth: 12, pro: 15, business: 25,
};

const fmt = (n: number) =>
  `£${n.toLocaleString('en-GB', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
const pct = (n: number) => `${n.toFixed(1)}%`;

const STATUS_COLOR: Record<string, string> = {
  paid: '#10b981', sent: '#3b82f6', pending: '#f59e0b',
  overdue: '#ef4444', cancelled: '#64748b', active: '#10b981',
  trialing: '#3b82f6', inactive: '#475569',
};
const PLAN_COLORS = ['#14b8a6', '#6366f1', '#f59e0b', '#ef4444', '#8b5cf6'];

// ── Badge ─────────────────────────────────────────────────────────────────────
function Badge({ status }: { status: string }) {
  const color = STATUS_COLOR[status] || '#64748b';
  return (
    <span style={{
      background: color + '22', color, border: `1px solid ${color}55`,
      borderRadius: 6, padding: '2px 8px', fontSize: 12, fontWeight: 600,
      textTransform: 'capitalize', whiteSpace: 'nowrap',
    }}>
      {status}
    </span>
  );
}

// ── DonutChart ────────────────────────────────────────────────────────────────
function DonutChart({ data }: { data: InvStatusData[] }) {
  const total = data.reduce((s, d) => s + d.count, 0);
  if (total === 0) return <p style={{ color: '#475569', fontSize: 13 }}>No data yet</p>;
  const colors = [STATUS_COLOR.paid, STATUS_COLOR.sent, STATUS_COLOR.pending, STATUS_COLOR.overdue, STATUS_COLOR.cancelled];
  let offset = 0;
  const slices = data.map((d, i) => {
    const p = d.count / total;
    const s = { ...d, p, offset, color: colors[i % colors.length] };
    offset += p;
    return s;
  });
  const r = 58, cx = 75, cy = 75, sw = 20, circ = 2 * Math.PI * r;
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 20 }}>
      <svg width={150} height={150} style={{ flexShrink: 0 }}>
        {slices.map((s, i) => (
          <circle key={i} cx={cx} cy={cy} r={r} fill="none"
            stroke={s.color} strokeWidth={sw}
            strokeDasharray={`${s.p * circ} ${circ}`}
            strokeDashoffset={-s.offset * circ}
            transform={`rotate(-90,${cx},${cy})`} />
        ))}
        <text x={cx} y={cy - 5} textAnchor="middle" fill="#e2e8f0" fontSize={20} fontWeight="700">{total}</text>
        <text x={cx} y={cy + 13} textAnchor="middle" fill="#475569" fontSize={10}>invoices</text>
      </svg>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
        {slices.map((s, i) => (
          <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 7, fontSize: 12 }}>
            <span style={{ width: 9, height: 9, borderRadius: 2, background: s.color, flexShrink: 0 }} />
            <span style={{ color: '#94a3b8', textTransform: 'capitalize', flex: 1 }}>{s.status}</span>
            <strong style={{ color: '#e2e8f0', paddingLeft: 8 }}>{s.count}</strong>
          </div>
        ))}
      </div>
    </div>
  );
}

// ── KPI Card ──────────────────────────────────────────────────────────────────
function KpiCard({ label, value, sub, accent = '#14b8a6' }: { label: string; value: string; sub?: string; accent?: string }) {
  return (
    <div className={bStyles.kpiCard} style={{ borderTop: `3px solid ${accent}` }}>
      <div className={bStyles.kpiLabel}>{label}</div>
      <div className={bStyles.kpiValue}>{value}</div>
      {sub && <div className={bStyles.kpiSub}>{sub}</div>}
    </div>
  );
}

// ══════════════════════════════════════════════════════════════════════════════
// ── Main Page ─────────────────────────────────────────────────────────────────
// ══════════════════════════════════════════════════════════════════════════════
type BillingPageProps = { token: string };

export default function BillingPage({ token }: BillingPageProps) {
  const router = useRouter();

  const [overview, setOverview]     = useState<Overview | null>(null);
  const [revenue, setRevenue]       = useState<RevenuePoint[]>([]);
  const [plans, setPlans]           = useState<PlanData[]>([]);
  const [invStatus, setInvStatus]   = useState<InvStatusData[]>([]);
  const [invoices, setInvoices]     = useState<Invoice[]>([]);
  const [subs, setSubs]             = useState<Sub[]>([]);
  const [loading, setLoading]       = useState(true);
  const [error, setError]           = useState('');
  const [tab, setTab]               = useState<'invoices' | 'subscriptions'>('invoices');
  const [invFilter, setInvFilter]   = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [actionMsg, setActionMsg]   = useState('');

  const flash = (msg: string) => { setActionMsg(msg); setTimeout(() => setActionMsg(''), 4000); };

  const fetchAll = useCallback(async () => {
    setLoading(true); setError('');
    try {
      const [ov, rv, pl, is_, inv, su] = await Promise.all([
        fetch(`${BILLING_URL}/analytics/overview`).then(r => r.json()),
        fetch(`${BILLING_URL}/analytics/revenue?months=12`).then(r => r.json()),
        fetch(`${BILLING_URL}/analytics/plans`).then(r => r.json()),
        fetch(`${BILLING_URL}/analytics/invoice-status`).then(r => r.json()),
        fetch(`${BILLING_URL}/invoices?limit=200`).then(r => r.json()),
        fetch(`${BILLING_URL}/subscriptions?limit=200`).then(r => r.json()),
      ]);
      setOverview(ov); setRevenue(rv.data || []); setPlans(pl.data || []);
      setInvStatus(is_.data || []); setInvoices(inv.items || []); setSubs(su.items || []);
    } catch {
      setError('⚠️ Cannot reach billing service (port 8016). Run start-services.ps1 first.');
    } finally { setLoading(false); }
  }, []);

  useEffect(() => { fetchAll(); }, [fetchAll]);

  const sendInvoice = async (id: string) => {
    const res = await fetch(`${BILLING_URL}/invoices/${id}/send`, { method: 'POST' });
    const d = await res.json();
    flash(d.email_sent ? '✅ Invoice emailed to customer' : '⚠️ Status updated — SMTP not configured for email dispatch');
    fetchAll();
  };

  const markPaid = async (id: string) => {
    await fetch(`${BILLING_URL}/invoices/${id}/mark-paid`, { method: 'POST' });
    flash('✅ Invoice marked as paid');
    fetchAll();
  };

  const generateBatch = async () => {
    flash('⏳ Generating monthly invoices…');
    await fetch(`${BILLING_URL}/invoices/generate-batch`, { method: 'POST' });
    flash('✅ Batch generation complete'); fetchAll();
  };

  const filteredInvoices = invoices.filter(inv =>
    (!invFilter || inv.user_email.toLowerCase().includes(invFilter.toLowerCase())) &&
    (!statusFilter || inv.status === statusFilter)
  );

  return (
    <>
      <Head><title>Billing — SelfMonitor</title></Head>
      <div style={{ background: '#0a0f1e', minHeight: '100vh', padding: '24px 32px', maxWidth: 1440, margin: '0 auto' }}>

        {/* ── Header ─────────────────────────────────────────────────────── */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 24, flexWrap: 'wrap', gap: 12 }}>
          <div>
            <h1 style={{ color: '#f1f5f9', margin: 0, fontSize: 28, fontWeight: 800 }}>💰 Billing &amp; Accounting</h1>
            <p style={{ color: '#64748b', margin: '4px 0 0', fontSize: 14 }}>
              Internal subscription control · Invoice management · Revenue analytics
            </p>
          </div>
          <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
            <button className={bStyles.btnSecondary} onClick={() => router.push('/dashboard')}>← Dashboard</button>
            <button className={bStyles.btnPrimary} onClick={generateBatch}>⚡ Generate Invoices</button>
            <button className={bStyles.btnSecondary} onClick={fetchAll}>↻ Refresh</button>
          </div>
        </div>

        {error    && <div className={bStyles.errorBanner}>{error}</div>}
        {actionMsg && <div className={bStyles.successBanner}>{actionMsg}</div>}

        {loading && !overview && (
          <div style={{ textAlign: 'center', color: '#475569', paddingTop: 80, fontSize: 16 }}>Loading billing data…</div>
        )}

        {/* ── KPI Grid ───────────────────────────────────────────────────── */}
        {overview && (
          <div className={bStyles.kpiGrid}>
            <KpiCard label="Monthly Recurring Revenue" value={fmt(overview.mrr)} sub="MRR" accent="#14b8a6" />
            <KpiCard label="Annual Recurring Revenue"  value={fmt(overview.arr)} sub="ARR" accent="#6366f1" />
            <KpiCard label="Active Subscriptions" value={String(overview.active_subscriptions)} sub={`of ${overview.total_subscriptions} total`} accent="#3b82f6" />
            <KpiCard label="Revenue Collected"    value={fmt(overview.revenue_collected)} sub={`${pct(overview.collection_rate)} collection rate`} accent="#10b981" />
            <KpiCard label="Outstanding Balance"  value={fmt(overview.revenue_outstanding)} sub="Pending + Sent" accent="#f59e0b" />
            <KpiCard label="Overdue Amount"       value={fmt(overview.revenue_overdue)} sub="Past due date" accent="#ef4444" />
            <KpiCard label="Churn Rate"           value={pct(overview.churn_rate)} sub={`${overview.cancelled_subscriptions} cancelled`} accent="#8b5cf6" />
            <KpiCard label="Total Invoiced"       value={fmt(overview.total_invoiced)} sub="All time" accent="#0ea5e9" />
          </div>
        )}

        {/* ── Charts Row 1 ───────────────────────────────────────────────── */}
        <div className={bStyles.chartsRow}>
          {/* Revenue line chart */}
          <div className={bStyles.chartCard} style={{ flex: 2 }}>
            <h3 className={bStyles.chartTitle}>📈 Revenue — Last 12 Months</h3>
            {revenue.length > 0 ? (
              <ResponsiveContainer width="100%" height={240}>
                <LineChart data={revenue} margin={{ top: 8, right: 16, left: 0, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                  <XAxis dataKey="month" tick={{ fill: '#64748b', fontSize: 11 }} />
                  <YAxis tickFormatter={v => `£${v}`} tick={{ fill: '#64748b', fontSize: 11 }} />
                  <Tooltip
                    contentStyle={{ background: '#1e293b', border: '1px solid #334155', borderRadius: 8, fontSize: 13 }}
                    labelStyle={{ color: '#e2e8f0' }}
                    formatter={(v: number) => [`£${v.toFixed(2)}`, '']}
                  />
                  <Legend wrapperStyle={{ fontSize: 12 }} />
                  <Line type="monotone" dataKey="collected"   stroke="#10b981" strokeWidth={2.5} dot={false} name="Collected" />
                  <Line type="monotone" dataKey="outstanding" stroke="#f59e0b" strokeWidth={2}   dot={false} name="Outstanding" strokeDasharray="4 2" />
                  <Line type="monotone" dataKey="total"       stroke="#6366f1" strokeWidth={1.5} dot={false} name="Total" strokeDasharray="2 2" />
                </LineChart>
              </ResponsiveContainer>
            ) : <p style={{ color: '#475569', fontSize: 13 }}>No revenue data available yet</p>}
          </div>

          {/* Invoice status donut */}
          <div className={bStyles.chartCard}>
            <h3 className={bStyles.chartTitle}>🍩 Invoice Status</h3>
            <DonutChart data={invStatus} />
            {invStatus.length > 0 && (
              <div style={{ marginTop: 14 }}>
                {invStatus.map(s => (
                  <div key={s.status} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '5px 0', borderBottom: '1px solid #1e293b' }}>
                    <Badge status={s.status} />
                    <span style={{ color: '#64748b', fontSize: 12 }}>{fmt(s.total)}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* ── Charts Row 2 ───────────────────────────────────────────────── */}
        <div className={bStyles.chartsRow}>
          {/* Plan distribution bar */}
          <div className={bStyles.chartCard} style={{ flex: 2 }}>
            <h3 className={bStyles.chartTitle}>📊 Subscriptions by Plan</h3>
            {plans.length > 0 ? (
              <ResponsiveContainer width="100%" height={220}>
                <BarChart data={plans} margin={{ top: 8, right: 16, left: 0, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                  <XAxis dataKey="name" tick={{ fill: '#64748b', fontSize: 12 }} />
                  <YAxis tick={{ fill: '#64748b', fontSize: 12 }} />
                  <Tooltip contentStyle={{ background: '#1e293b', border: '1px solid #334155', borderRadius: 8, fontSize: 13 }} labelStyle={{ color: '#e2e8f0' }} />
                  <Legend wrapperStyle={{ fontSize: 12 }} />
                  <Bar dataKey="active"    name="Active"    fill="#10b981" radius={[4,4,0,0]} />
                  <Bar dataKey="trialing"  name="Trialing"  fill="#3b82f6" radius={[4,4,0,0]} />
                  <Bar dataKey="cancelled" name="Cancelled" fill="#475569" radius={[4,4,0,0]} />
                </BarChart>
              </ResponsiveContainer>
            ) : <p style={{ color: '#475569', fontSize: 13 }}>No plan data available yet</p>}
          </div>

          {/* MRR pie */}
          <div className={bStyles.chartCard}>
            <h3 className={bStyles.chartTitle}>💎 MRR Split by Plan</h3>
            {plans.filter(p => p.mrr > 0).length > 0 ? (
              <>
                <ResponsiveContainer width="100%" height={190}>
                  <PieChart>
                    <Pie
                      data={plans.filter(p => p.mrr > 0)}
                      dataKey="mrr" nameKey="name"
                      cx="50%" cy="50%" outerRadius={75} innerRadius={35}
                      paddingAngle={3}
                    >
                      {plans.filter(p => p.mrr > 0).map((_, i) => (
                        <Cell key={i} fill={PLAN_COLORS[i % PLAN_COLORS.length]} />
                      ))}
                    </Pie>
                    <Tooltip
                      contentStyle={{ background: '#1e293b', border: '1px solid #334155', borderRadius: 8, fontSize: 13 }}
                      formatter={(v: number) => [`£${v.toFixed(2)}`, 'MRR']}
                    />
                  </PieChart>
                </ResponsiveContainer>
                <div>
                  {plans.filter(p => p.mrr > 0).map((p, i) => (
                    <div key={p.plan} style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, padding: '3px 0', alignItems: 'center' }}>
                      <span style={{ display: 'flex', alignItems: 'center', gap: 5, color: '#94a3b8' }}>
                        <span style={{ width: 8, height: 8, borderRadius: 2, background: PLAN_COLORS[i % PLAN_COLORS.length], display: 'inline-block' }} />
                        {p.name} <span style={{ color: '#475569' }}>({p.active + p.trialing} users)</span>
                      </span>
                      <strong style={{ color: '#e2e8f0' }}>{fmt(p.mrr)}</strong>
                    </div>
                  ))}
                </div>
              </>
            ) : <p style={{ color: '#475569', fontSize: 13 }}>No MRR data yet</p>}
          </div>
        </div>

        {/* ── Tabs ───────────────────────────────────────────────────────── */}
        <div className={bStyles.tabBar}>
          <button className={tab === 'invoices' ? bStyles.tabActive : bStyles.tab} onClick={() => setTab('invoices')}>
            📄 Invoices ({invoices.length})
          </button>
          <button className={tab === 'subscriptions' ? bStyles.tabActive : bStyles.tab} onClick={() => setTab('subscriptions')}>
            🔄 Subscriptions ({subs.length})
          </button>
        </div>

        {/* ── Invoices Table ─────────────────────────────────────────────── */}
        {tab === 'invoices' && (
          <div className={bStyles.tableCard}>
            <div className={bStyles.filters}>
              <input placeholder="Filter by email…" value={invFilter} onChange={e => setInvFilter(e.target.value)} className={bStyles.filterInput} />
              <select value={statusFilter} onChange={e => setStatusFilter(e.target.value)} className={bStyles.filterSelect}>
                <option value="">All statuses</option>
                {['pending','sent','paid','overdue','cancelled'].map(s => <option key={s} value={s}>{s}</option>)}
              </select>
              <span style={{ color: '#475569', fontSize: 13 }}>{filteredInvoices.length} of {invoices.length} invoices</span>
            </div>
            <div className={bStyles.tableWrap}>
              <table className={bStyles.table}>
                <thead>
                  <tr>
                    <th>Invoice #</th><th>Customer</th><th>Plan</th>
                    <th>Amount</th><th>Period</th><th>Due Date</th>
                    <th>Status</th><th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredInvoices.slice(0, 150).map(inv => (
                    <tr key={inv.id}>
                      <td style={{ fontWeight: 700, color: '#e2e8f0', fontFamily: 'monospace', fontSize: 13 }}>{inv.invoice_number}</td>
                      <td style={{ color: '#94a3b8', fontSize: 13 }}>{inv.user_email}</td>
                      <td><span style={{ color: '#14b8a6', fontSize: 11, fontWeight: 700, letterSpacing: 1 }}>{inv.plan.toUpperCase()}</span></td>
                      <td style={{ fontWeight: 700, color: '#e2e8f0' }}>{fmt(inv.amount)}</td>
                      <td style={{ color: '#64748b', fontSize: 12 }}>{inv.period_start}</td>
                      <td style={{ color: inv.status === 'overdue' ? '#ef4444' : '#64748b', fontSize: 12, fontWeight: inv.status === 'overdue' ? 600 : 400 }}>{inv.due_date}</td>
                      <td><Badge status={inv.status} /></td>
                      <td>
                        <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
                          {inv.status !== 'paid' && inv.status !== 'cancelled' && (
                            <>
                              <button className={bStyles.actionBtn} onClick={() => sendInvoice(inv.id)} title="Send email">✉️</button>
                              <button className={bStyles.actionBtnGreen} onClick={() => markPaid(inv.id)}>✓ Paid</button>
                            </>
                          )}
                          {inv.paid_at && <span style={{ color: '#475569', fontSize: 11 }}>Paid {inv.paid_at}</span>}
                        </div>
                      </td>
                    </tr>
                  ))}
                  {filteredInvoices.length === 0 && (
                    <tr><td colSpan={8} style={{ textAlign: 'center', color: '#334155', padding: 32 }}>No invoices match your filters</td></tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* ── Subscriptions Table ────────────────────────────────────────── */}
        {tab === 'subscriptions' && (
          <div className={bStyles.tableCard}>
            <div className={bStyles.tableWrap}>
              <table className={bStyles.table}>
                <thead>
                  <tr>
                    <th>#</th><th>Email</th><th>Plan</th>
                    <th>Status</th><th>MRR</th>
                    <th>Customer Since</th><th>Next Billing</th>
                  </tr>
                </thead>
                <tbody>
                  {subs.map(s => {
                    const mrr = PLAN_AMOUNT_GBP[s.plan] || 0;
                    const since = new Date(s.created_at * 1000).toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' });
                    const next = s.current_period_end
                      ? new Date(s.current_period_end * 1000).toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' })
                      : '—';
                    return (
                      <tr key={s.id}>
                        <td style={{ color: '#334155', fontSize: 12 }}>{s.id}</td>
                        <td style={{ color: '#94a3b8' }}>{s.email}</td>
                        <td><span style={{ color: '#14b8a6', fontWeight: 700, letterSpacing: 1, fontSize: 11 }}>{s.plan.toUpperCase()}</span></td>
                        <td><Badge status={s.status} /></td>
                        <td style={{ fontWeight: 700, color: (s.status === 'active' || s.status === 'trialing') ? '#10b981' : '#334155' }}>
                          {(s.status === 'active' || s.status === 'trialing') ? fmt(mrr) : '—'}
                        </td>
                        <td style={{ color: '#64748b', fontSize: 12 }}>{since}</td>
                        <td style={{ color: '#64748b', fontSize: 12 }}>{next}</td>
                      </tr>
                    );
                  })}
                  {subs.length === 0 && (
                    <tr><td colSpan={7} style={{ textAlign: 'center', color: '#334155', padding: 32 }}>No subscriptions yet</td></tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        )}

        <div style={{ height: 40 }} />
      </div>
    </>
  );
}


const API_GATEWAY_URL = process.env.NEXT_PUBLIC_API_GATEWAY_URL || 'http://localhost:8000/api';
const AUTH_SERVICE_URL = process.env.NEXT_PUBLIC_AUTH_SERVICE_URL || 'http://localhost:8001';

type BillingPageProps = {
  token: string;
};

type Subscription = {
  plan: string;
  status: string;
  trial_end?: string;
  current_period_end?: string;
};

const PLAN_NAMES: Record<string, string> = {
  free: 'Free',
  starter: 'Starter',
  growth: 'Growth',
  pro: 'Pro',
  business: 'Business',
};

const PLAN_PRICES: Record<string, string> = {
  free: '£0/mo',
  starter: '£9/mo',
  growth: '£12/mo',
  pro: '£15/mo',
  business: '£25/mo',
};

const PLAN_FEATURES: Record<string, string[]> = {
  free: [
    '1 bank connection',
    '200 transactions/month',
    'Basic tax calculator',
    'Email support',
  ],
  starter: [
    '1 bank connection',
    'Unlimited transactions',
    'AI expense categorisation',
    'Cash flow forecasting',
    'Secure cloud backup (2 GB)',
    'Email support',
  ],
  growth: [
    '2 bank connections',
    'Unlimited transactions',
    'AI categorisation + OCR receipts',
    'Tax estimation & HMRC prep',
    'Invoices & quotes',
    'Secure cloud backup (5 GB)',
    'Priority support',
  ],
  pro: [
    '3 bank connections',
    'Unlimited transactions',
    'HMRC auto-submission',
    'Smart document search',
    'Mortgage readiness reports',
    'Advanced analytics & charts',
    'Secure cloud backup (15 GB)',
    'API access',
  ],
  business: [
    'Up to 5 bank connections',
    'Everything in Pro',
    '5 team members',
    'Custom expense policies',
    'White-label reports',
    'Secure cloud backup (25 GB)',
    'Dedicated success manager',
  ],
};

const PLAN_ORDER = ['free', 'starter', 'growth', 'pro', 'business'];

function getDaysRemaining(dateStr: string): number {
  const end = new Date(dateStr);
  const now = new Date();
  const diff = end.getTime() - now.getTime();
  return Math.max(0, Math.ceil(diff / (1000 * 60 * 60 * 24)));
}

export default function BillingPage({ token }: BillingPageProps) {
  const [subscription, setSubscription] = useState<Subscription | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    const fetchSubscription = async () => {
      try {
        const response = await fetch(`${AUTH_SERVICE_URL}/subscription/me`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (!response.ok) {
          throw new Error('Failed to fetch subscription');
        }
        const data = await response.json();
        setSubscription(data);
      } catch (err: unknown) {
        const details = err instanceof Error ? err.message : 'Failed to load subscription';
        setError(details);
      } finally {
        setLoading(false);
      }
    };

    fetchSubscription();
  }, [token]);

  const currentPlan = subscription?.plan || 'free';
  const planName = PLAN_NAMES[currentPlan] || 'Free';
  const planPrice = PLAN_PRICES[currentPlan] || '£0/mo';
  const isTrialing = subscription?.status === 'trialing';
  const trialDaysRemaining = isTrialing && subscription?.trial_end
    ? getDaysRemaining(subscription.trial_end)
    : 0;

  return (
    <>
      <Head>
        <title>Billing — SelfMonitor</title>
      </Head>
      <div>
        <h1>💳 Billing &amp; Subscription</h1>

        {loading && <p style={{ color: '#94a3b8' }}>Loading subscription...</p>}
        {error && <p className={styles.error}>{error}</p>}

        {!loading && subscription && (
          <>
            {isTrialing && (
              <div style={{
                width: '100%',
                padding: '1rem 1.5rem',
                borderRadius: 12,
                background: 'rgba(13,148,136,0.15)',
                border: '1px solid rgba(13,148,136,0.3)',
                marginBottom: '1.5rem',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                gap: '1rem',
              }}>
                <span style={{ color: '#14b8a6', fontWeight: 600, fontSize: '1rem' }}>
                  🎉 {planName} trial — {trialDaysRemaining} day{trialDaysRemaining !== 1 ? 's' : ''} remaining
                </span>
                <span style={{ color: '#94a3b8', fontSize: '0.85rem' }}>
                  Ends {subscription.trial_end ? new Date(subscription.trial_end).toLocaleDateString() : ''}
                </span>
              </div>
            )}

            <div className={styles.subContainer}>
              <h2>Current Plan: {planName}</h2>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
                <div>
                  <p style={{ color: '#f1f5f9', fontSize: '2rem', fontWeight: 700, margin: 0 }}>
                    {planPrice}
                  </p>
                  <p style={{ color: '#94a3b8', fontSize: '0.9rem', margin: '0.25rem 0 0' }}>
                    Status: <span style={{
                      color: isTrialing ? '#14b8a6' : subscription.status === 'active' ? '#34d399' : '#f87171',
                      fontWeight: 600,
                      textTransform: 'capitalize',
                    }}>
                      {subscription.status}
                    </span>
                  </p>
                </div>
              </div>

              <h3 style={{ color: '#f1f5f9', fontSize: '1rem', marginTop: '1rem' }}>Plan Features</h3>
              <ul style={{ listStyle: 'none', padding: 0, margin: 0 }}>
                {(PLAN_FEATURES[currentPlan] || []).map((feature) => (
                  <li key={feature} style={{
                    padding: '0.4rem 0',
                    color: '#94a3b8',
                    fontSize: '0.9rem',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '0.5rem',
                  }}>
                    <span style={{ color: '#14b8a6' }}>✓</span> {feature}
                  </li>
                ))}
              </ul>
            </div>

            <div style={{ marginTop: '2rem' }}>
              <h2 style={{ color: '#f1f5f9', fontSize: '1.25rem', marginBottom: '1rem' }}>
                {currentPlan === 'business' ? 'Other Plans' : 'Upgrade Your Plan'}
              </h2>
              <div style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))',
                gap: '1rem',
              }}>
                {PLAN_ORDER.filter((p) => p !== currentPlan).map((plan) => (
                  <div key={plan} style={{
                    background: 'var(--lp-bg-elevated)',
                    border: '1px solid var(--lp-border)',
                    borderRadius: 12,
                    padding: '1.5rem',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '0.5rem',
                  }}>
                    <p style={{ color: '#f1f5f9', fontWeight: 700, fontSize: '1.1rem', margin: 0 }}>
                      {PLAN_NAMES[plan]}
                    </p>
                    <p style={{ color: '#14b8a6', fontWeight: 700, fontSize: '1.5rem', margin: 0 }}>
                      {PLAN_PRICES[plan]}
                    </p>
                    <ul style={{ listStyle: 'none', padding: 0, margin: '0.5rem 0', flex: 1 }}>
                      {(PLAN_FEATURES[plan] || []).slice(0, 3).map((f) => (
                        <li key={f} style={{ color: '#94a3b8', fontSize: '0.8rem', padding: '0.15rem 0' }}>
                          ✓ {f}
                        </li>
                      ))}
                      {(PLAN_FEATURES[plan] || []).length > 3 && (
                        <li style={{ color: '#64748b', fontSize: '0.8rem', padding: '0.15rem 0' }}>
                          +{(PLAN_FEATURES[plan] || []).length - 3} more features
                        </li>
                      )}
                    </ul>
                    <button
                      className={styles.button}
                      style={{ width: '100%', marginTop: '0.5rem' }}
                    >
                      {PLAN_ORDER.indexOf(plan) > PLAN_ORDER.indexOf(currentPlan) ? 'Upgrade' : 'Switch'}
                    </button>
                  </div>
                ))}
              </div>
            </div>
          </>
        )}

        {!loading && !subscription && !error && (
          <div className={styles.subContainer}>
            <h2>No Active Subscription</h2>
            <p style={{ color: '#94a3b8' }}>
              You are currently on the Free plan. Upgrade to unlock more features.
            </p>
          </div>
        )}
      </div>
    </>
  );
}
