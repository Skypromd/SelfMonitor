import AsyncStorage from '@react-native-async-storage/async-storage';

import { apiRequest } from './api';
import { addSyncLogEntry } from './syncLog';

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

type ReportRequestAction = {
  id: string;
  type: 'report_request';
  payload: {
    reportType: string;
    path: string;
  };
  createdAt: string;
};

type OfflineAction = CategoryUpdateAction | ProfileUpdateAction | SubscriptionUpdateAction | ReportRequestAction;

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
  await addSyncLogEntry('category', 'queued');
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
  await addSyncLogEntry('profile', 'queued');
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
  await addSyncLogEntry('subscription', 'queued');
  return filtered.length;
};

export const enqueueReportRequest = async (reportType: string, path: string) => {
  const queue = await loadQueue();
  const filtered = queue.filter(
    (item) => !(item.type === 'report_request' && item.payload.reportType === reportType)
  );
  const next: ReportRequestAction = {
    id: `report-${reportType}-${Date.now()}`,
    type: 'report_request',
    payload: { reportType, path },
    createdAt: new Date().toISOString(),
  };
  filtered.push(next);
  await saveQueue(filtered);
  await addSyncLogEntry('report', 'queued');
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
        await addSyncLogEntry('category', 'failed');
        break;
      }
      flushed += 1;
      await addSyncLogEntry('category', 'synced');
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
        await addSyncLogEntry('profile', 'failed');
        break;
      }
      flushed += 1;
      await addSyncLogEntry('profile', 'synced');
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
        await addSyncLogEntry('subscription', 'failed');
        break;
      }
      flushed += 1;
      await addSyncLogEntry('subscription', 'synced');
      queue = queue.filter((entry) => entry.id !== item.id);
      await saveQueue(queue);
    }
    if (item.type === 'report_request') {
      const response = await apiRequest(item.payload.path, { token });
      if (!response.ok) {
        await addSyncLogEntry('report', 'failed');
        break;
      }
      const contentType = response.headers.get('content-type') || '';
      if (contentType.includes('application/json')) {
        try {
          const data = await response.json();
          await AsyncStorage.setItem(
            'reports.cache.latest',
            JSON.stringify({
              summary: data,
              updatedAt: new Date().toISOString(),
              type: item.payload.reportType,
            })
          );
        } catch {
          return { flushed, remaining: queue.length };
        }
      }
      flushed += 1;
      await addSyncLogEntry('report', 'synced');
      queue = queue.filter((entry) => entry.id !== item.id);
      await saveQueue(queue);
    }
  }

  return { flushed, remaining: queue.length };
};
