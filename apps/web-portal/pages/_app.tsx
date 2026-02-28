import type { AppProps } from 'next/app';
import { useRouter } from 'next/router';
import { useContext, useEffect, useState } from 'react';
import ErrorBoundary from '../components/ErrorBoundary';
import Layout from '../components/Layout';
import { I18nContext, I18nProvider } from '../context/i18n';
import '../styles/globals.css';

const API_GATEWAY_URL = process.env.NEXT_PUBLIC_API_GATEWAY_URL || 'http://localhost:8000/api';
const AUTH_SERVICE_URL = process.env.NEXT_PUBLIC_AUTH_SERVICE_URL || 'http://localhost:8001';
const LOCALIZATION_URL = process.env.NEXT_PUBLIC_LOCALIZATION_SERVICE_URL || `${API_GATEWAY_URL}/localization`;

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
  const [isDarkMode, setIsDarkMode] = useState(false);
  const router = useRouter();

  const handleToggleTheme = () => setIsDarkMode((prev) => !prev);
  const { setTranslations, setLocale } = useContext(I18nContext);
  const { locale, defaultLocale } = router;

  useEffect(() => {
    const fetchTranslations = async () => {
      const lang = locale || defaultLocale || 'en-GB';
      // Sync locale into context so useTranslation uses correct locale for formatting
      setLocale(lang);
      try {
        const response = await fetch(`${LOCALIZATION_URL}/translations/${lang}/all`);
        if (!response.ok) {
          throw new Error('Failed to fetch translations');
        }
        const data = await response.json();
        setTranslations(data);
      } catch (error) {
        console.error('Could not load translations:', error);
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
    }
  };

  useEffect(() => {
    const saved = localStorage.getItem('preferredLocale');
    if (!saved && (router.pathname === '/' || router.pathname === '/landing')) {
      router.replace('/welcome');
    }
  }, [router]);

  useEffect(() => {
    const storedToken = sessionStorage.getItem('authToken');
    if (storedToken) {
      setToken(storedToken);
      setUser(decodeUserFromToken(storedToken));
      fetchUserInfo(storedToken);
    } else if (router.pathname !== '/' && router.pathname !== '/landing' && router.pathname !== '/register' && router.pathname !== '/welcome') {
      router.replace('/');
    }
  }, [router.pathname, router]);

  const handleLoginSuccess = (newToken: string) => {
    sessionStorage.setItem('authToken', newToken);
    setToken(newToken);
    setUser(decodeUserFromToken(newToken));
    fetchUserInfo(newToken);
    router.push('/dashboard');
  };

  const handleLogout = () => {
    sessionStorage.removeItem('authToken');
    setToken(null);
    setUser({ email: '', is_admin: false });
    router.push('/');
  };

  if (router.pathname === '/' || router.pathname === '/landing' || router.pathname === '/register' || router.pathname === '/welcome') {
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
