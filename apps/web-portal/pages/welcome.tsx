import Head from 'next/head';
import { useRouter } from 'next/router';
import { useEffect } from 'react';

const LANGUAGES = [
  { code: 'en-GB', flag: '🇬🇧', name: 'English', native: 'English' },
  { code: 'pl-PL', flag: '🇵🇱', name: 'Polish', native: 'Polski' },
  { code: 'ro-RO', flag: '🇷🇴', name: 'Romanian', native: 'Română' },
  { code: 'uk-UA', flag: '🇺🇦', name: 'Ukrainian', native: 'Українська' },
  { code: 'ru-RU', flag: '🇷🇺', name: 'Russian', native: 'Русский' },
  { code: 'es-ES', flag: '🇪🇸', name: 'Spanish', native: 'Español' },
  { code: 'it-IT', flag: '🇮🇹', name: 'Italian', native: 'Italiano' },
  { code: 'pt-PT', flag: '🇵🇹', name: 'Portuguese', native: 'Português' },
  { code: 'tr-TR', flag: '🇹🇷', name: 'Turkish', native: 'Türkçe' },
  { code: 'bn-BD', flag: '🇧🇩', name: 'Bengali', native: 'বাংলা' },
];

export default function WelcomePage() {
  const router = useRouter();

  useEffect(() => {
    const saved = localStorage.getItem('preferredLocale');
    if (saved) {
      router.replace('/landing', undefined, { locale: saved });
    }
  }, [router]);

  const selectLanguage = (code: string) => {
    localStorage.setItem('preferredLocale', code);
    router.push('/landing', undefined, { locale: code });
  };

  return (
    <>
      <Head>
        <title>Welcome to SelfMonitor — Choose Your Language</title>
      </Head>
      <div style={{
        minHeight: '100vh',
        background: 'var(--lp-bg)',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '2rem',
      }}>
        <div style={{ textAlign: 'center', marginBottom: '3rem' }}>
          <h1 style={{
            fontSize: 'clamp(2rem, 5vw, 3rem)',
            fontWeight: 700,
            color: 'var(--lp-accent-teal)',
            letterSpacing: '-0.04em',
            margin: '0 0 0.5rem',
          }}>
            SelfMonitor
          </h1>
          <p style={{ color: 'var(--lp-text-muted)', fontSize: '1.1rem' }}>
            Choose your language / Выберите язык
          </p>
        </div>

        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))',
          gap: '1rem',
          maxWidth: '900px',
          width: '100%',
        }}>
          {LANGUAGES.map(({ code, flag, name, native }) => (
            <button
              key={code}
              onClick={() => selectLanguage(code)}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '1rem',
                padding: '1.25rem 1.5rem',
                background: 'var(--lp-bg-elevated)',
                border: '1px solid var(--lp-border)',
                borderRadius: 12,
                cursor: 'pointer',
                transition: 'all 0.2s',
                color: 'var(--lp-text)',
                fontSize: '1rem',
                textAlign: 'left',
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.borderColor = 'rgba(13,148,136,0.5)';
                e.currentTarget.style.transform = 'translateY(-2px)';
                e.currentTarget.style.boxShadow = '0 8px 24px rgba(0,0,0,0.3)';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.borderColor = 'rgba(148,163,184,0.15)';
                e.currentTarget.style.transform = 'translateY(0)';
                e.currentTarget.style.boxShadow = 'none';
              }}
            >
              <span style={{ fontSize: '2rem' }}>{flag}</span>
              <div>
                <div style={{ fontWeight: 600 }}>{native}</div>
                <div style={{ fontSize: '0.8rem', color: 'var(--lp-text-muted)' }}>{name}</div>
              </div>
            </button>
          ))}
        </div>

        <p style={{
          marginTop: '2.5rem',
          color: 'var(--lp-text-muted)',
          fontSize: '0.85rem',
        }}>
          You can change the language anytime in Settings
        </p>
      </div>
    </>
  );
}
