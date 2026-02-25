import type { AppProps } from 'next/app';
import { useContext, useEffect, useState } from 'react';
import { useRouter } from 'next/router';
import '../styles/globals.css';
import Layout from '../components/Layout';
import ErrorBoundary from '../components/ErrorBoundary';
import { I18nProvider, I18nContext } from '../context/i18n';

const API_GATEWAY_URL = process.env.NEXT_PUBLIC_API_GATEWAY_URL || 'http://localhost:8000/api';

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
  const router = useRouter();
  const { setTranslations } = useContext(I18nContext);
  const { locale, defaultLocale } = router;

  useEffect(() => {
    const fetchTranslations = async () => {
      const lang = locale || defaultLocale || 'en-GB';
      try {
        const response = await fetch(`${API_GATEWAY_URL}/localization/translations/${lang}/all`);
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
  }, [locale, defaultLocale, setTranslations]);

  const fetchUserInfo = async (authToken: string) => {
    try {
      const response = await fetch(`${API_GATEWAY_URL}/auth/me`, {
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
    const storedToken = sessionStorage.getItem('authToken');
    if (storedToken) {
      setToken(storedToken);
      setUser(decodeUserFromToken(storedToken));
      fetchUserInfo(storedToken);
    } else if (router.pathname !== '/') {
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

  if (router.pathname === '/') {
    return <Component {...pageProps} onLoginSuccess={handleLoginSuccess} />;
  }

  if (!token) {
    return null;
  }

  return (
    <Layout onLogout={handleLogout} user={user}>
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
