import type { AppProps } from 'next/app';
import { useContext, useEffect, useState } from 'react';
import { useRouter } from 'next/router';
import '../styles/globals.css';
import Layout from '../components/Layout';
import { I18nProvider, I18nContext } from '../context/i18n';

const LOCALIZATION_SERVICE_URL = process.env.NEXT_PUBLIC_LOCALIZATION_SERVICE_URL || 'http://localhost:8012';

type AuthUser = {
  email: string;
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
      return { email: '' };
    }

    const normalized = payloadPart.replace(/-/g, '+').replace(/_/g, '/');
    const padded = normalized + '='.repeat((4 - (normalized.length % 4)) % 4);
    const payload = JSON.parse(atob(padded));
    return { email: typeof payload.sub === 'string' ? payload.sub : '' };
  } catch {
    return { email: '' };
  }
}

function AppContent({ Component, pageProps }: AppProps<AppPageProps>) {
  const [token, setToken] = useState<string | null>(null);
  const [user, setUser] = useState<AuthUser>({ email: '' });
  const router = useRouter();
  const { setTranslations } = useContext(I18nContext);
  const { locale, defaultLocale } = router;

  useEffect(() => {
    const fetchTranslations = async () => {
      const lang = locale || defaultLocale || 'en-GB';
      try {
        const response = await fetch(`${LOCALIZATION_SERVICE_URL}/translations/${lang}/all`);
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

  useEffect(() => {
    const storedToken = localStorage.getItem('authToken');
    if (storedToken) {
      setToken(storedToken);
      setUser(decodeUserFromToken(storedToken));
    } else if (router.pathname !== '/') {
      router.replace('/');
    }
  }, [router.pathname, router]);

  const handleLoginSuccess = (newToken: string) => {
    localStorage.setItem('authToken', newToken);
    setToken(newToken);
    setUser(decodeUserFromToken(newToken));
    router.push('/dashboard');
  };

  const handleLogout = () => {
    localStorage.removeItem('authToken');
    setToken(null);
    setUser({ email: '' });
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
      <AppContent {...props} />
    </I18nProvider>
  );
}

export default MyApp;
