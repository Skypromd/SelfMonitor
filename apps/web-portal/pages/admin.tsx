import { FormEvent, useState } from 'react';
import styles from '../styles/Home.module.css';
import { useTranslation } from '../hooks/useTranslation';

const API_GATEWAY_URL = process.env.NEXT_PUBLIC_API_GATEWAY_URL || 'http://localhost:8000/api';

type AdminPageProps = {
  token: string;
};

export default function AdminPage({ token }: AdminPageProps) {
  const [emailToDeactivate, setEmailToDeactivate] = useState('');
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');
  const { t } = useTranslation();

  const handleDeactivate = async (e: FormEvent) => {
    e.preventDefault();
    setError('');
    setMessage('');

    try {
      const response = await fetch(`${API_GATEWAY_URL}/auth/users/${emailToDeactivate}/deactivate`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
      });
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.detail || 'Failed to deactivate user');
      }
      setMessage(`User ${data.email} has been deactivated.`);
      setEmailToDeactivate('');
    } catch (err: unknown) {
      const details = err instanceof Error ? err.message : 'Failed to deactivate user';
      setError(details);
    }
  };

  return (
    <div>
      <h1>{t('nav.admin')}</h1>
      <p>{t('admin.description')}</p>
      <div className={styles.subContainer}>
        <h2>{t('admin.form_title')}</h2>
        <form onSubmit={handleDeactivate}>
          <input
            type="email"
            placeholder="user.email@example.com"
            value={emailToDeactivate}
            onChange={(e) => setEmailToDeactivate(e.target.value)}
            className={styles.input}
          />
          <button type="submit" className={styles.button}>
            {t('admin.deactivate_button')}
          </button>
        </form>
        {message && <p className={styles.message}>{message}</p>}
        {error && <p className={styles.error}>{error}</p>}
      </div>
    </div>
  );
}
