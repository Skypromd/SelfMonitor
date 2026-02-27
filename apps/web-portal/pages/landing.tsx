import Head from 'next/head';
import Link from 'next/link';
import dynamic from 'next/dynamic';
import { motion, useInView } from 'framer-motion';
import { useEffect, useRef, useState } from 'react';
import styles from '../styles/Landing.module.css';

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
              <a href="#pricing" className={styles.btnPrimary}>
                Start Free
              </a>
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
              <span className={styles.trustPill}>🔒 Bank-Grade Security</span>
              <span className={styles.trustPill}>🇬🇧 HMRC Compliant</span>
              <span className={styles.trustPill}>⚡ AI-Powered</span>
              <span className={styles.trustPill}>📱 Web + Mobile</span>
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
                <span className={styles.statValue}><AnimatedCounter target={5} /></span>
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
                <span className={styles.cardIcon}>📊</span>
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
                <span className={styles.cardIcon}>💸</span>
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
                <span className={styles.cardIcon}>📄</span>
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
                From bank connection to tax submission — automated.
              </p>
            </motion.div>

            <motion.div className={styles.grid3} {...staggerContainer}>
              <motion.div className={`${styles.card} ${styles.cardOnElevated}`} {...staggerItem}>
                <span className={styles.cardIcon}>🏦</span>
                <h3 className={styles.cardTitle}>Open Banking</h3>
                <p className={styles.cardDesc}>
                  Connect your banks. Transactions import automatically via
                  secure Open Banking APIs.
                </p>
              </motion.div>

              <motion.div className={`${styles.card} ${styles.cardOnElevated}`} {...staggerItem}>
                <span className={styles.cardIcon}>🤖</span>
                <h3 className={styles.cardTitle}>AI Categorization</h3>
                <p className={styles.cardDesc}>
                  Every transaction categorized instantly by AI. No more manual
                  tagging.
                </p>
              </motion.div>

              <motion.div className={`${styles.card} ${styles.cardOnElevated}`} {...staggerItem}>
                <span className={styles.cardIcon}>📱</span>
                <h3 className={styles.cardTitle}>Receipt Scanner</h3>
                <p className={styles.cardDesc}>
                  Snap a photo. OCR extracts vendor, amount, and date in
                  seconds.
                </p>
              </motion.div>

              <motion.div className={`${styles.card} ${styles.cardOnElevated}`} {...staggerItem}>
                <span className={styles.cardIcon}>💰</span>
                <h3 className={styles.cardTitle}>Tax Calculator</h3>
                <p className={styles.cardDesc}>
                  Real-time UK tax estimates. One-click HMRC submission when
                  you&rsquo;re ready.
                </p>
              </motion.div>

              <motion.div className={`${styles.card} ${styles.cardOnElevated}`} {...staggerItem}>
                <span className={styles.cardIcon}>📈</span>
                <h3 className={styles.cardTitle}>Cash Flow Forecast</h3>
                <p className={styles.cardDesc}>
                  30-day AI predictions so you never run out of cash.
                </p>
              </motion.div>

              <motion.div className={`${styles.card} ${styles.cardOnElevated}`} {...staggerItem}>
                <span className={styles.cardIcon}>🔍</span>
                <h3 className={styles.cardTitle}>Smart Search</h3>
                <p className={styles.cardDesc}>
                  Ask &ldquo;Where did I buy coffee last month?&rdquo; — AI
                  finds it instantly.
                </p>
              </motion.div>
            </motion.div>
          </div>
        </section>

        {/* ====== MOBILE APP ====== */}
        <section className={styles.section}>
          <div className={styles.container}>
            <div className={styles.mobileShowcase}>
              <motion.div className={styles.mobileContent} {...fadeUp}>
                <span className={styles.mobileBadge}>📱 MOBILE APP</span>
                <h2 className={styles.sectionHeading} style={{ textAlign: 'left' }}>
                  Your Finances in Your Pocket
                </h2>
                <p className={styles.mobileDesc}>
                  Everything you can do on the web — now on your phone. Scan receipts with your camera,
                  check cash flow on the go, get instant tax estimates, and submit to HMRC from anywhere.
                </p>

                <ul className={styles.mobileFeatures}>
                  <li><span className={styles.mobileCheck}>✓</span> Scan receipts with your camera — OCR extracts data instantly</li>
                  <li><span className={styles.mobileCheck}>✓</span> Push notifications for tax deadlines and unusual transactions</li>
                  <li><span className={styles.mobileCheck}>✓</span> Check your cash flow forecast anytime, anywhere</li>
                  <li><span className={styles.mobileCheck}>✓</span> Connect bank accounts with biometric authentication</li>
                  <li><span className={styles.mobileCheck}>✓</span> Offline mode — view your data even without internet</li>
                  <li><span className={styles.mobileCheck}>✓</span> Dark theme designed for comfortable night-time use</li>
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
                <span className={styles.cardIcon}>💻</span>
                <h3 className={styles.cardTitle}>Freelance Developers</h3>
                <p className={styles.cardDesc}>
                  Track project income, expenses, and IR35 status effortlessly.
                </p>
              </motion.div>

              <motion.div className={`${styles.card} ${styles.cardOnElevated}`} {...staggerItem}>
                <span className={styles.cardIcon}>🎨</span>
                <h3 className={styles.cardTitle}>
                  Designers &amp; Creatives
                </h3>
                <p className={styles.cardDesc}>
                  Receipt scanning, client invoicing, and portfolio expense
                  tracking.
                </p>
              </motion.div>

              <motion.div className={`${styles.card} ${styles.cardOnElevated}`} {...staggerItem}>
                <span className={styles.cardIcon}>🚗</span>
                <h3 className={styles.cardTitle}>Sole Traders</h3>
                <p className={styles.cardDesc}>
                  Mileage tracking, stock expenses, and quarterly VAT — sorted.
                </p>
              </motion.div>

              <motion.div className={`${styles.card} ${styles.cardOnElevated}`} {...staggerItem}>
                <span className={styles.cardIcon}>📋</span>
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
                <span className={styles.cardIcon}>🔐</span>
                <h3 className={styles.cardTitle}>Two-Factor Auth</h3>
                <p className={styles.cardDesc}>
                  TOTP-based 2FA with authenticator apps. Your account stays
                  yours.
                </p>
              </motion.div>

              <motion.div className={styles.card} {...staggerItem}>
                <span className={styles.cardIcon}>🛡️</span>
                <h3 className={styles.cardTitle}>Fraud Detection</h3>
                <p className={styles.cardDesc}>
                  Real-time anomaly detection with ML scoring flags suspicious
                  activity.
                </p>
              </motion.div>

              <motion.div className={styles.card} {...staggerItem}>
                <span className={styles.cardIcon}>📋</span>
                <h3 className={styles.cardTitle}>Audit Trail</h3>
                <p className={styles.cardDesc}>
                  Every action logged. Full GDPR compliance baked in from day
                  one.
                </p>
              </motion.div>

              <motion.div className={styles.card} {...staggerItem}>
                <span className={styles.cardIcon}>🔒</span>
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
                <Link href="/" className={styles.btnSecondary}>
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
                <Link href="/" className={styles.btnPrimary}>
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
                <Link href="/" className={styles.btnPrimaryLg}>
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
                <Link href="/" className={styles.btnGold}>
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
              <Link href="/" className={styles.btnGoldLg}>
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
