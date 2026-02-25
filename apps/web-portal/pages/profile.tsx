import { ChangeEvent, FormEvent, useEffect, useState } from 'react';
import styles from '../styles/Home.module.css';
import { useTranslation } from '../hooks/useTranslation';

const API_GATEWAY_URL = process.env.NEXT_PUBLIC_API_GATEWAY_URL || 'http://localhost:8000/api';

type ProfilePageProps = {
  token: string;
};

type UserProfile = {
  first_name: string;
  last_name: string;
  date_of_birth: string;
};

export default function ProfilePage({ token }: ProfilePageProps) {
  const [profile, setProfile] = useState<UserProfile>({
    first_name: '',
    last_name: '',
    date_of_birth: '',
  });
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const { t } = useTranslation();

  const fetchProfile = async () => {
    setMessage('');
    setError('');
    try {
      const response = await fetch(`${API_GATEWAY_URL}/profile/profiles/me`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (response.status === 404) {
        setMessage('No profile found. Create one by saving.');
        setProfile({ first_name: '', last_name: '', date_of_birth: '' });
        return;
      }
      if (!response.ok) {
        throw new Error('Failed to fetch profile');
      }
      const data = await response.json();
      setProfile({
        first_name: data.first_name || '',
        last_name: data.last_name || '',
        date_of_birth: data.date_of_birth || '',
      });
    } catch (err: unknown) {
      const details = err instanceof Error ? err.message : 'Failed to fetch profile';
      setError(details);
    }
  };

  useEffect(() => {
    fetchProfile();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token]);

  const handleProfileChange = (e: ChangeEvent<HTMLInputElement>) => {
    setProfile({ ...profile, [e.target.name]: e.target.value });
  };

  const handleSaveProfile = async (e: FormEvent) => {
    e.preventDefault();
    setMessage('');
    setError('');
    try {
      const response = await fetch(`${API_GATEWAY_URL}/profile/profiles/me`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({ ...profile, date_of_birth: profile.date_of_birth || null }),
      });
      if (!response.ok) {
        throw new Error('Failed to save profile');
      }
      setMessage('Profile saved successfully!');
    } catch (err: unknown) {
      const details = err instanceof Error ? err.message : 'Failed to save profile';
      setError(details);
    }
  };

  return (
    <div>
      <h1>{t('profile.title')}</h1>
      <p>Fetch and update your profile data from a protected endpoint.</p>
      <div className={styles.subContainer}>
        <form onSubmit={handleSaveProfile}>
          <input
            type="text"
            name="first_name"
            placeholder="First Name"
            value={profile.first_name}
            onChange={handleProfileChange}
            className={styles.input}
          />
          <input
            type="text"
            name="last_name"
            placeholder="Last Name"
            value={profile.last_name}
            onChange={handleProfileChange}
            className={styles.input}
          />
          <input
            type="date"
            name="date_of_birth"
            placeholder="Date of Birth"
            value={profile.date_of_birth}
            onChange={handleProfileChange}
            className={styles.input}
          />
          <button type="submit" className={styles.button}>
            {t('common.save')}
          </button>
        </form>
        {message && <p className={styles.message}>{message}</p>}
        {error && <p className={styles.error}>{error}</p>}
      </div>
    </div>
  );
}
