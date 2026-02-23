import { useState, FormEvent, useEffect, ChangeEvent } from 'react';
import styles from '../styles/Home.module.css';
import { useTranslation } from '../hooks/useTranslation';

const PROFILE_SERVICE_BASE_URL = process.env.NEXT_PUBLIC_PROFILE_SERVICE_URL || 'http://localhost:8001';

type ProfilePageProps = {
  token: string;
};

export default function ProfilePage({ token }: ProfilePageProps) {
  const [profile, setProfile] = useState({ first_name: '', last_name: '', date_of_birth: '' });
  const [subscription, setSubscription] = useState({
    subscription_plan: 'free',
    subscription_status: 'active',
    billing_cycle: 'monthly',
    current_period_start: '',
    current_period_end: '',
    monthly_close_day: 1,
  });
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

  const fetchSubscription = async () => {
    try {
      const response = await fetch(`${PROFILE_SERVICE_BASE_URL}/subscriptions/me`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (!response.ok) throw new Error('Failed to fetch subscription');
      const data = await response.json();
      setSubscription({
        subscription_plan: data.subscription_plan || 'free',
        subscription_status: data.subscription_status || 'active',
        billing_cycle: data.billing_cycle || 'monthly',
        current_period_start: data.current_period_start || '',
        current_period_end: data.current_period_end || '',
        monthly_close_day: data.monthly_close_day || 1,
      });
    } catch (err: any) {
      setError(err.message);
    }
  };

  useEffect(() => {
    fetchProfile();
    fetchSubscription();
  }, [token]);

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

  const handleSubscriptionChange = (e: ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    const { name, value } = e.target;
    setSubscription(prev => ({
      ...prev,
      [name]: name === 'monthly_close_day' ? Number(value) : value,
    }));
  };

  const handleSaveSubscription = async (e: FormEvent) => {
    e.preventDefault();
    setMessage('');
    setError('');
    try {
      const response = await fetch(`${PROFILE_SERVICE_BASE_URL}/subscriptions/me`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
        body: JSON.stringify({
          subscription_plan: subscription.subscription_plan,
          subscription_status: subscription.subscription_status,
          billing_cycle: subscription.billing_cycle,
          monthly_close_day: subscription.monthly_close_day,
        })
      });
      if (!response.ok) throw new Error('Failed to update subscription');
      const data = await response.json();
      setSubscription({
        subscription_plan: data.subscription_plan || 'free',
        subscription_status: data.subscription_status || 'active',
        billing_cycle: data.billing_cycle || 'monthly',
        current_period_start: data.current_period_start || '',
        current_period_end: data.current_period_end || '',
        monthly_close_day: data.monthly_close_day || 1,
      });
      setMessage(t('subscription.updated_message'));
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
