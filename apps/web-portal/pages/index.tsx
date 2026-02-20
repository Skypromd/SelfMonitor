import { FormEvent, useState } from 'react';
import styles from '../styles/Home.module.css';
import { useTranslation } from '../hooks/useTranslation';

const API_GATEWAY_URL = process.env.NEXT_PUBLIC_API_GATEWAY_URL || 'http://localhost:8000/api';

type IndexPageProps = {
  onLoginSuccess: (newToken: string) => void;
};

export default function HomePage({ onLoginSuccess }: IndexPageProps) {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const { t } = useTranslation();

  const clearFeedback = () => {
    setMessage('');
    setError('');
  };

  const handleRegister = async (e: FormEvent) => {
    e.preventDefault();
    clearFeedback();

    try {
      const response = await fetch(`${API_GATEWAY_URL}/auth/register`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password }),
      });
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.detail || 'Registration failed');
      }
      setMessage(`User ${data.email} registered successfully! You can now log in.`);
    } catch (err: unknown) {
      const details = err instanceof Error ? err.message : 'Registration failed';
      setError(details);
    }
  };

  const handleLogin = async (e: FormEvent) => {
    e.preventDefault();
    clearFeedback();

    try {
      const formData = new URLSearchParams();
      formData.append('username', email);
      formData.append('password', password);

      const response = await fetch(`${API_GATEWAY_URL}/auth/token`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: formData,
      });
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.detail || 'Login failed');
      }

      onLoginSuccess(data.access_token);
    } catch (err: unknown) {
      const details = err instanceof Error ? err.message : 'Login failed';
      setError(details);
    }
  };

  return (
    <div className={styles.container}>
      <main className={styles.main}>
        <h1 className={styles.title}>{t('login.title')}</h1>
        <p className={styles.description}>{t('login.description')}</p>
        <div className={styles.formContainer}>
          <form>
            <input
              type="email"
              placeholder="Email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className={styles.input}
            />
            <input
              type="password"
              placeholder="Password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className={styles.input}
            />
            <div className={styles.buttonGroup}>
              <button onClick={handleRegister} className={styles.button}>
                {t('login.register_button')}
              </button>
              <button onClick={handleLogin} className={styles.button}>
                {t('login.login_button')}
              </button>
            </div>
          </form>
        </div>
        {message && <p className={styles.message}>{message}</p>}
        {error && <p className={styles.error}>{error}</p>}
      </main>
    </div>
  );
}
