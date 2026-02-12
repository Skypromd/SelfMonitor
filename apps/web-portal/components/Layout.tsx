import Link from 'next/link';
import { useRouter } from 'next/router';
import type { ReactNode } from 'react';
import { useTranslation } from '../hooks/useTranslation';
import styles from '../styles/Layout.module.css';

type LayoutProps = {
  children: ReactNode;
  onLogout: () => void;
  userEmail?: string;
};

export default function Layout({ children, onLogout, userEmail }: LayoutProps) {
  const router = useRouter();
  const { t } = useTranslation();
  const { locales, locale: activeLocale } = router;

  // This is a placeholder for a real admin check.
  // We assume the first user registered is the admin, so we hardcode it here.
  // In a real app, this should come from user roles/permissions.
  const isAdmin = userEmail === 'admin@example.com';

  const navItems = [
    { href: '/dashboard', label: t('nav.dashboard') },
    { href: '/activity', label: t('nav.activity') },
    { href: '/transactions', label: t('nav.transactions') },
    { href: '/documents', label: t('nav.documents') },
    { href: '/reports', label: t('nav.reports') },
    { href: '/marketplace', label: t('nav.marketplace') },
    { href: '/submission', label: t('nav.submission') },
    { href: '/profile', label: t('nav.profile') },
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
            <Link href={href} key={href} locale={router.locale} className={styles.navLink}>
              <span className={`${styles.navLabel} ${router.pathname === href ? styles.active : ''}`}>
                {label}
              </span>
            </Link>
          ))}
        </nav>
        <div className={styles.sidebarFooter}>
          {userEmail && <p className={styles.userEmail}>{userEmail}</p>}
          <div className={styles.langSwitcher}>
            {locales?.map(locale => (
              <Link href={router.pathname} key={locale} locale={locale}>
                <span className={locale === activeLocale ? styles.activeLang : ''}>
                  {locale.split('-')[0].toUpperCase()}
                </span>
              </Link>
            ))}
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
