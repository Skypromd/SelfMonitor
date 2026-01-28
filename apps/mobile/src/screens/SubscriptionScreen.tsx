import React, { useEffect, useState } from 'react';
import { ScrollView, StyleSheet, Text, TextInput, Pressable, View } from 'react-native';

import Card from '../components/Card';
import SectionHeader from '../components/SectionHeader';
import PrimaryButton from '../components/PrimaryButton';
import { apiRequest } from '../services/api';
import { useAuth } from '../context/AuthContext';
import { useTranslation } from '../hooks/useTranslation';

export default function SubscriptionScreen() {
  const { token } = useAuth();
  const { t } = useTranslation();
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

  useEffect(() => {
    const fetchSubscription = async () => {
      try {
        const response = await apiRequest('/profile/subscriptions/me', { token });
        if (!response.ok) return;
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
        setError('Failed to load subscription.');
      }
    };
    fetchSubscription();
  }, [token]);

  const handleSave = async () => {
    setMessage('');
    setError('');
    try {
      const response = await apiRequest('/profile/subscriptions/me', {
        method: 'PUT',
        token,
        body: JSON.stringify({
          subscription_plan: subscription.subscription_plan,
          monthly_close_day: Number(subscription.monthly_close_day) || 1,
        }),
      });
      if (!response.ok) throw new Error();
      setMessage(t('subscription.updated_message'));
    } catch {
      setError('Failed to update subscription.');
    }
  };

  return (
    <ScrollView style={styles.container}>
      <SectionHeader title={t('subscription.title')} subtitle={t('subscription.subtitle')} />
      <Card>
        <Text style={styles.label}>{t('subscription.plan_label')}</Text>
        <View style={styles.planRow}>
          {['free', 'pro'].map(plan => (
            <Pressable
              key={plan}
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
            </Pressable>
          ))}
        </View>
        <Text style={styles.label}>{t('subscription.close_day_label')}</Text>
        <TextInput
          style={styles.input}
          value={subscription.monthly_close_day}
          onChangeText={(value) => setSubscription(prev => ({ ...prev, monthly_close_day: value }))}
          keyboardType="number-pad"
        />
        <Text style={styles.info}>{t('subscription.status_label')}: {subscription.subscription_status}</Text>
        <Text style={styles.info}>{t('subscription.cycle_label')}: {subscription.billing_cycle}</Text>
        <Text style={styles.info}>
          {t('subscription.period_label')}: {subscription.current_period_start || '-'} → {subscription.current_period_end || '-'}
        </Text>
        <PrimaryButton title={t('common.save')} onPress={handleSave} />
        {message ? <Text style={styles.message}>{message}</Text> : null}
        {error ? <Text style={styles.error}>{error}</Text> : null}
      </Card>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    padding: 16,
  },
  label: {
    color: '#64748b',
    marginBottom: 6,
  },
  input: {
    backgroundColor: '#f8fafc',
    borderRadius: 12,
    padding: 12,
    borderWidth: 1,
    borderColor: '#e2e8f0',
    marginBottom: 12,
  },
  planRow: {
    flexDirection: 'row',
    gap: 12,
    marginBottom: 12,
  },
  planOption: {
    flex: 1,
    borderWidth: 1,
    borderColor: '#e2e8f0',
    borderRadius: 12,
    paddingVertical: 12,
    alignItems: 'center',
    backgroundColor: '#ffffff',
  },
  planOptionActive: {
    borderColor: '#2563eb',
    backgroundColor: '#eff6ff',
  },
  planText: {
    color: '#64748b',
    fontWeight: '600',
  },
  planTextActive: {
    color: '#1d4ed8',
  },
  info: {
    color: '#0f172a',
    marginBottom: 4,
  },
  message: {
    marginTop: 12,
    color: '#16a34a',
  },
  error: {
    marginTop: 12,
    color: '#dc2626',
  },
});
