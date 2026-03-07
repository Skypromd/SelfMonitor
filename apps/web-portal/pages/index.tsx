import { motion, useInView } from 'framer-motion';
import {
    Archive,
    ArrowRight,
    BadgePercent,
    BarChart2,
    BarChart3,
    Bot,
    CalendarDays,
    CheckCircle2,
    ClipboardCheck,
    Clock,
    CreditCard,
    Download,
    FileText,
    FolderOpen,
    Gift,
    Globe2,
    Landmark,
    LineChart,
    Lock,
    Menu,
    PieChart,
    ReceiptText,
    ShieldCheck,
    Smartphone,
    Star,
    Store,
    TrendingUp,
    Wallet,
    X,
    Zap,
} from 'lucide-react';
import dynamic from 'next/dynamic';
import Head from 'next/head';
import { useRouter } from 'next/router';
import { FormEvent, useEffect, useMemo, useRef, useState } from 'react';
import styles from '../styles/Home.module.css';

const CashFlowChart = dynamic(() => import('../components/charts/CashFlowChart'), { ssr: false });
const ExpenseChart = dynamic(() => import('../components/charts/ExpenseChart'), { ssr: false });
const SavingsChart = dynamic(() => import('../components/charts/SavingsChart'), { ssr: false });
const RevenueVsExpensesChart = dynamic(() => import('../components/charts/RevenueVsExpensesChart'), { ssr: false });
const TaxSavingsAreaChart = dynamic(() => import('../components/charts/TaxSavingsAreaChart'), { ssr: false });

const AUTH_SERVICE_URL = process.env.NEXT_PUBLIC_AUTH_SERVICE_URL || 'http://localhost:8001';

type IndexPageProps = {
  onLoginSuccess: (newToken: string) => void;
};

