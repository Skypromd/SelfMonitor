import Head from 'next/head';
import { useEffect, useState } from 'react';
import styles from '../styles/Home.module.css';

const API_GATEWAY_URL = process.env.NEXT_PUBLIC_API_GATEWAY_URL || 'http://localhost:8000/api';
const AUTH_SERVICE_URL = process.env.NEXT_PUBLIC_AUTH_SERVICE_URL || 'http://localhost:8001';

type BillingPageProps = {
  token: string;
};

type Subscription = {
  plan: string;
  status: string;
  trial_end?: string;
  current_period_end?: string;
};

const PLAN_NAMES: Record<string, string> = {
  free: 'Free',
  starter: 'Starter',
  pro: 'Pro',
  business: 'Business',
};

const PLAN_PRICES: Record<string, string> = {
  free: '£0/mo',
  starter: '£9/mo',
  pro: '£19/mo',
  business: '£39/mo',
};

const PLAN_FEATURES: Record<string, string[]> = {
  free: [
    '1 bank connection',
    '200 transactions/month',
    'Basic tax calculator',
    'Email support',
  ],
  starter: [
    '3 bank connections',
    '1,000 transactions/month',
    'AI categorization',
    'Receipt OCR',
    'Cash flow forecasting',
  ],
  pro: [
    '3 bank connections',
    '5,000 transactions/month',
    'HMRC auto-submission',
    'Smart document search',
    'Mortgage readiness reports',
    'Advanced analytics',
    'API access',
  ],
  business: [
    'Everything in Pro',
    '5 team members',
    'Custom expense policies',
    'White-label reports',
    'Dedicated success manager',
  ],
};

const PLAN_ORDER = ['free', 'starter', 'pro', 'business'];

function getDaysRemaining(dateStr: string): number {
  const end = new Date(dateStr);
  const now = new Date();
  const diff = end.getTime() - now.getTime();
  return Math.max(0, Math.ceil(diff / (1000 * 60 * 60 * 24)));
}

