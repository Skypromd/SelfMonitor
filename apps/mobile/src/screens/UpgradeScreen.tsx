import React, { useMemo, useState } from 'react';
import { StyleSheet, Text, View } from 'react-native';

import Screen from '../components/Screen';
import SectionHeader from '../components/SectionHeader';
import Card from '../components/Card';
import PrimaryButton from '../components/PrimaryButton';
import InputField from '../components/InputField';
import Badge from '../components/Badge';
import ListItem from '../components/ListItem';
import FadeInView from '../components/FadeInView';
import { apiRequest } from '../services/api';
import { useNetworkStatus } from '../hooks/useNetworkStatus';
import { useSubscriptionPlan } from '../hooks/useSubscriptionPlan';
import { useTranslation } from '../hooks/useTranslation';
import { useAuth } from '../context/AuthContext';
import { colors, spacing } from '../theme';

const PRO_PRICE_MONTHLY = 12.99;

export default function UpgradeScreen() {
  const { t } = useTranslation();
  const { token } = useAuth();
  const { isOffline } = useNetworkStatus();
  const { plan, refresh } = useSubscriptionPlan();
  const [revenue, setRevenue] = useState('');
  const [expenses, setExpenses] = useState('');
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [isUpgrading, setIsUpgrading] = useState(false);

  const savings = useMemo(() => {
    const expenseValue = Number(expenses);
    if (!expenseValue) return 0;
    return expenseValue * 0.15;
  }, [expenses]);

  const netValue = savings - PRO_PRICE_MONTHLY;

  const handleUpgrade = async () => {
    setMessage('');
    setError('');
    if (isOffline) {
      setError(t('upgrade.offline_error'));
      return;
    }
    setIsUpgrading(true);
    try {
      const response = await apiRequest('/profile/subscriptions/me', {
        method: 'PUT',
        token,
        body: JSON.stringify({
          subscription_plan: 'pro',
          monthly_close_day: 1,
        }),
      });
      if (!response.ok) throw new Error();
      setMessage(t('upgrade.upgraded'));
      await refresh();
    } catch {
      setError(t('upgrade.upgrade_error'));
    } finally {
      setIsUpgrading(false);
    }
  };

  return (
    <Screen>
      <SectionHeader title={t('upgrade.title')} subtitle={t('upgrade.subtitle')} />
      <FadeInView>
        <Card>
          <View style={styles.titleRow}>
            <Text style={styles.cardTitle}>{t('upgrade.plan_title')}</Text>
            <Badge label={t('upgrade.badge_best')} tone="info" />
          </View>
          <Text style={styles.price}>{t('upgrade.price_label')} GBP {PRO_PRICE_MONTHLY.toFixed(2)}</Text>
          <Text style={styles.priceHint}>{t('upgrade.price_hint')}</Text>
          <ListItem title={t('upgrade.feature_reports')} icon="checkmark-circle-outline" />
          <ListItem title={t('upgrade.feature_hmrc')} icon="checkmark-circle-outline" />
          <ListItem title={t('upgrade.feature_mortgage')} icon="checkmark-circle-outline" />
          <ListItem title={t('upgrade.feature_sync')} icon="checkmark-circle-outline" />
          <PrimaryButton
            title={plan === 'pro' ? t('upgrade.current_plan') : t('upgrade.cta')}
            onPress={handleUpgrade}
            disabled={plan === 'pro' || isUpgrading}
            haptic="medium"
            style={styles.ctaButton}
          />
          {message ? <Text style={styles.message}>{message}</Text> : null}
          {error ? <Text style={styles.error}>{error}</Text> : null}
        </Card>
      </FadeInView>

      <FadeInView delay={120}>
        <Card>
          <Text style={styles.cardTitle}>{t('upgrade.savings_title')}</Text>
          <InputField
            label={t('upgrade.revenue_label')}
            value={revenue}
            onChangeText={setRevenue}
            keyboardType="decimal-pad"
          />
          <InputField
            label={t('upgrade.expenses_label')}
            value={expenses}
            onChangeText={setExpenses}
            keyboardType="decimal-pad"
          />
          <View style={styles.savingsRow}>
            <Text style={styles.savingsLabel}>{t('upgrade.estimated_savings')}</Text>
            <Text style={styles.savingsValue}>GBP {savings.toFixed(2)}</Text>
          </View>
          <View style={styles.savingsRow}>
            <Text style={styles.savingsLabel}>{t('upgrade.net_value')}</Text>
            <Text style={[styles.savingsValue, netValue >= 0 ? styles.positive : styles.negative]}>
              GBP {netValue.toFixed(2)}
            </Text>
          </View>
          <Text style={styles.disclaimer}>{t('upgrade.disclaimer')}</Text>
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
  titleRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  price: {
    fontSize: 24,
    fontWeight: '700',
    color: colors.textPrimary,
  },
  priceHint: {
    marginBottom: spacing.sm,
    color: colors.textSecondary,
  },
  ctaButton: {
    marginTop: spacing.sm,
  },
  message: {
    marginTop: spacing.sm,
    color: colors.success,
  },
  error: {
    marginTop: spacing.sm,
    color: colors.danger,
  },
  savingsRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: spacing.xs,
  },
  savingsLabel: {
    color: colors.textSecondary,
  },
  savingsValue: {
    color: colors.textPrimary,
    fontWeight: '600',
  },
  positive: {
    color: colors.success,
  },
  negative: {
    color: colors.danger,
  },
  disclaimer: {
    marginTop: spacing.sm,
    fontSize: 12,
    color: colors.textSecondary,
  },
});
