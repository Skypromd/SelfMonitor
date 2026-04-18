import Head from 'next/head';
import Link from 'next/link';
import { FormEvent, useState } from 'react';
import { loginWithPassword } from '../../lib/authLogin';
import styles from '../../styles/Home.module.css';

type AdminLoginProps = { onLoginSuccess: (token: string) => void };

/**
 * Отдельный вход для администраторов (визуально и по URL отличается от /login).
 */
export default function AdminLoginPage({ onLoginSuccess }: AdminLoginProps) {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [totpRequired, setTotpRequired] = useState(false);
  const [totpCode, setTotpCode] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleLogin = async (e: FormEvent, totpOverride?: string) => {
    e.preventDefault();
    setError('');
    if (!email.trim() || !password.trim()) {
      setError('Введите email и пароль.');
      return;
    }
    setLoading(true);
    try {
      const code = totpOverride || totpCode;
      const result = await loginWithPassword({
        email: email.trim(),
        password,
        totpCode: code || undefined,
      });

      if (!result.ok && result.status === 403 && result.detail === '2FA_REQUIRED') {
        setTotpRequired(true);
        setTotpCode('');
        setLoading(false);
        return;
      }
      if (!result.ok && result.status === 403 && result.detail === 'ADMIN_2FA_SETUP_REQUIRED') {
        setError(
          'Для админ-аккаунта нужна 2FA. Включите её в разделе Security, затем войдите снова.',
        );
        setLoading(false);
        return;
      }
      if (!result.ok) {
        throw new Error(result.detail || 'Ошибка входа');
      }
      onLoginSuccess(result.access_token);
    } catch (err: unknown) {
      if (err instanceof TypeError && err.message === 'Failed to fetch') {
        setError('Нет соединения с сервером. Проверьте Docker (шлюз :8000).');
      } else {
        setError(err instanceof Error ? err.message : 'Ошибка входа');
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      <Head>
        <title>Admin — MyNetTax Operations</title>
        <meta name="robots" content="noindex,nofollow" />
      </Head>
      <div
        className={styles.container}
        style={{
          background:
            'radial-gradient(ellipse 120% 80% at 50% -20%, rgba(180,83,9,0.15), transparent 50%), var(--lp-bg, #0f172a)',
        }}
      >
        <main className={styles.main} style={{ maxWidth: 440 }}>
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '0.75rem',
              marginBottom: '1.5rem',
              padding: '0.5rem 0.75rem',
              borderRadius: 12,
              background: 'rgba(245,158,11,0.08)',
              border: '1px solid rgba(245,158,11,0.25)',
            }}
          >
            <span
              style={{
                width: 40,
                height: 40,
                borderRadius: 10,
                background: 'linear-gradient(135deg,#b45309,#92400e)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontSize: '0.7rem',
                fontWeight: 800,
                color: '#fff',
              }}
            >
              OP
            </span>
            <div>
              <div style={{ fontWeight: 800, fontSize: '0.95rem', color: '#fbbf24' }}>
                Operations Console
              </div>
              <div style={{ fontSize: '0.75rem', color: '#94a3b8' }}>MyNetTax — только для staff</div>
            </div>
          </div>

          {!totpRequired ? (
            <>
              <h1 className={styles.title} style={{ fontSize: '1.65rem', marginBottom: '0.25rem' }}>
                Вход администратора
              </h1>
              <p className={styles.description} style={{ marginBottom: '1.75rem' }}>
                Учётные данные владельца / админа (не путать с обычным логином клиентов).
              </p>

              <form onSubmit={handleLogin} style={{ width: '100%' }}>
                <label htmlFor="admin-login-email">Служебный email</label>
                <input
                  id="admin-login-email"
                  type="email"
                  placeholder="admin@…"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className={styles.input}
                  required
                  autoComplete="username"
                />

                <label htmlFor="admin-login-password" style={{ marginTop: '0.75rem', display: 'block' }}>
                  Пароль
                </label>
                <div className={styles.passwordWrapper}>
                  <input
                    id="admin-login-password"
                    type={showPassword ? 'text' : 'password'}
                    placeholder="••••••••"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    className={styles.input}
                    style={{ paddingRight: '3rem' }}
                    required
                    autoComplete="current-password"
                  />
                  <button
                    type="button"
                    className={styles.passwordToggle}
                    onClick={() => setShowPassword((v) => !v)}
                    aria-label={showPassword ? 'Скрыть пароль' : 'Показать пароль'}
                  >
                    <span style={{ fontSize: '0.7rem', color: '#94a3b8' }}>
                      {showPassword ? 'Скрыть' : 'Показать'}
                    </span>
                  </button>
                </div>

                {error && (
                  <p className={styles.error} role="alert" style={{ marginTop: '0.5rem' }}>
                    {error}
                  </p>
                )}

                <button
                  type="submit"
                  className={styles.button}
                  disabled={loading}
                  style={{
                    width: '100%',
                    marginTop: '1.25rem',
                    height: 48,
                    background: 'linear-gradient(135deg,#b45309,#d97706)',
                  }}
                >
                  {loading ? 'Вход…' : 'Войти в панель →'}
                </button>
              </form>

              <p style={{ marginTop: '0.75rem', textAlign: 'center' }}>
                <Link href="/" style={{ color: '#475569', fontSize: '0.8rem' }}>
                  ← На главную
                </Link>
              </p>
            </>
          ) : (
            <>
              <h1 className={styles.title} style={{ fontSize: '1.5rem' }}>
                Двухфакторная аутентификация
              </h1>
              <p className={styles.description} style={{ marginBottom: '1.5rem' }}>
                Код из приложения-аутентификатора.
              </p>
              <form onSubmit={(e) => handleLogin(e)} style={{ width: '100%' }}>
                <label htmlFor="admin-totp">Код</label>
                <input
                  id="admin-totp"
                  type="text"
                  inputMode="numeric"
                  pattern="[0-9]*"
                  maxLength={6}
                  placeholder="000000"
                  value={totpCode}
                  onChange={(e) => setTotpCode(e.target.value.replace(/\D/g, '').slice(0, 6))}
                  className={styles.input}
                  style={{ letterSpacing: '0.4em', fontSize: '1.5rem', textAlign: 'center' }}
                  autoComplete="one-time-code"
                  autoFocus
                />
                {error && <p className={styles.error}>{error}</p>}
                <div style={{ display: 'flex', gap: '0.75rem', marginTop: '1rem' }}>
                  <button
                    type="button"
                    onClick={() => {
                      setTotpRequired(false);
                      setTotpCode('');
                      setError('');
                    }}
                    className={styles.button}
                    style={{
                      flex: 1,
                      background: 'transparent',
                      border: '1px solid var(--lp-border)',
                      color: '#94a3b8',
                      height: 48,
                    }}
                  >
                    ← Назад
                  </button>
                  <button
                    type="submit"
                    className={styles.button}
                    disabled={totpCode.length !== 6 || loading}
                    style={{ flex: 2, height: 48, background: 'linear-gradient(135deg,#b45309,#d97706)' }}
                  >
                    {loading ? '…' : 'Проверить →'}
                  </button>
                </div>
              </form>
            </>
          )}
        </main>
      </div>
    </>
  );
}
