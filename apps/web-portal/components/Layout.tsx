import {
    Activity, BarChart2, Bot, CalendarDays, CreditCard, FileText, Gift,
    Globe, Headphones, LayoutDashboard, Lock, LogOut, Receipt, Send, Settings,
    ShoppingBag, User, Wallet,
} from 'lucide-react';
import Link from 'next/link';
import { useRouter } from 'next/router';
import { ReactNode, useState } from 'react';
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

type UserSummary = {
  email?: string;
  is_admin?: boolean;
};

type LayoutProps = {
  children: ReactNode;
  onLogout: () => void;
  user: UserSummary;
  isDarkMode?: boolean;
  onToggleTheme?: () => void;
};

export default function Layout({ children, onLogout, user }: LayoutProps) {
  const router = useRouter();
  const { t } = useTranslation();
  const { locales, locale: activeLocale } = router;
  const [langOpen, setLangOpen] = useState(false);

  const isAdmin = user.is_admin === true;

  const navItems: { href: string; label: string; icon: ReactNode }[] = [
    { href: '/dashboard',    label: t('nav.dashboard'),    icon: <LayoutDashboard size={17} /> },
    { href: '/activity',     label: t('nav.activity'),     icon: <Activity size={17} /> },
    { href: '/transactions', label: t('nav.transactions'), icon: <Wallet size={17} /> },
    { href: '/documents',    label: t('nav.documents'),    icon: <FileText size={17} /> },
    { href: '/reports',      label: t('nav.reports'),      icon: <BarChart2 size={17} /> },
    { href: '/marketplace',  label: t('nav.marketplace'),  icon: <ShoppingBag size={17} /> },
    { href: '/submission',   label: t('nav.submission'),   icon: <Send size={17} /> },
    { href: '/profile',      label: t('nav.profile'),      icon: <User size={17} /> },
    { href: '/invoices',    label: 'Invoices',            icon: <Receipt size={17} /> },
    { href: '/calendar',    label: 'Calendar',            icon: <CalendarDays size={17} /> },
    { href: '/assistant',   label: 'AI Assistant',        icon: <Bot size={17} /> },
    { href: '/referrals',   label: 'Referrals',           icon: <Gift size={17} /> },
    { href: '/billing',     label: 'Billing',             icon: <CreditCard size={17} /> },
    { href: '/security',    label: 'Security',            icon: <Lock size={17} /> },
    { href: '/support',     label: 'Support',             icon: <Headphones size={17} /> },
  ];

  if (isAdmin) {
    navItems.push({ href: '/admin', label: t('nav.admin'), icon: <Settings size={17} /> });
  }

  return (
    <div className={styles.layoutContainer}>
      <aside className={styles.sidebar}>
        <h1 className={styles.logo}>FinTech</h1>
        <nav className={styles.nav}>
          {navItems.map(({ href, label, icon }) => (
            <Link href={href} key={href} locale={router.locale}>
              <span
                className={router.pathname === href ? styles.active : ''}
                style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}
              >
                <span style={{ display: 'flex', flexShrink: 0 }}>{icon}</span>
                {label}
              </span>
            </Link>
          ))}
        </nav>
        <div className={styles.sidebarFooter}>
          <div className={styles.langSwitcher} style={{ position: 'relative' }}>
            <button
              onClick={() => setLangOpen(!langOpen)}
              style={{
                background: 'none',
                border: 'none',
                cursor: 'pointer',
                fontSize: '0.85rem',
                padding: '0.5rem',
                display: 'flex',
                alignItems: 'center',
                gap: '0.5rem',
                color: 'var(--lp-text)',
              }}
            >
              <Globe size={15} />
              {LOCALE_FLAGS[activeLocale || 'en-GB'] || '🌐'}
              <span style={{ fontSize: '0.85rem', color: 'var(--lp-text-muted)' }}>
                {(activeLocale || 'en-GB').split('-')[0].toUpperCase()}
              </span>
              <span style={{ fontSize: '0.7rem', color: 'var(--lp-text-muted)' }}>▼</span>
            </button>
            {langOpen && (
              <div style={{
                position: 'absolute',
                bottom: '100%',
                left: 0,
                right: 0,
                background: 'var(--lp-bg-card)',
                border: '1px solid var(--lp-border)',
                borderRadius: 10,
                padding: '0.5rem',
                marginBottom: '0.5rem',
                maxHeight: '300px',
                overflowY: 'auto',
                zIndex: 100,
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
                      fontSize: '0.9rem',
                    }}>
                      <span style={{ fontSize: '1.2rem' }}>{LOCALE_FLAGS[loc] || '🌐'}</span>
                      <span>{loc.split('-')[0].toUpperCase()}</span>
                    </div>
                  </Link>
                ))}
              </div>
            )}
          </div>
          <button onClick={onLogout} className={styles.logoutButton} style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0.5rem' }}>
            <LogOut size={15} />
            {t('common.logout')}
          </button>
        </div>
      </aside>
      <main className={styles.mainContent}>
        {children}
      </main>
    </div>
  );
}
