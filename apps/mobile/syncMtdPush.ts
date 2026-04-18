import Constants from 'expo-constants';
import * as Notifications from 'expo-notifications';
import { apiCall, getToken } from './api';
import { ensureNotificationPermission } from './src/services/notifications';

/**
 * Registers Expo push token with finops-monitor (MTD deadline push). No-op if
 * not authenticated, permission denied, or token unavailable (e.g. simulator).
 */
export async function registerMtdExpoPushToken(): Promise<void> {
  const auth = await getToken();
  if (!auth) return;
  const allowed = await ensureNotificationPermission();
  if (!allowed) return;
  let expoToken: string;
  try {
    const projectId =
      (Constants.expoConfig?.extra as { eas?: { projectId?: string } } | undefined)?.eas
        ?.projectId;
    const tokenData = await Notifications.getExpoPushTokenAsync(
      projectId ? { projectId } : undefined
    );
    expoToken = tokenData.data;
  } catch {
    return;
  }
  const trimmed = expoToken?.trim() ?? '';
  if (!trimmed.startsWith('ExponentPushToken[') && !trimmed.startsWith('ExpoPushToken[')) {
    return;
  }
  const res = await apiCall('/finops/mtd/me/expo-push-token', {
    method: 'POST',
    body: JSON.stringify({ expo_push_token: trimmed }),
  });
  if (!res.ok) {
    return;
  }
}

export async function clearMtdExpoPushToken(): Promise<void> {
  const auth = await getToken();
  if (!auth) return;
  try {
    await apiCall('/finops/mtd/me/expo-push-token', { method: 'DELETE' });
  } catch {
    return;
  }
}
