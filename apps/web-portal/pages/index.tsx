import { FormEvent, useMemo, useState } from 'react';
import {
  ArrowRight,
  BarChart3,
  Bot,
  CalendarDays,
  CheckCircle2,
  ClipboardCheck,
  CreditCard,
  FileText,
  FolderOpen,
  Gift,
  Globe2,
  LineChart,
  Lock,
  ReceiptText,
  ShieldCheck,
  Smartphone,
  Store,
  TrendingUp,
  Zap,
} from 'lucide-react';
import { useTranslation } from '../hooks/useTranslation';
import styles from '../styles/Home.module.css';

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
  const { t } = useTranslation();

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
            <a href="#why" className={styles.lpNavLink}>Why Us</a>
            <a href="#get-started" className={styles.lpNavLink}>Pricing</a>
          </nav>
          <a href="#get-started" className={styles.lpNavCta}>Get Started <ArrowRight size={14} /></a>
        </div>
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
            <a href="#get-started" className={styles.lpCtaPrimary}>Start for Free <ArrowRight size={16} /></a>
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
        {STATS.map((s) => (
          <div key={s.label} className={styles.lpStat}>
            <div className={styles.lpStatVal}>{s.value}</div>
            <div className={styles.lpStatLabel}>{s.label}</div>
          </div>
        ))}
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
      </section>

      {/* ═══ APP STORE STRIP ═══ */}
      <section className={styles.lpAppStrip}>
        <Smartphone size={28} color="#0d9488" />
        <div>
          <div className={styles.lpAppStripTitle}>Available on iOS &amp; Android</div>
          <div className={styles.lpAppStripSub}>Built with React Native · Expo SDK 51 · Works offline</div>
        </div>
        <div className={styles.lpStoreBadges}>
          <div className={styles.lpStoreBadge}><span>▶</span> App Store</div>
          <div className={styles.lpStoreBadge}><span>▶</span> Google Play</div>
        </div>
      </section>

      {/* ═══ AUTH / GET STARTED ═══ */}
      <section className={styles.lpAuthSection} id="get-started">
        <div className={styles.lpAuthWrap}>
          <div className={styles.lpAuthLeft}>
            <div className={styles.lpChip}>Join 2,400+ freelancers</div>
            <h2 className={styles.lpAuthH2}>Start managing your finances smarter today</h2>
            <ul className={styles.lpAuthPerks}>
              {['Free to start — no credit card needed', 'Full access to all 12 modules', 'HMRC MTD compliant on day one', 'Set up in under 5 minutes'].map((p) => (
                <li key={p}><CheckCircle2 size={16} color="#0d9488" /> {p}</li>
              ))}
            </ul>
          </div>
          <div className={styles.lpAuthCard}>
            <main className={styles.main}>
              <h1 className={styles.title}>{t('login.title')}</h1>
              <p className={styles.description}>{t('login.description')}</p>
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
                        {loading && isRegistering ? 'Registering...' : t('login.register_button')}
                      </button>
                      <button type="button" className={styles.button} disabled={loading}
                        aria-label="Log in to your account"
                        style={!isRegistering ? {} : { background: 'transparent', border: '1px solid var(--lp-border)', color: 'var(--lp-text-muted)' }}
                        onClick={(e) => { if (isRegistering) { setIsRegistering(false); clearFeedback(); } else { handleLogin(e); } }}>
                        {loading && !isRegistering ? 'Logging in...' : t('login.login_button')}
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
  );
}
