import {
  BarChart2, Bot, CreditCard, ExternalLink, Globe, Headphones,
  LayoutDashboard, LogOut, Menu, Receipt, Send, ShieldCheck, Stethoscope, Users, User,
} from 'lucide-react';
import Link from 'next/link';
import { useRouter } from 'next/router';
import { ReactNode, useEffect, useRef, useState } from 'react';
import { ADMIN_SECTION_PATH, type AdminTab } from '../lib/adminRoutes';
import { clientSurfaceUrl } from '../lib/adminSurface';
import { useTranslation } from '../hooks/useTranslation';
import styles from '../styles/Layout.module.css';

type UserSummary = { email?: string; is_admin?: boolean };

type AdminLayoutProps = {
  children: ReactNode;
  onLogout: () => void;
  user: UserSummary;
};

type NavItem = {
  href: string;
  label: string;
  icon: ReactNode;
  match: (pathname: string) => boolean;
};

const ADMIN_TABS: { tab: AdminTab; label: string; icon: ReactNode }[] = [
  { tab: 'overview',       label: 'Overview',        icon: <LayoutDashboard size={17} /> },
  { tab: 'subscriptions',  label: 'Subscriptions',   icon: <CreditCard size={17} /> },
  { tab: 'users',          label: 'Users',           icon: <Users size={17} /> },
  { tab: 'billing',        label: 'Partner billing', icon: <BarChart2 size={17} /> },
  { tab: 'leadops',        label: 'Lead ops',        icon: <Send size={17} /> },
  { tab: 'invoices',       label: 'Invoices',        icon: <Receipt size={17} /> },
  { tab: 'ai-agent',       label: 'AI agent',        icon: <Bot size={17} /> },
  { tab: 'health',         label: 'System health',   icon: <Stethoscope size={17} /> },
  { tab: 'support',        label: 'Support',         icon: <Headphones size={17} /> },
  { tab: 'regulatory',     label: 'Regulatory',      icon: <ShieldCheck size={17} /> },
];

const LOCALE_FLAGS: Record<string, string> = {
  'en-GB': '🇬🇧', 'pl-PL': '🇵🇱', 'ro-RO': '🇷🇴', 'uk-UA': '🇺🇦',
  'ru-RU': '🇷🇺', 'es-ES': '🇪🇸', 'it-IT': '🇮🇹', 'pt-PT': '🇵🇹',
  'tr-TR': '🇹🇷', 'bn-BD': '🇧🇩',
};

