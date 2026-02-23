import React, { useEffect, useState } from 'react';
import { StyleSheet, Text, Pressable, View } from 'react-native';
import { useNavigation } from '@react-navigation/native';

import Card from '../components/Card';
import SectionHeader from '../components/SectionHeader';
import PrimaryButton from '../components/PrimaryButton';
import Screen from '../components/Screen';
import InputField from '../components/InputField';
import FadeInView from '../components/FadeInView';
import Badge from '../components/Badge';
import { apiRequest } from '../services/api';
import { openBillingPortal } from '../services/billing';
import { useNetworkStatus } from '../hooks/useNetworkStatus';
import { enqueueSubscriptionUpdate } from '../services/offlineQueue';
import { useAuth } from '../context/AuthContext';
import { useTranslation } from '../hooks/useTranslation';
import { colors, spacing } from '../theme';

export default function SubscriptionScreen() {
  const { token } = useAuth();
  const { t } = useTranslation();
  const { isOffline } = useNetworkStatus();
  const navigation = useNavigation();
  const [subscription, setSubscription] = useState({
    subscription_plan: 'free',
    monthly_close_day: '1',
    subscription_status: 'active',
    billing_cycle: 'monthly',
    current_period_start: '',
    current_period_end: '',
  });
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [isCached, setIsCached] = useState(false);

  useEffect(() => {
    const fetchSubscription = async () => {
      try {
        const response = await apiRequest('/profile/subscriptions/me', { token, cacheKey: 'subscription.me' });
        if (!response.ok) {
          setError(t('subscription.load_error'));
          return;
        }
        setIsCached(Boolean((response as Response & { cached?: boolean }).cached));
        const data = await response.json();
        setSubscription({
          subscription_plan: data.subscription_plan || 'free',
          monthly_close_day: String(data.monthly_close_day || 1),
          subscription_status: data.subscription_status || 'active',
          billing_cycle: data.billing_cycle || 'monthly',
          current_period_start: data.current_period_start || '',
          current_period_end: data.current_period_end || '',
        });
      } catch {
        setError(t('subscription.load_error'));
      }
    };
    fetchSubscription();
  }, [token]);

  const handleSave = async () => {
    setMessage('');
    setError('');
    const payload = {
      subscription_plan: subscription.subscription_plan,
      monthly_close_day: Number(subscription.monthly_close_day) || 1,
    };
    if (isOffline) {
      await enqueueSubscriptionUpdate(payload);
      setMessage(t('subscription.saved_offline'));
      return;
    }
    try {
      const response = await apiRequest('/profile/subscriptions/me', {
        method: 'PUT',
        token,
        body: JSON.stringify(payload),
      });
      if (!response.ok) throw new Error();
      setMessage(t('subscription.updated_message'));
    } catch {
      await enqueueSubscriptionUpdate(payload);
      setMessage(t('subscription.saved_offline'));
    }
  };

  const handleManageBilling = async () => {
    setMessage('');
    setError('');
    if (isOffline) {
      setError(t('upgrade.offline_error'));
      return;
    }
    const opened = await openBillingPortal();
    if (!opened) {
      setError(t('upgrade.portal_error'));
    }
  };

  const trialDaysLeft = (() => {
    if (subscription.subscription_status !== 'trialing' || !subscription.current_period_end) return null;
    const end = new Date(subscription.current_period_end);
    const days = Math.ceil((end.getTime() - Date.now()) / 86400000);
    return Math.max(days, 0);
  })();

  return (
    <Screen>
      <SectionHeader title={t('subscription.title')} subtitle={t('subscription.subtitle')} />
      <FadeInView>
        <Card>
          {isCached ? (
            <View style={styles.cachedRow}>
              <Badge label={t('common.cached_label')} tone="info" />
              <Text style={styles.cachedText}>{t('common.cached_notice')}</Text>
            </View>
          ) : null}
          <Text style={styles.label}>{t('subscription.plan_label')}</Text>
          <View style={styles.planRow}>
            {['free', 'pro'].map((plan, index) => (
              <View key={plan} style={[styles.planItem, index === 1 && styles.planItemLast]}>
                <Pressable
                  onPress={() => setSubscription(prev => ({ ...prev, subscription_plan: plan }))}
                  style={[
                    styles.planOption,
                    subscription.subscription_plan === plan && styles.planOptionActive
                  ]}
                >
                  <Text style={[
                    styles.planText,
                    subscription.subscription_plan === plan && styles.planTextActive
                  ]}>
                    {plan === 'free' ? t('subscription.plan_free') : t('subscription.plan_pro')}
                  </Text>
                  {subscription.subscription_plan === plan ? (
                    <View style={styles.planBadge}>
                      <Badge label={t('subscription.active_label')} tone="info" />
                    </View>
                  ) : null}
                </Pressable>
              </View>
            ))}
          </View>
          <InputField
            label={t('subscription.close_day_label')}
            value={subscription.monthly_close_day}
            onChangeText={(value) => setSubscription(prev => ({ ...prev, monthly_close_day: value }))}
            keyboardType="number-pad"
          />
          <Text style={styles.info}>{t('subscription.status_label')}: {subscription.subscription_status}</Text>
          <Text style={styles.info}>{t('subscription.cycle_label')}: {subscription.billing_cycle}</Text>
          <Text style={styles.info}>
            {t('subscription.period_label')}: {subscription.current_period_start || '-'} → {subscription.current_period_end || '-'}
          </Text>
          {trialDaysLeft !== null ? (
            <Text style={styles.trial}>{t('subscription.trial_left')} {trialDaysLeft} {t('upgrade.days_left')}</Text>
          ) : null}
          <PrimaryButton title={t('common.save')} onPress={handleSave} haptic="medium" />
          {subscription.subscription_plan === 'free' ? (
            <PrimaryButton
              title={t('upgrade.cta')}
              onPress={() => navigation.navigate('Upgrade' as never)}
              variant="secondary"
              haptic="light"
              style={styles.secondaryButton}
            />
          ) : (
            <PrimaryButton
              title={t('upgrade.manage_billing')}
              onPress={handleManageBilling}
              variant="secondary"
              haptic="light"
              style={styles.secondaryButton}
            />
          )}
          {message ? <Text style={styles.message}>{message}</Text> : null}
          {error ? <Text style={styles.error}>{error}</Text> : null}
        </Card>
      </FadeInView>
    </Screen>
  );
}

