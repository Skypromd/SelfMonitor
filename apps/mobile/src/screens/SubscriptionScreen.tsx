import React, { useCallback, useEffect, useState } from 'react';
import { StyleSheet, Text, Pressable, View } from 'react-native';
import { useFocusEffect, useNavigation } from '@react-navigation/native';

import Card from '../components/Card';
import SectionHeader from '../components/SectionHeader';
import PrimaryButton from '../components/PrimaryButton';
import Screen from '../components/Screen';
import InputField from '../components/InputField';
import FadeInView from '../components/FadeInView';
import Badge from '../components/Badge';
import { apiRequest } from '../services/api';
import {
  createAccountantConsultCheckout,
  fetchBillingAddons,
  fetchBillingSubscription,
  openBillingPortal,
  openUrl,
  type BillingAddonConsult,
} from '../services/billing';
import { jwtSub } from '../services/jwtPayload';
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
  const [billingEmail, setBillingEmail] = useState<string | null>(null);
  const [stripePlan, setStripePlan] = useState<string | null>(null);
  const [stripeStatus, setStripeStatus] = useState<string | null>(null);
  const [stripePeriodEnd, setStripePeriodEnd] = useState<number | null>(null);
  const [accountCreditGbp, setAccountCreditGbp] = useState<number>(0);
  const [consultSessions, setConsultSessions] = useState<number>(0);
  const [consultAddon, setConsultAddon] = useState<BillingAddonConsult | null>(null);
  const [billingLoaded, setBillingLoaded] = useState(false);
  const [billingError, setBillingError] = useState(false);
  const [consultCheckoutLoading, setConsultCheckoutLoading] = useState(false);

  const loadBilling = useCallback(async () => {
    if (!token) return;
    const email = jwtSub(token);
    setBillingEmail(email);
    if (!email) {
      setBillingLoaded(true);
      setBillingError(true);
      return;
    }
    setBillingError(false);
    const [subRes, addons] = await Promise.all([
      fetchBillingSubscription(email, token),
      fetchBillingAddons(),
    ]);
    if (addons?.accountant_cis_consult?.name) {
      setConsultAddon(addons.accountant_cis_consult);
    }
    if (!subRes.ok || !subRes.data) {
      setBillingError(true);
      setBillingLoaded(true);
      return;
    }
    const d = subRes.data;
    setStripePlan(typeof d.plan === 'string' ? d.plan : null);
    setStripeStatus(typeof d.status === 'string' ? d.status : null);
    setStripePeriodEnd(
      typeof d.current_period_end === 'number' ? d.current_period_end : null,
    );
    setAccountCreditGbp(Number(d.account_credit_balance_gbp) || 0);
    setConsultSessions(Number(d.accountant_consult_sessions_available) || 0);
    setBillingLoaded(true);
  }, [token]);

  useFocusEffect(
    useCallback(() => {
      void loadBilling();
    }, [loadBilling]),
  );

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

  const handleConsultCheckout = async () => {
    if (!billingEmail || isOffline) {
      setError(isOffline ? t('upgrade.offline_error') : t('subscription.billing_load_error'));
      return;
    }
    setConsultCheckoutLoading(true);
    setError('');
    try {
      const res = await createAccountantConsultCheckout(billingEmail);
      if (!res.ok || !res.checkout_url) {
        setError(res.detail || t('subscription.consult_checkout_error'));
        return;
      }
      const opened = await openUrl(res.checkout_url);
      if (!opened) setError(t('subscription.consult_checkout_error'));
    } finally {
      setConsultCheckoutLoading(false);
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

        <Card style={styles.stripeCard}>
          <Text style={styles.stripeTitle}>{t('subscription.stripe_card_title')}</Text>
          {!billingLoaded ? (
            <Text style={styles.info}>{t('common.loading')}</Text>
          ) : billingError ? (
            <Text style={styles.billingMuted}>{t('subscription.billing_load_error')}</Text>
          ) : (
            <>
              <Text style={styles.info}>
                {t('subscription.stripe_plan_label')}: {stripePlan ?? '—'}
              </Text>
              <Text style={styles.info}>
                {t('subscription.stripe_status_label')}: {stripeStatus ?? '—'}
              </Text>
              {stripePeriodEnd ? (
                <Text style={styles.info}>
                  {t('subscription.stripe_period_end')}:{' '}
                  {new Date(stripePeriodEnd * 1000).toLocaleDateString()}
                </Text>
              ) : null}
              {accountCreditGbp > 0 ? (
                <Text style={styles.info}>
                  {t('subscription.account_credit_label')}: £{accountCreditGbp.toFixed(2)}
                </Text>
              ) : null}
              {consultSessions > 0 ? (
                <Text style={styles.info}>
                  {t('subscription.consult_sessions_label')}: {consultSessions}
                </Text>
              ) : null}
              <Text style={styles.billingMuted}>{t('subscription.consult_section_hint')}</Text>
              {consultAddon?.sla_note ? (
                <Text style={styles.billingMutedSmall}>{consultAddon.sla_note}</Text>
              ) : null}
              <PrimaryButton
                title={
                  consultCheckoutLoading
                    ? t('subscription.consult_checkout_loading')
                    : consultAddon
                      ? `${t('subscription.consult_buy')} — £${(consultAddon.amount_pence / 100).toFixed(2)}`
                      : t('subscription.consult_buy')
                }
                onPress={() => void handleConsultCheckout()}
                variant="secondary"
                haptic="light"
                style={styles.secondaryButton}
                disabled={consultCheckoutLoading || !billingEmail || isOffline}
              />
            </>
          )}
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
  stripeCard: {
    marginTop: spacing.md,
  },
  stripeTitle: {
    fontWeight: '700',
    fontSize: 16,
    color: colors.textPrimary,
    marginBottom: spacing.sm,
  },
  billingMuted: {
    color: colors.textSecondary,
    fontSize: 13,
    marginTop: spacing.sm,
    lineHeight: 20,
  },
  billingMutedSmall: {
    color: colors.textSecondary,
    fontSize: 12,
    marginTop: spacing.xs,
    lineHeight: 18,
  },
});
