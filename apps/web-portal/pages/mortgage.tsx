import Head from 'next/head';
import Link from 'next/link';
import { useState } from 'react';
import styles from '../styles/Home.module.css';

const ANALYTICS_SERVICE_URL = process.env.NEXT_PUBLIC_ANALYTICS_SERVICE_URL || '/api/analytics';
const TAX_SERVICE_URL = process.env.NEXT_PUBLIC_TAX_ENGINE_URL || '/api/tax';
const AFFORDABILITY_TAX_YEAR = { start: '2025-04-06', end: '2026-04-05' } as const;

type Props = { token: string };

type AffordabilityResult = {
  max_loan_from_income_gbp: number;
  monthly_payment_gbp: number;
  monthly_payment_if_rates_up_3pp_gbp: number;
  stamp_duty_england_gbp: number | null;
  deposit_pct_computed: number | null;
  ltv_pct: number | null;
  disclaimer: string;
  lender_scenarios: Array<{
    id: string;
    label: string;
    max_loan_from_income_gbp: number;
    min_deposit_pct: number;
    income_multiple: number;
    notes: string;
    illustrative_fit_score: number;
  }>;
};

type ProgressStep = {
  id: string;
  title: string;
  detail: string;
  status: 'completed' | 'current' | 'upcoming';
  done: boolean;
};

type ProgressResult = {
  steps: ProgressStep[];
  estimated_timeline_note: string | null;
  disclaimer: string;
};

function fmt(n: number) {
  return `£${Math.round(n).toLocaleString('en-GB')}`;
}