const styles = StyleSheet.create({
  label: {
    color: colors.textSecondary,
    marginBottom: spacing.xs,
    fontWeight: '600',
  },
  planRow: {
    flexDirection: 'row',
    marginBottom: spacing.md,
  },
  cachedRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: spacing.md,
  },
  cachedText: {
    marginLeft: spacing.sm,
    color: colors.textSecondary,
    fontSize: 12,
  },
  planItem: {
    flex: 1,
    marginRight: spacing.md,
  },
  planItemLast: {
    marginRight: 0,
  },
  planOption: {
    flex: 1,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: 12,
    paddingVertical: spacing.md,
    alignItems: 'center',
    backgroundColor: colors.surface,
  },
  planBadge: {
    marginTop: spacing.xs,
  },
  planOptionActive: {
    borderColor: colors.primary,
    backgroundColor: '#eff6ff',
  },
  planText: {
    color: colors.textSecondary,
    fontWeight: '600',
  },
  planTextActive: {
    color: colors.primaryDark,
  },
  info: {
    color: colors.textPrimary,
    marginBottom: spacing.xs,
  },
  message: {
    marginTop: spacing.md,
    color: colors.success,
  },
  secondaryButton: {
    marginTop: spacing.sm,
  },
  trial: {
    marginTop: spacing.sm,
    color: colors.warning,
    fontWeight: '600',
  },
  error: {
    marginTop: spacing.md,
    color: colors.danger,
  },
});
