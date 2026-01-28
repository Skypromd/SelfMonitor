import { useState, FormEvent } from 'react';
import styles from '../styles/Home.module.css';
import { useTranslation } from '../hooks/useTranslation';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_GATEWAY_URL || 'http://localhost:8000/api';

type HomePageProps = {
  onLoginSuccess: (token: string) => void;
};

export default function HomePage({ onLoginSuccess }: HomePageProps) {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const { t } = useTranslation();

  const clearMessages = () => {
    setMessage('');
    setError('');
  };

  const handleRegister = async (e: FormEvent) => {
    e.preventDefault();
    clearMessages();
    try {
      const formData = new URLSearchParams();
      formData.append('username', email);
      formData.append('password', password);
      const response = await fetch(`${API_BASE_URL}/auth/register`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: formData,
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || 'Registration failed');
      setMessage(t('login.register_success'));
    } catch (err: any) {
      setError(err.message);
    }
  };

  const handleLogin = async (e: FormEvent) => {
    e.preventDefault();
    clearMessages();
    try {
      const formData = new URLSearchParams();
      formData.append('username', email);
      formData.append('password', password);
      const response = await fetch(`${API_BASE_URL}/auth/token`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: formData,
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || 'Login failed');
      onLoginSuccess(data.access_token);
    } catch (err: any) {
      setError(err.message);
    }
  };

  return (
    <div className={styles.container}>
      <main className={styles.main}>
        <h1 className={styles.title}>{t('login.title')}</h1>
        <p className={styles.description}>{t('login.description')}</p>
        <div className={styles.formContainer}>
          <form>
            <input type="email" placeholder={t('login.email_placeholder')} value={email} onChange={(e) => setEmail(e.target.value)} className={styles.input} />
            <input type="password" placeholder={t('login.password_placeholder')} value={password} onChange={(e) => setPassword(e.target.value)} className={styles.input} />
            <div className={styles.buttonGroup}>
              <button onClick={handleRegister} className={styles.button}>{t('login.register_button')}</button>
              <button onClick={handleLogin} className={styles.button}>{t('login.login_button')}</button>
            </div>
          </form>
        </div>
        {message && <p className={styles.message}>{message}</p>}
        {error && <p className={styles.error}>{error}</p>}
      </main>
    </div>
  );
}
