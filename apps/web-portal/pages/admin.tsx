import { useState, FormEvent } from 'react';
import styles from '../styles/Home.module.css';
import { useTranslation } from '../hooks/useTranslation';

const AUTH_SERVICE_BASE_URL = process.env.NEXT_PUBLIC_AUTH_SERVICE_URL || 'http://localhost:8000';

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
      const response = await fetch(`${AUTH_SERVICE_BASE_URL}/users/${emailToDeactivate}/deactivate`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` }
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || 'Failed to deactivate user');
      setMessage(`${t('admin.deactivated_message')} ${data.email}.`);
      setEmailToDeactivate('');
    } catch (err: any) {
      setError(err.message);
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
            placeholder={t('admin.email_placeholder')} 
            value={emailToDeactivate} 
            onChange={e => setEmailToDeactivate(e.target.value)} 
            className={styles.input}
          />
          <button type="submit" className={styles.button}>{t('admin.deactivate_button')}</button>
        </form>
        {message && <p className={styles.message}>{message}</p>}
        {error && <p className={styles.error}>{error}</p>}
      </div>
    </div>
  );
}
