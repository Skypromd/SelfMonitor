import { motion, useInView } from 'framer-motion';
import type { LucideIcon } from 'lucide-react';
import {
  ArrowRight,
  Archive,
  Banknote,
  BarChart3,
  Bell,
  Bot,
  Building2,
  Calculator,
  CalendarClock,
  CalendarDays,
  Camera,
  Car,
  CheckCircle2,
  Cloud,
  CircleDollarSign,
  ClipboardList,
  Crown,
  CreditCard,
  FileCheck,
  FileSearch,
  FileText,
  Flame,
  Fingerprint,
  Globe2,
  Home,
  KeyRound,
  Landmark,
  Laptop,
  Layers,
  LineChart,
  ListChecks,
  ListPlus,
  Lock,
  Mic,
  Mail,
  MonitorSmartphone,
  Moon,
  Palette,
  Phone,
  Plug,
  PieChart,
  Play,
  PoundSterling,
  Receipt,
  Rocket,
  Scale,
  Shield,
  ShieldCheck,
  Smartphone,
  Sparkles,
  Star,
  Store,
  Target,
  TrendingUp,
  User,
  Users,
  Wallet,
  WifiOff,
  Zap,
} from 'lucide-react';
import dynamic from 'next/dynamic';
import Head from 'next/head';
import Link from 'next/link';
import { useEffect, useRef, useState, type ReactNode } from 'react';
import homeStyles from '../styles/Home.module.css';
import styles from '../styles/Landing.module.css';

/** Demo transactions inside hero phone mockup (shared palette with pricing / accents) */
const HERO_PHONE_TX = [
  { name: 'Client Invoice #42', amt: '+£1,200', color: '#4ade80' },
  { name: 'Adobe CC Subscription', amt: '-£55', color: '#f87171' },
  { name: 'Co-working Space', amt: '-£120', color: '#f87171' },
  { name: 'Freelance Project', amt: '+£850', color: '#4ade80' },
] as const;

/** Semantic icon colours — aligned with pricing cards (teal / violet / amber …) */
const ACCENT = {
  teal: styles.accentTeal,
  tealDeep: styles.accentTealDeep,
  violet: styles.accentViolet,
  violetStrong: styles.accentVioletStrong,
  amber: styles.accentAmber,
  amberDeep: styles.accentAmberDeep,
  sky: styles.accentSky,
  rose: styles.accentRose,
  emerald: styles.accentEmerald,
  blue: styles.accentBlue,
  indigo: styles.accentIndigo,
  cyan: styles.accentCyan,
  muted: styles.accentMuted,
  greenPlay: styles.accentGreenPlay,
} as const;

type AccentKey = keyof typeof ACCENT;

const CATEGORY_ICON_SKIN: Record<string, string> = {
  tax: `${styles.categoryIconWrap} ${styles.iconCategoryTax}`,
  money: `${styles.categoryIconWrap} ${styles.iconCategoryMoney}`,
  invoicing: `${styles.categoryIconWrap} ${styles.iconCategoryInvoicing}`,
  mortgage: `${styles.categoryIconWrap} ${styles.iconCategoryMortgage}`,
  ai: `${styles.categoryIconWrap} ${styles.iconCategoryAi}`,
};

const SERVICE_CATEGORY_ACCENT: Record<string, AccentKey> = {
  tax: 'tealDeep',
  money: 'emerald',
  invoicing: 'violetStrong',
  mortgage: 'amberDeep',
  ai: 'indigo',
};

const CashFlowChart = dynamic(() => import('../components/charts/CashFlowChart'), { ssr: false });
const ExpenseChart = dynamic(() => import('../components/charts/ExpenseChart'), { ssr: false });
const SavingsChart = dynamic(() => import('../components/charts/SavingsChart'), { ssr: false });

const fadeUp = {
  initial: { opacity: 0, y: 32 },
  whileInView: { opacity: 1, y: 0 },
  transition: { type: 'spring' as const, stiffness: 120, damping: 26 },
  viewport: { once: true, margin: '-50px' },
};

const staggerContainer = {
  initial: {},
  whileInView: { transition: { staggerChildren: 0.08, delayChildren: 0.04 } },
  viewport: { once: true },
};

const staggerItem = {
  initial: { opacity: 0, y: 22, scale: 0.98 },
  whileInView: { opacity: 1, y: 0, scale: 1 },
  transition: { type: 'spring' as const, stiffness: 280, damping: 22 },
};

/** Plain bullet, or cloud row with GB highlighted in gold */
type PricingFeatureLine =
  | { icon: LucideIcon; text: string }
  | { icon: LucideIcon; cloudBackup: string };

/**
 * Public pricing — amounts are **excluding VAT** (UK VAT applied at checkout where applicable).
 * Feature tiers align with auth-service `PLAN_FEATURES` (see `docs/PLAN_FEATURES_TABLE.md`). One subscription = one user.
 * Interface language limits: Starter = English only; Growth = pick one locale; Pro = two; Business = all.
 */
