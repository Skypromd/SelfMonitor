import { useState, type FormEvent } from 'react';
import { useTranslation } from '../hooks/useTranslation';
import styles from '../styles/Home.module.css';

const AUTH_SERVICE_BASE_URL = process.env.NEXT_PUBLIC_AUTH_SERVICE_URL || 'http://localhost:8000';

type AdminPageProps = {
  token: string;
};

export default function AdminPage({ token }: AdminPageProps) {
  const [emailToDeactivate, setEmailToDeactivate] = useState('');
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');
  const { t } = useTranslation();

  const handleDeactivate = async (event: FormEvent) => {
    event.preventDefault();
    setError('');
    setMessage('');

    try {
      const response = await fetch(`${AUTH_SERVICE_BASE_URL}/users/${emailToDeactivate}/deactivate`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
      });
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.detail || 'Failed to deactivate user');
      }

      setMessage(`User ${data.email} has been deactivated.`);
      setEmailToDeactivate('');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unexpected error');
    }
  };

  return (
    <div className={styles.dashboard}>
      <h1>{t('nav.admin')}</h1>
      <p>{t('admin.description')}</p>
      <div className={styles.subContainer}>
        <h2>{t('admin.form_title')}</h2>
        <form onSubmit={handleDeactivate}>
          <input
            className={styles.input}
            onChange={(event) => setEmailToDeactivate(event.target.value)}
            placeholder="user.email@example.com"
            type="email"
            value={emailToDeactivate}
          />
          <button className={styles.button} type="submit">
            {t('admin.deactivate_button')}
          </button>
        </form>
        {message && <p className={styles.message}>{message}</p>}
        {error && <p className={styles.error}>{error}</p>}
      </div>
    </div>
  );
}