export default function MortgagePage({ token }: Props) {
  // Affordability form
  const [income, setIncome] = useState('');
  const [property, setProperty] = useState('');
  const [deposit, setDeposit] = useState('');
  const [rate, setRate] = useState('5');
  const [term, setTerm] = useState('30');
  const [employment, setEmployment] = useState<'employed' | 'self_employed'>('self_employed');
  const [ftb, setFtb] = useState(false);
  const [yearsTrading, setYearsTrading] = useState('');
  const [affordLoading, setAffordLoading] = useState(false);
  const [affordError, setAffordError] = useState('');
  const [affordResult, setAffordResult] = useState<AffordabilityResult | null>(null);

  // Road to mortgage
  const [depositSaved, setDepositSaved] = useState('');
  const [depositTarget, setDepositTarget] = useState('');
  const [monthlySave, setMonthlySave] = useState('');
  const [credit, setCredit] = useState<'unknown' | 'ok' | 'building'>('unknown');
  const [taxFiled, setTaxFiled] = useState<boolean | ''>('');
  const [progLoading, setProgLoading] = useState(false);
  const [progError, setProgError] = useState('');
  const [progResult, setProgResult] = useState<ProgressResult | null>(null);

  const fillIncomeFromTax = async () => {
    setAffordError('');
    try {
      const res = await fetch(`${TAX_SERVICE_URL}/calculate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({ start_date: AFFORDABILITY_TAX_YEAR.start, end_date: AFFORDABILITY_TAX_YEAR.end, jurisdiction: 'UK' }),
      });
      if (!res.ok) throw new Error('Tax calculation failed');
      const data = (await res.json()) as { taxable_profit?: number; total_income?: number };
      const inc = data.taxable_profit ?? data.total_income;
      if (inc == null || Number.isNaN(Number(inc))) throw new Error('No income data');
      setIncome(String(Math.max(0, Math.round(Number(inc) * 100) / 100)));
    } catch (e) {
      setAffordError(e instanceof Error ? e.message : 'Could not load income');
    }
  };

  const runAffordability = async (e: React.FormEvent) => {
    e.preventDefault();
    setAffordError('');
    setAffordResult(null);
    const incomeNum = parseFloat(income.replace(/,/g, ''));
    if (!incomeNum || incomeNum <= 0) { setAffordError('Enter a positive annual income.'); return; }
    const priceRaw = property.trim() ? parseFloat(property.replace(/,/g, '')) : NaN;
    const depRaw = deposit.trim() ? parseFloat(deposit.replace(/,/g, '')) : NaN;
    const ytRaw = yearsTrading.trim() ? parseInt(yearsTrading, 10) : NaN;
    setAffordLoading(true);
    try {
      const res = await fetch(`${ANALYTICS_SERVICE_URL}/mortgage/affordability`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({
          annual_income_gbp: incomeNum,
          annual_interest_rate_pct: parseFloat(rate) || 5,
          term_years: parseInt(term, 10) || 30,
          employment: employment === 'self_employed' ? 'self_employed' : 'employed',
          first_time_buyer: ftb,
          additional_property: false,
          credit_band: 'clean',
          property_type: 'standard_residential',
          ccj_in_past_6y: false,
          years_trading: !Number.isNaN(ytRaw) && ytRaw >= 0 ? ytRaw : null,
          ...(Number.isFinite(priceRaw) && priceRaw > 0 ? { property_value_gbp: priceRaw } : {}),
          ...(Number.isFinite(depRaw) && depRaw > 0 ? { deposit_gbp: depRaw } : {}),
        }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({})) as { detail?: string };
        throw new Error(typeof err.detail === 'string' ? err.detail : `HTTP ${res.status}`);
      }
      setAffordResult((await res.json()) as AffordabilityResult);
    } catch (e) {
      setAffordError(e instanceof Error ? e.message : 'Calculation failed');
    } finally {
      setAffordLoading(false);
    }
  };

  const runProgress = async (e: React.FormEvent) => {
    e.preventDefault();
    setProgError('');
    setProgResult(null);
    setProgLoading(true);
    try {
      const ds = parseFloat(depositSaved.replace(/,/g, ''));
      const dt = parseFloat(depositTarget.replace(/,/g, ''));
      const ms = parseFloat(monthlySave.replace(/,/g, ''));
      const res = await fetch(`${ANALYTICS_SERVICE_URL}/mortgage/progress`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({
          deposit_saved_gbp: Number.isFinite(ds) ? ds : null,
          deposit_target_gbp: Number.isFinite(dt) ? dt : null,
          monthly_savings_gbp: Number.isFinite(ms) ? ms : null,
          credit_health: credit,
          outstanding_debts: 'managing',
          self_assessment_filed: taxFiled === '' ? null : taxFiled,
          mortgage_readiness_status: 'unknown',
          years_self_employed: null,
        }),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      setProgResult((await res.json()) as ProgressResult);
    } catch (e) {
      setProgError(e instanceof Error ? e.message : 'Progress check failed');
    } finally {
      setProgLoading(false);
    }
  };

  const inputStyle = {
    padding: '0.45rem 0.75rem',
    borderRadius: 8,
    border: '1px solid var(--lp-border)',
    background: 'var(--lp-bg-elevated)',
    color: 'var(--text-primary)',
    fontSize: '0.9rem',
    width: '100%',
    boxSizing: 'border-box' as const,
  };

  const labelStyle = {
    display: 'block',
    fontSize: '0.8rem',
    color: 'var(--lp-muted)',
    marginBottom: 4,
    fontWeight: 600,
  };

  return (
    <>
      <Head>
        <title>Mortgage Advisor — MyNetTax</title>
      </Head>
      <div className={styles.pageContainer}>
        {/* Header */}
        <div className={styles.pageHeader}>
          <p className={styles.pageEyebrow}>Financial Planning</p>
          <h1 className={styles.pageTitle}>Mortgage Advisor</h1>
          <p className={styles.pageLead}>
            Estimate your borrowing power, track your path to homeownership, and prepare your mortgage documents — all in one place.
          </p>
          <div
            style={{
              padding: '0.75rem 1rem',
              borderRadius: 10,
              background: 'rgba(245,158,11,0.08)',
              border: '1px solid rgba(245,158,11,0.3)',
              fontSize: '0.8rem',
              color: 'var(--lp-muted)',
              marginTop: '0.75rem',
            }}
          >
            ⚠️ <strong>Informational only</strong> — this is not financial or mortgage advice. Always consult a qualified, FCA-authorised mortgage broker before making any financial decision.
          </div>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '1.5rem', marginBottom: '2rem' }}>
          {[
            { label: 'Affordability Calculator', icon: '🏡', desc: 'Estimate max loan and monthly payments', href: '#affordability' },
            { label: 'Road to Mortgage', icon: '🗺️', desc: 'Track your readiness milestones', href: '#progress' },
            { label: 'Document Readiness', icon: '📄', desc: 'See which documents you still need', href: '/reports#mortgage' },
            { label: 'Lender Matching', icon: '🏦', desc: '8 UK lenders assessed against your profile', href: '#affordability' },
          ].map(({ label, icon, desc, href }) => (
            <a
              key={label}
              href={href}
              style={{
                display: 'block',
                padding: '1.25rem',
                borderRadius: 12,
                border: '1px solid var(--lp-border)',
                background: 'var(--lp-bg-elevated)',
                textDecoration: 'none',
                transition: 'border-color 0.15s',
              }}
            >
              <div style={{ fontSize: '1.8rem', marginBottom: '0.5rem' }}>{icon}</div>
              <div style={{ fontWeight: 700, color: 'var(--text-primary)', marginBottom: '0.3rem', fontSize: '0.95rem' }}>{label}</div>
              <div style={{ fontSize: '0.82rem', color: 'var(--lp-muted)' }}>{desc}</div>
            </a>
          ))}
        </div>

        {/* Affordability Calculator */}
        <div className={styles.subContainer} id="affordability" style={{ marginBottom: '2rem' }}>
          <h2 style={{ margin: '0 0 1rem', fontSize: '1.1rem', fontWeight: 700 }}>Affordability Calculator</h2>
          <form onSubmit={(e) => void runAffordability(e)}>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1rem', marginBottom: '1rem' }}>
              <div>
                <label style={labelStyle}>Annual Income (£)</label>
                <input style={inputStyle} type="number" value={income} onChange={(e) => setIncome(e.target.value)} placeholder="e.g. 45000" min={0} />
                <button
                  type="button"
                  onClick={() => void fillIncomeFromTax()}
                  style={{ marginTop: 6, fontSize: '0.75rem', color: 'var(--lp-accent-teal)', background: 'none', border: 'none', cursor: 'pointer', padding: 0 }}
                >
                  Fill from tax estimate →
                </button>
              </div>
              <div>
                <label style={labelStyle}>Property Value (£, optional)</label>
                <input style={inputStyle} type="number" value={property} onChange={(e) => setProperty(e.target.value)} placeholder="e.g. 300000" min={0} />
              </div>
              <div>
                <label style={labelStyle}>Deposit (£, optional)</label>
                <input style={inputStyle} type="number" value={deposit} onChange={(e) => setDeposit(e.target.value)} placeholder="e.g. 30000" min={0} />
              </div>
              <div>
                <label style={labelStyle}>Interest Rate (%)</label>
                <input style={inputStyle} type="number" value={rate} onChange={(e) => setRate(e.target.value)} step="0.1" min={0} max={20} />
              </div>
              <div>
                <label style={labelStyle}>Mortgage Term (years)</label>
                <input style={inputStyle} type="number" value={term} onChange={(e) => setTerm(e.target.value)} min={5} max={40} />
              </div>
              <div>
                <label style={labelStyle}>Employment Type</label>
                <select style={inputStyle} value={employment} onChange={(e) => setEmployment(e.target.value as 'employed' | 'self_employed')}>
                  <option value="self_employed">Self-employed / Sole trader</option>
                  <option value="employed">PAYE employed</option>
                </select>
              </div>
              {employment === 'self_employed' && (
                <div>
                  <label style={labelStyle}>Years Self-Employed</label>
                  <input style={inputStyle} type="number" value={yearsTrading} onChange={(e) => setYearsTrading(e.target.value)} placeholder="e.g. 3" min={0} />
                </div>
              )}
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', paddingTop: '1.4rem' }}>
                <input type="checkbox" id="ftb" checked={ftb} onChange={(e) => setFtb(e.target.checked)} />
                <label htmlFor="ftb" style={{ fontSize: '0.85rem', color: 'var(--text-primary)', cursor: 'pointer' }}>First-time buyer</label>
              </div>
            </div>
            {affordError && <p style={{ color: '#ef4444', fontSize: '0.85rem', margin: '0 0 0.75rem' }}>{affordError}</p>}
            <button
              type="submit"
              disabled={affordLoading}
              style={{
                padding: '0.6rem 1.5rem', borderRadius: 10,
                background: 'var(--lp-accent-teal)', color: '#fff',
                fontWeight: 700, fontSize: '0.9rem', border: 'none', cursor: affordLoading ? 'wait' : 'pointer',
                opacity: affordLoading ? 0.7 : 1,
              }}
            >
              {affordLoading ? 'Calculating…' : 'Calculate Affordability'}
            </button>
          </form>

          {affordResult && (
            <div style={{ marginTop: '1.5rem', borderTop: '1px solid var(--lp-border)', paddingTop: '1.25rem' }}>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '1rem', marginBottom: '1rem' }}>
                {[
                  { label: 'Max loan estimate', value: fmt(affordResult.max_loan_from_income_gbp), accent: '#0d9488' },
                  { label: 'Monthly payment', value: fmt(affordResult.monthly_payment_gbp) },
                  { label: 'If rates +3pp', value: fmt(affordResult.monthly_payment_if_rates_up_3pp_gbp), accent: '#f59e0b' },
                  ...(affordResult.stamp_duty_england_gbp != null ? [{ label: 'Stamp duty (est.)', value: fmt(affordResult.stamp_duty_england_gbp) }] : []),
                  ...(affordResult.ltv_pct != null ? [{ label: 'LTV', value: `${affordResult.ltv_pct.toFixed(1)}%` }] : []),
                ].map(({ label, value, accent }) => (
                  <div
                    key={label}
                    style={{
                      padding: '0.85rem 1rem', borderRadius: 10,
                      background: accent ? `${accent}14` : 'var(--lp-bg-elevated)',
                      border: `1px solid ${accent ?? 'var(--lp-border)'}40`,
                    }}
                  >
                    <div style={{ fontSize: '0.75rem', color: 'var(--lp-muted)', marginBottom: 4 }}>{label}</div>
                    <div style={{ fontSize: '1.2rem', fontWeight: 800, color: accent ?? 'var(--text-primary)' }}>{value}</div>
                  </div>
                ))}
              </div>

              {affordResult.lender_scenarios?.length > 0 && (
                <>
                  <h3 style={{ fontSize: '0.95rem', fontWeight: 700, margin: '1rem 0 0.75rem' }}>Illustrative Lender Matches</h3>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                    {affordResult.lender_scenarios.slice(0, 5).map((ls) => (
                      <div
                        key={ls.id}
                        style={{
                          display: 'flex', justifyContent: 'space-between', flexWrap: 'wrap', gap: '0.5rem',
                          padding: '0.65rem 0.85rem', borderRadius: 8,
                          border: '1px solid var(--lp-border)', background: 'var(--lp-bg-elevated)',
                          fontSize: '0.85rem',
                        }}
                      >
                        <span style={{ fontWeight: 600, color: 'var(--text-primary)' }}>{ls.label}</span>
                        <span style={{ color: 'var(--lp-muted)' }}>
                          Max {fmt(ls.max_loan_from_income_gbp)} · {ls.income_multiple}× · Min {ls.min_deposit_pct}% deposit
                        </span>
                        <span
                          style={{
                            padding: '2px 8px', borderRadius: 999, fontSize: '0.72rem', fontWeight: 700,
                            background: ls.illustrative_fit_score >= 7 ? 'rgba(34,197,94,0.15)' : 'rgba(245,158,11,0.15)',
                            color: ls.illustrative_fit_score >= 7 ? '#22c55e' : '#f59e0b',
                          }}
                        >
                          Fit {ls.illustrative_fit_score}/10
                        </span>
                      </div>
                    ))}
                  </div>
                </>
              )}

              <p style={{ fontSize: '0.75rem', color: 'var(--lp-muted)', marginTop: '1rem', lineHeight: 1.5 }}>
                {affordResult.disclaimer}
              </p>
            </div>
          )}
        </div>

        {/* Road to Mortgage */}
        <div className={styles.subContainer} id="progress" style={{ marginBottom: '2rem' }}>
          <h2 style={{ margin: '0 0 1rem', fontSize: '1.1rem', fontWeight: 700 }}>Road to Mortgage</h2>
          <form onSubmit={(e) => void runProgress(e)}>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1rem', marginBottom: '1rem' }}>
              <div>
                <label style={labelStyle}>Deposit saved (£)</label>
                <input style={inputStyle} type="number" value={depositSaved} onChange={(e) => setDepositSaved(e.target.value)} placeholder="e.g. 15000" min={0} />
              </div>
              <div>
                <label style={labelStyle}>Deposit target (£)</label>
                <input style={inputStyle} type="number" value={depositTarget} onChange={(e) => setDepositTarget(e.target.value)} placeholder="e.g. 30000" min={0} />
              </div>
              <div>
                <label style={labelStyle}>Monthly saving (£)</label>
                <input style={inputStyle} type="number" value={monthlySave} onChange={(e) => setMonthlySave(e.target.value)} placeholder="e.g. 800" min={0} />
              </div>
              <div>
                <label style={labelStyle}>Credit health</label>
                <select style={inputStyle} value={credit} onChange={(e) => setCredit(e.target.value as 'unknown' | 'ok' | 'building')}>
                  <option value="unknown">Not sure</option>
                  <option value="ok">Good / Clean</option>
                  <option value="building">Building up</option>
                </select>
              </div>
              <div>
                <label style={labelStyle}>Self-assessment filed?</label>
                <select
                  style={inputStyle}
                  value={taxFiled === '' ? '' : String(taxFiled)}
                  onChange={(e) => setTaxFiled(e.target.value === '' ? '' : e.target.value === 'true')}
                >
                  <option value="">Not sure</option>
                  <option value="true">Yes, up to date</option>
                  <option value="false">No / behind</option>
                </select>
              </div>
            </div>
            {progError && <p style={{ color: '#ef4444', fontSize: '0.85rem', margin: '0 0 0.75rem' }}>{progError}</p>}
            <button
              type="submit"
              disabled={progLoading}
              style={{
                padding: '0.6rem 1.5rem', borderRadius: 10,
                background: 'linear-gradient(135deg,#7c3aed,#6366f1)', color: '#fff',
                fontWeight: 700, fontSize: '0.9rem', border: 'none', cursor: progLoading ? 'wait' : 'pointer',
                opacity: progLoading ? 0.7 : 1,
              }}
            >
              {progLoading ? 'Loading…' : 'Check My Progress'}
            </button>
          </form>

          {progResult && (
            <div style={{ marginTop: '1.5rem', borderTop: '1px solid var(--lp-border)', paddingTop: '1.25rem' }}>
              {progResult.estimated_timeline_note && (
                <p style={{ fontSize: '0.88rem', color: 'var(--lp-muted)', marginBottom: '1rem' }}>
                  {progResult.estimated_timeline_note}
                </p>
              )}
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.6rem' }}>
                {progResult.steps.map((step) => (
                  <div
                    key={step.id}
                    style={{
                      display: 'flex', gap: '0.85rem', alignItems: 'flex-start',
                      padding: '0.75rem 1rem', borderRadius: 10,
                      border: `1px solid ${step.status === 'completed' ? 'rgba(34,197,94,0.3)' : step.status === 'current' ? 'rgba(99,102,241,0.4)' : 'var(--lp-border)'}`,
                      background: step.status === 'completed' ? 'rgba(34,197,94,0.05)' : step.status === 'current' ? 'rgba(99,102,241,0.06)' : 'transparent',
                    }}
                  >
                    <span style={{ fontSize: '1.1rem', lineHeight: 1 }}>
                      {step.done ? '✓' : step.status === 'current' ? '●' : '○'}
                    </span>
                    <div>
                      <div style={{
                        fontWeight: 700, fontSize: '0.9rem',
                        color: step.status === 'completed' ? '#22c55e' : step.status === 'current' ? '#818cf8' : 'var(--text-primary)',
                      }}>
                        {step.title}
                      </div>
                      <div style={{ fontSize: '0.8rem', color: 'var(--lp-muted)', marginTop: 2 }}>{step.detail}</div>
                    </div>
                  </div>
                ))}
              </div>
              <p style={{ fontSize: '0.72rem', color: 'var(--lp-muted)', marginTop: '1rem', lineHeight: 1.5 }}>
                {progResult.disclaimer}
              </p>
            </div>
          )}
        </div>

        {/* Document readiness CTA */}
        <div className={styles.subContainer} style={{ marginBottom: '1.5rem' }}>
          <h2 style={{ margin: '0 0 0.75rem', fontSize: '1rem', fontWeight: 700 }}>Document Readiness</h2>
          <p style={{ fontSize: '0.88rem', color: 'var(--lp-muted)', margin: '0 0 1rem' }}>
            Upload your SA302, bank statements, payslips, and ID to check which lenders you qualify for and export a complete mortgage pack.
          </p>
          <Link
            href="/reports"
            style={{
              display: 'inline-block',
              padding: '0.6rem 1.4rem', borderRadius: 10,
              border: '1px solid var(--lp-border)',
              color: 'var(--lp-muted)', fontWeight: 600, fontSize: '0.88rem',
              textDecoration: 'none', background: 'var(--lp-bg-elevated)',
            }}
          >
            View Full Mortgage Readiness in Reports →
          </Link>
        </div>

        {/* Broker Bundle */}
        <BrokerBundlePanel token={token} analyticsUrl={ANALYTICS_SERVICE_URL} />
      </div>
    </>
  );
}

function BrokerBundlePanel({ token, analyticsUrl }: { token: string; analyticsUrl: string }) {
  const [mortgageType, setMortgageType] = useState('residential_purchase');
  const [downloading, setDownloading] = useState(false);
  const [dlErr, setDlErr] = useState('');

  const handleDownloadBundle = async () => {
    setDlErr('');
    setDownloading(true);
    try {
      const r = await fetch(`${analyticsUrl}/mortgage/broker-bundle.zip?mortgage_type=${encodeURIComponent(mortgageType)}&employment_profile=sole_trader`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!r.ok) {
        const j = await r.json().catch(() => ({})) as { detail?: string };
        setDlErr(j.detail || `Error ${r.status}`);
        return;
      }
      const blob = await r.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `broker-bundle-${mortgageType}.zip`;
      a.click();
      URL.revokeObjectURL(url);
    } catch {
      setDlErr('Download failed — please try again.');
    } finally {
      setDownloading(false);
    }
  };

  return (
    <div style={{ marginBottom: '1.5rem', padding: '1.25rem', borderRadius: 14, border: '1px solid rgba(99,102,241,0.3)', background: 'rgba(99,102,241,0.04)' }}>
      <h2 style={{ margin: '0 0 0.5rem', fontSize: '1rem', fontWeight: 700 }}>Broker Bundle</h2>
      <p style={{ fontSize: '0.85rem', color: 'var(--lp-muted)', margin: '0 0 1rem', lineHeight: 1.55 }}>
        Package your CIS records, SA302 evidence, and income/expenditure summary into a single ZIP for your mortgage broker.
        Your <Link href="/evidence-pack" style={{ color: 'var(--lp-accent-teal)' }}>Evidence Pack</Link> is automatically included.
      </p>

      {/* Multilingual readiness explanation */}
      <details style={{ marginBottom: '1rem' }}>
        <summary style={{ fontSize: '0.82rem', color: 'var(--lp-muted)', cursor: 'pointer', fontWeight: 600 }}>What self-employed applicants need (EN · RU · PL)</summary>
        <div style={{ marginTop: '0.75rem', display: 'flex', flexDirection: 'column', gap: '0.5rem', paddingLeft: '0.5rem' }}>
          <div>
            <span style={{ fontSize: '0.75rem', fontWeight: 700 }}>🇬🇧 English —</span>
            <span style={{ fontSize: '0.78rem', color: 'var(--lp-muted)' }}> UK mortgage lenders typically require 2 years of SA302s + tax year overviews, 3 months' bank statements, and proof of identity/address. CIS subcontractors should provide CIS deduction statements alongside.</span>
          </div>
          <div>
            <span style={{ fontSize: '0.75rem', fontWeight: 700 }}>🇷🇺 Русский —</span>
            <span style={{ fontSize: '0.78rem', color: 'var(--lp-muted)' }}> Для самозанятых заёмщиков в Великобритании, как правило, требуются SA302 за 2 года, обзоры налогового года, выписки банковского счёта за 3 месяца и удостоверение личности. Подрядчики CIS должны приложить справки об удержанном налоге.</span>
          </div>
          <div>
            <span style={{ fontSize: '0.75rem', fontWeight: 700 }}>🇵🇱 Polski —</span>
            <span style={{ fontSize: '0.78rem', color: 'var(--lp-muted)' }}> Kredytodawcy hipoteczni w Wielkiej Brytanii zwykle wymagają SA302 za 2 lata, przeglądów roku podatkowego, wyciągów bankowych za 3 miesiące oraz dokumentów tożsamości. Podwykonawcy CIS powinni dołączyć zaświadczenia o potrąconym podatku CIS.</span>
          </div>
        </div>
      </details>

      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.75rem', alignItems: 'flex-end' }}>
        <div>
          <label style={{ display: 'block', fontSize: '0.78rem', color: 'var(--lp-muted)', marginBottom: 4, fontWeight: 600 }}>Mortgage type</label>
          <select
            value={mortgageType}
            onChange={(e) => setMortgageType(e.target.value)}
            style={{ padding: '0.45rem 0.75rem', borderRadius: 8, border: '1px solid var(--lp-border)', background: 'var(--lp-bg-elevated)', color: 'var(--text-primary)', fontSize: '0.88rem' }}
          >
            <option value="residential_purchase">Residential purchase</option>
            <option value="residential_remortgage">Residential remortgage</option>
            <option value="buy_to_let_purchase">Buy-to-let purchase</option>
            <option value="buy_to_let_remortgage">Buy-to-let remortgage</option>
            <option value="help_to_buy">Help to Buy</option>
            <option value="shared_ownership">Shared ownership</option>
          </select>
        </div>
        <button
          type="button"
          onClick={() => void handleDownloadBundle()}
          disabled={downloading}
          style={{
            padding: '0.55rem 1.25rem', borderRadius: 8,
            background: 'linear-gradient(135deg,#7c3aed,#6366f1)', color: '#fff',
            fontWeight: 700, fontSize: '0.88rem', border: 'none',
            cursor: downloading ? 'not-allowed' : 'pointer', opacity: downloading ? 0.7 : 1,
          }}
        >
          {downloading ? 'Preparing ZIP…' : 'Download broker bundle ZIP'}
        </button>
        <Link href="/evidence-pack" style={{ padding: '0.55rem 1.1rem', borderRadius: 8, border: '1px solid rgba(99,102,241,0.5)', color: '#818cf8', fontWeight: 700, fontSize: '0.88rem', textDecoration: 'none' }}>
          View evidence pack
        </Link>
      </div>
      {dlErr && <p style={{ color: '#ef4444', fontSize: '0.82rem', marginTop: '0.6rem', marginBottom: 0 }}>{dlErr}</p>}
      <p style={{ fontSize: '0.7rem', color: 'var(--lp-muted)', marginTop: '0.75rem', marginBottom: 0, lineHeight: 1.5 }}>
        ⚠️ Informational only — not regulated mortgage or financial advice. Verify all figures with a qualified, FCA-authorised mortgage broker before submission.
      </p>
    </div>
  );
}
