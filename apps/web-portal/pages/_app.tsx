import type { AppProps } from 'next/app';
import type { NextRouter } from 'next/router';
import { useRouter } from 'next/router';
import { useContext, useEffect, useState } from 'react';
import ErrorBoundary from '../components/ErrorBoundary';
import AdminLayout from '../components/AdminLayout';
import ClientLayout from '../components/ClientLayout';
import { I18nContext, I18nProvider } from '../context/i18n';
import {
  ADMIN_SUBDOMAIN_ENABLED,
  adminSurfaceUrl,
  clientSurfaceUrl,
  isAdminHostname,
} from '../lib/adminSurface';
import '../styles/globals.css';

function navigateTo(router: NextRouter, pathOrUrl: string) {
  if (typeof window !== 'undefined' && pathOrUrl.startsWith('http')) {
    window.location.href = pathOrUrl;
    return;
  }
  void router.replace(pathOrUrl);
}

const AUTH_SERVICE_URL = process.env.NEXT_PUBLIC_AUTH_SERVICE_URL || '/api/auth';
/** Same-origin path — proxied to gateway by `next.config.js` rewrites (avoids cross-origin :8000 from the browser) */
const LOCALIZATION_URL = '/api/localization';

/** Dev: set NEXT_PUBLIC_SKIP_I18N_FETCH=1 to avoid calling :8000 when the gateway is not running */
const SKIP_I18N_FETCH = process.env.NEXT_PUBLIC_SKIP_I18N_FETCH === '1';

let i18nOfflineNotified = false;

const PUBLIC_PATHS = new Set([
  '/',
  '/register',
  '/login',
  '/welcome',
  '/checkout-success',
  '/checkout-cancel',
  '/forgot-password',
  '/reset-password',
  '/admin/login',
]);

type AuthUser = {
  email: string;
  is_admin: boolean;
};

type AppPageProps = {
  onLoginSuccess?: (newToken: string) => void;
  token?: string;
  user?: AuthUser;
};

function decodeUserFromToken(token: string): AuthUser {
  try {
    const payloadPart = token.split('.')[1];
    if (!payloadPart) {
      return { email: '', is_admin: false };
    }

    const normalized = payloadPart.replace(/-/g, '+').replace(/_/g, '/');
    const padded = normalized + '='.repeat((4 - (normalized.length % 4)) % 4);
    const payload = JSON.parse(atob(padded));
    return {
      email: typeof payload.sub === 'string' ? payload.sub : '',
      is_admin: typeof payload.is_admin === 'boolean' ? payload.is_admin : false,
    };
  } catch {
    return { email: '', is_admin: false };
  }
}

