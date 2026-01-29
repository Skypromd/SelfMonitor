import React, { useEffect, useMemo, useState } from 'react';
import { StyleSheet, Text, View } from 'react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';

import Screen from '../components/Screen';
import SectionHeader from '../components/SectionHeader';
import Card from '../components/Card';
import PrimaryButton from '../components/PrimaryButton';
import Badge from '../components/Badge';
import ListItem from '../components/ListItem';
import FadeInView from '../components/FadeInView';
import InfoRow from '../components/InfoRow';
import { apiRequest } from '../services/api';
import { cancelAllScheduled, scheduleReminder } from '../services/notifications';
import { useNetworkStatus } from '../hooks/useNetworkStatus';
import { useTranslation } from '../hooks/useTranslation';
import { useAuth } from '../context/AuthContext';
import { colors, spacing } from '../theme';

type DeadlineItem = {
  id: string;
  title: string;
  date: Date;
  notes: string;
};

const PREF_KEY = 'deadlines.reminders.enabled';

const buildDeadlines = (t: (key: string) => string) => {
  const today = new Date();
  const year = today.getFullYear();
  const candidates: DeadlineItem[] = [
    {
      id: `sa-${year + 1}-jan`,
      title: t('deadlines.sa_deadline_title'),
      date: new Date(year + 1, 0, 31),
      notes: t('deadlines.sa_deadline_note'),
    },
    {
      id: `poa-${year}-jul`,
      title: t('deadlines.poa_deadline_title'),
      date: new Date(year, 6, 31),
      notes: t('deadlines.poa_deadline_note'),
    },
    {
      id: `register-${year}-oct`,
      title: t('deadlines.register_title'),
      date: new Date(year, 9, 5),
      notes: t('deadlines.register_note'),
    },
    {
      id: `paper-${year}-oct`,
      title: t('deadlines.paper_title'),
      date: new Date(year, 9, 31),
      notes: t('deadlines.paper_note'),
    },
    {
      id: `sa-${year}-jan`,
      title: t('deadlines.sa_deadline_title'),
      date: new Date(year, 0, 31),
      notes: t('deadlines.sa_deadline_note'),
    },
  ];

  return candidates
    .filter((item) => item.date.getTime() >= today.getTime() - 86400000)
    .sort((a, b) => a.date.getTime() - b.date.getTime())
    .slice(0, 6);
};

export default function DeadlinesScreen() {
  const { t } = useTranslation();
  const { token } = useAuth();
  const { isOffline } = useNetworkStatus();
  const [remindersEnabled, setRemindersEnabled] = useState(false);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');

  const deadlines = useMemo(() => buildDeadlines(t), [t]);

  useEffect(() => {
    const loadPrefs = async () => {
      try {
        const stored = await AsyncStorage.getItem(PREF_KEY);
        if (stored) {
          setRemindersEnabled(stored === 'true');
        }
      } catch {
        return;
      }
    };
    loadPrefs();
  }, []);

  const toggleReminders = async () => {
    setMessage('');
    setError('');
    const next = !remindersEnabled;
    setRemindersEnabled(next);
    await AsyncStorage.setItem(PREF_KEY, String(next));
    if (!next) {
      await cancelAllScheduled();
      setMessage(t('deadlines.reminders_disabled'));
      return;
    }
    for (const item of deadlines) {
      const sevenDays = new Date(item.date.getTime() - 7 * 86400000);
      const oneDay = new Date(item.date.getTime() - 86400000);
      await scheduleReminder(item.title, item.notes, sevenDays);
      await scheduleReminder(item.title, item.notes, oneDay);
    }
    setMessage(t('deadlines.reminders_enabled'));
  };

  const createCalendarEvent = async (item: DeadlineItem) => {
    setMessage('');
    setError('');
    if (isOffline) {
      setError(t('deadlines.offline_error'));
      return;
    }
    try {
      const response = await apiRequest('/calendar/events', {
        method: 'POST',
        token,
        body: JSON.stringify({
          user_id: 'me',
          event_title: item.title,
          event_date: item.date.toISOString().slice(0, 10),
          notes: item.notes,
        }),
      });
      if (!response.ok) throw new Error();
      setMessage(t('deadlines.calendar_success'));
    } catch {
      setError(t('deadlines.calendar_error'));
    }
  };

  return (
    <Screen>
      <SectionHeader title={t('deadlines.title')} subtitle={t('deadlines.subtitle')} />
      <FadeInView>
        <Card>
          <Text style={styles.cardTitle}>{t('deadlines.reminders_title')}</Text>
          <InfoRow label={t('deadlines.reminders_status')} value={remindersEnabled ? t('common.online_label') : t('common.offline_label')} />
          <PrimaryButton title={t('deadlines.toggle_reminders')} onPress={toggleReminders} variant="secondary" haptic="light" />
          {message ? <Text style={styles.message}>{message}</Text> : null}
          {error ? <Text style={styles.error}>{error}</Text> : null}
        </Card>
      </FadeInView>

      <SectionHeader title={t('deadlines.upcoming_title')} subtitle={t('deadlines.upcoming_subtitle')} />
      <FadeInView delay={120}>
        <Card>
          {deadlines.map((item) => (
            <ListItem
              key={item.id}
              title={`${item.title} · ${item.date.toLocaleDateString()}`}
              subtitle={item.notes}
              icon="calendar-outline"
              badge={<Badge label={t('deadlines.deadline_badge')} tone="warning" />}
              onPress={() => createCalendarEvent(item)}
            />
          ))}
        </Card>
      </FadeInView>
    </Screen>
  );
}

const styles = StyleSheet.create({
  cardTitle: {
    fontSize: 16,
    fontWeight: '700',
    color: colors.textPrimary,
    marginBottom: spacing.sm,
  },
  message: {
    marginTop: spacing.sm,
    color: colors.success,
  },
  error: {
    marginTop: spacing.sm,
    color: colors.danger,
  },
});