const PRICING_PLANS: ReadonlyArray<{
  plan: 'starter' | 'growth' | 'pro' | 'business';
  name: string;
  Icon: LucideIcon;
  iconColor: string;
  price: string;
  popular?: boolean;
  features: readonly PricingFeatureLine[];
  cta: string;
}> = [
  {
    plan: 'starter',
    name: 'Starter',
    Icon: Flame,
    iconColor: 'var(--lp-accent-teal)',
    price: '£12',
    features: [
      { icon: Landmark, text: '1 Open Banking connection · 1 sync / day' },
      { icon: BarChart3, text: 'Up to 500 transactions / month · ~90 days history focus' },
      { icon: Sparkles, text: 'CIS refund tracker, statement upload & verified vs unverified flow' },
      { icon: Receipt, text: 'Receipt capture & OCR' },
      { icon: CalendarClock, text: 'HMRC MTD guided submit (draft → confirm) & filing reminders' },
      { icon: MonitorSmartphone, text: 'Web + iOS & Android apps' },
      { icon: Globe2, text: 'Interface language: English only' },
      { icon: PieChart, text: 'Profit & loss & tax estimates' },
      { icon: Cloud, cloudBackup: '2 GB' },
      { icon: Archive, text: 'Secure report storage — up to 6 years' },
      { icon: Mail, text: 'Email support' },
    ],
    cta: 'Start Free Trial',
  },
  {
    plan: 'growth',
    name: 'Growth',
    Icon: TrendingUp,
    iconColor: '#8b5cf6',
    price: '£15',
    features: [
      { icon: Landmark, text: '2 Open Banking connections · 3 sync / day' },
      { icon: BarChart3, text: 'Up to 2,000 transactions / month · 12 months history' },
      { icon: ListPlus, text: 'Everything in Starter, plus:' },
      { icon: Globe2, text: 'One interface language — your choice from available locales' },
      { icon: FileText, text: 'Invoices & branded PDF export' },
      { icon: LineChart, text: 'Cash-flow forecast (30 / 60 / 90 days)' },
      { icon: Calculator, text: 'Full tax calculator & liability estimates' },
      { icon: Cloud, cloudBackup: '6 GB' },
      { icon: Archive, text: 'Secure report storage — up to 6 years' },
      { icon: Mail, text: 'Priority email support' },
    ],
    cta: 'Start Free Trial',
  },
  {
    plan: 'pro',
    name: 'Pro',
    Icon: Rocket,
    iconColor: 'var(--lp-accent-teal)',
    price: '£18',
    popular: true,
    features: [
      { icon: Landmark, text: '5 Open Banking connections · 10 sync / day' },
      { icon: BarChart3, text: 'Up to 5,000 transactions / month · 24 months history' },
      { icon: Bot, text: 'SelfMate AI assistant (unlimited)' },
      { icon: FileCheck, text: 'HMRC MTD direct-style submit (full fraud context) · VAT returns (Pro+)' },
      { icon: FileSearch, text: 'Smart document search' },
      { icon: LineChart, text: 'Mortgage-readiness & BI-style reports' },
      { icon: Cloud, cloudBackup: '10 GB' },
      { icon: Archive, text: 'Secure report storage — up to 6 years' },
      { icon: Plug, text: 'REST API access' },
      { icon: Phone, text: 'Phone & priority support' },
    ],
    cta: 'Start Pro Trial',
  },
  {
    plan: 'business',
    name: 'Business',
    Icon: Crown,
    iconColor: '#d97706',
    price: '£28',
    features: [
      { icon: Landmark, text: '10 Open Banking connections · 25 sync / day · 36 months history' },
      { icon: Zap, text: 'High transaction volume' },
      { icon: ListPlus, text: 'Everything in Pro, plus:' },
      { icon: Globe2, text: 'All interface languages included' },
      { icon: Users, text: 'Single-user licence; higher limits & white-label for practices' },
      { icon: ShieldCheck, text: 'Compliance trail & audit-friendly exports' },
      { icon: Store, text: 'Partner marketplace & referral tools' },
      { icon: Palette, text: 'White-label client reports' },
      { icon: Cloud, cloudBackup: '25 GB' },
      { icon: Archive, text: 'Secure report storage — up to 6 years' },
      { icon: User, text: 'Dedicated account manager' },
    ],
    cta: 'Start Business Trial',
  },
];

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

type ServiceItem = {
  title: string;
  desc: string;
  tags?: string[];
  Icon: LucideIcon;
};

type ServiceCategory = {
  key: string;
  eyebrow: string;
  title: string;
  subtitle: string;
  CatIcon: LucideIcon;
  items: ServiceItem[];
};