function getPasswordChecks(password: string) {
  return {
    length: password.length >= 8,
    uppercase: /[A-Z]/.test(password),
    lowercase: /[a-z]/.test(password),
    digit: /\d/.test(password),
    special: /[!@#$%^&*()_+\-=[\]{};':"\\|,.<>/?`~]/.test(password),
  };
}

function getStrength(checks: ReturnType<typeof getPasswordChecks>) {
  const passed = Object.values(checks).filter(Boolean).length;
  if (passed >= 5) return 'strong';
  if (passed >= 3) return 'medium';
  return 'weak';
}

const FEATURES = [
  { Icon: ReceiptText,    title: 'Smart Invoicing',        color: '#0d9488', desc: 'Professional invoices with line-items, VAT & PDF export. Track draft, sent, paid and overdue at a glance.' },
  { Icon: BarChart3,      title: 'Transaction Analytics',  color: '#7c3aed', desc: 'AI auto-categorises every payment. Interactive charts for spending patterns, cash flow and profit trends.' },
  { Icon: CalendarDays,   title: 'HMRC Tax Calendar',       color: '#ea580c', desc: 'Built-in reminders for Self Assessment, Payment on Account, quarterly VAT returns and P60 filing dates.' },
  { Icon: Bot,            title: 'AI Tax Assistant',        color: '#0284c7', desc: 'Ask anything about UK self-employment tax, NI thresholds, Trading Allowance or allowable expense deductions.' },
  { Icon: TrendingUp,     title: 'Cash Flow Forecast',      color: '#16a34a', desc: 'Predict your financial position 30, 60 and 90 days ahead based on recurring income and upcoming invoices.' },
  { Icon: ShieldCheck,    title: 'Bank-Grade Security',     color: '#b45309', desc: 'TOTP 2FA, device session management, account lockdown, encrypted storage and a full security event log.' },
  { Icon: FolderOpen,     title: 'Document Storage',        color: '#db2777', desc: 'Upload receipts, contracts and tax documents. Instantly searchable for Self Assessment or accountant review.' },
  { Icon: Globe2,         title: 'Multi-Currency',          color: '#0891b2', desc: 'Invoice in GBP, EUR, USD, PLN, RON, UAH and more. Real-time rate conversion for accurate profit tracking.' },
  { Icon: Gift,           title: 'Referral Programme',      color: '#7c3aed', desc: 'Earn rewards by referring freelancers. Share your code, track conversions and climb the live leaderboard.' },
  { Icon: Store,          title: 'Partner Marketplace',     color: '#ea580c', desc: 'Access vetted accountants, legal advisors, insurance providers and fintech tools — all integrated.' },
  { Icon: LineChart,      title: 'Business Intelligence',   color: '#0d9488', desc: 'Revenue trends, top clients, expense breakdowns and ML-powered recommendations in one dashboard.' },
  { Icon: ClipboardCheck, title: 'Compliance Engine',       color: '#16a34a', desc: 'HMRC MTD compliance checks, audit trail logging, consent management and GDPR-ready data controls.' },
];

const ADVANTAGES = [
  { Icon: Smartphone,    title: 'Mobile-First Design',        desc: 'A native iOS & Android app gives you full access to invoices, expenses and tax deadlines from anywhere — built with React Native and Expo.' },
  { Icon: Zap,           title: 'AI Saves 90% of Your Time',  desc: 'Automatic bank import and ML categorisation means zero manual data entry. Reconcile a full month in under a minute.' },
  { Icon: CreditCard,    title: 'Cut Accountancy Costs',       desc: 'Automated tax-liability calculations, Self Assessment summaries and MTD submissions reduce your annual bill by hundreds.' },
  { Icon: Lock,          title: 'Your Data, Your Control',     desc: 'SOC 2-aligned: MFA, per-session audit logs, encrypted storage and one-click GDPR data export. No data selling.' },
  { Icon: FileText,      title: 'Built for UK Tax Law',        desc: 'Platform rules maintained for UK sole traders — Class 2/4 NI, Trading Allowance, VAT flat-rate and more.' },
  { Icon: CheckCircle2,  title: 'HMRC MTD Ready',              desc: 'Connect directly to Making Tax Digital APIs. Submit VAT returns and income tax updates without leaving the app.' },
];

const STATS = [
  { value: '2,400+', label: 'Active freelancers' },
  { value: '£14M+',  label: 'Invoices processed' },
  { value: '94%',    label: 'Time saved on bookkeeping' },
  { value: '4.8 ★',  label: 'App Store rating' },
];

const PRICING = [
  {
    name: 'Starter',
    price: '£9',
    sub: 'per month · 14-day free trial',
    highlight: false,
    features: [
      '1 bank connection',
      '500 transactions / month',
      'AI auto-categorisation',
      'Receipt OCR scanning',
      'HMRC tax calendar & deadlines',
      'Mobile app (iOS & Android)',
      '⛳ Secure cloud backup (2 GB)',
      '🗄️ Secure report storage — up to 6 years',
      'Email support',
    ],
    cta: 'Start Free Trial',
  },
  {
    name: 'Growth',
    price: '£12',
    sub: 'per month · 14-day free trial',
    highlight: false,
    features: [
      '2 bank connections',
      '2,000 transactions / month',
      'Unlimited invoices & PDF export',
      'Cash flow forecast 30/60/90 days',
      'Tax calculator & liability estimates',
      'Multi-currency (8+ currencies)',
      '⛳ Secure cloud backup (5 GB)',
      '🗄️ Secure report storage — up to 6 years',
      'Priority email support',
    ],
    cta: 'Start Free Trial',
  },
  {
    name: 'Pro',
    price: '£15',
    sub: 'per month · 14-day free trial',
    highlight: true,
    features: [
      '3 bank connections',
      '5,000 transactions / month',
      'AI Tax Assistant (unlimited)',
      'HMRC MTD auto-submission',
      'Smart document search',
      'Business Intelligence dashboard',
      '⛳ Secure cloud backup (15 GB)',
      '🗄️ Secure report storage — up to 6 years',
      'Phone & priority support',
    ],
    cta: 'Start Pro Trial',
  },
  {
    name: 'Business',
    price: '£25',
    sub: 'per month · 14-day free trial',
    highlight: false,
    features: [
      'Up to 5 bank connections',
      'Everything in Pro',
      '10 team members',
      'Compliance & full audit trail',
      'Partner Marketplace access',
      'Referral Programme',
      '⛳ Secure cloud backup (25 GB)',
      '🗄️ Secure report storage — up to 6 years',
      'API access & white-label reports',
      'Dedicated account manager',
    ],
    cta: 'Start Business Trial',
  },
];

const TESTIMONIALS = [
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

const fadeUp = {
  initial: { opacity: 0, y: 40 },
  whileInView: { opacity: 1, y: 0 } as object,
  transition: { duration: 0.7 },
  viewport: { once: true, margin: '-50px' as string },
};

function AnimatedCounter({ target, prefix = '', suffix = '' }: { target: number; prefix?: string; suffix?: string }) {
  const ref = useRef(null);
  const isInView = useInView(ref, { once: true });
  const [count, setCount] = useState(0);
  useEffect(() => {
    if (isInView) {
      let start = 0;
      const step = target / (2000 / 16);
      const timer = setInterval(() => {
        start += step;
        if (start >= target) { setCount(target); clearInterval(timer); }
        else { setCount(Math.floor(start)); }
      }, 16);
      return () => clearInterval(timer);
    }
  }, [isInView, target]);
  return <span ref={ref}>{prefix}{count.toLocaleString()}{suffix}</span>;
}

export default function HomePage({ onLoginSuccess }: IndexPageProps) {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [isRegistering, setIsRegistering] = useState(false);
  const [totpRequired, setTotpRequired] = useState(false);
  const [totpCode, setTotpCode] = useState('');
  const [loading, setLoading] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);
  const [langOpen, setLangOpen] = useState(false);
  const router = useRouter();
  const { locales, locale: activeLocale } = router;
  const LOCALE_FLAGS: Record<string, string> = { 'en-GB': '🇬🇧', 'pl-PL': '🇵🇱', 'ro-RO': '🇷🇴', 'uk-UA': '🇺🇦', 'ru-RU': '🇷🇺', 'es-ES': '🇪🇸', 'it-IT': '🇮🇹', 'pt-PT': '🇵🇹', 'tr-TR': '🇹🇷', 'bn-BD': '🇧🇩' };

  const passwordChecks = useMemo(() => getPasswordChecks(password), [password]);
  const strength = useMemo(() => getStrength(passwordChecks), [passwordChecks]);

  const clearFeedback = () => {
    setMessage('');
    setError('');
  };

  const formatErrorMessage = (detail: string): string => {
    if (/locked/i.test(detail)) {
      return 'Account temporarily locked. Please try again later.';
    }
    if (/password must/i.test(detail)) {
      const missing: string[] = [];
      if (!passwordChecks.length) missing.push('at least 8 characters');
      if (!passwordChecks.uppercase) missing.push('an uppercase letter');
      if (!passwordChecks.lowercase) missing.push('a lowercase letter');
      if (!passwordChecks.digit) missing.push('a number');
      if (!passwordChecks.special) missing.push('a special character');
      return missing.length
        ? `Password must contain: ${missing.join(', ')}.`
        : detail;
    }
    return detail;
  };

  const handleRegister = async (e: FormEvent) => {
    e.preventDefault();
    clearFeedback();
    if (!email.trim() || !password.trim()) {
      setError('Please enter your email and password.');
      return;
    }
    setLoading(true);

    try {
      const response = await fetch(`${AUTH_SERVICE_URL}/register`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: email.trim(), password }),
      });
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.detail || 'Registration failed');
      }
      setMessage(`User ${data.email} registered successfully! You can now log in.`);
      setIsRegistering(false);
    } catch (err: unknown) {
      if (err instanceof TypeError && err.message === 'Failed to fetch') {
        setError('Connection failed. Please try again.');
      } else {
        const details = err instanceof Error ? err.message : 'Registration failed';
        setError(formatErrorMessage(details));
      }
    } finally {
      setLoading(false);
    }
  };

  const handleLogin = async (e: FormEvent, totpOverride?: string) => {
    e.preventDefault();
    clearFeedback();
    if (!email.trim() || !password.trim()) {
      setError('Please enter your email and password.');
      return;
    }
    setLoading(true);

    try {
      const formData = new URLSearchParams();
      formData.append('username', email.trim());
      formData.append('password', password);

      const code = totpOverride || totpCode;
      if (code) {
        formData.append('scope', `totp:${code}`);
      }

      const response = await fetch(`${AUTH_SERVICE_URL}/token`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: formData.toString(),
      });
      const data = await response.json();

      if (response.status === 403 && data.detail === '2FA_REQUIRED') {
        setTotpRequired(true);
        setTotpCode('');
        setLoading(false);
        return;
      }

      if (!response.ok) {
        throw new Error(data.detail || 'Login failed');
      }

      onLoginSuccess(data.access_token);
    } catch (err: unknown) {
      if (err instanceof TypeError && err.message === 'Failed to fetch') {
        setError('Connection failed. Please try again.');
      } else {
        const details = err instanceof Error ? err.message : 'Login failed';
        setError(formatErrorMessage(details));
      }
    } finally {
      setLoading(false);
    }
  };

  const handleTotpSubmit = (e: FormEvent) => {
    handleLogin(e);
  };

  const handleBackToLogin = () => {
    setTotpRequired(false);
    setTotpCode('');
    clearFeedback();
  };

  const strengthClass = strength === 'strong' ? styles.strengthStrong : strength === 'medium' ? styles.strengthMedium : styles.strengthWeak;
  const strengthLabel = strength === 'strong' ? 'Strong' : strength === 'medium' ? 'Medium' : 'Weak';

  return (
    <>
      <Head>
        <title>SelfMonitor — Financial Freedom for UK Freelancers</title>
        <meta name="description" content="AI-powered banking, taxes, and insights for UK freelancers and sole traders. From receipt to HMRC submission in minutes." />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
      </Head>

    <div className={styles.lpRoot}>

      {/* ═══ NAVBAR ═══ */}
      <header className={styles.lpNav}>
        <div className={styles.lpNavInner}>
          <div className={styles.lpNavBrand}>
            <span className={styles.lpNavLogo}>SM</span>
            <span className={styles.lpNavName}>SelfMonitor</span>
          </div>
          <nav className={styles.lpNavLinks}>
            <a href="#features" className={styles.lpNavLink}>Features</a>
            <a href="#insights" className={styles.lpNavLink}>Charts</a>
            <a href="#why" className={styles.lpNavLink}>Why Us</a>
            <a href="#pricing" className={styles.lpNavLink}>Pricing</a>
          </nav>
          <div className={styles.lpNavLangSwitcher}>
            <button
              className={styles.lpNavLangBtn}
              onClick={() => setLangOpen(o => !o)}
              aria-label="Switch language"
            >
              <span style={{ fontSize: '1.1rem' }}>{LOCALE_FLAGS[activeLocale || 'en-GB'] || '🌐'}</span>
              <span style={{ fontSize: '0.75rem' }}>{(activeLocale || 'en-GB').split('-')[0].toUpperCase()}</span>
              <span style={{ fontSize: '0.65rem', opacity: 0.6 }}>▼</span>
            </button>
            {langOpen && (
              <div className={styles.lpNavLangDropdown}>
                {(locales || ['en-GB', 'pl-PL', 'ro-RO', 'uk-UA', 'ru-RU', 'es-ES', 'it-IT', 'pt-PT', 'tr-TR', 'bn-BD']).map(loc => (
                  <button
                    key={loc}
                    className={styles.lpNavLangOption}
                    style={{ color: loc === activeLocale ? 'var(--lp-accent-teal)' : 'var(--lp-text)', background: loc === activeLocale ? 'rgba(13,148,136,0.12)' : 'transparent' }}
                    onClick={() => { router.push(router.pathname, router.asPath, { locale: loc }); if (typeof window !== 'undefined') localStorage.setItem('preferredLocale', loc); setLangOpen(false); }}
                  >
                    <span style={{ fontSize: '1.1rem' }}>{LOCALE_FLAGS[loc] || '🌐'}</span>
                    <span>{loc.split('-')[0].toUpperCase()}</span>
                  </button>
                ))}
              </div>
            )}
          </div>
          <a href="#get-started" className={styles.lpNavCta}>Get Started <ArrowRight size={14} /></a>
          <button
            className={styles.lpNavHamburger}
            onClick={() => setMenuOpen(o => !o)}
            aria-label="Toggle menu"
          >
            {menuOpen ? <X size={22} /> : <Menu size={22} />}
          </button>
        </div>
        {menuOpen && (
          <div className={styles.lpNavMobileMenu}>
            <a href="#features" className={styles.lpNavMobileLink} onClick={() => setMenuOpen(false)}>Features</a>
            <a href="#insights" className={styles.lpNavMobileLink} onClick={() => setMenuOpen(false)}>Charts</a>
            <a href="#why" className={styles.lpNavMobileLink} onClick={() => setMenuOpen(false)}>Why Us</a>
            <a href="#pricing" className={styles.lpNavMobileLink} onClick={() => setMenuOpen(false)}>Pricing</a>
            <a href="#get-started" className={styles.lpNavMobileCta} onClick={() => setMenuOpen(false)}>Get Started <ArrowRight size={14} /></a>
          </div>
        )}
      </header>

      {/* ═══ HERO ═══ */}
      <section className={styles.lpHero}>
        <div className={styles.lpHeroContent}>
          <div className={styles.lpHeroBadge}><Smartphone size={13} /> Mobile &amp; Web App</div>
          <h1 className={styles.lpHeroH1}>
            Your complete<br />
            <span className={styles.lpHeroAccent}>financial command centre</span><br />
            for UK freelancers
          </h1>
          <p className={styles.lpHeroSub}>
            Invoicing · AI Tax Advice · HMRC Deadlines · Cash Flow Forecasts ·
            Expense Tracking · Document Storage — in one beautifully designed mobile app.
          </p>
          <div className={styles.lpHeroCtas}>
            <a href="#get-started" className={styles.lpCtaGold}>Start for Free <ArrowRight size={16} /></a>
            <a href="#features" className={styles.lpCtaSecondary}>See Features</a>
          </div>
          <div className={styles.lpHeroTrust}>
            <CheckCircle2 size={14} color="#0d9488" />
            <span>No credit card required</span>
            <CheckCircle2 size={14} color="#0d9488" />
            <span>HMRC MTD compliant</span>
            <CheckCircle2 size={14} color="#0d9488" />
            <span>GDPR ready</span>
          </div>
        </div>

        {/* Phone mockup */}
        <div className={styles.lpPhoneWrap}>
          <div className={styles.lpPhone}>
            <div className={styles.lpPhoneNotch} />
            <div className={styles.lpPhoneScreen}>
              <div className={styles.lpAppBar}>
                <span className={styles.lpAppBarTitle}>Dashboard</span>
                <div className={styles.lpAppBarAvatar}>A</div>
              </div>
              <div className={styles.lpAppCards}>
                <div className={styles.lpAppCard} style={{ background: 'linear-gradient(135deg,#0d9488,#0891b2)' }}>
                  <div className={styles.lpAppCardLabel}>Net Profit</div>
                  <div className={styles.lpAppCardVal}>£4,280</div>
                  <div className={styles.lpAppCardSub}>↑ 12% this month</div>
                </div>
                <div className={styles.lpAppCard} style={{ background: 'linear-gradient(135deg,#7c3aed,#db2777)' }}>
                  <div className={styles.lpAppCardLabel}>Tax Reserved</div>
                  <div className={styles.lpAppCardVal}>£1,070</div>
                  <div className={styles.lpAppCardSub}>20% auto-set aside</div>
                </div>
              </div>
              <div className={styles.lpAppSection}>Recent Transactions</div>
              {[
                { name: 'Client Invoice #42', amt: '+£1,200', color: '#4ade80' },
                { name: 'Adobe CC Subscription', amt: '-£55', color: '#f87171' },
                { name: 'Co-working Space', amt: '-£120', color: '#f87171' },
                { name: 'Freelance Project', amt: '+£850', color: '#4ade80' },
              ].map((tx) => (
                <div key={tx.name} className={styles.lpAppTx}>
                  <div className={styles.lpAppTxDot} style={{ background: tx.color }} />
                  <span className={styles.lpAppTxName}>{tx.name}</span>
                  <span className={styles.lpAppTxAmt} style={{ color: tx.color }}>{tx.amt}</span>
                </div>
              ))}
              <div className={styles.lpAppSection}>Tax Calendar</div>
              <div className={styles.lpAppDeadline}>
                <CalendarDays size={12} color="#f59e0b" />
                <span>VAT Return due in <b>14 days</b></span>
              </div>
              <div className={styles.lpAppDeadline}>
                <CalendarDays size={12} color="#4ade80" />
                <span>Self Assessment — Jan 31</span>
              </div>
            </div>
            <div className={styles.lpPhoneHome} />
          </div>
          <div className={`${styles.lpBadge} ${styles.lpBadge1}`}>
            <ShieldCheck size={14} color="#0d9488" />
            <span>Bank-level security</span>
          </div>
          <div className={`${styles.lpBadge} ${styles.lpBadge2}`}>
            <Bot size={14} color="#7c3aed" />
            <span>AI Tax Assistant</span>
          </div>
          <div className={`${styles.lpBadge} ${styles.lpBadge3}`}>
            <TrendingUp size={14} color="#16a34a" />
            <span>+12% profit this month</span>
          </div>
        </div>
      </section>

      {/* ═══ STATS ═══ */}
      <section className={styles.lpStats}>
        <motion.div className={styles.lpStat} initial={{ opacity: 0 }} whileInView={{ opacity: 1 }} viewport={{ once: true }} transition={{ duration: 0.5, delay: 0 }}>
          <div className={styles.lpStatVal}><AnimatedCounter target={2400} suffix="+" /></div>
          <div className={styles.lpStatLabel}>Active freelancers</div>
        </motion.div>
        <motion.div className={styles.lpStat} initial={{ opacity: 0 }} whileInView={{ opacity: 1 }} viewport={{ once: true }} transition={{ duration: 0.5, delay: 0.15 }}>
          <div className={styles.lpStatVal}>£<AnimatedCounter target={14} suffix="M+" /></div>
          <div className={styles.lpStatLabel}>Invoices processed</div>
        </motion.div>
        <motion.div className={styles.lpStat} initial={{ opacity: 0 }} whileInView={{ opacity: 1 }} viewport={{ once: true }} transition={{ duration: 0.5, delay: 0.3 }}>
          <div className={styles.lpStatVal}><AnimatedCounter target={94} suffix="%" /></div>
          <div className={styles.lpStatLabel}>Time saved on bookkeeping</div>
        </motion.div>
        <motion.div className={styles.lpStat} initial={{ opacity: 0 }} whileInView={{ opacity: 1 }} viewport={{ once: true }} transition={{ duration: 0.5, delay: 0.45 }}>
          <div className={styles.lpStatVal}>4.8 ★</div>
          <div className={styles.lpStatLabel}>App Store rating</div>
        </motion.div>
      </section>

      {/* ═══ CHALLENGE ═══ */}
      <section className={styles.lpSection} style={{ background: 'var(--lp-bg-elevated)' }}>
        <div className={styles.lpSectionHeader}>
          <div className={styles.lpChip}>The Problem</div>
          <h2 className={styles.lpSectionH2}>Self-Employment Shouldn&rsquo;t Mean Self-Struggle</h2>
          <p className={styles.lpSectionSub}>UK freelancers lose hours every week to admin that AI can handle instantly.</p>
        </div>
        <div className={styles.challengeGrid}>
          <motion.div className={styles.challengeCard} {...fadeUp}>
            <div className={styles.challengeIconBox}><Clock size={28} color="#14b8a6" /></div>
            <h3 className={styles.challengeCardTitle}>Hours lost on manual bookkeeping</h3>
            <p className={styles.challengeDesc}>
              Spreadsheets, bank exports, copy-paste — the admin never ends.
              <span className={styles.challengeHighlight}>Average freelancer spends <strong>5 hrs/week</strong> on admin</span>
            </p>
          </motion.div>
          <motion.div className={styles.challengeCard} initial={{ opacity: 0, y: 40 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }} transition={{ duration: 0.7, delay: 0.15 }}>
            <div className={styles.challengeIconBox}><BadgePercent size={28} color="#d97706" /></div>
            <h3 className={styles.challengeCardTitle}>Missed tax deductions</h3>
            <p className={styles.challengeDesc}>
              Without AI categorisation, legitimate expenses slip through the cracks.
              <span className={styles.challengeHighlight}>UK freelancers overpay <strong>£1,200/year</strong> in taxes on average</span>
            </p>
          </motion.div>
          <motion.div className={styles.challengeCard} initial={{ opacity: 0, y: 40 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }} transition={{ duration: 0.7, delay: 0.3 }}>
            <div className={styles.challengeIconBox}><Archive size={28} color="#7c3aed" /></div>
            <h3 className={styles.challengeCardTitle}>Receipts in a shoebox</h3>
            <p className={styles.challengeDesc}>
              Paper receipts fade. Email receipts get buried. Audits happen.
              <span className={styles.challengeHighlight}>HMRC requires <strong>5 years</strong> of records — can you find them?</span>
            </p>
          </motion.div>
        </div>
      </section>

      {/* ═══ 6 CHARTS ═══ */}
      <section className={styles.lpSection} id="insights">
        <div className={styles.lpSectionHeader}>
          <div className={styles.lpChip}>Live Data Insights</div>
          <h2 className={styles.lpSectionH2}>See Your Finances Come Alive</h2>
          <p className={styles.lpSectionSub}>6 interactive charts powered by real data — AI categorises everything automatically.</p>
        </div>
        <div className={styles.chartsGrid}>
          <motion.div className={styles.chartCard} {...fadeUp}>
            <div className={styles.chartTitleRow}><TrendingUp size={16} color="#14b8a6" /><span>Cash Flow Trend — 12 months</span></div>
            <CashFlowChart />
            <p className={styles.chartCaption}>Track monthly cash flow with AI-powered forecasting and trend detection</p>
          </motion.div>
          <motion.div className={styles.chartCard} initial={{ opacity: 0, y: 40 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }} transition={{ duration: 0.7, delay: 0.1 }}>
            <div className={styles.chartTitleRow}><BarChart2 size={16} color="#7c3aed" /><span>Revenue vs Expenses — Monthly</span></div>
            <RevenueVsExpensesChart />
            <p className={styles.chartCaption}>Compare income against spending each month — spot the gap and grow it</p>
          </motion.div>
          <motion.div className={styles.chartCard} initial={{ opacity: 0, y: 40 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }} transition={{ duration: 0.7, delay: 0.2 }}>
            <div className={styles.chartTitleRow}><Wallet size={16} color="#d97706" /><span>Tax Savings Accumulated YTD</span></div>
            <TaxSavingsAreaChart />
            <p className={styles.chartCaption}>Watch your identified deductions grow — average user saves £2,080/year</p>
          </motion.div>
          <motion.div className={styles.chartCard} initial={{ opacity: 0, y: 40 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }} transition={{ duration: 0.7, delay: 0.3 }}>
            <div className={styles.chartTitleRow}><ReceiptText size={16} color="#0891b2" /><span>Expense Breakdown by Category</span></div>
            <ExpenseChart />
            <p className={styles.chartCaption}>AI categorises every expense automatically — see exactly where your money goes</p>
          </motion.div>
          <motion.div className={styles.chartCard} initial={{ opacity: 0, y: 40 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }} transition={{ duration: 0.7, delay: 0.4 }}>
            <div className={styles.chartTitleRow}><PieChart size={16} color="#16a34a" /><span>Tax Savings Distribution</span></div>
            <SavingsChart />
            <p className={styles.chartCaption}>Breakdown of how SelfMonitor identifies and maximises your allowable deductions</p>
          </motion.div>
          <motion.div className={styles.chartCard} initial={{ opacity: 0, y: 40 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }} transition={{ duration: 0.7, delay: 0.5 }}>
            <div className={styles.chartTitleRow}><Landmark size={16} color="#f59e0b" /><span>Financial Health Summary</span></div>
            <div style={{ padding: '1rem 0' }}>
              {[
                { label: 'Annual Revenue', value: '£67,200', bar: 100, color: '#14b8a6' },
                { label: 'Total Expenses',  value: '£18,600', bar: 28,  color: '#f87171' },
                { label: 'Tax Reserved',    value: '£9,720',  bar: 14,  color: '#d97706' },
                { label: 'Net Profit',      value: '£48,600', bar: 72,  color: '#4ade80' },
              ].map((item) => (
                <div key={item.label} style={{ marginBottom: '1.1rem' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.3rem' }}>
                    <span style={{ fontSize: '0.82rem', color: '#94a3b8' }}>{item.label}</span>
                    <span style={{ fontSize: '0.85rem', fontWeight: 600, color: item.color }}>{item.value}</span>
                  </div>
                  <div style={{ height: 6, borderRadius: 3, background: 'rgba(148,163,184,0.1)' }}>
                    <div style={{ height: '100%', borderRadius: 3, background: item.color, width: `${item.bar}%` }} />
                  </div>
                </div>
              ))}
            </div>
            <p className={styles.chartCaption}>Full-year financial overview — calculated automatically from your transactions</p>
          </motion.div>
        </div>
      </section>

      {/* ═══ FEATURES ═══ */}
      <section className={styles.lpSection} id="features">
        <div className={styles.lpSectionHeader}>
          <div className={styles.lpChip}>Full Feature Suite</div>
          <h2 className={styles.lpSectionH2}>Everything you need to run your finances</h2>
          <p className={styles.lpSectionSub}>12 integrated modules — no switching between apps, no manual exports.</p>
        </div>
        <div className={styles.lpFeatureGrid}>
          {FEATURES.map(({ Icon, title, color, desc }) => (
            <div key={title} className={styles.lpFeatureCard}>
              <div className={styles.lpFeatureIconWrap} style={{ background: `${color}18`, border: `1px solid ${color}40` }}>
                <Icon size={20} color={color} />
              </div>
              <h3 className={styles.lpFeatureTitle}>{title}</h3>
              <p className={styles.lpFeatureDesc}>{desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* ═══ AI ENGINE ═══ */}
      <section className={styles.lpSection} id="ai-engine" style={{ background: 'linear-gradient(135deg, rgba(2,132,199,0.06) 0%, rgba(13,148,136,0.06) 100%)' }}>
        <div className={styles.lpSectionHeader}>
          <div className={styles.lpChip}><Bot size={13} /> Powered by GPT-4o</div>
          <h2 className={styles.lpSectionH2}>The AI brain behind SelfMonitor</h2>
          <p className={styles.lpSectionSub}>Not just automation — a financial co-pilot that understands UK tax law, speaks 10 languages, and learns your business patterns.</p>
        </div>
        <div className={styles.aiEngineGrid}>
          <motion.div className={styles.aiEngineCard} {...fadeUp}>
            <div className={styles.aiEngineIcon} style={{ background: 'rgba(2,132,199,0.12)', border: '1px solid rgba(2,132,199,0.3)' }}>
              <Bot size={28} color="#0284c7" />
            </div>
            <h3 className={styles.aiEngineTitle}>GPT-4o Core Model</h3>
            <p className={styles.aiEngineDesc}>Your AI assistant runs on OpenAI&apos;s GPT-4o — the same model used by Fortune 500 finance teams. Ask about allowable expenses, NI thresholds, VAT rules or HMRC deadlines in plain English.</p>
            <div className={styles.aiEngineBadge}>128k context window</div>
          </motion.div>
          <motion.div className={styles.aiEngineCard} initial={{ opacity: 0, y: 40 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }} transition={{ duration: 0.7, delay: 0.15 }}>
            <div className={styles.aiEngineIcon} style={{ background: 'rgba(13,148,136,0.12)', border: '1px solid rgba(13,148,136,0.3)' }}>
              <Globe2 size={28} color="#0d9488" />
            </div>
            <h3 className={styles.aiEngineTitle}>10 Languages, One App</h3>
            <p className={styles.aiEngineDesc}>Switch the entire interface and AI responses between English, Polish, Romanian, Ukrainian, Russian, Spanish, Italian, Portuguese, Turkish and Bengali — instantly, no reload.</p>
            <div className={styles.aiEngineLangs}>🇬🇧 🇵🇱 🇷🇴 🇺🇦 🇷🇺 🇪🇸 🇮🇹 🇵🇹 🇹🇷 🇧🇩</div>
          </motion.div>
          <motion.div className={styles.aiEngineCard} initial={{ opacity: 0, y: 40 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }} transition={{ duration: 0.7, delay: 0.3 }}>
            <div className={styles.aiEngineIcon} style={{ background: 'rgba(124,58,237,0.12)', border: '1px solid rgba(124,58,237,0.3)' }}>
              <TrendingUp size={28} color="#7c3aed" />
            </div>
            <h3 className={styles.aiEngineTitle}>Learns Your Business</h3>
            <p className={styles.aiEngineDesc}>ML models auto-categorise transactions with 94% accuracy from day one. After 30 days it knows your patterns — flagging anomalies, predicting cash dips and recommending tax deductions.</p>
            <div className={styles.aiEngineBadge} style={{ background: 'rgba(124,58,237,0.15)', color: '#a78bfa', borderColor: 'rgba(124,58,237,0.3)' }}>94% accuracy</div>
          </motion.div>
        </div>
      </section>

      {/* ═══ WHY SELFMONITOR ═══ */}
      <section className={styles.lpSection} id="why" style={{ background: 'var(--lp-bg-elevated)' }}>
        <div className={styles.lpSectionHeader}>
          <div className={styles.lpChip}>Why SelfMonitor</div>
          <h2 className={styles.lpSectionH2}>Built specifically for how you work</h2>
          <p className={styles.lpSectionSub}>Not a generic accounting tool. Designed from the ground up for UK sole traders and freelancers.</p>
        </div>
        <div className={styles.lpAdvGrid}>
          {ADVANTAGES.map(({ Icon, title, desc }) => (
            <div key={title} className={styles.lpAdvCard}>
              <div className={styles.lpAdvIconRow}>
                <div className={styles.lpAdvIconWrap}><Icon size={22} color="#0d9488" /></div>
                <h3 className={styles.lpAdvTitle}>{title}</h3>
              </div>
              <p className={styles.lpAdvDesc}>{desc}</p>
            </div>
          ))}
        </div>

        {/* Security guarantee strip */}
        <div className={styles.lpSecurityStrip}>
          <div className={styles.lpSecurityItem}>
            <Lock size={15} color="#0d9488" />
            <span>AES-256 encryption at rest &amp; in transit</span>
          </div>
          <div className={styles.lpSecurityItem}>
            <ShieldCheck size={15} color="#0d9488" />
            <span>2FA on every account — no exceptions</span>
          </div>
          <div className={styles.lpSecurityItem}>
            <FolderOpen size={15} color="#0d9488" />
            <span>Automatic daily cloud backups</span>
          </div>
          <div className={styles.lpSecurityItem}>
            <CheckCircle2 size={15} color="#0d9488" />
            <span>GDPR compliant · your data is never sold</span>
          </div>
          <div className={styles.lpSecurityItem}>
            <Globe2 size={15} color="#0d9488" />
            <span>UK data centres · 99.9% uptime SLA</span>
          </div>
        </div>
      </section>

      {/* ═══ TESTIMONIALS ═══ */}
      <section className={styles.lpSection} id="testimonials" style={{ background: 'var(--lp-bg-elevated)' }}>
        <div className={styles.lpSectionHeader}>
          <div className={styles.lpChip}>Customer Stories</div>
          <h2 className={styles.lpSectionH2}>What Our Users Say</h2>
          <p className={styles.lpSectionSub}>Trusted by thousands of UK freelancers and sole traders.</p>
        </div>
        <div className={styles.testimonialGrid}>
          {TESTIMONIALS.map((t, i) => (
            <motion.div
              key={t.name}
              className={styles.testimonialCard}
              initial={{ opacity: 0, y: 30 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.6, delay: i * 0.15 }}
            >
              <span className={styles.testimonialStars}>{'★'.repeat(t.stars)}</span>
              <p className={styles.testimonialQuote}>&ldquo;{t.quote}&rdquo;</p>
              <div className={styles.testimonialAuthor}>
                <div className={styles.testimonialAvatar}>{t.initials}</div>
                <div>
                  <span className={styles.testimonialName}>{t.name}</span>
                  <span className={styles.testimonialRole}>{t.role}</span>
                </div>
              </div>
            </motion.div>
          ))}
        </div>
      </section>

      {/* ═══ ROI CALCULATOR ═══ */}
      <section className={styles.lpSection}>
        <div className={styles.lpSectionHeader}>
          <div className={styles.lpChip}>ROI Calculator</div>
          <h2 className={styles.lpSectionH2}>See How Much You Save</h2>
          <p className={styles.lpSectionSub}>SelfMonitor pays for itself in weeks — the numbers speak for themselves.</p>
        </div>
        <div className={styles.roiGrid}>
          <motion.div className={`${styles.roiCol} ${styles.roiColBad}`} {...fadeUp}>
            <p className={`${styles.roiColTitle} ${styles.roiColTitleBad}`}>❌ Without SelfMonitor</p>
            <div className={styles.roiRow}><span className={styles.roiRowLabel}>Weekly admin</span><span className={styles.roiRowBad}>5 hrs/week</span></div>
            <div className={styles.roiRow}><span className={styles.roiRowLabel}>Overpaid tax</span><span className={styles.roiRowBad}>£1,200/yr</span></div>
            <div className={styles.roiRow}><span className={styles.roiRowLabel}>Accountant fees</span><span className={styles.roiRowBad}>£500/yr</span></div>
            <div className={styles.roiRow}><span className={styles.roiRowLabel}>Total cost</span><span className={styles.roiRowBad}>£2,700/yr</span></div>
          </motion.div>
          <motion.div className={`${styles.roiCol} ${styles.roiColGood}`} initial={{ opacity: 0, y: 40 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }} transition={{ duration: 0.7, delay: 0.2 }}>
            <p className={`${styles.roiColTitle} ${styles.roiColTitleGood}`}>✅ With SelfMonitor</p>
            <div className={styles.roiRow}><span className={styles.roiRowLabel}>Weekly admin</span><span className={styles.roiRowGood}>30 min/week</span></div>
            <div className={styles.roiRow}><span className={styles.roiRowLabel}>Overpaid tax</span><span className={styles.roiRowGood}>£0</span></div>
            <div className={styles.roiRow}><span className={styles.roiRowLabel}>Pro plan</span><span className={styles.roiRowGood}>£15/month</span></div>
            <div className={styles.roiRow}><span className={styles.roiRowLabel}>Total cost</span><span className={styles.roiRowGood}>£180/yr</span></div>
          </motion.div>
        </div>
        <motion.div {...fadeUp} style={{ marginTop: '2.5rem', textAlign: 'center' }}>
          <div className={styles.roiSaving}><AnimatedCounter target={2520} prefix="£" />/yr</div>
          <p className={styles.roiSavingLbl}>That&rsquo;s the average annual saving with SelfMonitor</p>
          <a href="#get-started" className={styles.lpCtaGoldLg} style={{ marginTop: '1.5rem', display: 'inline-flex' }}>
            Start Saving Today <ArrowRight size={18} />
          </a>
        </motion.div>
      </section>

      {/* ═══ PRICING ═══ */}
      <section className={styles.lpSection} id="pricing" style={{ background: 'var(--lp-bg-elevated)' }}>
        <div className={styles.lpSectionHeader}>
          <div className={styles.lpChip}>Simple Pricing</div>
          <h2 className={styles.lpSectionH2}>Choose the plan that works for you</h2>
          <p className={styles.lpSectionSub}>All plans include a 14-day free trial, mobile app access, HMRC compliance and <strong>secure 6-year report storage</strong> — the full retention period required by HMRC. No credit card required to start.</p>
        </div>
        <div className={styles.lpPricingGrid}>
          {PRICING.map((plan) => (
            <div key={plan.name} className={`${styles.lpPricingCard} ${plan.highlight ? styles.lpPricingCardHL : ''}`}>
              {plan.highlight && <div className={styles.lpPricingBadge}>Most Popular</div>}
              <div className={styles.lpPricingName}>{plan.name}</div>
              <div className={styles.lpPricingPrice}>
                <span className={styles.lpPricingAmount}>{plan.price}</span>
                {plan.price !== 'Free' && <span className={styles.lpPricingSub}>/mo</span>}
              </div>
              <div className={styles.lpPricingNote}>{plan.sub}</div>
              <ul className={styles.lpPricingFeatures}>
                {plan.features.map((f) => (
                  <li key={f}><CheckCircle2 size={14} color={plan.highlight ? '#0d9488' : '#6b7280'} />{f}</li>
                ))}
              </ul>
              <a href="#get-started" className={plan.highlight ? styles.lpCtaGold : styles.lpPricingCta}>{plan.cta}</a>
            </div>
          ))}
        </div>
      </section>

      {/* ═══ MOBILE APP DOWNLOAD ═══ */}
      <section className={styles.lpSection}>
        <div className={styles.appDownloadWrap}>
          <motion.div className={styles.appDownloadContent} {...fadeUp}>
            <div className={styles.lpChip}><Smartphone size={13} /> Available Now</div>
            <h2 className={styles.lpSectionH2} style={{ textAlign: 'left', marginTop: '1rem' }}>
              Take SelfMonitor<br />Everywhere You Go
            </h2>
            <p className={styles.lpSectionSub} style={{ textAlign: 'left' }}>
              Full access on iOS &amp; Android. Scan receipts with your camera, check cash flow on the go,
              submit to HMRC from anywhere. Works offline too.
            </p>
            <ul className={styles.appDownloadFeatures}>
              <li><CheckCircle2 size={15} color="#0d9488" /> Scan receipts instantly with OCR camera</li>
              <li><CheckCircle2 size={15} color="#0d9488" /> Push alerts for tax deadlines &amp; anomalies</li>
              <li><CheckCircle2 size={15} color="#0d9488" /> Biometric login — Face ID &amp; fingerprint</li>
              <li><CheckCircle2 size={15} color="#0d9488" /> Offline mode — works without internet</li>
              <li><CheckCircle2 size={15} color="#0d9488" /> Dark theme &amp; accessibility support</li>
            </ul>
            <div className={styles.appStoreBtns}>
              <a
                href="https://apps.apple.com/app/selfmonitor"
                className={styles.appStoreBtnApple}
                target="_blank"
                rel="noopener noreferrer"
              >
                <svg width="22" height="22" viewBox="0 0 24 24" fill="currentColor">
                  <path d="M18.71 19.5c-.83 1.24-1.71 2.45-3.05 2.47-1.34.03-1.77-.79-3.29-.79-1.53 0-2 .77-3.27.82-1.31.05-2.3-1.32-3.14-2.53C4.25 17 2.94 12.45 4.7 9.39c.87-1.52 2.43-2.48 4.12-2.51 1.28-.02 2.5.87 3.29.87.78 0 2.26-1.07 3.8-.91.65.03 2.47.26 3.64 1.98-.09.06-2.17 1.28-2.15 3.81.03 3.02 2.65 4.03 2.68 4.04-.03.07-.42 1.44-1.38 2.83M13 3.5c.73-.83 1.94-1.46 2.94-1.5.13 1.17-.34 2.35-1.04 3.19-.69.85-1.83 1.51-2.95 1.42-.15-1.15.41-2.35 1.05-3.11z"/>
                </svg>
                <div>
                  <div style={{ fontSize: '0.65rem', opacity: 0.8, lineHeight: 1 }}>Download on the</div>
                  <div style={{ fontSize: '1rem', fontWeight: 700, lineHeight: 1.2 }}>App Store</div>
                </div>
              </a>
              <a
                href="https://play.google.com/store/apps/details?id=com.selfmonitor.app"
                className={styles.appStoreBtnGoogle}
                target="_blank"
                rel="noopener noreferrer"
              >
                <svg width="22" height="22" viewBox="0 0 24 24" fill="currentColor">
                  <path d="M3.18 23.76c.3.17.65.22 1.01.14l12.19-7.03-2.68-2.68-10.52 9.57zm-1.87-20.2a1.94 1.94 0 0 0-.31 1.07v18.74c0 .39.11.74.31 1.04l.06.06 10.5-10.5v-.25L1.37 3.5l-.06.06zm20.5 8.98-2.86-1.65-3.01 3.01 3.01 3.01 2.88-1.66c.82-.47.82-1.24-.02-1.71zm-18.63 9.22 10.52-10.52-2.68-2.68L1.31 19.49l.87.27z"/>
                </svg>
                <div>
                  <div style={{ fontSize: '0.65rem', opacity: 0.8, lineHeight: 1 }}>Get it on</div>
                  <div style={{ fontSize: '1rem', fontWeight: 700, lineHeight: 1.2 }}>Google Play</div>
                </div>
              </a>
            </div>
            <div className={styles.appRating}>
              {[...Array(5)].map((_, i) => <Star key={i} size={14} color="#f59e0b" fill="#f59e0b" />)}
              <span>4.8 · 2,400+ reviews</span>
            </div>
          </motion.div>

          <motion.div
            className={styles.appDownloadPhone}
            initial={{ opacity: 0, scale: 0.92, y: 20 }}
            whileInView={{ opacity: 1, scale: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.75, delay: 0.2 }}
          >
            <div className={styles.lpPhone}>
              <div className={styles.lpPhoneNotch} />
              <div className={styles.lpPhoneScreen}>
                <div className={styles.lpAppBar}>
                  <span className={styles.lpAppBarTitle}>SelfMonitor</span>
                  <div className={styles.lpAppBarAvatar}><Download size={12} /></div>
                </div>
                <div className={styles.lpAppCards}>
                  <div className={styles.lpAppCard} style={{ background: 'linear-gradient(135deg,#0d9488,#0891b2)' }}>
                    <div className={styles.lpAppCardLabel}>Net Profit This Month</div>
                    <div className={styles.lpAppCardVal}>£4,280</div>
                    <div className={styles.lpAppCardSub}>↑ 12% vs last month</div>
                  </div>
                </div>
                {[
                  { icon: '📸', action: 'Scan Receipt', sub: 'OCR in 2 seconds' },
                  { icon: '📊', action: 'View Cash Flow', sub: 'Live charts' },
                  { icon: '🏦', action: 'HMRC Submit', sub: 'MTD compliant' },
                  { icon: '🔔', action: 'Tax Deadline', sub: 'VAT due in 14 days' },
                ].map((item) => (
                  <div key={item.action} className={styles.lpAppTx}>
                    <span style={{ fontSize: '1rem', width: 22, textAlign: 'center' }}>{item.icon}</span>
                    <div style={{ flex: 1 }}>
                      <div style={{ fontSize: '0.72rem', fontWeight: 600, color: '#f1f5f9' }}>{item.action}</div>
                      <div style={{ fontSize: '0.65rem', color: '#64748b' }}>{item.sub}</div>
                    </div>
                  </div>
                ))}
              </div>
              <div className={styles.lpPhoneHome} />
            </div>
          </motion.div>
        </div>
      </section>

      {/* ═══ AUTH / GET STARTED ═══ */}
      <section className={styles.lpAuthSection} id="get-started">
        <div className={styles.lpAuthWrap}>
          <div className={styles.lpAuthLeft}>
            <div className={styles.lpChip}>Join 2,400+ freelancers</div>
            <h2 className={styles.lpAuthH2}>Start managing your finances smarter today</h2>
            <ul className={styles.lpAuthPerks}>
              {['14-day free trial — no credit card needed', 'Full access to all 12 modules during trial', 'HMRC MTD compliant on day one', 'Set up in under 5 minutes'].map((p) => (
                <li key={p}><CheckCircle2 size={16} color="#0d9488" /> {p}</li>
              ))}
            </ul>
            <a
              href="#email-input"
              className={styles.lpCtaGoldLg}
              style={{ marginTop: '0.5rem' }}
              onClick={() => { setIsRegistering(true); clearFeedback(); }}
            >
              Start Free Trial — No Credit Card <ArrowRight size={18} />
            </a>
          </div>
          <div className={styles.lpAuthCard}>
            <main className={styles.main}>
              <h1 className={styles.title}>SelfMonitor</h1>
              <p className={styles.description}>Sign up or log in to continue</p>
              <div className={styles.formContainer}>
                {totpRequired ? (
                  <form onSubmit={handleTotpSubmit}>
                    <div className={styles.totpSection}>
                      <p>Enter your 6-digit code from authenticator app</p>
                    </div>
                    <input
                      id="totp-input"
                      type="text"
                      inputMode="numeric"
                      pattern="[0-9]*"
                      maxLength={6}
                      placeholder="000000"
                      value={totpCode}
                      onChange={(e) => setTotpCode(e.target.value.replace(/\D/g, '').slice(0, 6))}
                      className={`${styles.input} ${styles.totpInput}`}
                      aria-label="Two-factor authentication code"
                      autoFocus
                    />
                    <div className={styles.buttonGroup}>
                      <button type="button" onClick={handleBackToLogin} className={styles.button}
                        style={{ background: 'transparent', border: '1px solid var(--lp-border)', color: 'var(--lp-text-muted)' }}>
                        Back
                      </button>
                      <button type="submit" className={styles.button} disabled={totpCode.length !== 6 || loading} aria-label="Verify TOTP code">
                        {loading ? 'Verifying...' : 'Verify'}
                      </button>
                    </div>
                  </form>
                ) : (
                  <form>
                    <label htmlFor="email-input">Email</label>
                    <input id="email-input" type="email" placeholder="Email" value={email}
                      onChange={(e) => setEmail(e.target.value)} className={styles.input} aria-label="Email address" />
                    <label htmlFor="password-input">Password</label>
                    <div className={styles.passwordWrapper}>
                      <input id="password-input" type={showPassword ? 'text' : 'password'} placeholder="Password"
                        value={password} onChange={(e) => setPassword(e.target.value)}
                        className={styles.input} aria-label="Password" style={{ paddingRight: '3rem' }} />
                      <button type="button" className={styles.passwordToggle}
                        onClick={() => setShowPassword(!showPassword)}
                        aria-label={showPassword ? 'Hide password' : 'Show password'}>
                        {showPassword ? '🙈' : '👁️'}
                      </button>
                    </div>
                    {isRegistering && password.length > 0 && (
                      <>
                        <div className={strengthClass} style={{ height: 4, borderRadius: 2, marginTop: '0.5rem', transition: 'all 0.3s' }} />
                        <div className={styles.strengthLabel} style={{ color: strength === 'strong' ? '#14b8a6' : strength === 'medium' ? '#d97706' : '#ef4444' }}>
                          {strengthLabel}
                        </div>
                        <ul className={styles.requirements}>
                          <li className={passwordChecks.length ? styles.requirementMet : styles.requirementUnmet}>{passwordChecks.length ? '✓' : '✗'} At least 8 characters</li>
                          <li className={passwordChecks.uppercase ? styles.requirementMet : styles.requirementUnmet}>{passwordChecks.uppercase ? '✓' : '✗'} Uppercase letter</li>
                          <li className={passwordChecks.lowercase ? styles.requirementMet : styles.requirementUnmet}>{passwordChecks.lowercase ? '✓' : '✗'} Lowercase letter</li>
                          <li className={passwordChecks.digit ? styles.requirementMet : styles.requirementUnmet}>{passwordChecks.digit ? '✓' : '✗'} Number</li>
                          <li className={passwordChecks.special ? styles.requirementMet : styles.requirementUnmet}>{passwordChecks.special ? '✓' : '✗'} Special character</li>
                        </ul>
                      </>
                    )}
                    <div className={styles.buttonGroup}>
                      <button type="button" className={styles.button} disabled={loading}
                        aria-label="Register a new account"
                        style={isRegistering ? {} : { background: 'transparent', border: '1px solid var(--lp-border)', color: 'var(--lp-text-muted)' }}
                        onClick={(e) => { if (!isRegistering) { setIsRegistering(true); clearFeedback(); } else { handleRegister(e); } }}>
                        {loading && isRegistering ? 'Registering...' : 'Register'}
                      </button>
                      <button type="button" className={styles.button} disabled={loading}
                        aria-label="Log in to your account"
                        style={!isRegistering ? {} : { background: 'transparent', border: '1px solid var(--lp-border)', color: 'var(--lp-text-muted)' }}
                        onClick={(e) => { if (isRegistering) { setIsRegistering(false); clearFeedback(); } else { handleLogin(e); } }}>
                        {loading && !isRegistering ? 'Logging in...' : 'Log In'}
                      </button>
                    </div>
                  </form>
                )}
              </div>
              {message && <p className={styles.message} role="alert">{message}</p>}
              {error   && <p className={styles.error}   role="alert">{error}</p>}
            </main>
          </div>
        </div>
      </section>

      {/* ═══ FOOTER ═══ */}
      <footer className={styles.lpFooter}>
        <div className={styles.lpFooterBrand}>
          <span className={styles.lpNavLogo} style={{ width: 28, height: 28, fontSize: '0.7rem' }}>SM</span>
          <span className={styles.lpNavName}>SelfMonitor</span>
        </div>
        <p className={styles.lpFooterText}>© 2026 SelfMonitor · Built for UK freelancers · HMRC MTD ready · GDPR compliant</p>
      </footer>

    </div>
    </>
  );
}
