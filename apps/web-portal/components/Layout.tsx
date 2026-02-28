import Link from 'next/link';
import { useRouter } from 'next/router';
import { useState } from 'react';
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
  children: React.ReactNode;
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

  const navItems = [
    { href: '/dashboard', label: t('nav.dashboard') },
    { href: '/activity', label: t('nav.activity') },
    { href: '/transactions', label: t('nav.transactions') },
    { href: '/documents', label: t('nav.documents') },
    { href: '/reports', label: t('nav.reports') },
    { href: '/marketplace', label: t('nav.marketplace') },
    { href: '/submission', label: t('nav.submission') },
    { href: '/profile', label: t('nav.profile') },
    { href: '/billing', label: '💳 Billing' },
  ];

  if (isAdmin) {
    navItems.push({ href: '/admin', label: t('nav.admin') });
  }

  return (
    <div className={styles.layoutContainer}>
      <aside className={styles.sidebar}>
        <h1 className={styles.logo}>FinTech</h1>
        <nav className={styles.nav}>
          {navItems.map(({ href, label }) => (
            <Link href={href} key={href} locale={router.locale}>
              <span className={router.pathname === href ? styles.active : ''}>
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
                fontSize: '1.5rem',
                padding: '0.5rem',
                display: 'flex',
                alignItems: 'center',
                gap: '0.5rem',
                color: 'var(--lp-text)',
              }}
            >
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
          <button onClick={onLogout} className={styles.logoutButton}>
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
