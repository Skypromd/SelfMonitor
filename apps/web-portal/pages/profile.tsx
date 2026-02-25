import { useCallback, useEffect, useState, type ChangeEvent, type FormEvent } from 'react';
import { useTranslation } from '../hooks/useTranslation';
import styles from '../styles/Home.module.css';

const PROFILE_SERVICE_BASE_URL = process.env.NEXT_PUBLIC_PROFILE_SERVICE_URL || 'http://localhost:8001';

type ProfilePageProps = {
  token: string;
};

type ProfileState = {
  first_name: string;
  last_name: string;
  date_of_birth: string;
};

export default function ProfilePage({ token }: ProfilePageProps) {
  const [profile, setProfile] = useState<ProfileState>({
    first_name: '',
    last_name: '',
    date_of_birth: '',
  });
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const { t } = useTranslation();

  const fetchProfile = useCallback(async () => {
    setMessage('');
    setError('');
    try {
      const response = await fetch(`${PROFILE_SERVICE_BASE_URL}/profiles/me`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (response.status === 404) {
        setMessage(t('profile.empty_profile'));
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
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unexpected error');
    }
  }, [token]);

  useEffect(() => {
    fetchProfile();
  }, [fetchProfile]);

  const handleProfileChange = (event: ChangeEvent<HTMLInputElement>) => {
    setProfile((current) => ({ ...current, [event.target.name]: event.target.value }));
  };

  const handleSaveProfile = async (event: FormEvent) => {
    event.preventDefault();
    setMessage('');
    setError('');

    try {
      const response = await fetch(`${PROFILE_SERVICE_BASE_URL}/profiles/me`, {
        body: JSON.stringify({ ...profile, date_of_birth: profile.date_of_birth || null }),
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        method: 'PUT',
      });
      if (!response.ok) {
        throw new Error('Failed to save profile');
      }
      setMessage('Profile saved successfully!');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unexpected error');
    }
  };

  return (
    <div className={styles.dashboard}>
      <h1>{t('profile.title')}</h1>
      <p>Fetch and update your profile data from a protected endpoint.</p>
      <div className={styles.subContainer}>
        <form onSubmit={handleSaveProfile}>
          <input
            className={styles.input}
            name="first_name"
            onChange={handleProfileChange}
            placeholder="First Name"
            type="text"
            value={profile.first_name}
          />
          <input
            className={styles.input}
            name="last_name"
            onChange={handleProfileChange}
            placeholder="Last Name"
            type="text"
            value={profile.last_name}
          />
          <input
            className={styles.input}
            name="date_of_birth"
            onChange={handleProfileChange}
            placeholder="Date of Birth"
            type="date"
            value={profile.date_of_birth}
          />
          <button className={styles.button} type="submit">
            {t('common.save')}
          </button>
        </form>
        {message && <p className={styles.message}>{message}</p>}
        {error && <p className={styles.error}>{error}</p>}
      </div>
      <div className={styles.subContainer}>
        <h2>{t('subscription.title')}</h2>
        <p>{t('subscription.description')}</p>
        <form onSubmit={handleSaveSubscription}>
          <div style={{ marginBottom: '1rem' }}>
            <div style={{ marginBottom: '0.5rem', color: '#4a5568' }}>{t('subscription.plan_label')}</div>
            <select name="subscription_plan" value={subscription.subscription_plan} onChange={handleSubscriptionChange} className={styles.input}>
              <option value="free">{t('subscription.plan_free')}</option>
              <option value="pro">{t('subscription.plan_pro')}</option>
            </select>
          </div>
          <div style={{ marginBottom: '1rem' }}>
            <div style={{ marginBottom: '0.5rem', color: '#4a5568' }}>{t('subscription.close_day_label')}</div>
            <input
              type="number"
              name="monthly_close_day"
              min={1}
              max={28}
              value={subscription.monthly_close_day}
              onChange={handleSubscriptionChange}
              className={styles.input}
            />
          </div>
          <div className={styles.subContainer} style={{ marginTop: 0 }}>
            <p><strong>{t('subscription.status_label')}:</strong> {subscription.subscription_status}</p>
            <p><strong>{t('subscription.cycle_label')}:</strong> {subscription.billing_cycle}</p>
            <p><strong>{t('subscription.period_label')}:</strong> {subscription.current_period_start || '-'} → {subscription.current_period_end || '-'}</p>
          </div>
          <button type="submit" className={styles.button}>{t('subscription.update_button')}</button>
        </form>
        {message && <p className={styles.message}>{message}</p>}
        {error && <p className={styles.error}>{error}</p>}
      </div>
    </div>
  );
}