export default function BillingPage({ token }: BillingPageProps) {
  const [subscription, setSubscription] = useState<Subscription | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    const fetchSubscription = async () => {
      try {
        const response = await fetch(`${AUTH_SERVICE_URL}/subscription/me`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (!response.ok) {
          throw new Error('Failed to fetch subscription');
        }
        const data = await response.json();
        setSubscription(data);
      } catch (err: unknown) {
        const details = err instanceof Error ? err.message : 'Failed to load subscription';
        setError(details);
      } finally {
        setLoading(false);
      }
    };

    fetchSubscription();
  }, [token]);

  const currentPlan = subscription?.plan || 'free';
  const planName = PLAN_NAMES[currentPlan] || 'Free';
  const planPrice = PLAN_PRICES[currentPlan] || '£0/mo';
  const isTrialing = subscription?.status === 'trialing';
  const trialDaysRemaining = isTrialing && subscription?.trial_end
    ? getDaysRemaining(subscription.trial_end)
    : 0;

  return (
    <>
      <Head>
        <title>Billing — SelfMonitor</title>
      </Head>
      <div>
        <h1>💳 Billing &amp; Subscription</h1>

        {loading && <p style={{ color: '#94a3b8' }}>Loading subscription...</p>}
        {error && <p className={styles.error}>{error}</p>}

        {!loading && subscription && (
          <>
            {isTrialing && (
              <div style={{
                width: '100%',
                padding: '1rem 1.5rem',
                borderRadius: 12,
                background: 'rgba(13,148,136,0.15)',
                border: '1px solid rgba(13,148,136,0.3)',
                marginBottom: '1.5rem',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                gap: '1rem',
              }}>
                <span style={{ color: '#14b8a6', fontWeight: 600, fontSize: '1rem' }}>
                  🎉 {planName} trial — {trialDaysRemaining} day{trialDaysRemaining !== 1 ? 's' : ''} remaining
                </span>
                <span style={{ color: '#94a3b8', fontSize: '0.85rem' }}>
                  Ends {subscription.trial_end ? new Date(subscription.trial_end).toLocaleDateString() : ''}
                </span>
              </div>
            )}

            <div className={styles.subContainer}>
              <h2>Current Plan: {planName}</h2>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
                <div>
                  <p style={{ color: '#f1f5f9', fontSize: '2rem', fontWeight: 700, margin: 0 }}>
                    {planPrice}
                  </p>
                  <p style={{ color: '#94a3b8', fontSize: '0.9rem', margin: '0.25rem 0 0' }}>
                    Status: <span style={{
                      color: isTrialing ? '#14b8a6' : subscription.status === 'active' ? '#34d399' : '#f87171',
                      fontWeight: 600,
                      textTransform: 'capitalize',
                    }}>
                      {subscription.status}
                    </span>
                  </p>
                </div>
              </div>

              <h3 style={{ color: '#f1f5f9', fontSize: '1rem', marginTop: '1rem' }}>Plan Features</h3>
              <ul style={{ listStyle: 'none', padding: 0, margin: 0 }}>
                {(PLAN_FEATURES[currentPlan] || []).map((feature) => (
                  <li key={feature} style={{
                    padding: '0.4rem 0',
                    color: '#94a3b8',
                    fontSize: '0.9rem',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '0.5rem',
                  }}>
                    <span style={{ color: '#14b8a6' }}>✓</span> {feature}
                  </li>
                ))}
              </ul>
            </div>

            <div style={{ marginTop: '2rem' }}>
              <h2 style={{ color: '#f1f5f9', fontSize: '1.25rem', marginBottom: '1rem' }}>
                {currentPlan === 'business' ? 'Other Plans' : 'Upgrade Your Plan'}
              </h2>
              <div style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))',
                gap: '1rem',
              }}>
                {PLAN_ORDER.filter((p) => p !== currentPlan).map((plan) => (
                  <div key={plan} style={{
                    background: 'var(--lp-bg-elevated)',
                    border: '1px solid var(--lp-border)',
                    borderRadius: 12,
                    padding: '1.5rem',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '0.5rem',
                  }}>
                    <p style={{ color: '#f1f5f9', fontWeight: 700, fontSize: '1.1rem', margin: 0 }}>
                      {PLAN_NAMES[plan]}
                    </p>
                    <p style={{ color: '#14b8a6', fontWeight: 700, fontSize: '1.5rem', margin: 0 }}>
                      {PLAN_PRICES[plan]}
                    </p>
                    <ul style={{ listStyle: 'none', padding: 0, margin: '0.5rem 0', flex: 1 }}>
                      {(PLAN_FEATURES[plan] || []).slice(0, 3).map((f) => (
                        <li key={f} style={{ color: '#94a3b8', fontSize: '0.8rem', padding: '0.15rem 0' }}>
                          ✓ {f}
                        </li>
                      ))}
                      {(PLAN_FEATURES[plan] || []).length > 3 && (
                        <li style={{ color: '#64748b', fontSize: '0.8rem', padding: '0.15rem 0' }}>
                          +{(PLAN_FEATURES[plan] || []).length - 3} more features
                        </li>
                      )}
                    </ul>
                    <button
                      className={styles.button}
                      style={{ width: '100%', marginTop: '0.5rem' }}
                    >
                      {PLAN_ORDER.indexOf(plan) > PLAN_ORDER.indexOf(currentPlan) ? 'Upgrade' : 'Switch'}
                    </button>
                  </div>
                ))}
              </div>
            </div>
          </>
        )}

        {!loading && !subscription && !error && (
          <div className={styles.subContainer}>
            <h2>No Active Subscription</h2>
            <p style={{ color: '#94a3b8' }}>
              You are currently on the Free plan. Upgrade to unlock more features.
            </p>
          </div>
        )}
      </div>
    </>
  );
}