/** Mirrors README / platform capabilities — grouped for scanning */
const SERVICE_CATEGORIES: ServiceCategory[] = [
  {
    key: 'tax',
    eyebrow: 'Tax & HMRC',
    title: 'Making Tax Digital, end-to-end',
    subtitle:
      'Quarterly updates, final declaration, calculators, and HMRC routes — built for MTD ITSA and tested in sandbox.',
    CatIcon: Calculator,
    items: [
      {
        title: 'MTD submissions',
        desc: 'Periodic updates and final declaration with review before anything reaches HMRC.',
        tags: ['MTD ITSA', 'HMRC'],
        Icon: FileCheck,
      },
      {
        title: 'Tax calculators',
        desc: 'PAYE, self-employed, rental, CIS, dividends, crypto & more — consistent estimates in one place.',
        tags: ['7+ engines'],
        Icon: Calculator,
      },
      {
        title: 'Obligations & deadlines',
        desc: 'Calendar-driven reminders so quarterly windows and declarations are never a surprise.',
        tags: ['Calendar'],
        Icon: CalendarClock,
      },
      {
        title: 'Adjustments & compliance',
        desc: 'Loss adjustments, BSAS-style workflows, and audit-friendly trails for investigations.',
        tags: ['Compliance'],
        Icon: Scale,
      },
    ],
  },
  {
    key: 'money',
    eyebrow: 'Banking & money',
    title: 'Transactions, sync, and control',
    subtitle:
      'Connect accounts, import activity, and keep ledgers aligned with consent and compliance services behind the scenes.',
    CatIcon: Landmark,
    items: [
      {
        title: 'Bank sync',
        desc: 'Secure bank connections with manual sync — you stay in control of when data imports.',
        tags: ['Open Banking'],
        Icon: Landmark,
      },
      {
        title: 'Smart categorisation',
        desc: 'Merchant-aware categories (incl. 200+ UK patterns) so P&L stays clean without spreadsheets.',
        tags: ['AI rules'],
        Icon: PieChart,
      },
      {
        title: 'Transactions hub',
        desc: 'Full history, receipt links, reconciliation helpers, and exports for your accountant.',
        tags: ['Core ledger'],
        Icon: Banknote,
      },
      {
        title: 'Consent & audit',
        desc: 'Consent logging plus compliance signals so data use stays transparent and defensible.',
        tags: ['GDPR'],
        Icon: ShieldCheck,
      },
    ],
  },
  {
    key: 'invoicing',
    eyebrow: 'Invoices & billing',
    title: 'Get paid, stay organised',
    subtitle:
      'Professional invoicing with automation, Stripe-backed subscriptions, and documents that match your books.',
    CatIcon: FileText,
    items: [
      {
        title: 'Invoicing & chasing',
        desc: 'Create, send, auto-chase, recurring invoices, and payment links with PDF output.',
        tags: ['Invoices'],
        Icon: FileText,
      },
      {
        title: 'Receipts & OCR',
        desc: 'Scan or upload — text extraction and matching to draft transactions faster.',
        tags: ['Documents'],
        Icon: Receipt,
      },
      {
        title: 'Subscription billing',
        desc: 'Plan tiers, upgrades, and checkout flows that map to your SelfMonitor subscription.',
        tags: ['Stripe'],
        Icon: CreditCard,
      },
      {
        title: 'Partner & B2B tools',
        desc: 'Partner registry hooks for referrals, reporting scopes, and shared workflows.',
        tags: ['Partners'],
        Icon: Store,
      },
    ],
  },
  {
    key: 'mortgage',
    eyebrow: 'Mortgage & analytics',
    title: 'Readiness, cash flow, and insight',
    subtitle:
      'Mortgage scoring, affordability views, and operational analytics — the same data that powers tax stays in sync.',
    CatIcon: Home,
    items: [
      {
        title: 'Mortgage readiness',
        desc: 'Readiness score, affordability, stamp duty context, and lender-style insights for UK borrowers.',
        tags: ['8+ lenders data'],
        Icon: Home,
      },
      {
        title: 'Cash flow & BI',
        desc: 'Forecasts, dashboards, and business intelligence views fed from your real activity.',
        tags: ['Analytics'],
        Icon: LineChart,
      },
      {
        title: 'FinOps & monitoring',
        desc: 'Operational signals on money movement — spot drift before it hits your runway.',
        tags: ['FinOps'],
        Icon: Target,
      },
      {
        title: 'Documents vault',
        desc: 'Secure storage with encrypted artefacts — contracts, IDs, and statements in one vaulted place.',
        tags: ['Vault'],
        Icon: Building2,
      },
    ],
  },
  {
    key: 'ai',
    eyebrow: 'AI & growth',
    title: 'Assistant, voice, and scale',
    subtitle:
      'Multilingual guidance, voice interfaces, and growth loops — so the product works across web, mobile, and support.',
    CatIcon: Sparkles,
    items: [
      {
        title: 'SelfMate AI agent',
        desc: 'Context-aware help across tax, mortgage, and expenses with tool-backed answers.',
        tags: ['Agent'],
        Icon: Sparkles,
      },
      {
        title: 'Voice gateway',
        desc: 'Speech-to-text and text-to-speech for hands-free capture and answers on the go.',
        tags: ['STT / TTS'],
        Icon: Mic,
      },
      {
        title: 'Support & search',
        desc: 'Support AI plus semantic document search — find the right record without digging.',
        tags: ['Q&A'],
        Icon: FileSearch,
      },
      {
        title: 'Referrals & languages',
        desc: 'Referral programmes plus localisation — how many UI languages you can use depends on your subscription tier.',
        tags: ['Locales'],
        Icon: Globe2,
      },
    ],
  },
];

/** Bottom tab bar — vector icons, Revolut-style (matches pricing icon wraps) */
const PHONE_NAV_ITEMS: { Icon: LucideIcon; label: string; accent: AccentKey }[] = [
  { Icon: Home, label: 'Home', accent: 'teal' },
  { Icon: Wallet, label: 'Money', accent: 'emerald' },
  { Icon: Camera, label: 'Scan', accent: 'amber' },
  { Icon: PoundSterling, label: 'Tax', accent: 'violetStrong' },
  { Icon: User, label: 'Me', accent: 'cyan' },
];

/** Hero trust row — same squircle + line icon language as pricing cards */
const TRUST_PILLS: { Icon: LucideIcon; label: string; accent: AccentKey }[] = [
  { Icon: Lock, label: 'Bank-Grade Security', accent: 'teal' },
  { Icon: Landmark, label: 'HMRC Compliant', accent: 'violetStrong' },
  { Icon: Zap, label: 'AI-Powered', accent: 'amber' },
  { Icon: MonitorSmartphone, label: 'Web + Mobile', accent: 'cyan' },
  { Icon: CheckCircle2, label: 'MTD Ready', accent: 'emerald' },
];

/** Platform intro chips — pairs with “33 microservices” etc. */
const PLATFORM_CHIPS: { Icon: LucideIcon; text: string; muted?: boolean; accent?: AccentKey }[] = [
  { Icon: Layers, text: '33 microservices', accent: 'teal' },
  { Icon: ShieldCheck, text: 'HMRC MTD ready', accent: 'emerald' },
  { Icon: Globe2, text: 'Web + mobile · locales by plan', muted: true },
];

