import Head from 'next/head';
import Link from 'next/link';
import styles from '../styles/Landing.module.css';

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
            <h1 className={styles.heroHeadline}>
              Financial Freedom for the Self-Employed
            </h1>
            <p className={styles.heroSub}>
              AI-powered banking, taxes, and insights — all in one platform.
              From receipt to HMRC submission in minutes, not hours.
            </p>

            <div className={styles.heroButtons}>
              <a href="#pricing" className={styles.btnPrimary}>
                Start Free
              </a>
              <a href="#pricing" className={styles.btnSecondary}>
                See Pricing
              </a>
            </div>

            <div className={styles.storeButtons}>
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

            <div className={styles.trustPills}>
              <span className={styles.trustPill}>🔒 Bank-Grade Security</span>
              <span className={styles.trustPill}>🇬🇧 HMRC Compliant</span>
              <span className={styles.trustPill}>⚡ AI-Powered</span>
              <span className={styles.trustPill}>📱 Web + Mobile</span>
            </div>

            <div className={styles.statsRow}>
              <div className={styles.statItem}>
                <span className={styles.statValue}>23+</span>
                <span className={styles.statLabel}>Services</span>
              </div>
              <div className={styles.statItem}>
                <span className={styles.statValue}>2FA</span>
                <span className={styles.statLabel}>Security</span>
              </div>
              <div className={styles.statItem}>
                <span className={styles.statValue}>5</span>
                <span className={styles.statLabel}>Languages</span>
              </div>
              <div className={styles.statItem}>
                <span className={styles.statValue}>99.9%</span>
                <span className={styles.statLabel}>Uptime</span>
              </div>
            </div>
          </div>
        </section>

        {/* ====== CHALLENGE ====== */}
        <section className={styles.sectionElevated}>
          <div className={styles.container}>
            <h2 className={styles.sectionHeading}>
              Self-Employment Shouldn&rsquo;t Mean Self-Struggle
            </h2>

            <div className={styles.grid3}>
              <div className={`${styles.card} ${styles.cardOnElevated}`}>
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
              </div>

              <div className={`${styles.card} ${styles.cardOnElevated}`}>
                <span className={styles.cardIcon}>💸</span>
                <h3 className={styles.cardTitle}>Missed tax deductions</h3>
                <p className={styles.cardDesc}>
                  Without AI categorisation, legitimate expenses slip through the
                  cracks.
                  <span className={styles.challengeHighlight}>
                    UK freelancers overpay £1,200/year in taxes on average
                  </span>
                </p>
              </div>

              <div className={`${styles.card} ${styles.cardOnElevated}`}>
                <span className={styles.cardIcon}>📄</span>
                <h3 className={styles.cardTitle}>Receipts in a shoebox</h3>
                <p className={styles.cardDesc}>
                  Paper receipts fade. Email receipts get buried. Audits happen.
                  <span className={styles.challengeHighlight}>
                    HMRC requires 5 years of records — can you find them?
                  </span>
                </p>
              </div>
            </div>
          </div>
        </section>

        {/* ====== SOLUTIONS ====== */}
        <section id="features" className={styles.section}>
          <div className={styles.container}>
            <h2 className={styles.sectionHeading}>
              One Platform. Every Tool You Need.
            </h2>
            <p className={styles.sectionSub}>
              From bank connection to tax submission — automated.
            </p>

            <div className={styles.grid3}>
              <div className={styles.card}>
                <span className={styles.cardIcon}>🏦</span>
                <h3 className={styles.cardTitle}>Open Banking</h3>
                <p className={styles.cardDesc}>
                  Connect your banks. Transactions import automatically via
                  secure Open Banking APIs.
                </p>
              </div>

              <div className={styles.card}>
                <span className={styles.cardIcon}>🤖</span>
                <h3 className={styles.cardTitle}>AI Categorization</h3>
                <p className={styles.cardDesc}>
                  Every transaction categorized instantly by AI. No more manual
                  tagging.
                </p>
              </div>

              <div className={styles.card}>
                <span className={styles.cardIcon}>📱</span>
                <h3 className={styles.cardTitle}>Receipt Scanner</h3>
                <p className={styles.cardDesc}>
                  Snap a photo. OCR extracts vendor, amount, and date in
                  seconds.
                </p>
              </div>

              <div className={styles.card}>
                <span className={styles.cardIcon}>💰</span>
                <h3 className={styles.cardTitle}>Tax Calculator</h3>
                <p className={styles.cardDesc}>
                  Real-time UK tax estimates. One-click HMRC submission when
                  you&rsquo;re ready.
                </p>
              </div>

              <div className={styles.card}>
                <span className={styles.cardIcon}>📈</span>
                <h3 className={styles.cardTitle}>Cash Flow Forecast</h3>
                <p className={styles.cardDesc}>
                  30-day AI predictions so you never run out of cash.
                </p>
              </div>

              <div className={styles.card}>
                <span className={styles.cardIcon}>🔍</span>
                <h3 className={styles.cardTitle}>Smart Search</h3>
                <p className={styles.cardDesc}>
                  Ask &ldquo;Where did I buy coffee last month?&rdquo; — AI
                  finds it instantly.
                </p>
              </div>
            </div>
          </div>
        </section>

        {/* ====== MOBILE APP ====== */}
        <section className={styles.sectionElevated}>
          <div className={styles.container}>
            <div className={styles.mobileShowcase}>
              <div className={styles.mobileContent}>
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
              </div>

              <div className={styles.mobilePreview}>
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
              </div>
            </div>
          </div>
        </section>

        {/* ====== WHO IT'S FOR ====== */}
        <section className={styles.sectionElevated}>
          <div className={styles.container}>
            <h2 className={styles.sectionHeading}>
              Built for Every Self-Employed Professional
            </h2>

            <div className={styles.grid4}>
              <div className={`${styles.card} ${styles.cardOnElevated}`}>
                <span className={styles.cardIcon}>💻</span>
                <h3 className={styles.cardTitle}>Freelance Developers</h3>
                <p className={styles.cardDesc}>
                  Track project income, expenses, and IR35 status effortlessly.
                </p>
              </div>

              <div className={`${styles.card} ${styles.cardOnElevated}`}>
                <span className={styles.cardIcon}>🎨</span>
                <h3 className={styles.cardTitle}>
                  Designers &amp; Creatives
                </h3>
                <p className={styles.cardDesc}>
                  Receipt scanning, client invoicing, and portfolio expense
                  tracking.
                </p>
              </div>

              <div className={`${styles.card} ${styles.cardOnElevated}`}>
                <span className={styles.cardIcon}>🚗</span>
                <h3 className={styles.cardTitle}>Sole Traders</h3>
                <p className={styles.cardDesc}>
                  Mileage tracking, stock expenses, and quarterly VAT — sorted.
                </p>
              </div>

              <div className={`${styles.card} ${styles.cardOnElevated}`}>
                <span className={styles.cardIcon}>📋</span>
                <h3 className={styles.cardTitle}>Consultants</h3>
                <p className={styles.cardDesc}>
                  Multi-client billing, expense reports, and tax forecasting in
                  one place.
                </p>
              </div>
            </div>
          </div>
        </section>

        {/* ====== TRUST & SECURITY ====== */}
        <section className={styles.section}>
          <div className={styles.container}>
            <h2 className={styles.sectionHeading}>
              Your Data. Your Control. Bank-Grade Security.
            </h2>

            <div className={styles.grid4}>
              <div className={styles.card}>
                <span className={styles.cardIcon}>🔐</span>
                <h3 className={styles.cardTitle}>Two-Factor Auth</h3>
                <p className={styles.cardDesc}>
                  TOTP-based 2FA with authenticator apps. Your account stays
                  yours.
                </p>
              </div>

              <div className={styles.card}>
                <span className={styles.cardIcon}>🛡️</span>
                <h3 className={styles.cardTitle}>Fraud Detection</h3>
                <p className={styles.cardDesc}>
                  Real-time anomaly detection with ML scoring flags suspicious
                  activity.
                </p>
              </div>

              <div className={styles.card}>
                <span className={styles.cardIcon}>📋</span>
                <h3 className={styles.cardTitle}>Audit Trail</h3>
                <p className={styles.cardDesc}>
                  Every action logged. Full GDPR compliance baked in from day
                  one.
                </p>
              </div>

              <div className={styles.card}>
                <span className={styles.cardIcon}>🔒</span>
                <h3 className={styles.cardTitle}>Encrypted Storage</h3>
                <p className={styles.cardDesc}>
                  Vault-secured credentials. S3-encrypted documents. Zero
                  compromise.
                </p>
              </div>
            </div>
          </div>
        </section>

        {/* ====== PRICING ====== */}
        <section id="pricing" className={styles.sectionElevated}>
          <div className={styles.container}>
            <h2 className={styles.sectionHeading}>
              Simple Pricing. No Surprises.
            </h2>
            <p className={styles.sectionSub}>
              Start free. Upgrade when you&rsquo;re ready.
            </p>

            <div className={styles.pricingGrid}>
              {/* Free */}
              <div className={styles.pricingCard}>
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
              </div>

              {/* Starter */}
              <div className={styles.pricingCard}>
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
              </div>

              {/* Pro — POPULAR */}
              <div
                className={`${styles.pricingCard} ${styles.pricingPopular}`}
              >
                <span className={styles.popularBadge}>Popular</span>
                <p className={styles.pricingName}>Pro</p>
                <p className={styles.pricingPrice}>
                  £19<span>/mo</span>
                </p>
                <ul className={styles.pricingFeatures}>
                  <li>Unlimited banks</li>
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
              </div>

              {/* Business */}
              <div className={styles.pricingCard}>
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
              </div>
            </div>
          </div>
        </section>

        {/* ====== CTA ====== */}
        <section className={styles.cta}>
          <div className={styles.container}>
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
