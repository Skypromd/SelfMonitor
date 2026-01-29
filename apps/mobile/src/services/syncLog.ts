import AsyncStorage from '@react-native-async-storage/async-storage';

const LOG_KEY = 'sync.log.v1';

export type SyncAction = 'category' | 'profile' | 'subscription' | 'report';
export type SyncStatus = 'queued' | 'synced' | 'failed';

export type SyncLogEntry = {
  id: string;
  action: SyncAction;
  status: SyncStatus;
  createdAt: string;
};

const loadLog = async (): Promise<SyncLogEntry[]> => {
  try {
    const stored = await AsyncStorage.getItem(LOG_KEY);
    if (!stored) return [];
    return JSON.parse(stored) as SyncLogEntry[];
  } catch {
    return [];
  }
};

const saveLog = async (entries: SyncLogEntry[]) => {
  try {
    await AsyncStorage.setItem(LOG_KEY, JSON.stringify(entries.slice(0, 50)));
  } catch {
    return;
  }
};

export const addSyncLogEntry = async (action: SyncAction, status: SyncStatus) => {
  const entries = await loadLog();
  const next: SyncLogEntry = {
    id: `${action}-${status}-${Date.now()}`,
    action,
    status,
    createdAt: new Date().toISOString(),
  };
  entries.unshift(next);
  await saveLog(entries);
};

export const getSyncLogEntries = async (limit = 6) => {
  const entries = await loadLog();
  return entries.slice(0, limit);
};
