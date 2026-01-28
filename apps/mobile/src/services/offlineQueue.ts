import AsyncStorage from '@react-native-async-storage/async-storage';

import { apiRequest } from './api';

const QUEUE_KEY = 'offline.queue.v1';

type CategoryUpdateAction = {
  id: string;
  type: 'update_category';
  payload: {
    transactionId: string;
    category: string;
  };
  createdAt: string;
};

type ProfileUpdateAction = {
  id: string;
  type: 'update_profile';
  payload: {
    first_name: string;
    last_name: string;
    date_of_birth?: string | null;
  };
  createdAt: string;
};

type SubscriptionUpdateAction = {
  id: string;
  type: 'update_subscription';
  payload: {
    subscription_plan: string;
    monthly_close_day: number;
  };
  createdAt: string;
};

type OfflineAction = CategoryUpdateAction | ProfileUpdateAction | SubscriptionUpdateAction;

const loadQueue = async (): Promise<OfflineAction[]> => {
  try {
    const stored = await AsyncStorage.getItem(QUEUE_KEY);
    if (!stored) return [];
    return JSON.parse(stored) as OfflineAction[];
  } catch {
    return [];
  }
};

const saveQueue = async (queue: OfflineAction[]) => {
  try {
    await AsyncStorage.setItem(QUEUE_KEY, JSON.stringify(queue));
  } catch {
    return;
  }
};

export const getQueueCount = async () => {
  const queue = await loadQueue();
  return queue.length;
};

export const enqueueCategoryUpdate = async (transactionId: string, category: string) => {
  const queue = await loadQueue();
  const filtered = queue.filter(
    (item) => !(item.type === 'update_category' && item.payload.transactionId === transactionId)
  );
  const next: CategoryUpdateAction = {
    id: `${transactionId}-${Date.now()}`,
    type: 'update_category',
    payload: { transactionId, category },
    createdAt: new Date().toISOString(),
  };
  filtered.push(next);
  await saveQueue(filtered);
  return filtered.length;
};

export const enqueueProfileUpdate = async (payload: ProfileUpdateAction['payload']) => {
  const queue = await loadQueue();
  const filtered = queue.filter((item) => item.type !== 'update_profile');
  const next: ProfileUpdateAction = {
    id: `profile-${Date.now()}`,
    type: 'update_profile',
    payload,
    createdAt: new Date().toISOString(),
  };
  filtered.push(next);
  await saveQueue(filtered);
  return filtered.length;
};

export const enqueueSubscriptionUpdate = async (payload: SubscriptionUpdateAction['payload']) => {
  const queue = await loadQueue();
  const filtered = queue.filter((item) => item.type !== 'update_subscription');
  const next: SubscriptionUpdateAction = {
    id: `subscription-${Date.now()}`,
    type: 'update_subscription',
    payload,
    createdAt: new Date().toISOString(),
  };
  filtered.push(next);
  await saveQueue(filtered);
  return filtered.length;
};

export const flushQueue = async (token: string | null) => {
  if (!token) return { flushed: 0, remaining: 0 };
  let queue = await loadQueue();
  let flushed = 0;

  for (const item of queue) {
    if (item.type === 'update_category') {
      const response = await apiRequest(`/transactions/transactions/${item.payload.transactionId}`, {
        method: 'PATCH',
        token,
        body: JSON.stringify({ category: item.payload.category }),
      });
      if (!response.ok) {
        break;
      }
      flushed += 1;
      queue = queue.filter((entry) => entry.id !== item.id);
      await saveQueue(queue);
    }
    if (item.type === 'update_profile') {
      const response = await apiRequest('/profile/profiles/me', {
        method: 'PUT',
        token,
        body: JSON.stringify(item.payload),
      });
      if (!response.ok) {
        break;
      }
      flushed += 1;
      queue = queue.filter((entry) => entry.id !== item.id);
      await saveQueue(queue);
    }
    if (item.type === 'update_subscription') {
      const response = await apiRequest('/profile/subscriptions/me', {
        method: 'PUT',
        token,
        body: JSON.stringify(item.payload),
      });
      if (!response.ok) {
        break;
      }
      flushed += 1;
      queue = queue.filter((entry) => entry.id !== item.id);
      await saveQueue(queue);
    }
  }

  return { flushed, remaining: queue.length };
};