const CHALLENGE_CARDS: { Icon: LucideIcon; title: string; body: ReactNode; accent: AccentKey }[] = [
  {
    Icon: BarChart3,
    accent: 'sky',
    title: 'Hours lost on manual bookkeeping',
    body: (
      <>
        Spreadsheets, bank exports, copy-paste — the admin never ends.
        <span className={styles.challengeHighlight}>Average freelancer spends 5 hrs/week on admin</span>
      </>
    ),
  },
  {
    Icon: CircleDollarSign,
    accent: 'rose',
    title: 'Missed tax deductions',
    body: (
      <>
        Without AI categorisation, legitimate expenses slip through the cracks.
        <span className={styles.challengeHighlight}>UK freelancers overpay £1,200/year in taxes on average</span>
      </>
    ),
  },
  {
    Icon: FileText,
    accent: 'amberDeep',
    title: 'Receipts in a shoebox',
    body: (
      <>
        Paper receipts fade. Email receipts get buried. Audits happen.
        <span className={styles.challengeHighlight}>HMRC requires 5 years of records — can you find them?</span>
      </>
    ),
  },
];

const AUDIENCE_CARDS: { Icon: LucideIcon; title: string; desc: string; accent: AccentKey }[] = [
  { Icon: Laptop, title: 'Freelance Developers', desc: 'Track project income, expenses, and IR35 status effortlessly.', accent: 'sky' },
  { Icon: Palette, title: 'Designers & Creatives', desc: 'Receipt scanning, client invoicing, and portfolio expense tracking.', accent: 'violetStrong' },
  { Icon: Car, title: 'Sole Traders', desc: 'Mileage tracking, stock expenses, and quarterly VAT — sorted.', accent: 'amberDeep' },
  { Icon: ClipboardList, title: 'Consultants', desc: 'Multi-client billing, expense reports, and tax forecasting in one place.', accent: 'teal' },
];

const SECURITY_CARDS: { Icon: LucideIcon; title: string; desc: string; accent: AccentKey }[] = [
  { Icon: KeyRound, title: 'Two-Factor Auth', desc: 'TOTP-based 2FA with authenticator apps. Your account stays yours.', accent: 'emerald' },
  { Icon: Shield, title: 'Fraud Detection', desc: 'Real-time anomaly detection with ML scoring flags suspicious activity.', accent: 'blue' },
  { Icon: ListChecks, title: 'Audit Trail', desc: 'Every action logged. Full GDPR compliance baked in from day one.', accent: 'teal' },
  { Icon: Lock, title: 'Encrypted Storage', desc: 'Vault-secured credentials. S3-encrypted documents. Zero compromise.', accent: 'amberDeep' },
];

