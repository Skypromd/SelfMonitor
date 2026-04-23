import AsyncStorage from '@react-native-async-storage/async-storage';

import { apiRequest } from './api';
import { jwtSub } from './jwtPayload';

export type UserBusinessRow = {
  id: string;
  user_id: string;
  display_name: string;
  created_at: string;
};

export function txActiveBusinessStorageKey(sub: string): string {
  return `mynettax.txActiveBusiness.${sub}`;
}

export async function readStoredTransactionsBusinessId(token: string): Promise<string | null> {
  const sub = jwtSub(token);
  if (!sub) return null;
  try {
    return await AsyncStorage.getItem(txActiveBusinessStorageKey(sub));
  } catch {
    return null;
  }
}

export async function writeStoredTransactionsBusinessId(token: string, businessId: string): Promise<void> {
  const sub = jwtSub(token);
  if (!sub) return;
  try {
    await AsyncStorage.setItem(txActiveBusinessStorageKey(sub), businessId);
  } catch {
    /* ignore */
  }
}

export async function fetchUserBusinesses(token: string): Promise<UserBusinessRow[]> {
  const res = await apiRequest('/transactions/businesses', { token });
  if (!res.ok) return [];
  try {
    return (await res.json()) as UserBusinessRow[];
  } catch {
    return [];
  }
}
