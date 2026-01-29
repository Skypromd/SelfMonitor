import { useEffect, useState } from 'react';

import { apiRequest } from '../services/api';
import { useAuth } from '../context/AuthContext';

type SubscriptionPlan = 'free' | 'pro';
type SubscriptionStatus = 'active' | 'trialing' | 'past_due' | 'canceled' | 'incomplete';

export const useSubscriptionPlan = () => {
  const { token } = useAuth();
  const [plan, setPlan] = useState<SubscriptionPlan>('free');
  const [status, setStatus] = useState<SubscriptionStatus>('active');
  const [billingCycle, setBillingCycle] = useState<string>('monthly');
  const [currentPeriodEnd, setCurrentPeriodEnd] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const refresh = async () => {
    if (!token) return;
    setIsLoading(true);
    try {
      const response = await apiRequest('/profile/subscriptions/me', { token });
      if (!response.ok) return;
      const data = await response.json();
      setPlan((data.subscription_plan || 'free') as SubscriptionPlan);
      setStatus((data.subscription_status || 'active') as SubscriptionStatus);
      setBillingCycle(data.billing_cycle || 'monthly');
      setCurrentPeriodEnd(data.current_period_end || null);
    } catch {
      return;
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    refresh();
  }, [token]);

  const trialDaysLeft = (() => {
    if (status !== 'trialing' || !currentPeriodEnd) return null;
    const end = new Date(currentPeriodEnd);
    const days = Math.ceil((end.getTime() - Date.now()) / 86400000);
    return Math.max(days, 0);
  })();

  return { plan, status, billingCycle, currentPeriodEnd, trialDaysLeft, isLoading, refresh };
};
