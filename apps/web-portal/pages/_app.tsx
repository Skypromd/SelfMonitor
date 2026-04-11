import type { AppProps } from 'next/app';
import { useRouter } from 'next/router';
import { useContext, useEffect, useState } from 'react';
import ErrorBoundary from '../components/ErrorBoundary';
import Layout from '../components/Layout';
import { I18nContext, I18nProvider } from '../context/i18n';
import '../styles/globals.css';

const API_GATEWAY_URL = process.env.NEXT_PUBLIC_API_GATEWAY_URL || 'http://localhost:8000/api';
const AUTH_SERVICE_URL = process.env.NEXT_PUBLIC_AUTH_SERVICE_URL || 'http://localhost:8001';
/** Same-origin path — proxied to gateway by `next.config.js` rewrites (avoids cross-origin :8000 from the browser) */
const LOCALIZATION_URL = '/api/localization';

/** Dev: set NEXT_PUBLIC_SKIP_I18N_FETCH=1 to avoid calling :8000 when the gateway is not running */
const SKIP_I18N_FETCH = process.env.NEXT_PUBLIC_SKIP_I18N_FETCH === '1';

let i18nOfflineNotified = false;

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
  const [isDarkMode, setIsDarkMode] = useState(false);
  const router = useRouter();

  const handleToggleTheme = () => setIsDarkMode((prev) => !prev);
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
        const likelyOffline =
          (error instanceof TypeError && msg === 'Failed to fetch') ||
          msg.includes('NetworkError');
        if (likelyOffline) {
          if (!i18nOfflineNotified) {
            i18nOfflineNotified = true;
            console.info(
              '[i18n] Gateway not running on localhost:8000 — translations skipped. UI still works. Start: docker compose up -d nginx-gateway',
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
    const saved = localStorage.getItem('preferredLocale');
    if (!saved && router.pathname === '/') {
      router.replace('/welcome');
    }
  }, [router]);

  useEffect(() => {
    const storedToken = sessionStorage.getItem('authToken');
    if (storedToken) {
      setToken(storedToken);
      setUser(decodeUserFromToken(storedToken));
      fetchUserInfo(storedToken);
    } else if (router.pathname !== '/' && router.pathname !== '/register' && router.pathname !== '/login' && router.pathname !== '/welcome' && router.pathname !== '/checkout-success' && router.pathname !== '/checkout-cancel' && router.pathname !== '/forgot-password' && router.pathname !== '/reset-password') {
      router.replace('/');
    }
  }, [router.pathname, router]);

  const handleLoginSuccess = (newToken: string) => {
    sessionStorage.setItem('authToken', newToken);
    setToken(newToken);
    const decoded = decodeUserFromToken(newToken);
    setUser(decoded);
    fetchUserInfo(newToken);
    router.push(decoded.is_admin ? '/admin' : '/dashboard');
  };

  const handleLogout = () => {
    sessionStorage.removeItem('authToken');
    setToken(null);
    setUser({ email: '', is_admin: false });
    setIsUserLoaded(false);
    router.push('/');
  };

  // ── Hard guard: /admin — is_admin + session freshness (< 60 min) ─────────────
  if (router.pathname === '/admin' && token) {
    if (!isUserLoaded) return null; // wait for /me before deciding
    if (!user.is_admin) {
      router.replace('/dashboard');
      return null;
    }
    // If token was issued more than 60 minutes ago, force re-login
    try {
      const p = token.split('.')[1];
      const pl = JSON.parse(atob((p.replace(/-/g, '+').replace(/_/g, '/')) + '=='));
      if (pl.iat && (Date.now() / 1000 - pl.iat) / 60 > 60) {
        handleLogout();
        return null;
      }
    } catch { /* ignore */ }
  }

  if (router.pathname === '/' || router.pathname === '/register' || router.pathname === '/login' || router.pathname === '/welcome' || router.pathname === '/checkout-success' || router.pathname === '/checkout-cancel' || router.pathname === '/forgot-password' || router.pathname === '/reset-password') {
    return <Component {...pageProps} onLoginSuccess={handleLoginSuccess} />;
  }

  if (!token) {
    return null;
  }

  return (
    <Layout onLogout={handleLogout} user={user} isDarkMode={isDarkMode} onToggleTheme={handleToggleTheme}>
      <Component {...pageProps} token={token} user={user} />
    </Layout>
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
