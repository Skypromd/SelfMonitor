import type { AppProps } from 'next/app';
import { useContext, useEffect, useState, type ComponentType } from 'react';
import { useRouter } from 'next/router';
import Layout from '../components/Layout';
import { I18nContext, I18nProvider } from '../context/i18n';
import '../styles/globals.css';

const LOCALIZATION_SERVICE_URL = process.env.NEXT_PUBLIC_LOCALIZATION_SERVICE_URL || 'http://localhost:8012';
const AUTH_TOKEN_KEY = 'authToken';
const AUTH_EMAIL_KEY = 'authUserEmail';

function AppContent({ Component, pageProps }: AppProps) {
  const [token, setToken] = useState<string | null>(null);
  const [userEmail, setUserEmail] = useState<string | null>(null);
  const router = useRouter();
  const { setTranslations } = useContext(I18nContext);
  const { defaultLocale, locale } = router;

  useEffect(() => {
    const fetchTranslations = async () => {
      const lang = locale || defaultLocale || 'en-GB';
      try {
        const response = await fetch(`${LOCALIZATION_SERVICE_URL}/translations/${lang}/all`);
        if (!response.ok) {
          throw new Error('Failed to fetch translations');
        }
        setTranslations(await response.json());
      } catch (error) {
        console.error('Could not load translations:', error);
      }
    };
    fetchTranslations();
  }, [defaultLocale, locale, setTranslations]);

  useEffect(() => {
    const storedToken = localStorage.getItem(AUTH_TOKEN_KEY);
    const storedEmail = localStorage.getItem(AUTH_EMAIL_KEY);
    if (storedToken) {
      setToken(storedToken);
      if (storedEmail) {
        setUserEmail(storedEmail);
      }
    } else if (router.pathname !== '/') {
      router.push('/');
    }
  }, [router]);

  const handleLoginSuccess = (newToken: string, email?: string) => {
    localStorage.setItem(AUTH_TOKEN_KEY, newToken);
    setToken(newToken);
    if (email) {
      localStorage.setItem(AUTH_EMAIL_KEY, email);
      setUserEmail(email);
    }
    router.push('/dashboard');
  };

  const handleLogout = () => {
    localStorage.removeItem(AUTH_TOKEN_KEY);
    localStorage.removeItem(AUTH_EMAIL_KEY);
    setToken(null);
    setUserEmail(null);
    router.push('/');
  };

  const PageComponent = Component as ComponentType<Record<string, unknown>>;
  if (router.pathname === '/') {
    return <PageComponent {...pageProps} onLoginSuccess={handleLoginSuccess} />;
  }

  if (!token) {
    return null;
  }

  return (
    <Layout onLogout={handleLogout} userEmail={userEmail ?? undefined}>
      <PageComponent {...pageProps} token={token} userEmail={userEmail} />
    </Layout>
  );
}

export default function MyApp(props: AppProps) {
  return (
    <I18nProvider>
      <AppContent {...props} />
    </I18nProvider>
  );
}
