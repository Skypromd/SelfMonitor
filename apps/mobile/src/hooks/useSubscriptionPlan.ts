import { useEffect, useState } from 'react';

import { apiRequest } from '../services/api';
import { useAuth } from '../context/AuthContext';

type SubscriptionPlan = 'free' | 'pro';

export const useSubscriptionPlan = () => {
  const { token } = useAuth();
  const [plan, setPlan] = useState<SubscriptionPlan>('free');
  const [isLoading, setIsLoading] = useState(false);

  const refresh = async () => {
    if (!token) return;
    setIsLoading(true);
    try {
      const response = await apiRequest('/profile/subscriptions/me', { token });
      if (!response.ok) return;
      const data = await response.json();
      setPlan((data.subscription_plan || 'free') as SubscriptionPlan);
    } catch {
      return;
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    refresh();
  }, [token]);

  return { plan, isLoading, refresh };
};
