import React, { useEffect, useMemo, useState } from 'react';
import { Share, StyleSheet, Text, View } from 'react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';

import Screen from '../components/Screen';
import SectionHeader from '../components/SectionHeader';
import Card from '../components/Card';
import InputField from '../components/InputField';
import PrimaryButton from '../components/PrimaryButton';
import ListItem from '../components/ListItem';
import Badge from '../components/Badge';
import FadeInView from '../components/FadeInView';
import Chip from '../components/Chip';
import InfoRow from '../components/InfoRow';
import { toCsv } from '../utils/csv';
import { useTranslation } from '../hooks/useTranslation';
import { colors, spacing } from '../theme';

type MileageEntry = {
  id: string;
  date: string;
  miles: number;
  purpose: string;
};

const STORAGE_KEY = 'mileage.log.v1';
const formatDate = (date: Date) => date.toISOString().slice(0, 10);

const calculateAllowance = (totalMiles: number) => {
  const firstBand = Math.min(totalMiles, 10000);
  const secondBand = Math.max(totalMiles - 10000, 0);
  return firstBand * 0.45 + secondBand * 0.25;
};

export default function MileageLogScreen() {
  const { t } = useTranslation();
  const [entries, setEntries] = useState<MileageEntry[]>([]);
  const [date, setDate] = useState(formatDate(new Date()));
  const [distance, setDistance] = useState('');
  const [purpose, setPurpose] = useState('');
  const [unit, setUnit] = useState<'miles' | 'km'>('miles');
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');

  useEffect(() => {
    const load = async () => {
      try {
        const stored = await AsyncStorage.getItem(STORAGE_KEY);
        if (stored) {
          setEntries(JSON.parse(stored));
        }
      } catch {
        return;
      }
    };
    load();
  }, []);

  const saveEntries = async (next: MileageEntry[]) => {
    setEntries(next);
    try {
      await AsyncStorage.setItem(STORAGE_KEY, JSON.stringify(next));
    } catch {
      return;
    }
  };

  const totalMiles = useMemo(() => entries.reduce((sum, entry) => sum + entry.miles, 0), [entries]);
  const allowance = calculateAllowance(totalMiles);

  const addEntry = async () => {
    setMessage('');
    setError('');
    const numeric = Number(distance);
    if (!numeric || numeric <= 0) {
      setError(t('mileage.invalid_distance'));
      return;
    }
    const miles = unit === 'km' ? numeric * 0.621371 : numeric;
    const next: MileageEntry = {
      id: `${Date.now()}`,
      date,
      miles,
      purpose: purpose || t('mileage.default_purpose'),
    };
    const updated = [next, ...entries];
    await saveEntries(updated);
    setMessage(t('mileage.saved'));
    setDistance('');
    setPurpose('');
  };

  const exportCsv = async () => {
    const headers = ['date', 'miles', 'purpose'];
    const rows = entries.map((entry) => [entry.date, entry.miles.toFixed(2), entry.purpose]);
    const csv = toCsv(headers, rows);
    await Share.share({ message: csv });
  };

  return (
    <Screen>
      <SectionHeader title={t('mileage.title')} subtitle={t('mileage.subtitle')} />
      <FadeInView>
        <Card>
          <Text style={styles.cardTitle}>{t('mileage.add_trip')}</Text>
          <View style={styles.unitRow}>
            <View style={styles.unitChip}>
              <Chip label={t('mileage.unit_miles')} selected={unit === 'miles'} onPress={() => setUnit('miles')} />
            </View>
            <View style={styles.unitChip}>
              <Chip label={t('mileage.unit_km')} selected={unit === 'km'} onPress={() => setUnit('km')} />
            </View>
          </View>
          <InputField label={t('mileage.date')} value={date} onChangeText={setDate} />
          <InputField label={t('mileage.distance')} value={distance} onChangeText={setDistance} keyboardType="decimal-pad" />
          <InputField label={t('mileage.purpose')} value={purpose} onChangeText={setPurpose} />
          <PrimaryButton title={t('mileage.save_trip')} onPress={addEntry} haptic="medium" />
          {message ? <Text style={styles.message}>{message}</Text> : null}
          {error ? <Text style={styles.error}>{error}</Text> : null}
        </Card>
      </FadeInView>

      <FadeInView delay={120}>
        <Card>
          <Text style={styles.cardTitle}>{t('mileage.summary_title')}</Text>
          <InfoRow label={t('mileage.total_miles')} value={`${totalMiles.toFixed(1)} ${t('mileage.unit_miles')}`} />
          <InfoRow label={t('mileage.allowance')} value={`GBP ${allowance.toFixed(2)}`} />
          <PrimaryButton title={t('mileage.export_csv')} onPress={exportCsv} variant="secondary" haptic="light" style={styles.secondaryButton} />
        </Card>
      </FadeInView>

      <SectionHeader title={t('mileage.log_title')} subtitle={t('mileage.log_subtitle')} />
      <FadeInView delay={180}>
        <Card>
          {entries.length ? (
            entries.map((entry) => (
              <ListItem
                key={entry.id}
                title={`${entry.miles.toFixed(1)} ${t('mileage.unit_miles')}`}
                subtitle={`${entry.date} · ${entry.purpose}`}
                icon="car-outline"
                badge={<Badge label={t('mileage.business_badge')} tone="info" />}
              />
            ))
          ) : (
            <Text style={styles.emptyText}>{t('mileage.empty')}</Text>
          )}
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
  unitRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    marginBottom: spacing.sm,
  },
  unitChip: {
    marginRight: spacing.sm,
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
  secondaryButton: {
    marginTop: spacing.sm,
  },
  emptyText: {
    color: colors.textSecondary,
    fontSize: 12,
    paddingVertical: spacing.md,
  },
});
