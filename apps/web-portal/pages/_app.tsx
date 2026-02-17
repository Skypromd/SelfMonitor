import type { AppProps } from 'next/app';
import { useContext, useEffect, useState, type ComponentType } from 'react';
import { useRouter } from 'next/router';
import Layout from '../components/Layout';
import { buildDefaultFormatStandards, I18nContext, type LocaleFormatStandards, I18nProvider } from '../context/i18n';
import '../styles/globals.css';

const LOCALIZATION_SERVICE_URL = process.env.NEXT_PUBLIC_LOCALIZATION_SERVICE_URL || 'http://localhost:8012';
const AUTH_TOKEN_KEY = 'authToken';
const AUTH_REFRESH_TOKEN_KEY = 'authRefreshToken';
const AUTH_EMAIL_KEY = 'authUserEmail';
const THEME_KEY = 'appTheme';
type ThemeMode = 'light' | 'dark';
type NativeBridgeMessage =
  | {
      type: 'WEB_AUTH_STATE';
      payload: {
        email: string | null;
        refreshToken: string | null;
        token: string | null;
      };
    }
  | {
      type: 'WEB_THEME_STATE';
      payload: {
        theme: ThemeMode;
      };
    };

type ReactNativeBridgeWindow = Window & {
  ReactNativeWebView?: {
    postMessage: (message: string) => void;
  };
};

type NativeAuthStateEventDetail = {
  email?: string | null;
  refreshToken?: string | null;
  token?: string | null;
};

function postMessageToNativeApp(message: NativeBridgeMessage): void {
  if (typeof window === 'undefined') {
    return;
  }
  const bridge = (window as ReactNativeBridgeWindow).ReactNativeWebView;
  if (!bridge || typeof bridge.postMessage !== 'function') {
    return;
  }
  try {
    bridge.postMessage(JSON.stringify(message));
  } catch (error) {
    console.error('Failed to send message to native shell:', error);
  }
}

