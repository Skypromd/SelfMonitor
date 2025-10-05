import type { AppProps } from 'next/app';
import { useState, useEffect, useContext } from 'react';
import { useRouter } from 'next/router';
import '../styles/globals.css';
import Layout from '../components/Layout';
import { I18nProvider, I18nContext } from '../context/i18n';

const LOCALIZATION_SERVICE_URL = process.env.NEXT_PUBLIC_LOCALIZATION_SERVICE_URL || 'http://localhost:8012';

function AppContent({ Component, pageProps }: AppProps) {
  const [token, setToken] = useState<string | null>(null);
  const router = useRouter();
  const { setTranslations } = useContext(I18nContext);
  const { locale, defaultLocale } = router;

  // Fetch translations when locale changes
  useEffect(() => {
    const fetchTranslations = async () => {
      const lang = locale || defaultLocale || 'en-GB';
      try {
        const response = await fetch(`${LOCALIZATION_SERVICE_URL}/translations/${lang}/all`);
        if (!response.ok) throw new Error('Failed to fetch translations');
        const data = await response.json();
        setTranslations(data);
      } catch (error) {
        console.error("Could not load translations:", error);
      }
    };
    fetchTranslations();
  }, [locale, defaultLocale, setTranslations]);

  // Auth logic
  useEffect(() => {
    const storedToken = localStorage.getItem('authToken');
    if (storedToken) {
      setToken(storedToken);
    } else if (router.pathname !== '/') {
      router.push('/');
    }
  }, [router.pathname]);

  const handleLoginSuccess = (newToken: string) => {
    localStorage.setItem('authToken', newToken);
    setToken(newToken);
    router.push('/dashboard');
  };

  const handleLogout = () => {
    localStorage.removeItem('authToken');
    setToken(null);
    router.push('/');
  };

  const isLoginPage = router.pathname === '/';

  if (isLoginPage) {
    return <Component {...pageProps} onLoginSuccess={handleLoginSuccess} />;
  }

  return token ? (
    <Layout onLogout={handleLogout}>
      <Component {...pageProps} token={token} />
    </Layout>
  ) : null;
}
import type { AppProps } from 'next/app';
import { useState, useEffect, useContext } from 'react';
import { useRouter } from 'next/router';
import '../styles/globals.css';
import Layout from '../components/Layout';
import { I18nProvider, I18nContext } from '../context/i18n';

const LOCALIZATION_SERVICE_URL = process.env.NEXT_PUBLIC_LOCALIZATION_SERVICE_URL || 'http://localhost:8012';

function AppContent({ Component, pageProps }: AppProps) {
  const [token, setToken] = useState<string | null>(null);
  const router = useRouter();
  const { setTranslations } = useContext(I18nContext);
  const { locale, defaultLocale } = router;

  // Fetch translations when locale changes
  useEffect(() => {
    const fetchTranslations = async () => {
      const lang = locale || defaultLocale || 'en-GB';
      try {
        const response = await fetch(`${LOCALIZATION_SERVICE_URL}/translations/${lang}/all`);
        if (!response.ok) throw new Error('Failed to fetch translations');
        const data = await response.json();
        setTranslations(data);
      } catch (error) {
        console.error("Could not load translations:", error);
      }
    };
    fetchTranslations();
  }, [locale, defaultLocale, setTranslations]);

  // Auth logic
  useEffect(() => {
    const storedToken = localStorage.getItem('authToken');
    if (storedToken) {
      setToken(storedToken);
    } else if (router.pathname !== '/') {
      router.push('/');
    }
  }, [router.pathname]);

  const handleLoginSuccess = (newToken: string) => {
    localStorage.setItem('authToken', newToken);
    setToken(newToken);
    router.push('/dashboard');
  };

  const handleLogout = () => {
    localStorage.removeItem('authToken');
    setToken(null);
    router.push('/');
  };

  const isLoginPage = router.pathname === '/';

  if (isLoginPage) {
    return <Component {...pageProps} onLoginSuccess={handleLoginSuccess} />;
  }

  return token ? (
    <Layout onLogout={handleLogout}>
      <Component {...pageProps} token={token} />
    </Layout>
  ) : null;
}

function MyApp(props: AppProps) {
  return (
    <I18nProvider>
      <AppContent {...props} />
    </I18nProvider>
  );
}

export default MyApp;
function MyApp(props: AppProps) {
  return (
    <I18nProvider>
      <AppContent {...props} />
    </I18nProvider>
  );
}

export default MyApp;
