import React, { useEffect, useMemo, useState } from 'react';
import { StyleSheet, Text, View } from 'react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';

import Screen from '../components/Screen';
import SectionHeader from '../components/SectionHeader';
import Card from '../components/Card';
import InputField from '../components/InputField';
import PrimaryButton from '../components/PrimaryButton';
import Chip from '../components/Chip';
import ListItem from '../components/ListItem';
import Badge from '../components/Badge';
import FadeInView from '../components/FadeInView';
import { apiRequest } from '../services/api';
import { useNetworkStatus } from '../hooks/useNetworkStatus';
import { useAuth } from '../context/AuthContext';
import { useTranslation } from '../hooks/useTranslation';
import { colors, spacing } from '../theme';

type Rule = {
  id: string;
  merchantContains: string;
  category: string;
};

type Transaction = {
  id: string;
  description: string;
  category?: string | null;
  tax_category?: string | null;
};

const RULES_KEY = 'rules.v1';

export default function RulesScreen() {
  const { token } = useAuth();
  const { t } = useTranslation();
  const { isOffline } = useNetworkStatus();
  const [rules, setRules] = useState<Rule[]>([]);
  const [merchant, setMerchant] = useState('');
  const [category, setCategory] = useState('other');
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [isApplying, setIsApplying] = useState(false);

  const categoryOptions = useMemo(() => ([
    { value: 'income', label: t('rules.category_income') },
    { value: 'groceries', label: t('rules.category_groceries') },
    { value: 'transport', label: t('rules.category_transport') },
    { value: 'food_and_drink', label: t('rules.category_food') },
    { value: 'subscriptions', label: t('rules.category_subscriptions') },
    { value: 'office', label: t('rules.category_office') },
    { value: 'travel', label: t('rules.category_travel') },
    { value: 'advertising', label: t('rules.category_advertising') },
    { value: 'other', label: t('rules.category_other') },
  ]), [t]);

  useEffect(() => {
    const loadRules = async () => {
      try {
        const stored = await AsyncStorage.getItem(RULES_KEY);
        if (stored) {
          setRules(JSON.parse(stored));
        }
      } catch {
        return;
      }
    };
    loadRules();
  }, []);

  const saveRules = async (next: Rule[]) => {
    setRules(next);
    try {
      await AsyncStorage.setItem(RULES_KEY, JSON.stringify(next));
    } catch {
      return;
    }
  };

  const addRule = async () => {
    setMessage('');
    setError('');
    if (!merchant.trim()) {
      setError(t('rules.merchant_required'));
      return;
    }
    const nextRule: Rule = {
      id: `${Date.now()}`,
      merchantContains: merchant.trim(),
      category,
    };
    await saveRules([nextRule, ...rules]);
    setMerchant('');
    setCategory('other');
    setMessage(t('rules.rule_saved'));
  };

  const removeRule = async (ruleId: string) => {
    const next = rules.filter((rule) => rule.id !== ruleId);
    await saveRules(next);
    setMessage(t('rules.rule_removed'));
  };

  const applyRules = async () => {
    setMessage('');
    setError('');
    if (!rules.length) {
      setError(t('rules.no_rules'));
      return;
    }
    if (isOffline) {
      setError(t('rules.offline_error'));
      return;
    }
    setIsApplying(true);
    try {
      const response = await apiRequest('/transactions/transactions/me', { token });
      if (!response.ok) throw new Error();
      const data: Transaction[] = await response.json();
      let updated = 0;
      let skipped = 0;
      for (const txn of data) {
        const hasCategory = Boolean(txn.tax_category || txn.category);
        if (hasCategory) {
          skipped += 1;
          continue;
        }
        const match = rules.find((rule) =>
          txn.description?.toLowerCase().includes(rule.merchantContains.toLowerCase())
        );
        if (!match) {
          skipped += 1;
          continue;
        }
        const updateResponse = await apiRequest(`/transactions/transactions/${txn.id}`, {
          method: 'PATCH',
          token,
          body: JSON.stringify({ category: match.category }),
        });
        if (updateResponse.ok) {
          updated += 1;
        }
      }
      setMessage(`${t('rules.apply_result')} ${updated}. ${t('rules.apply_skipped')} ${skipped}.`);
    } catch {
      setError(t('rules.apply_error'));
    } finally {
      setIsApplying(false);
    }
  };

  return (
    <Screen>
      <SectionHeader title={t('rules.title')} subtitle={t('rules.subtitle')} />
      <FadeInView>
        <Card>
          <Text style={styles.cardTitle}>{t('rules.add_title')}</Text>
          <InputField label={t('rules.merchant_label')} value={merchant} onChangeText={setMerchant} />
          <Text style={styles.label}>{t('rules.category_label')}</Text>
          <View style={styles.categoryRow}>
            {categoryOptions.map((option) => (
              <View key={option.value} style={styles.categoryChip}>
                <Chip
                  label={option.label}
                  selected={category === option.value}
                  onPress={() => setCategory(option.value)}
                />
              </View>
            ))}
          </View>
          <PrimaryButton title={t('rules.save_rule')} onPress={addRule} haptic="medium" />
          <PrimaryButton
            title={isApplying ? t('common.loading') : t('rules.apply_rules')}
            onPress={applyRules}
            variant="secondary"
            haptic="light"
            style={styles.secondaryButton}
            disabled={isApplying}
          />
          {message ? <Text style={styles.message}>{message}</Text> : null}
          {error ? <Text style={styles.error}>{error}</Text> : null}
        </Card>
      </FadeInView>

      <SectionHeader title={t('rules.list_title')} subtitle={t('rules.list_subtitle')} />
      <FadeInView delay={120}>
        <Card>
          {rules.length ? (
            rules.map((rule) => (
              <ListItem
                key={rule.id}
                title={`${rule.merchantContains}`}
                subtitle={`${t('rules.applies_as')} ${rule.category}`}
                icon="flash-outline"
                badge={<Badge label={t('rules.active')} tone="info" />}
                onPress={() => removeRule(rule.id)}
              />
            ))
          ) : (
            <Text style={styles.emptyText}>{t('rules.no_rules')}</Text>
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
  label: {
    color: colors.textSecondary,
    marginBottom: spacing.xs,
  },
  categoryRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    marginBottom: spacing.sm,
  },
  categoryChip: {
    marginRight: spacing.sm,
    marginBottom: spacing.sm,
  },
  secondaryButton: {
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
  emptyText: {
    color: colors.textSecondary,
    fontSize: 12,
    paddingVertical: spacing.md,
  },
});