function AppContent({ Component, pageProps }: AppProps) {
  const [token, setToken] = useState<string | null>(null);
  const [refreshToken, setRefreshToken] = useState<string | null>(null);
  const [userEmail, setUserEmail] = useState<string | null>(null);
  const [theme, setTheme] = useState<ThemeMode>('light');
  const [authHydrated, setAuthHydrated] = useState(false);
  const router = useRouter();
  const { setFormatStandards, setLocale, setTranslations } = useContext(I18nContext);
  const { defaultLocale, locale } = router;

  useEffect(() => {
    const fetchTranslations = async () => {
      const lang = locale || defaultLocale || 'en-GB';
      setLocale(lang);
      try {
        const [translationsResponse, formatStandardsResponse] = await Promise.all([
          fetch(`${LOCALIZATION_SERVICE_URL}/translations/${lang}/all`),
          fetch(`${LOCALIZATION_SERVICE_URL}/translations/${lang}/format-standards`),
        ]);
        if (!translationsResponse.ok) {
          throw new Error('Failed to fetch translations');
        }
        setTranslations(await translationsResponse.json());

        if (formatStandardsResponse.ok) {
          setFormatStandards((await formatStandardsResponse.json()) as LocaleFormatStandards);
        } else {
          setFormatStandards(buildDefaultFormatStandards(lang));
        }
      } catch (error) {
        console.error('Could not load translations:', error);
        setFormatStandards(buildDefaultFormatStandards(lang));
      }
    };
    fetchTranslations();
  }, [defaultLocale, locale, setFormatStandards, setLocale, setTranslations]);

  useEffect(() => {
    const storedToken = localStorage.getItem(AUTH_TOKEN_KEY);
    const storedRefreshToken = localStorage.getItem(AUTH_REFRESH_TOKEN_KEY);
    const storedEmail = localStorage.getItem(AUTH_EMAIL_KEY);
    if (storedToken) {
      setToken(storedToken);
      if (storedRefreshToken) {
        setRefreshToken(storedRefreshToken);
      }
      if (storedEmail) {
        setUserEmail(storedEmail);
      }
    } else if (router.pathname !== '/') {
      router.push('/');
    }
    setAuthHydrated(true);
  }, [router]);

  useEffect(() => {
    const storedTheme = localStorage.getItem(THEME_KEY);
    if (storedTheme === 'dark' || storedTheme === 'light') {
      setTheme(storedTheme);
      return;
    }

    if (window.matchMedia('(prefers-color-scheme: dark)').matches) {
      setTheme('dark');
    }
  }, []);

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem(THEME_KEY, theme);
  }, [theme]);

  useEffect(() => {
    if (!authHydrated) {
      return;
    }
    postMessageToNativeApp({
      type: 'WEB_AUTH_STATE',
      payload: {
        token,
        email: userEmail,
        refreshToken,
      },
    });
  }, [authHydrated, refreshToken, token, userEmail]);

  useEffect(() => {
    const applyNativeAuthState = (detail: NativeAuthStateEventDetail) => {
      if (typeof detail.token !== 'undefined') {
        if (detail.token) {
          localStorage.setItem(AUTH_TOKEN_KEY, detail.token);
          setToken(detail.token);
        } else {
          localStorage.removeItem(AUTH_TOKEN_KEY);
          setToken(null);
        }
      }
      if (typeof detail.refreshToken !== 'undefined') {
        if (detail.refreshToken) {
          localStorage.setItem(AUTH_REFRESH_TOKEN_KEY, detail.refreshToken);
          setRefreshToken(detail.refreshToken);
        } else {
          localStorage.removeItem(AUTH_REFRESH_TOKEN_KEY);
          setRefreshToken(null);
        }
      }
      if (typeof detail.email !== 'undefined') {
        if (detail.email) {
          localStorage.setItem(AUTH_EMAIL_KEY, detail.email);
          setUserEmail(detail.email);
        } else {
          localStorage.removeItem(AUTH_EMAIL_KEY);
          setUserEmail(null);
        }
      }
    };

    const handleNativeBootstrap = (event: Event) => {
      const customEvent = event as CustomEvent<NativeAuthStateEventDetail>;
      if (!customEvent.detail || typeof customEvent.detail !== 'object') {
        return;
      }
      applyNativeAuthState(customEvent.detail);
    };

    window.addEventListener('selfmonitor-mobile-auth-state', handleNativeBootstrap as EventListener);
    window.addEventListener('selfmonitor-native-bootstrap', handleNativeBootstrap as EventListener);
    return () => {
      window.removeEventListener('selfmonitor-mobile-auth-state', handleNativeBootstrap as EventListener);
      window.removeEventListener('selfmonitor-native-bootstrap', handleNativeBootstrap as EventListener);
    };
  }, []);

  useEffect(() => {
    postMessageToNativeApp({
      type: 'WEB_THEME_STATE',
      payload: {
        theme,
      },
    });
  }, [theme]);

  const handleLoginSuccess = (newToken: string, email?: string, newRefreshToken?: string) => {
    localStorage.setItem(AUTH_TOKEN_KEY, newToken);
    setToken(newToken);
    if (newRefreshToken) {
      localStorage.setItem(AUTH_REFRESH_TOKEN_KEY, newRefreshToken);
      setRefreshToken(newRefreshToken);
    }
    if (email) {
      localStorage.setItem(AUTH_EMAIL_KEY, email);
      setUserEmail(email);
    }
    router.push('/dashboard');
  };

  const handleAuthSessionUpdated = (nextAccessToken: string, nextRefreshToken?: string | null) => {
    localStorage.setItem(AUTH_TOKEN_KEY, nextAccessToken);
    setToken(nextAccessToken);
    if (nextRefreshToken === null) {
      localStorage.removeItem(AUTH_REFRESH_TOKEN_KEY);
      setRefreshToken(null);
      return;
    }
    if (typeof nextRefreshToken === 'string' && nextRefreshToken.length > 0) {
      localStorage.setItem(AUTH_REFRESH_TOKEN_KEY, nextRefreshToken);
      setRefreshToken(nextRefreshToken);
    }
  };

  const handleLogout = () => {
    localStorage.removeItem(AUTH_TOKEN_KEY);
    localStorage.removeItem(AUTH_REFRESH_TOKEN_KEY);
    localStorage.removeItem(AUTH_EMAIL_KEY);
    setToken(null);
    setRefreshToken(null);
    setUserEmail(null);
    router.push('/');
  };

  const toggleTheme = () => {
    setTheme((current) => (current === 'dark' ? 'light' : 'dark'));
  };

  const PageComponent = Component as ComponentType<Record<string, unknown>>;
  if (router.pathname === '/') {
    return <PageComponent {...pageProps} onLoginSuccess={handleLoginSuccess} />;
  }

  if (!token) {
    return null;
  }

  return (
    <Layout
      isDarkMode={theme === 'dark'}
      onLogout={handleLogout}
      onToggleTheme={toggleTheme}
      userEmail={userEmail ?? undefined}
    >
      <PageComponent
        {...pageProps}
        onAuthSessionUpdated={handleAuthSessionUpdated}
        onLogout={handleLogout}
        refreshToken={refreshToken}
        token={token}
        userEmail={userEmail}
      />
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
