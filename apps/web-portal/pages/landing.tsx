import { motion, useInView } from 'framer-motion';
import {
    BarChart3, Bot, Briefcase, Calculator, CalendarClock,
    Check, ClipboardList, Code2, FileCheck, FileText, FolderLock,
    Globe, KeyRound, Landmark, Lightbulb, Lock,
    Palette, PiggyBank, Plug2, Receipt, ScanLine,
    ScrollText, ShieldAlert, ShieldCheck,
    Smartphone,
    Target, TrendingUp, Users, Zap
} from 'lucide-react';
import dynamic from 'next/dynamic';
import Head from 'next/head';
import Link from 'next/link';
import { useRouter } from 'next/router';
import { useEffect, useRef, useState } from 'react';
import styles from '../styles/Landing.module.css';

const LOCALE_FLAGS: Record<string, string> = {
  'en-GB': '🇬🇧',
  'pl-PL': '🇵🇱',
  'ro-RO': '🇷🇴',
  'uk-UA': '🇺🇦',
  'ru-RU': '🇷🇺',
  'es-ES': '🇪🇸',
  'it-IT': '🇮🇹',
  'pt-PT': '🇵🇹',
  'tr-TR': '🇹🇷',
  'bn-BD': '🇧🇩',
};

const CashFlowChart = dynamic(() => import('../components/charts/CashFlowChart'), { ssr: false });
const ExpenseChart = dynamic(() => import('../components/charts/ExpenseChart'), { ssr: false });
const SavingsChart = dynamic(() => import('../components/charts/SavingsChart'), { ssr: false });

const fadeUp = {
  initial: { opacity: 0, y: 40 },
  whileInView: { opacity: 1, y: 0 },
  transition: { duration: 0.7 },
  viewport: { once: true, margin: '-50px' },
};

const staggerContainer = {
  initial: {},
  whileInView: { transition: { staggerChildren: 0.15 } },
  viewport: { once: true },
};

const staggerItem = {
  initial: { opacity: 0, y: 30 },
  whileInView: { opacity: 1, y: 0 },
  transition: { duration: 0.5 },
};

function AnimatedCounter({ target, prefix = '', suffix = '' }: { target: number; prefix?: string; suffix?: string }) {
  const ref = useRef(null);
  const isInView = useInView(ref, { once: true });
  const [count, setCount] = useState(0);

  useEffect(() => {
    if (isInView) {
      let start = 0;
      const duration = 2000;
      const step = target / (duration / 16);
      const timer = setInterval(() => {
        start += step;
        if (start >= target) {
          setCount(target);
          clearInterval(timer);
        } else {
          setCount(Math.floor(start));
        }
      }, 16);
      return () => clearInterval(timer);
    }
  }, [isInView, target]);

  return <span ref={ref}>{prefix}{count.toLocaleString()}{suffix}</span>;
}

const testimonials = [
  {
    name: 'Sarah K.',
    role: 'Freelance Developer, London',
    initials: 'SK',
    quote: 'SelfMonitor saved me 6 hours every week. My tax return was filed in 3 clicks. I wish I had found this 5 years ago.',
    stars: 5,
  },
  {
    name: 'Marcus T.',
    role: 'Sole Trader, Manchester',
    initials: 'MT',
    quote: 'The receipt scanner is magic. I just photograph everything and the AI sorts it out. My accountant was impressed with my records.',
    stars: 5,
  },
  {
    name: 'Priya D.',
    role: 'Design Consultant, Birmingham',
    initials: 'PD',
    quote: 'Cash flow forecasting changed my business. I can now plan 30 days ahead and never worry about running out of money.',
    stars: 5,
  },
];