function AppContent({ Component, pageProps }: AppProps<AppPageProps>) {
  const [token, setToken] = useState<string | null>(null);
  const [user, setUser] = useState<AuthUser>({ email: '', is_admin: false });
  const [isUserLoaded, setIsUserLoaded] = useState(false);
  const [isDarkMode, setIsDarkMode] = useState(true);
  const router = useRouter();

  useEffect(() => {
    if (typeof window === 'undefined') return;
    const saved = localStorage.getItem('smTheme');
    const theme = saved === 'light' ? 'light' : 'dark';
    document.documentElement.setAttribute('data-theme', theme);
    setIsDarkMode(theme === 'dark');
  }, []);

  const handleToggleTheme = () => {
    const next = isDarkMode ? 'light' : 'dark';
    document.documentElement.setAttribute('data-theme', next);
    if (typeof window !== 'undefined') localStorage.setItem('smTheme', next);
    setIsDarkMode(!isDarkMode);
  };
  const { setTranslations, setLocale } = useContext(I18nContext);
  const { locale, defaultLocale } = router;

  useEffect(() => {
    const fetchTranslations = async () => {
      const lang = locale || defaultLocale || 'en-GB';
      setLocale(lang);
      if (SKIP_I18N_FETCH) {
        setTranslations({});
        return;
      }
      const url = (loc: string) => `${LOCALIZATION_URL}/translations/${loc}/all`;
      try {
        let res = await fetch(url(lang));
        if (res.status === 404 && lang !== 'en-GB') {
          res = await fetch(url('en-GB'));
        }
        if (!res.ok) {
          throw new Error(`Failed to fetch translations (${res.status})`);
        }
        setTranslations(await res.json());
      } catch (error) {
        setTranslations({});
        if (process.env.NODE_ENV !== 'development') {
          return;
        }
        const msg = error instanceof Error ? error.message : String(error);
        const statusMatch = msg.match(/Failed to fetch translations \((\d+)\)/);
        const statusCode = statusMatch ? parseInt(statusMatch[1], 10) : 0;
        const gatewayDown =
          (error instanceof TypeError && msg === 'Failed to fetch') ||
          msg.includes('NetworkError') ||
          (statusCode >= 500 && statusCode < 600);
        if (gatewayDown) {
          if (!i18nOfflineNotified) {
            i18nOfflineNotified = true;
            console.info(
              '[i18n] API gateway недоступен (localhost:8000 или прокси Next вернул 5xx) — переводы пропущены. Запуск бэкенда: из корня репозитория `scripts/start_backend_v1.ps1` или `scripts/start_backend_v1.sh` (нужен Docker Desktop).',
            );
          }
          return;
        }
        console.warn('[i18n] Translations error:', msg);
      }
    };

    fetchTranslations();
  }, [locale, defaultLocale, setTranslations, setLocale]);

  const fetchUserInfo = async (authToken: string) => {
    try {
      const response = await fetch(`${AUTH_SERVICE_URL}/me`, {
        headers: { Authorization: `Bearer ${authToken}` },
      });
      if (response.ok) {
        const data = await response.json();
        setUser((prev) => ({ ...prev, is_admin: data.is_admin === true }));
      }
    } catch {
      // Fall back to JWT-decoded values
    } finally {
      setIsUserLoaded(true);
    }
  };

  useEffect(() => {
    if (!router.isReady) return;
    const saved = localStorage.getItem('preferredLocale');
    if (!saved && router.pathname === '/') {
      void router.replace('/welcome');
    }
  }, [router.isReady, router.pathname, router]);

  useEffect(() => {
    if (!router.isReady) return;
    const storedToken = sessionStorage.getItem('authToken');
    if (storedToken) {
      setToken(storedToken);
      setUser(decodeUserFromToken(storedToken));
      fetchUserInfo(storedToken);
      return;
    }
    if (PUBLIC_PATHS.has(router.pathname)) return;

    const next = encodeURIComponent(router.asPath || '/dashboard');
    const adminEntry =
      router.pathname === '/admin' ||
      (router.pathname.startsWith('/admin/') && router.pathname !== '/admin/login');
    const dest = adminEntry ? `/admin/login?next=${next}` : `/login?next=${next}`;
    void router.replace(dest);
  }, [router.isReady, router.pathname, router.asPath, router]);

  /** Дубль middleware: на операторском хосте не показывать клиентские страницы (CSR / обход `/_next/data`). */
  useEffect(() => {
    if (!router.isReady || typeof window === 'undefined') return;
    if (!ADMIN_SUBDOMAIN_ENABLED) return;
    if (!isAdminHostname(window.location.hostname)) return;
    const pathname = router.pathname;
    if (pathname.startsWith('/admin') || pathname === '/billing' || pathname.startsWith('/billing/')) {
      return;
    }
    const path = (router.asPath || '/').split('#')[0];
    window.location.replace(clientSurfaceUrl(path));
  }, [router.isReady, router.pathname, router.asPath]);

  /** Не вызывать router.* во время render — только в эффектах (иначе Next: Abort fetching component). */
  useEffect(() => {
    const onAdminApp =
      router.pathname.startsWith('/admin') && router.pathname !== '/admin/login';
    if (!router.isReady || !onAdminApp || !token) return;
    if (!isUserLoaded) return;
    if (!user.is_admin) {
      navigateTo(router, clientSurfaceUrl('/dashboard'));
    }
  }, [router.isReady, router.pathname, token, isUserLoaded, user.is_admin, router]);

  /** `/billing` — аналитика и счета по всей платформе; только для админов (не клиентский кабинет). */
  useEffect(() => {
    if (!router.isReady || router.pathname !== '/billing' || !token) return;
    if (!isUserLoaded) return;
    if (!user.is_admin) {
      navigateTo(router, clientSurfaceUrl('/dashboard'));
    }
  }, [router.isReady, router.pathname, token, isUserLoaded, user.is_admin, router]);

  useEffect(() => {
    const onAdminApp =
      router.pathname.startsWith('/admin') && router.pathname !== '/admin/login';
    if (!router.isReady || !onAdminApp || !token) return;
    try {
      const p = token.split('.')[1];
      const pl = JSON.parse(atob((p.replace(/-/g, '+').replace(/_/g, '/')) + '=='));
      if (pl.iat && (Date.now() / 1000 - pl.iat) / 60 > 60) {
        sessionStorage.removeItem('authToken');
        setToken(null);
        setUser({ email: '', is_admin: false });
        setIsUserLoaded(false);
        const next = encodeURIComponent(router.asPath || '/admin');
        navigateTo(router, adminSurfaceUrl(`/admin/login?next=${next}`));
      }
    } catch {
      /* ignore */
    }
  }, [router.isReady, router.pathname, router.asPath, token, router]);

  const handleLoginSuccess = (newToken: string) => {
    sessionStorage.setItem('authToken', newToken);
    setToken(newToken);
    const decoded = decodeUserFromToken(newToken);
    setUser(decoded);
    fetchUserInfo(newToken);

    const rawNext = router.query.next;
    const nextStr = typeof rawNext === 'string' ? rawNext : Array.isArray(rawNext) ? rawNext[0] : '';
    const safeNext =
      nextStr && nextStr.startsWith('/') && !nextStr.startsWith('//') ? nextStr.split('#')[0] : '';
    const onAdminLoginPage = router.pathname === '/admin/login';

    if (safeNext === '/admin' && !decoded.is_admin) {
      navigateTo(router, clientSurfaceUrl('/dashboard'));
    } else if (safeNext) {
      void router.push(safeNext);
    } else if (onAdminLoginPage) {
      if (decoded.is_admin) {
        void router.push('/admin');
      } else {
        navigateTo(router, clientSurfaceUrl('/login'));
      }
    } else {
      if (decoded.is_admin) {
        if (
          typeof window !== 'undefined' &&
          process.env.NEXT_PUBLIC_ADMIN_SUBDOMAIN_ENABLED === '1' &&
          !isAdminHostname(window.location.hostname)
        ) {
          window.location.href = adminSurfaceUrl('/admin');
        } else {
          void router.push('/admin');
        }
      } else {
        navigateTo(router, clientSurfaceUrl('/dashboard'));
      }
    }
  };

  const handleLogout = () => {
    sessionStorage.removeItem('authToken');
    setToken(null);
    setUser({ email: '', is_admin: false });
    setIsUserLoaded(false);
    if (typeof window !== 'undefined' && isAdminHostname(window.location.hostname)) {
      window.location.href = adminSurfaceUrl('/admin/login');
      return;
    }
    void router.push('/');
  };

  const adminShellRoute =
    router.pathname === '/admin' ||
    router.pathname === '/billing' ||
    (router.pathname.startsWith('/admin/') && router.pathname !== '/admin/login');

  if (adminShellRoute && token && !isUserLoaded) {
    return null;
  }

  if (
    router.pathname === '/' ||
    router.pathname === '/register' ||
    router.pathname === '/login' ||
    router.pathname === '/welcome' ||
    router.pathname === '/checkout-success' ||
    router.pathname === '/checkout-cancel' ||
    router.pathname === '/forgot-password' ||
    router.pathname === '/reset-password' ||
    router.pathname === '/admin/login'
  ) {
    return <Component {...pageProps} onLoginSuccess={handleLoginSuccess} />;
  }

  if (!token) {
    return null;
  }

  if (adminShellRoute && user.is_admin) {
    return (
      <AdminLayout onLogout={handleLogout} user={user}>
        <Component {...pageProps} token={token} user={user} />
      </AdminLayout>
    );
  }

  return (
    <ClientLayout onLogout={handleLogout} user={user} isDarkMode={isDarkMode} onToggleTheme={handleToggleTheme}>
      <Component {...pageProps} token={token} user={user} />
    </ClientLayout>
  );
}

function MyApp(props: AppProps<AppPageProps>) {
  return (
    <I18nProvider>
      <ErrorBoundary>
        <AppContent {...props} />
      </ErrorBoundary>
    </I18nProvider>
  );
}

export default MyApp;