const MOBILE_FEATURES: { Icon: LucideIcon; text: string; accent: AccentKey }[] = [
  { Icon: Camera, text: 'Scan receipts with your camera — OCR extracts data instantly', accent: 'teal' },
  { Icon: Bell, text: 'Push notifications for tax deadlines and unusual transactions', accent: 'amber' },
  { Icon: LineChart, text: 'Check your cash flow forecast anytime, anywhere', accent: 'violetStrong' },
  { Icon: Fingerprint, text: 'Connect bank accounts with biometric authentication', accent: 'emerald' },
  { Icon: WifiOff, text: 'Offline mode — view your data even without internet', accent: 'muted' },
  { Icon: Moon, text: 'Dark theme designed for comfortable night-time use', accent: 'indigo' },
];

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
  return (
    <>
      <Head>
        <title>SelfMonitor — Financial Freedom for the Self-Employed</title>
        <meta
          name="description"
          content="SelfMonitor — MTD tax, invoicing, mortgage readiness, bank sync, AI assistant, and 30+ services behind one UK self-employed platform. Web and mobile."
        />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
      </Head>

      {/* ====== NAVBAR ====== */}
      <nav className={styles.navbar}>
        <div className={styles.navInner}>
          <Link href="/" className={styles.navBrandRow} aria-label="SelfMonitor home">
            <span className={styles.navMark} aria-hidden>
              SM
            </span>
            <span className={styles.navWordmark}>SelfMonitor</span>
          </Link>
          <div className={styles.navLinks}>
            <a href="#services">Platform</a>
            <a href="#pricing">Pricing</a>
            <a href="#testimonials">Reviews</a>
          </div>
          <Link href="/login" className={styles.btnPrimary} style={{ height: '38px', padding: '0 1.25rem', fontSize: '0.9rem' }}>
            Sign In
          </Link>
        </div>
      </nav>

      <div className={styles.page}>
        {/* ====== HERO (shared Home.module design: split + phone + floating badges) ====== */}
        <section className={homeStyles.lpHero} aria-label="Hero">
          <motion.div
            className={homeStyles.lpHeroContent}
            initial={{ opacity: 0, y: 24 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.65 }}
          >
            <div className={homeStyles.lpHeroBadge}>
              <Smartphone size={13} strokeWidth={2} aria-hidden />
              Mobile &amp; Web App
            </div>
            <h1 className={homeStyles.lpHeroH1}>
              Your complete<br />
              <span className={homeStyles.lpHeroAccent}>financial command centre</span>
              <br />
              for UK freelancers
            </h1>
            <p className={homeStyles.lpHeroSub}>
              MTD filing, invoicing, mortgage insights, bank sync, and AI — thirty-plus services behind one gateway.
              Invoicing · AI tax · HMRC deadlines · cash flow — in one beautifully designed app.
            </p>
            <div className={homeStyles.lpHeroCtas}>
              <Link href="/register" className={homeStyles.lpCtaGold}>
                Start for Free <ArrowRight size={16} strokeWidth={2} aria-hidden />
              </Link>
              <a href="#services" className={homeStyles.lpCtaSecondary}>
                Explore platform
              </a>
            </div>
            <div className={homeStyles.lpHeroTrust}>
              <CheckCircle2 size={14} color="#0d9488" aria-hidden />
              <span>No credit card required</span>
              <CheckCircle2 size={14} color="#0d9488" aria-hidden />
              <span>HMRC MTD compliant</span>
              <CheckCircle2 size={14} color="#0d9488" aria-hidden />
              <span>GDPR ready</span>
            </div>
          </motion.div>

          <motion.div
            className={homeStyles.lpPhoneWrap}
            initial={{ opacity: 0, x: 36 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.75, delay: 0.12, ease: [0.22, 1, 0.36, 1] }}
          >
            <div className={homeStyles.lpPhone}>
              <div className={homeStyles.lpPhoneNotch} />
              <div className={homeStyles.lpPhoneScreen}>
                <div className={homeStyles.lpAppBar}>
                  <span className={homeStyles.lpAppBarTitle}>Dashboard</span>
                  <div className={homeStyles.lpAppBarAvatar}>A</div>
                </div>
                <div className={homeStyles.lpAppCards}>
                  <div
                    className={homeStyles.lpAppCard}
                    style={{ background: 'linear-gradient(135deg,#0d9488,#0891b2)' }}
                  >
                    <div className={homeStyles.lpAppCardLabel}>Net Profit</div>
                    <div className={homeStyles.lpAppCardVal}>£4,280</div>
                    <div className={homeStyles.lpAppCardSub}>↑ 12% this month</div>
                  </div>
                  <div
                    className={homeStyles.lpAppCard}
                    style={{ background: 'linear-gradient(135deg,#7c3aed,#db2777)' }}
                  >
                    <div className={homeStyles.lpAppCardLabel}>Tax Reserved</div>
                    <div className={homeStyles.lpAppCardVal}>£1,070</div>
                    <div className={homeStyles.lpAppCardSub}>20% auto-set aside</div>
                  </div>
                </div>
                <div className={homeStyles.lpAppSection}>Recent Transactions</div>
                {HERO_PHONE_TX.map((tx) => (
                  <div key={tx.name} className={homeStyles.lpAppTx}>
                    <div className={homeStyles.lpAppTxDot} style={{ background: tx.color }} />
                    <span className={homeStyles.lpAppTxName}>{tx.name}</span>
                    <span className={homeStyles.lpAppTxAmt} style={{ color: tx.color }}>
                      {tx.amt}
                    </span>
                  </div>
                ))}
                <div className={homeStyles.lpAppSection}>Tax Calendar</div>
                <div className={homeStyles.lpAppDeadline}>
                  <CalendarDays size={12} color="#f59e0b" aria-hidden />
                  <span>
                    VAT Return due in <b>14 days</b>
                  </span>
                </div>
                <div className={homeStyles.lpAppDeadline}>
                  <CalendarDays size={12} color="#4ade80" aria-hidden />
                  <span>Self Assessment — Jan 31</span>
                </div>
              </div>
              <div className={homeStyles.lpPhoneHome} />
            </div>
            <div className={`${homeStyles.lpBadge} ${homeStyles.lpBadge1}`}>
              <ShieldCheck size={14} color="#0d9488" aria-hidden />
              <span>Bank-level security</span>
            </div>
            <div className={`${homeStyles.lpBadge} ${homeStyles.lpBadge2}`}>
              <Bot size={14} color="#7c3aed" aria-hidden />
              <span>AI Tax Assistant</span>
            </div>
            <div className={`${homeStyles.lpBadge} ${homeStyles.lpBadge3}`}>
              <TrendingUp size={14} color="#16a34a" aria-hidden />
              <span>+12% profit this month</span>
            </div>
          </motion.div>
        </section>

        <section className={homeStyles.lpStats} aria-label="Key metrics">
          <motion.div
            className={homeStyles.lpStat}
            initial={{ opacity: 0 }}
            whileInView={{ opacity: 1 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5, delay: 0 }}
          >
            <div className={homeStyles.lpStatVal}>
              <AnimatedCounter target={2400} suffix="+" />
            </div>
            <div className={homeStyles.lpStatLabel}>Active freelancers</div>
          </motion.div>
          <motion.div
            className={homeStyles.lpStat}
            initial={{ opacity: 0 }}
            whileInView={{ opacity: 1 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5, delay: 0.15 }}
          >
            <div className={homeStyles.lpStatVal}>
              £<AnimatedCounter target={14} suffix="M+" />
            </div>
            <div className={homeStyles.lpStatLabel}>Invoices processed</div>
          </motion.div>
          <motion.div
            className={homeStyles.lpStat}
            initial={{ opacity: 0 }}
            whileInView={{ opacity: 1 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5, delay: 0.3 }}
          >
            <div className={homeStyles.lpStatVal}>
              <AnimatedCounter target={94} suffix="%" />
            </div>
            <div className={homeStyles.lpStatLabel}>Time saved on bookkeeping</div>
          </motion.div>
          <motion.div
            className={homeStyles.lpStat}
            initial={{ opacity: 0 }}
            whileInView={{ opacity: 1 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5, delay: 0.45 }}
          >
            <div className={homeStyles.lpStatVal}>4.8 ★</div>
            <div className={homeStyles.lpStatLabel}>App Store rating</div>
          </motion.div>
        </section>

        <section className={`${styles.container} ${styles.section}`} style={{ paddingTop: '2rem', paddingBottom: '2.5rem' }}>
          <motion.div
            className={styles.storeButtons}
            initial={{ opacity: 0, y: 12 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5 }}
            style={{ justifyContent: 'center' }}
          >
            <a href="https://apps.apple.com/app/selfmonitor" className={styles.storeButton} target="_blank" rel="noopener noreferrer">
              <span className={`${styles.storeIconWrap} ${ACCENT.teal}`} aria-hidden>
                <Smartphone size={22} strokeWidth={2} />
              </span>
              <span className={styles.storeText}>
                <small>Download on the</small>
                <strong>App Store</strong>
              </span>
            </a>
            <a href="https://play.google.com/store/apps/details?id=com.selfmonitor.app" className={styles.storeButton} target="_blank" rel="noopener noreferrer">
              <span className={`${styles.storeIconWrap} ${ACCENT.greenPlay}`} aria-hidden>
                <Play size={22} strokeWidth={2} />
              </span>
              <span className={styles.storeText}>
                <small>Get it on</small>
                <strong>Google Play</strong>
              </span>
            </a>
          </motion.div>

          <motion.div
            className={styles.trustPills}
            initial={{ opacity: 0 }}
            whileInView={{ opacity: 1 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5 }}
            style={{ justifyContent: 'center', marginTop: '1.25rem' }}
          >
            {TRUST_PILLS.map(({ Icon, label, accent }) => (
              <span key={label} className={styles.trustPill}>
                <span className={`${styles.trustPillIconWrap} ${ACCENT[accent]}`} aria-hidden>
                  <Icon size={13} strokeWidth={2.25} />
                </span>
                {label}
              </span>
            ))}
          </motion.div>
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
              {CHALLENGE_CARDS.map(({ Icon, title, body, accent }) => (
                <motion.div key={title} className={`${styles.card} ${styles.cardOnElevated}`} {...staggerItem}>
                  <span className={`${styles.cardIconWrap} ${ACCENT[accent]}`} aria-hidden>
                    <Icon size={22} strokeWidth={2} />
                  </span>
                  <h3 className={styles.cardTitle}>{title}</h3>
                  <p className={styles.cardDesc}>{body}</p>
                </motion.div>
              ))}
            </motion.div>
          </div>
        </section>

        {/* ====== CHARTS: SEE YOUR FINANCES COME ALIVE ====== */}
        <section className={styles.section}>
          <div className={styles.container}>
            <motion.div {...fadeUp}>
              <h2 className={styles.sectionHeading}>See Your Finances Come Alive</h2>
              <p className={styles.sectionSub}>Real-time charts. AI insights. Zero manual work.</p>
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

        {/* ====== PLATFORM / SERVICES (full capability map) ====== */}
        <section id="services" className={`${styles.sectionElevated} ${styles.sectionServices}`}>
          <div className={styles.container}>
            <motion.div {...fadeUp}>
              <h2 className={styles.sectionHeading}>The full platform — built for UK self-employed</h2>
              <p className={styles.sectionSub}>
                Every capability below maps to live services behind our gateway: tax engine, banking connector,
                invoicing, mortgage analytics, AI agents, and more — orchestrated for web and mobile.
              </p>
            </motion.div>

            <motion.div className={styles.servicesIntro} {...fadeUp}>
              {PLATFORM_CHIPS.map(({ Icon, text, muted, accent }) => (
                <span
                  key={text}
                  className={muted ? `${styles.platformBadge} ${styles.platformBadgeMuted}` : styles.platformBadge}
                >
                  <span
                    className={`${styles.platformBadgeIconWrap}${muted || !accent ? '' : ` ${ACCENT[accent]}`}`}
                    aria-hidden
                  >
                    <Icon size={14} strokeWidth={2.25} />
                  </span>
                  {text}
                </span>
              ))}
            </motion.div>

            {SERVICE_CATEGORIES.map((cat) => {
              const CategoryIcon = cat.CatIcon;
              const categorySkin =
                CATEGORY_ICON_SKIN[cat.key] ?? `${styles.categoryIconWrap} ${styles.iconCategoryTax}`;
              const catAccent = SERVICE_CATEGORY_ACCENT[cat.key] ?? 'teal';
              return (
                <motion.div key={cat.key} className={styles.serviceCategory} {...fadeUp}>
                  <div className={styles.categoryHeader}>
                    <div className={categorySkin} aria-hidden>
                      <CategoryIcon size={26} strokeWidth={2} />
                    </div>
                    <div className={styles.categoryTitles}>
                      <p className={styles.categoryEyebrow}>{cat.eyebrow}</p>
                      <h3 className={styles.categoryTitle}>{cat.title}</h3>
                      <p className={styles.categorySubtitle}>{cat.subtitle}</p>
                    </div>
                  </div>

                  <motion.div className={styles.servicesBento} {...staggerContainer}>
                    {cat.items.map((item) => {
                      const ItemIcon = item.Icon;
                      return (
                        <motion.div key={item.title} className={styles.serviceCardPro} {...staggerItem}>
                          <div className={styles.serviceCardInner}>
                            <div className={`${styles.cardIconSvg} ${ACCENT[catAccent]}`} aria-hidden>
                              <ItemIcon size={20} strokeWidth={2} />
                            </div>
                            <h4 className={styles.serviceCardTitle}>{item.title}</h4>
                            <p className={styles.serviceCardDesc}>{item.desc}</p>
                            {item.tags && item.tags.length > 0 && (
                              <div className={styles.serviceTags}>
                                {item.tags.map((tag) => (
                                  <span key={tag} className={styles.tagPill}>
                                    {tag}
                                  </span>
                                ))}
                              </div>
                            )}
                          </div>
                        </motion.div>
                      );
                    })}
                  </motion.div>
                </motion.div>
              );
            })}
          </div>
        </section>

        {/* ====== MOBILE APP SHOWCASE ====== */}
        <section className={styles.section}>
          <div className={styles.container}>
            <div className={styles.mobileShowcase}>
              <motion.div className={styles.mobileContent} {...fadeUp}>
                <span className={styles.mobileBadge}>
                  <span className={`${styles.mobileBadgeIconWrap} ${ACCENT.teal}`} aria-hidden>
                    <Smartphone size={14} strokeWidth={2.25} />
                  </span>
                  Mobile app
                </span>
                <h2 className={styles.sectionHeading} style={{ textAlign: 'left' }}>
                  Your Finances in Your Pocket
                </h2>
                <p className={styles.mobileDesc}>
                  Everything you can do on the web — now on your phone. Scan receipts with your camera,
                  check cash flow on the go, get instant tax estimates, and submit to HMRC from anywhere.
                </p>

                <ul className={styles.mobileFeatures}>
                  {MOBILE_FEATURES.map(({ Icon, text, accent }) => (
                    <li key={text}>
                      <span className={`${styles.mobileFeatureIconWrap} ${ACCENT[accent]}`} aria-hidden>
                        <Icon size={14} strokeWidth={2.25} />
                      </span>
                      {text}
                    </li>
                  ))}
                </ul>

                <div className={styles.storeButtonsLeft}>
                  <a href="https://apps.apple.com/app/selfmonitor" className={styles.storeButton} target="_blank" rel="noopener noreferrer">
                    <span className={`${styles.storeIconWrap} ${ACCENT.teal}`} aria-hidden>
                      <Smartphone size={22} strokeWidth={2} />
                    </span>
                    <span className={styles.storeText}>
                      <small>Download on the</small>
                      <strong>App Store</strong>
                    </span>
                  </a>
                  <a href="https://play.google.com/store/apps/details?id=com.selfmonitor.app" className={styles.storeButton} target="_blank" rel="noopener noreferrer">
                    <span className={`${styles.storeIconWrap} ${ACCENT.greenPlay}`} aria-hidden>
                      <Play size={22} strokeWidth={2} />
                    </span>
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
                      <p className={styles.phoneCardLabel}>Tax Reserve</p>
                      <p className={styles.phoneCardValue}>£2,100.00</p>
                      <p className={styles.phoneCardSub}>25% auto-saved</p>
                    </div>
                    <nav className={styles.phoneNav} aria-label="App navigation preview">
                      {PHONE_NAV_ITEMS.map(({ Icon, label, accent }) => (
                        <div key={label} className={styles.phoneNavItem}>
                          <span className={`${styles.phoneNavIconWrap} ${ACCENT[accent]}`} title={label}>
                            <Icon size={18} strokeWidth={2} aria-hidden />
                          </span>
                          <span className={styles.phoneNavLabel}>{label}</span>
                        </div>
                      ))}
                    </nav>
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
              <h2 className={styles.sectionHeading}>Built for Every Self-Employed Professional</h2>
            </motion.div>

            <motion.div className={styles.grid4} {...staggerContainer}>
              {AUDIENCE_CARDS.map(({ Icon, title, desc, accent }) => (
                <motion.div key={title} className={`${styles.card} ${styles.cardOnElevated}`} {...staggerItem}>
                  <span className={`${styles.cardIconWrap} ${ACCENT[accent]}`} aria-hidden>
                    <Icon size={22} strokeWidth={2} />
                  </span>
                  <h3 className={styles.cardTitle}>{title}</h3>
                  <p className={styles.cardDesc}>{desc}</p>
                </motion.div>
              ))}
            </motion.div>
          </div>
        </section>

        {/* ====== TRUST & SECURITY ====== */}
        <section className={styles.section}>
          <div className={styles.container}>
            <motion.div {...fadeUp}>
              <h2 className={styles.sectionHeading}>Your Data. Your Control. Bank-Grade Security.</h2>
            </motion.div>

            <motion.div className={styles.grid4} {...staggerContainer}>
              {SECURITY_CARDS.map(({ Icon, title, desc, accent }) => (
                <motion.div key={title} className={styles.card} {...staggerItem}>
                  <span className={`${styles.cardIconWrap} ${ACCENT[accent]}`} aria-hidden>
                    <Icon size={22} strokeWidth={2} />
                  </span>
                  <h3 className={styles.cardTitle}>{title}</h3>
                  <p className={styles.cardDesc}>{desc}</p>
                </motion.div>
              ))}
            </motion.div>
          </div>
        </section>

        {/* ====== TESTIMONIALS ====== */}
        <section id="testimonials" className={styles.sectionElevated}>
          <div className={styles.container}>
            <motion.div {...fadeUp}>
              <h2 className={styles.sectionHeading}>What Our Users Say</h2>
              <p className={styles.sectionSub}>Trusted by thousands of UK freelancers and sole traders.</p>
            </motion.div>

            <motion.div className={styles.testimonialGrid} {...staggerContainer}>
              {testimonials.map((t) => (
                <motion.div key={t.name} className={styles.testimonialCard} {...staggerItem}>
                  <span className={styles.testimonialStars} aria-label={`${t.stars} out of 5 stars`}>
                    {Array.from({ length: t.stars }).map((_, i) => (
                      <Star key={i} size={18} strokeWidth={2} className={styles.testimonialStarIcon} fill="currentColor" aria-hidden />
                    ))}
                  </span>
                  <p className={styles.testimonialQuote}>&ldquo;{t.quote}&rdquo;</p>
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
              <p className={styles.sectionSub}>The numbers speak for themselves — SelfMonitor pays for itself in weeks.</p>
            </motion.div>

            <motion.div className={styles.roiSection} {...fadeUp}>
              <div className={`${styles.roiColumn} ${styles.roiColumnBad}`}>
                <p className={`${styles.roiColumnTitle} ${styles.roiColumnTitleBad}`}>Without SelfMonitor</p>
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
                <p className={`${styles.roiColumnTitle} ${styles.roiColumnTitleGood}`}>With SelfMonitor</p>
                <div className={styles.roiItem}>
                  <span className={styles.roiItemLabel}>Weekly admin</span>
                  <span className={styles.roiItemValueGood}>30 min/week</span>
                </div>
                <div className={styles.roiItem}>
                  <span className={styles.roiItemLabel}>Overpaid tax</span>
                  <span className={styles.roiItemValueGood}>£0</span>
                </div>
                <div className={styles.roiItem}>
                  <span className={styles.roiItemLabel}>Pro plan (excl. VAT)</span>
                  <span className={styles.roiItemValueGood}>£21/month</span>
                </div>
                <div className={styles.roiItem}>
                  <span className={styles.roiItemLabel}>Total cost</span>
                  <span className={styles.roiItemValueGood}>£252/yr</span>
                </div>
              </div>
            </motion.div>

            <motion.div {...fadeUp} style={{ textAlign: 'center', marginTop: '2.5rem' }}>
              <p className={styles.roiTotal}>
                <AnimatedCounter target={2448} prefix="£" />/year
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
              <h2 className={styles.sectionHeading}>Choose the plan that works for you</h2>
              <p className={styles.sectionSub}>
                All plans include a 14-day free trial, mobile app access, HMRC compliance and{' '}
                <strong>secure 6-year report storage</strong> — the full retention period required by HMRC. No credit
                card required to start.
              </p>
              <p className={styles.sectionSub} style={{ marginTop: '0.75rem', opacity: 0.92, fontSize: '0.95rem' }}>
                Prices exclude VAT — UK VAT is added at checkout where applicable.
              </p>
              <p className={styles.sectionSub} style={{ marginTop: '0.5rem', opacity: 0.9, fontSize: '0.95rem' }}>
                <strong>Interface languages:</strong> Starter is English only; Growth includes one language of your
                choice; Pro includes two; Business includes every locale we offer.
              </p>
            </motion.div>

            <motion.div className={styles.pricingGrid} {...staggerContainer}>
              {PRICING_PLANS.map((p) => {
                const PlanIcon = p.Icon;
                return (
                  <motion.div
                    key={p.plan}
                    className={`${styles.pricingCard} ${p.popular ? styles.pricingPopular : ''}`}
                    {...staggerItem}
                  >
                    {p.popular ? <span className={styles.popularBadge}>Most Popular</span> : null}
                    <div className={styles.pricingIconWrap} style={{ color: p.iconColor }}>
                      <PlanIcon size={28} strokeWidth={2} />
                    </div>
                    <p className={styles.pricingTrial}>14-day free trial</p>
                    <p className={styles.pricingName}>{p.name}</p>
                    <p className={styles.pricingPrice}>
                      {p.price}
                      <span>/mo</span>
                    </p>
                    <ul className={styles.pricingFeatures}>
                      {p.features.map((f) => {
                        const FeatureIcon = f.icon;
                        const key =
                          'cloudBackup' in f ? `${p.plan}-cloud-${f.cloudBackup}` : `${p.plan}-${f.text}`;
                        const label =
                          'cloudBackup' in f ? (
                            <>
                              Secure cloud backup (
                              <span className={styles.pricingFeatureVolume}>{f.cloudBackup}</span>)
                            </>
                          ) : (
                            f.text
                          );
                        return (
                          <li key={key}>
                            <span
                              className={styles.pricingFeatureIcon}
                              style={{ color: p.iconColor }}
                              aria-hidden
                            >
                              <FeatureIcon size={15} strokeWidth={2} />
                            </span>
                            <span>{label}</span>
                          </li>
                        );
                      })}
                    </ul>
                    <Link href={`/register?plan=${p.plan}`} className={styles.btnPrimary}>
                      {p.cta}
                    </Link>
                  </motion.div>
                );
              })}
            </motion.div>
          </div>
        </section>

        {/* ====== CTA ====== */}
        <section className={styles.cta}>
          <div className={styles.container}>
            <motion.div {...fadeUp} style={{ textAlign: 'center' }}>
              <h2 className={styles.sectionHeading}>
                Ready to Take Control of Your Finances?
              </h2>
              <p className={styles.sectionSub}>
                Join thousands of UK self-employed professionals who saved 5+ hours per week.
              </p>
              <Link href="/register" className={styles.btnGoldLg}>
                Start Free — No Credit Card Required
              </Link>
              <br />
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
                <div className={styles.footerBrandRow}>
                  <span className={styles.footerMark} aria-hidden>
                    SM
                  </span>
                  <p className={styles.footerLogo}>SelfMonitor</p>
                </div>
                <p className={styles.footerTagline}>AI-powered financial tools for the self-employed.</p>
              </div>

              <div>
                <p className={styles.footerColTitle}>Product</p>
                <ul className={styles.footerLinks}>
                  <li><a href="#services">Platform</a></li>
                  <li><a href="#pricing">Pricing</a></li>
                  <li><a href="https://apps.apple.com/app/selfmonitor" target="_blank" rel="noopener noreferrer">iOS App</a></li>
                  <li><a href="https://play.google.com/store/apps/details?id=com.selfmonitor.app" target="_blank" rel="noopener noreferrer">Android App</a></li>
                  <li><a href="#services">API</a></li>
                </ul>
              </div>

              <div>
                <p className={styles.footerColTitle}>Company</p>
                <ul className={styles.footerLinks}>
                  <li><a href="#services">About</a></li>
                  <li><a href="#services">Blog</a></li>
                  <li><a href="#services">Careers</a></li>
                  <li><a href="#services">Contact</a></li>
                </ul>
              </div>

              <div>
                <p className={styles.footerColTitle}>Legal</p>
                <ul className={styles.footerLinks}>
                  <li><Link href="/privacy">Privacy Policy</Link></li>
                  <li><Link href="/terms">Terms of Service</Link></li>
                  <li><Link href="/cookies">Cookie Policy</Link></li>
                  <li><Link href="/privacy">GDPR</Link></li>
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