export default function LandingPage() {
  const router = useRouter();
  const { locales, locale: activeLocale } = router;
  const [langOpen, setLangOpen] = useState(false);

  return (
    <>
      <Head>
        <title>SelfMonitor — Financial Freedom for the Self-Employed</title>
        <meta
          name="description"
          content="AI-powered banking, taxes, and insights for UK freelancers and sole traders. From receipt to HMRC submission in minutes."
        />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
      </Head>

      <div className={styles.page}>
        {/* Sign In button — fixed top-left */}
        <div style={{ position: 'fixed', top: '1rem', left: '1.5rem', zIndex: 1000 }}>
          <Link
            href="/"
            style={{
              display: 'inline-block',
              padding: '0.5rem 1.2rem',
              borderRadius: '8px',
              background: 'var(--lp-accent-teal)',
              color: '#fff',
              fontWeight: 600,
              fontSize: '0.9rem',
              textDecoration: 'none',
              boxShadow: '0 2px 8px rgba(0,0,0,0.2)',
            }}
          >
            Sign In
          </Link>
        </div>
        <div style={{
          position: 'fixed',
          top: '1rem',
          right: '1.5rem',
          zIndex: 1000,
        }}>
          <button
            onClick={() => setLangOpen(!langOpen)}
            style={{
              background: 'rgba(30,41,59,0.85)',
              backdropFilter: 'blur(8px)',
              border: '1px solid var(--lp-border)',
              borderRadius: 10,
              cursor: 'pointer',
              fontSize: '1.3rem',
              padding: '0.5rem 0.75rem',
              display: 'flex',
              alignItems: 'center',
              gap: '0.5rem',
              color: 'var(--lp-text)',
            }}
          >
            {LOCALE_FLAGS[activeLocale || 'en-GB'] || '🌐'}
            <span style={{ fontSize: '0.8rem', color: 'var(--lp-text-muted)' }}>
              {(activeLocale || 'en-GB').split('-')[0].toUpperCase()}
            </span>
            <span style={{ fontSize: '0.65rem', color: 'var(--lp-text-muted)' }}>▼</span>
          </button>
          {langOpen && (
            <div style={{
              position: 'absolute',
              top: '100%',
              right: 0,
              marginTop: '0.5rem',
              background: 'var(--lp-bg-card)',
              border: '1px solid var(--lp-border)',
              borderRadius: 10,
              padding: '0.5rem',
              minWidth: '140px',
              maxHeight: '300px',
              overflowY: 'auto',
              zIndex: 1001,
            }}>
              {locales?.map(loc => (
                <Link
                  href={router.pathname}
                  key={loc}
                  locale={loc}
                  onClick={() => {
                    localStorage.setItem('preferredLocale', loc);
                    setLangOpen(false);
                  }}
                >
                  <div style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '0.75rem',
                    padding: '0.5rem 0.75rem',
                    borderRadius: 6,
                    cursor: 'pointer',
                    background: loc === activeLocale ? 'rgba(13,148,136,0.15)' : 'transparent',
                    color: loc === activeLocale ? 'var(--lp-accent-teal)' : 'var(--lp-text)',
                    fontSize: '0.85rem',
                  }}>
                    <span style={{ fontSize: '1.1rem' }}>{LOCALE_FLAGS[loc] || '🌐'}</span>
                    <span>{loc.split('-')[0].toUpperCase()}</span>
                  </div>
                </Link>
              ))}
            </div>
          )}
        </div>
        {/* ====== HERO ====== */}
        <section className={styles.hero}>
          <div className={styles.container}>
            <motion.div
              initial={{ opacity: 0, y: 30 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.8 }}
            >
              <h1 className={styles.heroHeadline}>
                Financial Freedom for the Self-Employed
              </h1>
              <p className={styles.heroSub}>
                AI-powered banking, taxes, and insights — all in one platform.
                From receipt to HMRC submission in minutes, not hours.
              </p>
            </motion.div>

            <motion.div
              className={styles.heroButtons}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.7, delay: 0.3 }}
            >
              <Link href="/register?plan=pro" className={styles.btnPrimary}>
                Start Free
              </Link>
              <Link href="/" className={styles.btnSecondary}>
                Sign In
              </Link>
              <a href="#pricing" className={styles.btnSecondary}>
                See Pricing
              </a>
            </motion.div>

            <motion.div
              className={styles.storeButtons}
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ duration: 0.6, delay: 0.5 }}
            >
              <a href="https://apps.apple.com/app/selfmonitor" className={styles.storeButton} target="_blank" rel="noopener noreferrer">
                <span className={styles.storeIcon}>🍎</span>
                <span className={styles.storeText}>
                  <small>Download on the</small>
                  <strong>App Store</strong>
                </span>
              </a>
              <a href="https://play.google.com/store/apps/details?id=com.selfmonitor.app" className={styles.storeButton} target="_blank" rel="noopener noreferrer">
                <span className={styles.storeIcon}>▶️</span>
                <span className={styles.storeText}>
                  <small>Get it on</small>
                  <strong>Google Play</strong>
                </span>
              </a>
            </motion.div>

            <motion.div
              className={styles.trustPills}
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ duration: 0.6, delay: 0.6 }}
            >
              <span className={styles.trustPill}><Lock size={13} strokeWidth={2} /> Bank-Grade Security</span>
              <span className={styles.trustPill}>🇬🇧 HMRC Compliant</span>
              <span className={styles.trustPill}><Zap size={13} strokeWidth={2} /> AI-Powered</span>
              <span className={styles.trustPill}><Smartphone size={13} strokeWidth={2} /> Web + Mobile</span>
            </motion.div>

            <motion.div
              className={styles.statsRow}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.7, delay: 0.8 }}
            >
              <div className={styles.statItem}>
                <span className={styles.statValue}><AnimatedCounter target={23} suffix="+" /></span>
                <span className={styles.statLabel}>Services</span>
              </div>
              <div className={styles.statItem}>
                <span className={styles.statValue}>2FA</span>
                <span className={styles.statLabel}>Security</span>
              </div>
              <div className={styles.statItem}>
                <span className={styles.statValue}><AnimatedCounter target={10} /></span>
                <span className={styles.statLabel}>Languages</span>
              </div>
              <div className={styles.statItem}>
                <span className={styles.statValue}><AnimatedCounter target={99} suffix=".9%" /></span>
                <span className={styles.statLabel}>Uptime</span>
              </div>
            </motion.div>
          </div>
        </section>

        {/* ====== CHALLENGE ====== */}
        <section className={styles.sectionElevated}>
          <div className={styles.container}>
            <motion.div {...fadeUp}>
              <h2 className={styles.sectionHeading}>
                Self-Employment Shouldn&rsquo;t Mean Self-Struggle
              </h2>
            </motion.div>

            <motion.div className={styles.grid3} {...staggerContainer}>
              <motion.div className={`${styles.card} ${styles.cardOnElevated}`} {...staggerItem}>
                <ClipboardList className={styles.cardIcon} />
                <h3 className={styles.cardTitle}>
                  Hours lost on manual bookkeeping
                </h3>
                <p className={styles.cardDesc}>
                  Spreadsheets, bank exports, copy-paste — the admin never ends.
                  <span className={styles.challengeHighlight}>
                    Average freelancer spends 5 hrs/week on admin
                  </span>
                </p>
              </motion.div>

              <motion.div className={`${styles.card} ${styles.cardOnElevated}`} {...staggerItem}>
                <PiggyBank className={styles.cardIcon} />
                <h3 className={styles.cardTitle}>Missed tax deductions</h3>
                <p className={styles.cardDesc}>
                  Without AI categorisation, legitimate expenses slip through the
                  cracks.
                  <span className={styles.challengeHighlight}>
                    UK freelancers overpay £1,200/year in taxes on average
                  </span>
                </p>
              </motion.div>

              <motion.div className={`${styles.card} ${styles.cardOnElevated}`} {...staggerItem}>
                <FileText className={styles.cardIcon} />
                <h3 className={styles.cardTitle}>Receipts in a shoebox</h3>
                <p className={styles.cardDesc}>
                  Paper receipts fade. Email receipts get buried. Audits happen.
                  <span className={styles.challengeHighlight}>
                    HMRC requires 5 years of records — can you find them?
                  </span>
                </p>
              </motion.div>
            </motion.div>
          </div>
        </section>

        {/* ====== CHARTS: SEE YOUR FINANCES COME ALIVE ====== */}
        <section className={styles.section}>
          <div className={styles.container}>
            <motion.div {...fadeUp}>
              <h2 className={styles.sectionHeading}>
                See Your Finances Come Alive
              </h2>
              <p className={styles.sectionSub}>
                Real-time charts. AI insights. Zero manual work.
              </p>
            </motion.div>

            <motion.div className={styles.chartsGrid} {...staggerContainer}>
              <motion.div className={styles.chartCard} {...staggerItem}>
                <p className={styles.chartLabel}>Cash Flow Trend</p>
                <CashFlowChart />
                <p className={styles.chartCaption}>
                  Track 12-month cash flow trends with AI-powered forecasting
                </p>
              </motion.div>

              <motion.div className={styles.chartCard} {...staggerItem}>
                <p className={styles.chartLabel}>Expense Breakdown</p>
                <ExpenseChart />
                <p className={styles.chartCaption}>
                  AI categorizes every expense automatically — see where your money goes
                </p>
              </motion.div>

              <motion.div className={styles.chartCard} {...staggerItem}>
                <p className={styles.chartLabel}>Tax Savings</p>
                <SavingsChart />
                <p className={styles.chartCaption}>
                  Average user saves £2,000/year in identified deductions
                </p>
              </motion.div>
            </motion.div>
          </div>
        </section>

        {/* ====== SOLUTIONS ====== */}
        <section id="features" className={styles.sectionElevated}>
          <div className={styles.container}>
            <motion.div {...fadeUp}>
              <h2 className={styles.sectionHeading}>
                One Platform. Every Tool You Need.
              </h2>
              <p className={styles.sectionSub}>
                23+ microservices working together — from bank connection to tax submission, invoicing to fraud detection.
              </p>
            </motion.div>

            {/* Row 1 — Banking & Transactions */}
            <motion.div {...fadeUp} style={{ marginBottom: '0.5rem' }}>
              <p style={{ color: 'var(--lp-accent-teal)', fontWeight: 700, fontSize: '0.75rem', letterSpacing: '0.12em', textTransform: 'uppercase', marginBottom: '1rem' }}>
                Banking &amp; Transactions
              </p>
            </motion.div>
            <motion.div className={styles.grid3} {...staggerContainer} style={{ marginBottom: '2.5rem' }}>
              <motion.div className={`${styles.card} ${styles.cardOnElevated}`} {...staggerItem}>
                <Landmark className={styles.cardIcon} />
                <h3 className={styles.cardTitle}>Open Banking Connector</h3>
                <p className={styles.cardDesc}>
                  Connect to 20,000+ banks globally via secure Open Banking APIs. Transactions sync automatically — no CSV exports.
                </p>
              </motion.div>

              <motion.div className={`${styles.card} ${styles.cardOnElevated}`} {...staggerItem}>
                <Bot className={styles.cardIcon} />
                <h3 className={styles.cardTitle}>AI Categorization</h3>
                <p className={styles.cardDesc}>
                  Every transaction categorized instantly by ML. Learns your patterns — 97%+ accuracy from week one.
                </p>
              </motion.div>

              <motion.div className={`${styles.card} ${styles.cardOnElevated}`} {...staggerItem}>
                <ShieldCheck className={styles.cardIcon} />
                <h3 className={styles.cardTitle}>Fraud Detection</h3>
                <p className={styles.cardDesc}>
                  Real-time ML anomaly detection. Every transaction scored for risk. Suspicious activity alerted in seconds.
                </p>
              </motion.div>
            </motion.div>

            {/* Row 2 — Tax & Compliance */}
            <motion.div {...fadeUp} style={{ marginBottom: '0.5rem' }}>
              <p style={{ color: 'var(--lp-accent-teal)', fontWeight: 700, fontSize: '0.75rem', letterSpacing: '0.12em', textTransform: 'uppercase', marginBottom: '1rem' }}>
                Tax &amp; Compliance
              </p>
            </motion.div>
            <motion.div className={styles.grid3} {...staggerContainer} style={{ marginBottom: '2.5rem' }}>
              <motion.div className={`${styles.card} ${styles.cardOnElevated}`} {...staggerItem}>
                <Calculator className={styles.cardIcon} />
                <h3 className={styles.cardTitle}>Tax Engine</h3>
                <p className={styles.cardDesc}>
                  Real-time UK Income Tax, National Insurance, and VAT calculations. One-click HMRC MTD submission — fully Making Tax Digital compliant.
                </p>
              </motion.div>

              <motion.div className={`${styles.card} ${styles.cardOnElevated}`} {...staggerItem}>
                <CalendarClock className={styles.cardIcon} />
                <h3 className={styles.cardTitle}>Tax Calendar &amp; Deadlines</h3>
                <p className={styles.cardDesc}>
                  Never miss a deadline. Smart calendar tracks Self Assessment, VAT quarters, and payments on account with push reminders.
                </p>
              </motion.div>

              <motion.div className={`${styles.card} ${styles.cardOnElevated}`} {...staggerItem}>
                <FileCheck className={styles.cardIcon} />
                <h3 className={styles.cardTitle}>Compliance &amp; Audit Trail</h3>
                <p className={styles.cardDesc}>
                  Full GDPR consent management, AML checks, and immutable audit log. Every action timestamped — HMRC audit-ready in one click.
                </p>
              </motion.div>
            </motion.div>

            {/* Row 3 — Documents & Invoicing */}
            <motion.div {...fadeUp} style={{ marginBottom: '0.5rem' }}>
              <p style={{ color: 'var(--lp-accent-teal)', fontWeight: 700, fontSize: '0.75rem', letterSpacing: '0.12em', textTransform: 'uppercase', marginBottom: '1rem' }}>
                Documents &amp; Invoicing
              </p>
            </motion.div>
            <motion.div className={styles.grid3} {...staggerContainer} style={{ marginBottom: '2.5rem' }}>
              <motion.div className={`${styles.card} ${styles.cardOnElevated}`} {...staggerItem}>
                <ScanLine className={styles.cardIcon} />
                <h3 className={styles.cardTitle}>Receipt Scanner (OCR)</h3>
                <p className={styles.cardDesc}>
                  Snap a photo on mobile. AI extracts vendor, amount, VAT, and date in seconds. Receipts stored encrypted for 5+ years.
                </p>
              </motion.div>

              <motion.div className={`${styles.card} ${styles.cardOnElevated}`} {...staggerItem}>
                <Receipt className={styles.cardIcon} />
                <h3 className={styles.cardTitle}>Invoice Management</h3>
                <p className={styles.cardDesc}>
                  Create professional invoices in seconds. Send, track, and automatically reconcile payments. Overdue reminders sent automatically.
                </p>
              </motion.div>

              <motion.div className={`${styles.card} ${styles.cardOnElevated}`} {...staggerItem}>
                <FolderLock className={styles.cardIcon} />
                <h3 className={styles.cardTitle}>Document Vault</h3>
                <p className={styles.cardDesc}>
                  Encrypted S3 storage for contracts, receipts, and certificates. Smart full-text search — find any document in under 2 seconds.
                </p>
              </motion.div>
            </motion.div>

            {/* Row 4 — Analytics & AI */}
            <motion.div {...fadeUp} style={{ marginBottom: '0.5rem' }}>
              <p style={{ color: 'var(--lp-accent-teal)', fontWeight: 700, fontSize: '0.75rem', letterSpacing: '0.12em', textTransform: 'uppercase', marginBottom: '1rem' }}>
                Analytics &amp; AI Intelligence
              </p>
            </motion.div>
            <motion.div className={styles.grid3} {...staggerContainer} style={{ marginBottom: '2.5rem' }}>
              <motion.div className={`${styles.card} ${styles.cardOnElevated}`} {...staggerItem}>
                <TrendingUp className={styles.cardIcon} />
                <h3 className={styles.cardTitle}>Cash Flow Forecasting</h3>
                <p className={styles.cardDesc}>
                  30–90 day AI predictions. Scenario modelling — see the impact of a new client or big expense before it happens.
                </p>
              </motion.div>

              <motion.div className={`${styles.card} ${styles.cardOnElevated}`} {...staggerItem}>
                <BarChart3 className={styles.cardIcon} />
                <h3 className={styles.cardTitle}>Business Intelligence</h3>
                <p className={styles.cardDesc}>
                  Power BI-style dashboards. P&amp;L, revenue trends, expense breakdowns, and profitability by client — all generated automatically.
                </p>
              </motion.div>

              <motion.div className={`${styles.card} ${styles.cardOnElevated}`} {...staggerItem}>
                <Target className={styles.cardIcon} />
                <h3 className={styles.cardTitle}>Predictive Analytics</h3>
                <p className={styles.cardDesc}>
                  ML models trained on your financial history predict tax liability, slow months, and growth opportunities months in advance.
                </p>
              </motion.div>
            </motion.div>

            {/* Row 5 — Growth & Integrations */}
            <motion.div {...fadeUp} style={{ marginBottom: '0.5rem' }}>
              <p style={{ color: 'var(--lp-accent-teal)', fontWeight: 700, fontSize: '0.75rem', letterSpacing: '0.12em', textTransform: 'uppercase', marginBottom: '1rem' }}>
                Growth &amp; Integrations
              </p>
            </motion.div>
            <motion.div className={styles.grid3} {...staggerContainer}>
              <motion.div className={`${styles.card} ${styles.cardOnElevated}`} {...staggerItem}>
                <Plug2 className={styles.cardIcon} />
                <h3 className={styles.cardTitle}>Third-Party Integrations</h3>
                <p className={styles.cardDesc}>
                  Native connectors for Xero, QuickBooks, Stripe, Zapier, and 50+ tools. GraphQL &amp; REST API for custom workflows.
                </p>
              </motion.div>

              <motion.div className={`${styles.card} ${styles.cardOnElevated}`} {...staggerItem}>
                <Globe className={styles.cardIcon} />
                <h3 className={styles.cardTitle}>Multi-Currency &amp; 10 Languages</h3>
                <p className={styles.cardDesc}>
                  Support for GBP, EUR, USD, PLN, RON, UAH, and more. Full UI in 10 languages — serve global clients without currency headaches.
                </p>
              </motion.div>

              <motion.div className={`${styles.card} ${styles.cardOnElevated}`} {...staggerItem}>
                <Lightbulb className={styles.cardIcon} />
                <h3 className={styles.cardTitle}>Recommendation Engine</h3>
                <p className={styles.cardDesc}>
                  Personalised financial tips — weekly savings opportunities, tax deduction alerts, and cost-cutting suggestions based on your data.
                </p>
              </motion.div>
            </motion.div>
          </div>
        </section>

        {/* ====== AI AGENT SPOTLIGHT ====== */}
        <section className={styles.section}>
          <div className={styles.container}>
            <div className={styles.mobileShowcase}>
              <motion.div className={styles.mobileContent} {...fadeUp}>
                <span className={styles.mobileBadge}><Bot size={13} strokeWidth={2} style={{ display: 'inline', verticalAlign: 'middle', marginRight: '0.35rem' }} /> AI FINANCIAL AGENT</span>
                <h2 className={styles.sectionHeading} style={{ textAlign: 'left' }}>
                  Ask Anything. Get Instant Answers.
                </h2>
                <p className={styles.mobileDesc}>
                  SelfMonitor&rsquo;s AI Agent understands natural language. Ask financial questions in plain English — it queries your real data and answers in seconds.
                </p>

                <ul className={styles.mobileFeatures}>
                  <li><Check size={15} strokeWidth={2.5} className={styles.mobileCheck} /> &ldquo;How much did I spend on travel this quarter?&rdquo; — answered instantly</li>
                  <li><Check size={15} strokeWidth={2.5} className={styles.mobileCheck} /> &ldquo;What&rsquo;s my estimated tax bill for this year?&rdquo; — real number, real time</li>
                  <li><Check size={15} strokeWidth={2.5} className={styles.mobileCheck} /> &ldquo;Which clients are most profitable?&rdquo; — ranked list in seconds</li>
                  <li><Check size={15} strokeWidth={2.5} className={styles.mobileCheck} /> &ldquo;Flag any unusual expenses last month&rdquo; — fraud &amp; anomaly detection</li>
                  <li><Check size={15} strokeWidth={2.5} className={styles.mobileCheck} /> Proactive alerts — agent notifies you before problems occur</li>
                  <li><Check size={15} strokeWidth={2.5} className={styles.mobileCheck} /> Available via web, mobile app, and REST API</li>
                </ul>
              </motion.div>

              <motion.div
                className={styles.mobilePreview}
                initial={{ opacity: 0, scale: 0.9 }}
                whileInView={{ opacity: 1, scale: 1 }}
                transition={{ duration: 0.7 }}
                viewport={{ once: true }}
              >
                <div className={styles.phoneFrame}>
                  <div className={styles.phoneNotch}></div>
                  <div className={styles.phoneScreen}>
                    <div className={styles.phoneHeader}>
                      <span className={styles.phoneLogo}>AI Agent</span>
                    </div>
                    <div className={styles.phoneCard} style={{ background: 'rgba(13,148,136,0.15)', borderLeft: '3px solid var(--lp-accent-teal)' }}>
                      <p className={styles.phoneCardLabel}>You asked</p>
                      <p className={styles.phoneCardSub}>&ldquo;What&rsquo;s my tax estimate this year?&rdquo;</p>
                    </div>
                    <div className={styles.phoneCard}>
                      <p className={styles.phoneCardLabel}>AI Answer</p>
                      <p className={styles.phoneCardValue}>£4,830</p>
                      <p className={styles.phoneCardSub}>Due 31 Jan 2027 · 3 deductions found</p>
                    </div>
                    <div className={styles.phoneCard} style={{ background: 'rgba(234,179,8,0.1)', borderLeft: '3px solid #eab308' }}>
                      <p className={styles.phoneCardLabel}>💡 Tip</p>
                      <p className={styles.phoneCardSub}>Claim £480 home office allowance — not yet applied</p>
                    </div>
                    <div className={styles.phoneNav}>
                      <span>🏠</span>
                      <span>💳</span>
                      <span>🤖</span>
                      <span>📊</span>
                      <span>👤</span>
                    </div>
                  </div>
                </div>
              </motion.div>
            </div>
          </div>
        </section>

        {/* ====== MOBILE APP ====== */}
        <section className={styles.section}>
          <div className={styles.container}>
            <div className={styles.mobileShowcase}>
              <motion.div className={styles.mobileContent} {...fadeUp}>
                <span className={styles.mobileBadge}><Smartphone size={13} strokeWidth={2} style={{ display: 'inline', verticalAlign: 'middle', marginRight: '0.35rem' }} /> MOBILE APP</span>
                <h2 className={styles.sectionHeading} style={{ textAlign: 'left' }}>
                  Your Finances in Your Pocket
                </h2>
                <p className={styles.mobileDesc}>
                  Everything you can do on the web — now on your phone. Scan receipts with your camera,
                  check cash flow on the go, get instant tax estimates, and submit to HMRC from anywhere.
                </p>

                <ul className={styles.mobileFeatures}>
                  <li><Check size={15} strokeWidth={2.5} className={styles.mobileCheck} /> Scan receipts with your camera — OCR extracts data instantly</li>
                  <li><Check size={15} strokeWidth={2.5} className={styles.mobileCheck} /> Push notifications for tax deadlines and unusual transactions</li>
                  <li><Check size={15} strokeWidth={2.5} className={styles.mobileCheck} /> Check your cash flow forecast anytime, anywhere</li>
                  <li><Check size={15} strokeWidth={2.5} className={styles.mobileCheck} /> Connect bank accounts with biometric authentication</li>
                  <li><Check size={15} strokeWidth={2.5} className={styles.mobileCheck} /> Offline mode — view your data even without internet</li>
                  <li><Check size={15} strokeWidth={2.5} className={styles.mobileCheck} /> Dark theme designed for comfortable night-time use</li>
                </ul>

                <div className={styles.storeButtonsLeft}>
                  <a href="https://apps.apple.com/app/selfmonitor" className={styles.storeButton} target="_blank" rel="noopener noreferrer">
                    <span className={styles.storeIcon}>🍎</span>
                    <span className={styles.storeText}>
                      <small>Download on the</small>
                      <strong>App Store</strong>
                    </span>
                  </a>
                  <a href="https://play.google.com/store/apps/details?id=com.selfmonitor.app" className={styles.storeButton} target="_blank" rel="noopener noreferrer">
                    <span className={styles.storeIcon}>▶️</span>
                    <span className={styles.storeText}>
                      <small>Get it on</small>
                      <strong>Google Play</strong>
                    </span>
                  </a>
                </div>
              </motion.div>

              <motion.div
                className={styles.mobilePreview}
                initial={{ opacity: 0, scale: 0.9 }}
                whileInView={{ opacity: 1, scale: 1 }}
                transition={{ duration: 0.7 }}
                viewport={{ once: true }}
              >
                <div className={styles.phoneFrame}>
                  <div className={styles.phoneNotch}></div>
                  <div className={styles.phoneScreen}>
                    <div className={styles.phoneHeader}>
                      <span className={styles.phoneLogo}>SelfMonitor</span>
                    </div>
                    <div className={styles.phoneCard}>
                      <p className={styles.phoneCardLabel}>Cash Flow</p>
                      <p className={styles.phoneCardValue}>£4,230.50</p>
                      <p className={styles.phoneCardSub}>+12% from last month</p>
                    </div>
                    <div className={styles.phoneCard}>
                      <p className={styles.phoneCardLabel}>Tax Due</p>
                      <p className={styles.phoneCardValue}>£1,847.00</p>
                      <p className={styles.phoneCardSub}>Due 31 Jan 2026</p>
                    </div>
                    <div className={styles.phoneCard}>
                      <p className={styles.phoneCardLabel}>Receipts Scanned</p>
                      <p className={styles.phoneCardValue}>127</p>
                      <p className={styles.phoneCardSub}>This quarter</p>
                    </div>
                    <div className={styles.phoneNav}>
                      <span>🏠</span>
                      <span>💳</span>
                      <span>📄</span>
                      <span>📊</span>
                      <span>👤</span>
                    </div>
                  </div>
                </div>
              </motion.div>
            </div>
          </div>
        </section>

        {/* ====== WHO IT'S FOR ====== */}
        <section className={styles.sectionElevated}>
          <div className={styles.container}>
            <motion.div {...fadeUp}>
              <h2 className={styles.sectionHeading}>
                Built for Every Self-Employed Professional
              </h2>
            </motion.div>

            <motion.div className={styles.grid4} {...staggerContainer}>
              <motion.div className={`${styles.card} ${styles.cardOnElevated}`} {...staggerItem}>
                <Code2 className={styles.cardIcon} />
                <h3 className={styles.cardTitle}>Freelance Developers</h3>
                <p className={styles.cardDesc}>
                  Track project income, expenses, and IR35 status effortlessly.
                </p>
              </motion.div>

              <motion.div className={`${styles.card} ${styles.cardOnElevated}`} {...staggerItem}>
                <Palette className={styles.cardIcon} />
                <h3 className={styles.cardTitle}>
                  Designers &amp; Creatives
                </h3>
                <p className={styles.cardDesc}>
                  Receipt scanning, client invoicing, and portfolio expense
                  tracking.
                </p>
              </motion.div>

              <motion.div className={`${styles.card} ${styles.cardOnElevated}`} {...staggerItem}>
                <Briefcase className={styles.cardIcon} />
                <h3 className={styles.cardTitle}>Sole Traders</h3>
                <p className={styles.cardDesc}>
                  Mileage tracking, stock expenses, and quarterly VAT — sorted.
                </p>
              </motion.div>

              <motion.div className={`${styles.card} ${styles.cardOnElevated}`} {...staggerItem}>
                <Users className={styles.cardIcon} />
                <h3 className={styles.cardTitle}>Consultants</h3>
                <p className={styles.cardDesc}>
                  Multi-client billing, expense reports, and tax forecasting in
                  one place.
                </p>
              </motion.div>
            </motion.div>
          </div>
        </section>

        {/* ====== TRUST & SECURITY ====== */}
        <section className={styles.section}>
          <div className={styles.container}>
            <motion.div {...fadeUp}>
              <h2 className={styles.sectionHeading}>
                Your Data. Your Control. Bank-Grade Security.
              </h2>
            </motion.div>

            <motion.div className={styles.grid4} {...staggerContainer}>
              <motion.div className={styles.card} {...staggerItem}>
                <KeyRound className={styles.cardIcon} />
                <h3 className={styles.cardTitle}>Two-Factor Auth</h3>
                <p className={styles.cardDesc}>
                  TOTP-based 2FA with authenticator apps. Your account stays
                  yours.
                </p>
              </motion.div>

              <motion.div className={styles.card} {...staggerItem}>
                <ShieldAlert className={styles.cardIcon} />
                <h3 className={styles.cardTitle}>Fraud Detection</h3>
                <p className={styles.cardDesc}>
                  Real-time anomaly detection with ML scoring flags suspicious
                  activity.
                </p>
              </motion.div>

              <motion.div className={styles.card} {...staggerItem}>
                <ScrollText className={styles.cardIcon} />
                <h3 className={styles.cardTitle}>Audit Trail</h3>
                <p className={styles.cardDesc}>
                  Every action logged. Full GDPR compliance baked in from day
                  one.
                </p>
              </motion.div>

              <motion.div className={styles.card} {...staggerItem}>
                <Lock className={styles.cardIcon} />
                <h3 className={styles.cardTitle}>Encrypted Storage</h3>
                <p className={styles.cardDesc}>
                  Vault-secured credentials. S3-encrypted documents. Zero
                  compromise.
                </p>
              </motion.div>
            </motion.div>
          </div>
        </section>

        {/* ====== TESTIMONIALS ====== */}
        <section className={styles.sectionElevated}>
          <div className={styles.container}>
            <motion.div {...fadeUp}>
              <h2 className={styles.sectionHeading}>What Our Users Say</h2>
              <p className={styles.sectionSub}>
                Trusted by thousands of UK freelancers and sole traders.
              </p>
            </motion.div>

            <motion.div className={styles.testimonialGrid} {...staggerContainer}>
              {testimonials.map((t) => (
                <motion.div key={t.name} className={styles.testimonialCard} {...staggerItem}>
                  <span className={styles.testimonialStars}>
                    {'★'.repeat(t.stars)}
                  </span>
                  <p className={styles.testimonialQuote}>
                    &ldquo;{t.quote}&rdquo;
                  </p>
                  <div className={styles.testimonialAuthor}>
                    <div className={styles.testimonialAvatar}>{t.initials}</div>
                    <div className={styles.testimonialInfo}>
                      <span className={styles.testimonialName}>{t.name}</span>
                      <span className={styles.testimonialRole}>{t.role}</span>
                    </div>
                  </div>
                </motion.div>
              ))}
            </motion.div>
          </div>
        </section>

        {/* ====== ROI CALCULATOR ====== */}
        <section className={styles.section}>
          <div className={styles.container}>
            <motion.div {...fadeUp}>
              <h2 className={styles.sectionHeading}>See How Much You Save</h2>
              <p className={styles.sectionSub}>
                The numbers speak for themselves — SelfMonitor pays for itself in weeks.
              </p>
            </motion.div>

            <motion.div className={styles.roiSection} {...fadeUp}>
              <div className={`${styles.roiColumn} ${styles.roiColumnBad}`}>
                <p className={`${styles.roiColumnTitle} ${styles.roiColumnTitleBad}`}>
                  Without SelfMonitor
                </p>
                <div className={styles.roiItem}>
                  <span className={styles.roiItemLabel}>Weekly admin</span>
                  <span className={styles.roiItemValueBad}>5 hrs/week</span>
                </div>
                <div className={styles.roiItem}>
                  <span className={styles.roiItemLabel}>Overpaid tax</span>
                  <span className={styles.roiItemValueBad}>£1,200</span>
                </div>
                <div className={styles.roiItem}>
                  <span className={styles.roiItemLabel}>Accountant fees</span>
                  <span className={styles.roiItemValueBad}>£500</span>
                </div>
                <div className={styles.roiItem}>
                  <span className={styles.roiItemLabel}>Total cost</span>
                  <span className={styles.roiItemValueBad}>£2,700/yr</span>
                </div>
              </div>

              <div className={`${styles.roiColumn} ${styles.roiColumnGood}`}>
                <p className={`${styles.roiColumnTitle} ${styles.roiColumnTitleGood}`}>
                  With SelfMonitor
                </p>
                <div className={styles.roiItem}>
                  <span className={styles.roiItemLabel}>Weekly admin</span>
                  <span className={styles.roiItemValueGood}>30 min/week</span>
                </div>
                <div className={styles.roiItem}>
                  <span className={styles.roiItemLabel}>Overpaid tax</span>
                  <span className={styles.roiItemValueGood}>£0</span>
                </div>
                <div className={styles.roiItem}>
                  <span className={styles.roiItemLabel}>Pro plan</span>
                  <span className={styles.roiItemValueGood}>£19/month</span>
                </div>
                <div className={styles.roiItem}>
                  <span className={styles.roiItemLabel}>Total cost</span>
                  <span className={styles.roiItemValueGood}>£228/yr</span>
                </div>
              </div>
            </motion.div>

            <motion.div {...fadeUp}>
              <p className={styles.roiTotal}>
                <AnimatedCounter target={2472} prefix="£" />/year
              </p>
              <p className={styles.roiTotalLabel}>
                That&rsquo;s how much you save with SelfMonitor
              </p>
            </motion.div>
          </div>
        </section>

        {/* ====== PRICING ====== */}
        <section id="pricing" className={styles.sectionElevated}>
          <div className={styles.container}>
            <motion.div {...fadeUp}>
              <h2 className={styles.sectionHeading}>
                Simple Pricing. No Surprises.
              </h2>
              <p className={styles.sectionSub}>
                Start free. Upgrade when you&rsquo;re ready.
              </p>
            </motion.div>

            <motion.div className={styles.pricingGrid} {...staggerContainer}>
              {/* Free */}
              <motion.div className={styles.pricingCard} {...staggerItem}>
                <p className={styles.pricingName}>Free</p>
                <p className={styles.pricingPrice}>
                  £0<span>/mo</span>
                </p>
                <ul className={styles.pricingFeatures}>
                  <li>1 bank connection</li>
                  <li>200 transactions/month</li>
                  <li>Basic tax calculator</li>
                  <li>Email support</li>
                </ul>
                <Link href="/register?plan=free" className={styles.btnSecondary}>
                  Get Started
                </Link>
              </motion.div>

              {/* Starter */}
              <motion.div className={styles.pricingCard} {...staggerItem}>
                <p className={styles.pricingName}>Starter</p>
                <p className={styles.pricingPrice}>
                  £9<span>/mo</span>
                </p>
                <ul className={styles.pricingFeatures}>
                  <li>3 bank connections</li>
                  <li>1,000 transactions/month</li>
                  <li>AI categorization</li>
                  <li>Receipt OCR</li>
                  <li>Cash flow forecasting</li>
                </ul>
                <Link href="/register?plan=starter" className={styles.btnPrimary}>
                  Start Free Trial
                </Link>
              </motion.div>

              {/* Pro — POPULAR */}
              <motion.div
                className={`${styles.pricingCard} ${styles.pricingPopular}`}
                {...staggerItem}
              >
                <span className={styles.popularBadge}>Popular</span>
                <p className={styles.pricingName}>Pro</p>
                <p className={styles.pricingPrice}>
                  £19<span>/mo</span>
                </p>
                <ul className={styles.pricingFeatures}>
                  <li>3 bank connections</li>
                  <li>5,000 transactions/month</li>
                  <li>HMRC auto-submission</li>
                  <li>Smart document search</li>
                  <li>Mortgage readiness reports</li>
                  <li>Advanced analytics</li>
                  <li>API access</li>
                </ul>
                <Link href="/register?plan=pro" className={styles.btnPrimaryLg}>
                  Start Free Trial
                </Link>
              </motion.div>

              {/* Business */}
              <motion.div className={styles.pricingCard} {...staggerItem}>
                <p className={styles.pricingName}>Business</p>
                <p className={styles.pricingPrice}>
                  £39<span>/mo</span>
                </p>
                <ul className={styles.pricingFeatures}>
                  <li>Everything in Pro</li>
                  <li>5 team members</li>
                  <li>Custom expense policies</li>
                  <li>White-label reports</li>
                  <li>Dedicated success manager</li>
                </ul>
                <Link href="/register?plan=business" className={styles.btnGold}>
                  Contact Sales
                </Link>
              </motion.div>
            </motion.div>
          </div>
        </section>

        {/* ====== CTA ====== */}
        <section className={styles.cta}>
          <div className={styles.container}>
            <motion.div {...fadeUp}>
              <h2 className={styles.sectionHeading}>
                Ready to Take Control of Your Finances?
              </h2>
              <p className={styles.sectionSub}>
                Join thousands of UK self-employed professionals who saved 5+ hours
                per week.
              </p>
              <Link href="/register?plan=pro" className={styles.btnGoldLg}>
                Start Free — No Credit Card Required
              </Link>
              <small className={styles.ctaSmall}>
                Free plan includes 200 transactions/month. Upgrade anytime.
              </small>
            </motion.div>
          </div>
        </section>

        {/* ====== FOOTER ====== */}
        <footer className={styles.footer}>
          <div className={styles.container}>
            <div className={styles.footerTop}>
              <div>
                <p className={styles.footerLogo}>SelfMonitor</p>
                <p className={styles.footerTagline}>
                  AI-powered financial tools for the self-employed.
                </p>
              </div>

              <div>
                <p className={styles.footerColTitle}>Product</p>
                <ul className={styles.footerLinks}>
                  <li>
                    <a href="#features">Features</a>
                  </li>
                  <li>
                    <a href="#pricing">Pricing</a>
                  </li>
                  <li>
                    <a href="https://apps.apple.com/app/selfmonitor" target="_blank" rel="noopener noreferrer">iOS App</a>
                  </li>
                  <li>
                    <a href="https://play.google.com/store/apps/details?id=com.selfmonitor.app" target="_blank" rel="noopener noreferrer">Android App</a>
                  </li>
                  <li>
                    <a href="#features">API</a>
                  </li>
                </ul>
              </div>

              <div>
                <p className={styles.footerColTitle}>Company</p>
                <ul className={styles.footerLinks}>
                  <li>
                    <a href="#features">About</a>
                  </li>
                  <li>
                    <a href="#features">Blog</a>
                  </li>
                  <li>
                    <a href="#features">Careers</a>
                  </li>
                  <li>
                    <a href="#features">Contact</a>
                  </li>
                </ul>
              </div>

              <div>
                <p className={styles.footerColTitle}>Legal</p>
                <ul className={styles.footerLinks}>
                  <li>
                    <a href="#features">Privacy Policy</a>
                  </li>
                  <li>
                    <a href="#features">Terms of Service</a>
                  </li>
                  <li>
                    <a href="#features">Cookie Policy</a>
                  </li>
                  <li>
                    <a href="#features">GDPR</a>
                  </li>
                </ul>
              </div>
            </div>

            <div className={styles.footerBottom}>
              © 2026 SelfMonitor Ltd. Registered in England &amp; Wales.
            </div>
          </div>
        </footer>
      </div>
    </>
  );
}