export default function AdminLayout({ children, onLogout, user }: AdminLayoutProps) {
  const router = useRouter();
  const { t } = useTranslation();
  const { locales, locale: activeLocale } = router;
  const [langOpen, setLangOpen] = useState(false);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const sidebarRef = useRef<HTMLElement>(null);

  const clientAppHref = clientSurfaceUrl('/dashboard');

  useEffect(() => {
    setDrawerOpen(false);
  }, [router.pathname]);

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

  useEffect(() => {
    const onDocClick = () => setLangOpen(false);
    if (langOpen) document.addEventListener('click', onDocClick);
    return () => document.removeEventListener('click', onDocClick);
  }, [langOpen]);

  const navItems: NavItem[] = [
    ...ADMIN_TABS.map(({ tab, label, icon }) => {
      const href = ADMIN_SECTION_PATH[tab];
      return {
        href,
        label,
        icon,
        match: (pathname: string) =>
          pathname === href ||
          (tab === 'overview' && pathname === '/admin') ||
          (tab === 'users' && pathname.startsWith('/admin/users/')),
      };
    }),
    {
      href: '/billing',
      label: 'Platform billing',
      icon: <CreditCard size={17} />,
      match: (pathname: string) => pathname === '/billing',
    },
  ];

  const currentTab = navItems.find((n) => n.match(router.pathname));

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
        aria-label="Admin navigation"
      >
        <h1 className={styles.logo}>
          SelfMonitor
          <span style={{ display: 'block', fontSize: '0.62rem', fontWeight: 600, color: 'var(--accent-hover)', marginTop: 3, letterSpacing: '0.1em', textTransform: 'uppercase' }}>
            Ops Console
          </span>
        </h1>

        <nav className={styles.nav} aria-label="Admin navigation">
          {navItems.map(({ href, label, icon, match }) => (
            <Link
              href={href}
              key={href}
              locale={router.locale}
              className={match(router.pathname) ? styles.active : ''}
              aria-current={match(router.pathname) ? 'page' : undefined}
            >
              <span className={styles.navIcon}>{icon}</span>
              <span className={styles.navLabel}>{label}</span>
            </Link>
          ))}

          <div className={styles.sidebarDivider} />

          <a href={clientAppHref} key="client-app">
            <span className={styles.navIcon}><ExternalLink size={17} /></span>
            <span className={styles.navLabel}>Client app</span>
          </a>
        </nav>

        <div className={styles.sidebarFooter}>
          {/* Lang switcher */}
          <div className={styles.langSwitcher} style={{ position: 'relative' }} onClick={(e) => e.stopPropagation()}>
            <button
              type="button"
              onClick={() => setLangOpen(!langOpen)}
              aria-label="Change language"
              style={{
                background: 'none', border: 'none', cursor: 'pointer',
                padding: '0.45rem 0.6rem', display: 'flex', alignItems: 'center',
                gap: '0.45rem', color: 'var(--text-secondary)',
                borderRadius: 'var(--radius-md)', fontSize: '0.85rem',
              }}
            >
              <Globe size={14} />
              <span>{LOCALE_FLAGS[activeLocale || 'en-GB'] || '🌐'}</span>
              <span style={{ fontSize: '0.78rem' }}>{(activeLocale || 'en-GB').split('-')[0].toUpperCase()}</span>
            </button>

            {langOpen && (
              <div style={{
                position: 'absolute', bottom: '100%', left: 0, right: 0,
                background: 'var(--bg-surface)', border: '1px solid var(--border)',
                borderRadius: 'var(--radius-lg)', padding: '0.4rem', marginBottom: '0.35rem',
                maxHeight: '280px', overflowY: 'auto', zIndex: 'var(--z-dropdown)',
                boxShadow: 'var(--shadow-lg)',
              }}>
                {locales?.map((loc) => (
                  <Link
                    href={router.pathname}
                    key={loc}
                    locale={loc}
                    onClick={() => { localStorage.setItem('preferredLocale', loc); setLangOpen(false); }}
                  >
                    <div style={{
                      display: 'flex', alignItems: 'center', gap: '0.65rem',
                      padding: '0.45rem 0.7rem', borderRadius: 'var(--radius-sm)',
                      cursor: 'pointer',
                      background: loc === activeLocale ? 'var(--accent-muted)' : 'transparent',
                      color: loc === activeLocale ? 'var(--accent-hover)' : 'var(--text-primary)',
                      fontSize: '0.88rem', fontWeight: loc === activeLocale ? 600 : 400,
                    }}>
                      <span style={{ fontSize: '1.1rem' }}>{LOCALE_FLAGS[loc] || '🌐'}</span>
                      <span>{loc.split('-')[0].toUpperCase()}</span>
                    </div>
                  </Link>
                ))}
              </div>
            )}
          </div>

          <div className={styles.userRow}>
            <User size={13} style={{ color: 'var(--text-tertiary)', flexShrink: 0 }} />
            <span className={styles.userEmail}>{user.email}</span>
            <span className={styles.adminBadge} style={{ marginLeft: 'auto' }}>Admin</span>
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
        >
          <Menu size={22} />
        </button>
        <span className={styles.topBarBrand} style={{ color: 'var(--accent-hover)' }}>Ops Console</span>
        <div className={styles.topBarRight} />
      </header>

      {/* ── Mobile horizontal scroll tabs ── */}
      <div className={styles.adminMobileTabs} role="tablist" aria-label="Admin sections">
        {navItems.slice(0, -1).map(({ href, label, icon, match }) => (
          <Link
            href={href}
            key={href}
            locale={router.locale}
            role="tab"
            aria-selected={match(router.pathname)}
            className={`${styles.adminMobileTab} ${match(router.pathname) ? styles.active : ''}`}
          >
            {icon}
            <span>{label}</span>
          </Link>
        ))}
      </div>

      {/* ── Main content ── */}
      <main className={styles.mainContent}>
        {/* Breadcrumbs */}
        {currentTab && router.pathname !== '/admin' && (
          <nav className={styles.breadcrumbs} aria-label="Breadcrumb">
            <Link href="/admin">Overview</Link>
            <span className={styles.breadcrumbSep}>/</span>
            <span className={styles.breadcrumbCurrent}>{currentTab.label}</span>
          </nav>
        )}
        {children}
      </main>
    </div>
  );
}
