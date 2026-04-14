import {
  Activity, BarChart2, Bot, CalendarDays, CreditCard, ExternalLink, FileText, Gift,
  Globe, Headphones, Home, LayoutDashboard, Lock, LogOut, Menu, Receipt, Send, Settings,
  ShoppingBag, User, Wallet, X,
} from 'lucide-react';
import Link from 'next/link';
import { useRouter } from 'next/router';
import { ReactNode, useEffect, useRef, useState } from 'react';
import {
  adminHostPattern,
  clientSurfaceUrl,
  isAdminHostname,
} from '../lib/adminSurface';
import { useTranslation } from '../hooks/useTranslation';
import styles from '../styles/Layout.module.css';

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

type UserSummary = { email?: string; is_admin?: boolean };

type ClientLayoutProps = {
  children: ReactNode;
  onLogout: () => void;
  user: UserSummary;
  isDarkMode?: boolean;
  onToggleTheme?: () => void;
};

type NavItem = { href: string; label: string; icon: ReactNode; external?: boolean };

const BOTTOM_NAV_TABS: NavItem[] = [
  { href: '/dashboard',    label: 'Home',         icon: <Home size={20} /> },
  { href: '/transactions', label: 'Transactions', icon: <Wallet size={20} /> },
  { href: '/reports',      label: 'Reports',      icon: <BarChart2 size={20} /> },
  { href: '/assistant',    label: 'AI',           icon: <Bot size={20} /> },
  { href: '/support',      label: 'Support',      icon: <Headphones size={20} /> },
];

