import React, { useEffect, useMemo, useState } from 'react';
import { StyleSheet, Text, TextInput, View } from 'react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';

import Screen from '../components/Screen';
import SectionHeader from '../components/SectionHeader';
import Card from '../components/Card';
import PrimaryButton from '../components/PrimaryButton';
import Chip from '../components/Chip';
import FadeInView from '../components/FadeInView';
import InfoRow from '../components/InfoRow';
import { apiRequest } from '../services/api';
import { useNetworkStatus } from '../hooks/useNetworkStatus';
import { useAuth } from '../context/AuthContext';
import { useTranslation } from '../hooks/useTranslation';
import { colors, spacing } from '../theme';

type InsightData = {
  expenseRatio: number;
  missingCategories: number;
  totalIncome: number;
  totalExpenses: number;
  estimatedTax: number;
};

type Message = {
  id: string;
  role: 'assistant' | 'user';
  text: string;
};

const INSIGHT_CACHE = 'assistant.insights.v1';

export default function AssistantScreen() {
  const { token } = useAuth();
  const { t } = useTranslation();
  const { isOffline } = useNetworkStatus();
  const [messages, setMessages] = useState<Message[]>([
    { id: 'welcome', role: 'assistant', text: t('assistant.welcome') },
  ]);
  const [input, setInput] = useState('');
  const [insights, setInsights] = useState<InsightData | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const loadInsights = async () => {
    if (isOffline) {
      try {
        const cached = await AsyncStorage.getItem(INSIGHT_CACHE);
        if (cached) {
          setInsights(JSON.parse(cached));
        }
      } catch {
        return;
      }
      return;
    }
    setIsLoading(true);
    try {
      const summaryResponse = await apiRequest('/analytics/reports/monthly-summary', { token });
      const transactionsResponse = await apiRequest('/transactions/transactions/me', { token });
      let expenseRatio = 0;
      let totalIncome = 0;
      let totalExpenses = 0;
      let missingCategories = 0;
      if (summaryResponse.ok) {
        const summary = await summaryResponse.json();
        totalIncome = summary.total_income || 0;
        totalExpenses = summary.total_expenses || 0;
        expenseRatio = totalIncome > 0 ? totalExpenses / totalIncome : 0;
      }
      if (transactionsResponse.ok) {
        const transactions = await transactionsResponse.json();
        missingCategories = transactions.filter((item: any) => !item.tax_category && !item.category).length;
      }
      const taxResponse = await apiRequest('/tax/calculate', {
        method: 'POST',
        token,
        body: JSON.stringify({
          start_date: new Date(new Date().getFullYear(), 3, 6).toISOString().slice(0, 10),
          end_date: new Date(new Date().getFullYear() + 1, 3, 5).toISOString().slice(0, 10),
          jurisdiction: 'UK',
        }),
      });
      let estimatedTax = 0;
      if (taxResponse.ok) {
        const tax = await taxResponse.json();
        estimatedTax = tax.estimated_tax_due || 0;
      }
      const nextInsights: InsightData = {
        expenseRatio,
        missingCategories,
        totalIncome,
        totalExpenses,
        estimatedTax,
      };
      setInsights(nextInsights);
      await AsyncStorage.setItem(INSIGHT_CACHE, JSON.stringify(nextInsights));
    } catch {
      return;
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadInsights();
  }, [token, isOffline]);

  const promptOptions = [
    t('assistant.prompt_tax'),
    t('assistant.prompt_expenses'),
    t('assistant.prompt_missing'),
  ];

  const responseMap = useMemo(() => {
    if (!insights) return {};
    return {
      tax: `${t('assistant.response_tax')} GBP ${insights.estimatedTax.toFixed(2)}`,
      expenses: `${t('assistant.response_expenses')} ${Math.round(insights.expenseRatio * 100)}% · GBP ${insights.totalExpenses.toFixed(2)}`,
      missing: `${t('assistant.response_missing')} ${insights.missingCategories}`,
    };
  }, [insights, t]);

  const generateResponse = (text: string) => {
    const lower = text.toLowerCase();
    if (lower.includes('tax')) return responseMap.tax || t('assistant.response_generic');
    if (lower.includes('expense') || lower.includes('cost')) return responseMap.expenses || t('assistant.response_generic');
    if (lower.includes('category') || lower.includes('missing')) return responseMap.missing || t('assistant.response_generic');
    return t('assistant.response_generic');
  };

  const handleSend = (text: string) => {
    if (!text.trim()) return;
    const userMessage: Message = { id: `${Date.now()}-user`, role: 'user', text };
    const assistantMessage: Message = { id: `${Date.now()}-assistant`, role: 'assistant', text: generateResponse(text) };
    setMessages((prev) => [...prev, userMessage, assistantMessage]);
    setInput('');
  };

  return (
    <Screen>
      <SectionHeader title={t('assistant.title')} subtitle={t('assistant.subtitle')} />
      <FadeInView>
        <Card>
          <Text style={styles.cardTitle}>{t('assistant.insights_title')}</Text>
          <InfoRow label={t('assistant.insights_income')} value={`GBP ${insights?.totalIncome?.toFixed(2) || '0.00'}`} />
          <InfoRow label={t('assistant.insights_expenses')} value={`GBP ${insights?.totalExpenses?.toFixed(2) || '0.00'}`} />
          <InfoRow label={t('assistant.insights_ratio')} value={`${Math.round((insights?.expenseRatio || 0) * 100)}%`} />
          <InfoRow label={t('assistant.insights_missing')} value={`${insights?.missingCategories ?? 0}`} />
          <InfoRow label={t('assistant.insights_tax')} value={`GBP ${insights?.estimatedTax?.toFixed(2) || '0.00'}`} />
          {isLoading ? <Text style={styles.helper}>{t('common.loading')}</Text> : null}
        </Card>
      </FadeInView>

      <FadeInView delay={120}>
        <Card>
          <Text style={styles.cardTitle}>{t('assistant.quick_prompts')}</Text>
          <View style={styles.promptRow}>
            {promptOptions.map((prompt) => (
              <View key={prompt} style={styles.promptChip}>
                <Chip label={prompt} onPress={() => handleSend(prompt)} />
              </View>
            ))}
          </View>
        </Card>
      </FadeInView>

      <FadeInView delay={160}>
        <Card>
          {messages.map((message) => (
            <View
              key={message.id}
              style={[styles.messageBubble, message.role === 'user' ? styles.messageUser : styles.messageAssistant]}
            >
              <Text style={styles.messageText}>{message.text}</Text>
            </View>
          ))}
        </Card>
      </FadeInView>

      <FadeInView delay={200}>
        <Card>
          <TextInput
            style={styles.input}
            placeholder={t('assistant.input_placeholder')}
            value={input}
            onChangeText={setInput}
          />
          <PrimaryButton title={t('assistant.ask_button')} onPress={() => handleSend(input)} haptic="medium" />
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
  helper: {
    marginTop: spacing.sm,
    color: colors.textSecondary,
  },
  promptRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
  },
  promptChip: {
    marginRight: spacing.sm,
    marginBottom: spacing.sm,
  },
  messageBubble: {
    padding: spacing.sm,
    borderRadius: 16,
    marginBottom: spacing.sm,
  },
  messageUser: {
    backgroundColor: '#dbeafe',
    alignSelf: 'flex-end',
  },
  messageAssistant: {
    backgroundColor: colors.surfaceAlt,
    alignSelf: 'flex-start',
  },
  messageText: {
    color: colors.textPrimary,
    fontSize: 13,
  },
  input: {
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: 12,
    padding: spacing.md,
    marginBottom: spacing.sm,
    backgroundColor: colors.surface,
  },
});
