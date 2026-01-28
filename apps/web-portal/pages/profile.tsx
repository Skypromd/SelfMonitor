import { useState, FormEvent, useEffect, ChangeEvent } from 'react';
import styles from '../styles/Home.module.css';
import { useTranslation } from '../hooks/useTranslation';

const PROFILE_SERVICE_BASE_URL = process.env.NEXT_PUBLIC_PROFILE_SERVICE_URL || 'http://localhost:8001';

type ProfilePageProps = {
  token: string;
};

export default function ProfilePage({ token }: ProfilePageProps) {
  const [profile, setProfile] = useState({ first_name: '', last_name: '', date_of_birth: '' });
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const { t } = useTranslation();

  const fetchProfile = async () => {
    setMessage('');
    setError('');
    try {
      const response = await fetch(`${PROFILE_SERVICE_BASE_URL}/profiles/me`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (response.status === 404) {
        setMessage(t('profile.empty_profile'));
        setProfile({ first_name: '', last_name: '', date_of_birth: '' });
        return;
      }
      if (!response.ok) throw new Error('Failed to fetch profile');
      const data = await response.json();
      setProfile({ first_name: data.first_name || '', last_name: data.last_name || '', date_of_birth: data.date_of_birth || '' });
    } catch (err: any) {
      setError(err.message);
    }
  };

  useEffect(() => { fetchProfile(); }, [token]);

  const handleProfileChange = (e: ChangeEvent<HTMLInputElement>) => setProfile({ ...profile, [e.target.name]: e.target.value });

  const handleSaveProfile = async (e: FormEvent) => {
    e.preventDefault();
    setMessage('');
    setError('');
    try {
      const response = await fetch(`${PROFILE_SERVICE_BASE_URL}/profiles/me`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
        body: JSON.stringify({ ...profile, date_of_birth: profile.date_of_birth || null })
      });
      if (!response.ok) throw new Error('Failed to save profile');
      setMessage(t('profile.saved_message'));
    } catch (err: any) {
      setError(err.message);
    }
  };

  return (
    <div>
      <h1>{t('profile.title')}</h1>
      <p>{t('profile.description')}</p>
      <div className={styles.subContainer}>
        <form onSubmit={handleSaveProfile}>
          <input type="text" name="first_name" placeholder={t('profile.first_name')} value={profile.first_name} onChange={handleProfileChange} className={styles.input} />
          <input type="text" name="last_name" placeholder={t('profile.last_name')} value={profile.last_name} onChange={handleProfileChange} className={styles.input} />
          <input type="date" name="date_of_birth" placeholder={t('profile.date_of_birth')} value={profile.date_of_birth} onChange={handleProfileChange} className={styles.input} />
          <button type="submit" className={styles.button}>{t('common.save')}</button>
        </form>
        {message && <p className={styles.message}>{message}</p>}
        {error && <p className={styles.error}>{error}</p>}
      </div>
    </div>
  );
}