export default function ClientLayout({
  children,
  onLogout,
  user,
  isDarkMode,
  onToggleTheme,
}: ClientLayoutProps) {
  const router = useRouter();
  const { t } = useTranslation();
  const { locales, locale: activeLocale } = router;
  const [langOpen, setLangOpen] = useState(false);
  const [opsHost, setOpsHost] = useState(false);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const sidebarRef = useRef<HTMLElement>(null);

  useEffect(() => {
    if (typeof window === 'undefined') return;
    const h = window.location.hostname.toLowerCase();
    setOpsHost(isAdminHostname(h) || h === adminHostPattern());
  }, []);

  // Close drawer on route change
  useEffect(() => {
    setDrawerOpen(false);
  }, [router.pathname]);

  // Close drawer on outside click
  useEffect(() => {
    if (!drawerOpen) return;
    const handler = (e: MouseEvent) => {
      if (sidebarRef.current && !sidebarRef.current.contains(e.target as Node)) {
        setDrawerOpen(false);
      }
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, [drawerOpen]);

  const clientNavItems: NavItem[] = [
    { href: '/dashboard',       label: t('nav.dashboard'),    icon: <LayoutDashboard size={17} /> },
    { href: '/activity',        label: t('nav.activity'),     icon: <Activity size={17} /> },
    { href: '/transactions',    label: t('nav.transactions'), icon: <Wallet size={17} /> },
    { href: '/documents',       label: t('nav.documents'),    icon: <FileText size={17} /> },
    { href: '/reports',         label: t('nav.reports'),      icon: <BarChart2 size={17} /> },
    { href: '/marketplace',     label: t('nav.marketplace'),  icon: <ShoppingBag size={17} /> },
    { href: '/submission',      label: t('nav.submission'),   icon: <Send size={17} /> },
    { href: '/profile',         label: t('nav.profile'),      icon: <User size={17} /> },
    { href: '/my-subscription', label: 'My subscription',     icon: <CreditCard size={17} /> },
    { href: '/invoices',        label: 'Invoices',            icon: <Receipt size={17} /> },
    { href: '/calendar',        label: 'Calendar',            icon: <CalendarDays size={17} /> },
    { href: '/assistant',       label: 'AI Assistant',        icon: <Bot size={17} /> },
    { href: '/referrals',       label: 'Referrals',           icon: <Gift size={17} /> },
    { href: '/security',        label: 'Security',            icon: <Lock size={17} /> },
    { href: '/support',         label: 'Support',             icon: <Headphones size={17} /> },
  ];

  const opsNavItems: NavItem[] = [
    { href: '/admin',   label: t('nav.admin'),       icon: <Settings size={17} /> },
    { href: '/billing', label: 'Platform billing',   icon: <CreditCard size={17} /> },
  ];

  const navItems = opsHost ? opsNavItems : clientNavItems;
  const clientAppHref = clientSurfaceUrl('/dashboard');

  const isActive = (href: string) =>
    href === '/dashboard' ? router.pathname === href : router.pathname.startsWith(href.split('?')[0]);

  return (
    <div className={styles.layoutContainer}>
      {/* ── Backdrop ── */}
      <div
        className={drawerOpen ? styles.backdropVisible : styles.backdrop}
        onClick={() => setDrawerOpen(false)}
        aria-hidden="true"
      />

      {/* ── Sidebar ── */}
      <aside
        ref={sidebarRef}
        className={`${styles.sidebar} ${drawerOpen ? styles.sidebarOpen : ''}`}
        aria-label="Navigation"
      >
        <h1 className={styles.logo}>
          SelfMonitor
          {opsHost && (
            <span style={{ display: 'block', fontSize: '0.62rem', fontWeight: 500, color: 'var(--text-tertiary)', marginTop: 3 }}>
              Operations
            </span>
          )}
        </h1>

        <nav className={styles.nav} aria-label="Main navigation">
          {navItems.map(({ href, label, icon, external }) =>
            external ? (
              <a href={href} key={href}>
                <span className={styles.navIcon}>{icon}</span>
                <span className={styles.navLabel}>{label}</span>
              </a>
            ) : (
              <Link
                href={href}
                key={href}
                locale={router.locale}
                className={isActive(href) ? styles.active : ''}
                aria-current={isActive(href) ? 'page' : undefined}
              >
                <span className={styles.navIcon}>{icon}</span>
                <span className={styles.navLabel}>{label}</span>
              </Link>
            ),
          )}

          {opsHost && (
            <>
              <div className={styles.sidebarDivider} />
              <a href={clientAppHref} key="client-app">
                <span className={styles.navIcon}><ExternalLink size={17} /></span>
                <span className={styles.navLabel}>Client app</span>
              </a>
            </>
          )}
        </nav>

        <div className={styles.sidebarFooter}>
          {/* Lang switcher */}
          <div className={styles.langSwitcher} style={{ position: 'relative' }}>
            <button
              type="button"
              onClick={() => setLangOpen(!langOpen)}
              aria-label="Change language"
              style={{
                background: 'none',
                border: 'none',
                cursor: 'pointer',
                padding: '0.45rem 0.6rem',
                display: 'flex',
                alignItems: 'center',
                gap: '0.45rem',
                color: 'var(--text-secondary)',
                borderRadius: 'var(--radius-md)',
                fontSize: '0.85rem',
                transition: 'background var(--ease-fast)',
              }}
            >
              <Globe size={14} />
              <span style={{ fontSize: '1rem' }}>{LOCALE_FLAGS[activeLocale || 'en-GB'] || '🌐'}</span>
              <span style={{ fontSize: '0.78rem' }}>{(activeLocale || 'en-GB').split('-')[0].toUpperCase()}</span>
            </button>

            {langOpen && (
              <div style={{
                position: 'absolute',
                bottom: '100%',
                left: 0,
                right: 0,
                background: 'var(--bg-surface)',
                border: '1px solid var(--border)',
                borderRadius: 'var(--radius-lg)',
                padding: '0.4rem',
                marginBottom: '0.35rem',
                maxHeight: '280px',
                overflowY: 'auto',
                zIndex: 'var(--z-dropdown)',
                boxShadow: 'var(--shadow-lg)',
              }}>
                {locales?.map((loc) => (
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
                      gap: '0.65rem',
                      padding: '0.45rem 0.7rem',
                      borderRadius: 'var(--radius-sm)',
                      cursor: 'pointer',
                      background: loc === activeLocale ? 'var(--accent-muted)' : 'transparent',
                      color: loc === activeLocale ? 'var(--accent-hover)' : 'var(--text-primary)',
                      fontSize: '0.88rem',
                      fontWeight: loc === activeLocale ? 600 : 400,
                    }}>
                      <span style={{ fontSize: '1.1rem' }}>{LOCALE_FLAGS[loc] || '🌐'}</span>
                      <span>{loc.split('-')[0].toUpperCase()}</span>
                    </div>
                  </Link>
                ))}
              </div>
            )}
          </div>

          {/* Theme toggle */}
          {onToggleTheme && (
            <button
              type="button"
              onClick={onToggleTheme}
              aria-label="Toggle theme"
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '0.5rem',
                background: 'none',
                border: '1px solid var(--border)',
                borderRadius: 'var(--radius-md)',
                padding: '0.45rem 0.75rem',
                color: 'var(--text-secondary)',
                cursor: 'pointer',
                fontSize: '0.82rem',
                fontFamily: 'var(--font)',
                width: '100%',
                transition: 'border-color var(--ease-fast), color var(--ease-fast)',
              }}
            >
              <span>{isDarkMode ? '☀️' : '🌙'}</span>
              <span className={styles.navLabel}>{isDarkMode ? 'Light mode' : 'Dark mode'}</span>
            </button>
          )}

          <div className={styles.userRow}>
            <User size={13} style={{ color: 'var(--text-tertiary)', flexShrink: 0 }} />
            <span className={styles.userEmail}>{user.email}</span>
          </div>

          <button type="button" onClick={onLogout} className={styles.logoutButton}>
            <LogOut size={15} />
            <span className={styles.navLabel}>{t('common.logout')}</span>
          </button>
        </div>
      </aside>

      {/* ── Mobile top bar ── */}
      <header className={styles.topBar}>
        <button
          type="button"
          className={styles.hamburger}
          onClick={() => setDrawerOpen(true)}
          aria-label="Open navigation"
          aria-expanded={drawerOpen}
        >
          <Menu size={22} />
        </button>
        <span className={styles.topBarBrand}>SelfMonitor</span>
        <div className={styles.topBarRight}>
          {onToggleTheme && (
            <button
              type="button"
              onClick={onToggleTheme}
              aria-label="Toggle theme"
              style={{
                background: 'none', border: 'none', cursor: 'pointer',
                color: 'var(--text-secondary)', padding: '0.5rem',
                display: 'flex', alignItems: 'center',
              }}
            >
              {isDarkMode ? '☀️' : '🌙'}
            </button>
          )}
        </div>
      </header>

      {/* ── Main content ── */}
      <main className={styles.mainContent}>
        {children}
      </main>

      {/* ── Mobile bottom nav ── */}
      <nav className={styles.bottomNav} aria-label="Bottom navigation">
        {BOTTOM_NAV_TABS.map(({ href, label, icon }) => (
          <Link
            href={href}
            key={href}
            locale={router.locale}
            className={`${styles.bottomNavItem} ${isActive(href) ? styles.active : ''}`}
            aria-current={isActive(href) ? 'page' : undefined}
          >
            <span className={styles.bottomNavIcon}>{icon}</span>
            <span>{label}</span>
          </Link>
        ))}
      </nav>
    </div>
  );
}
