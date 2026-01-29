import * as Notifications from 'expo-notifications';

Notifications.setNotificationHandler({
  handleNotification: async () => ({
    shouldShowAlert: true,
    shouldPlaySound: false,
    shouldSetBadge: false,
  }),
});

export const ensureNotificationPermission = async () => {
  try {
    const settings = await Notifications.getPermissionsAsync();
    if (settings.status === 'granted') return true;
    const requested = await Notifications.requestPermissionsAsync();
    return requested.status === 'granted';
  } catch {
    return false;
  }
};

export const notifyReportReady = async (title: string, body: string) => {
  const allowed = await ensureNotificationPermission();
  if (!allowed) return;
  try {
    await Notifications.scheduleNotificationAsync({
      content: {
        title,
        body,
      },
      trigger: null,
    });
  } catch {
    return;
  }
};

export const scheduleReminder = async (title: string, body: string, date: Date) => {
  const allowed = await ensureNotificationPermission();
  if (!allowed) return;
  try {
    await Notifications.scheduleNotificationAsync({
      content: {
        title,
        body,
      },
      trigger: date,
    });
  } catch {
    return;
  }
};

export const cancelAllScheduled = async () => {
  try {
    await Notifications.cancelAllScheduledNotificationsAsync();
  } catch {
    return;
  }
};
