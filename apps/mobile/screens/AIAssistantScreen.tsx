import React, { useState, useCallback, useRef } from 'react';
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  ActivityIndicator,
  TextInput,
  FlatList,
  KeyboardAvoidingView,
  Platform,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { colors, spacing, fontSize } from '../theme';
import { apiCall } from '../api';

type Message = {
  id: string;
  role: 'user' | 'assistant';
  content: string;
};

const QUICK_ACTIONS = [
  { label: '💰 Tax estimate', prompt: 'Give me a quick tax estimate for this year' },
  { label: '🏠 Mortgage advice', prompt: 'What should I know about getting a mortgage as self-employed?' },
  { label: '📊 Expense help', prompt: 'Help me categorise my recent expenses' },
];

export default function AIAssistantScreen() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const flatListRef = useRef<FlatList<Message>>(null);

  const sendMessage = useCallback(
    async (text: string) => {
      const trimmed = text.trim();
      if (!trimmed || loading) return;

      const userMsg: Message = {
        id: String(Date.now()),
        role: 'user',
        content: trimmed,
      };
      setMessages((prev) => [...prev, userMsg]);
      setInput('');
      setLoading(true);

      try {
        const res = await apiCall('/agent/chat', {
          method: 'POST',
          body: JSON.stringify({ message: trimmed }),
        });
        let reply: string;
        if (res.ok) {
          const data = await res.json();
          reply = data.response || data.message || data.reply || JSON.stringify(data);
        } else {
          reply = getMockReply(trimmed);
        }
        const aiMsg: Message = {
          id: String(Date.now() + 1),
          role: 'assistant',
          content: reply,
        };
        setMessages((prev) => [...prev, aiMsg]);
      } catch {
        const aiMsg: Message = {
          id: String(Date.now() + 1),
          role: 'assistant',
          content: getMockReply(trimmed),
        };
        setMessages((prev) => [...prev, aiMsg]);
      } finally {
        setLoading(false);
      }
    },
    [loading]
  );

  const renderMessage = ({ item }: { item: Message }) => {
    const isUser = item.role === 'user';
    return (
      <View
        style={[
          styles.bubble,
          isUser ? styles.userBubble : styles.aiBubble,
        ]}
      >
        <Text style={[styles.bubbleText, isUser ? styles.userText : styles.aiText]}>
          {item.content}
        </Text>
      </View>
    );
  };

  return (
    <SafeAreaView style={styles.container} edges={['top']}>
      <View style={styles.header}>
        <Text style={styles.title}>AI Assistant</Text>
        <Text style={styles.subtitle}>Your personal finance advisor</Text>
      </View>

      <FlatList
        ref={flatListRef}
        data={messages}
        keyExtractor={(item) => item.id}
        renderItem={renderMessage}
        contentContainerStyle={styles.messageList}
        onContentSizeChange={() =>
          flatListRef.current?.scrollToEnd({ animated: true })
        }
        ListEmptyComponent={
          <View style={styles.emptyContainer}>
            <Text style={styles.emptyTitle}>👋 How can I help?</Text>
            <Text style={styles.emptyText}>
              Ask me anything about your finances, tax, or business.
            </Text>
          </View>
        }
      />

      {loading && (
        <View style={styles.typingRow}>
          <ActivityIndicator size="small" color={colors.accentTeal} />
          <Text style={styles.typingText}>AI is typing...</Text>
        </View>
      )}

      {messages.length === 0 && !loading && (
        <View style={styles.quickActions}>
          {QUICK_ACTIONS.map((action, i) => (
            <TouchableOpacity
              key={i}
              style={styles.quickAction}
              onPress={() => sendMessage(action.prompt)}
            >
              <Text style={styles.quickActionText}>{action.label}</Text>
            </TouchableOpacity>
          ))}
        </View>
      )}

      <KeyboardAvoidingView
        behavior={Platform.OS === 'ios' ? 'padding' : undefined}
        keyboardVerticalOffset={90}
      >
        <View style={styles.inputRow}>
          <TextInput
            style={styles.input}
            value={input}
            onChangeText={setInput}
            placeholder="Type a message..."
            placeholderTextColor={colors.textMuted}
            multiline
            maxLength={2000}
          />
          <TouchableOpacity
            style={[styles.sendButton, (!input.trim() || loading) && styles.sendButtonDisabled]}
            onPress={() => sendMessage(input)}
            disabled={!input.trim() || loading}
          >
            <Text style={styles.sendButtonText}>➤</Text>
          </TouchableOpacity>
        </View>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

function getMockReply(prompt: string): string {
  const lower = prompt.toLowerCase();
  if (lower.includes('tax'))
    return 'Based on typical self-employed income, your estimated tax liability for 2025/26 would be around £8,400 (Income Tax) plus £3,200 (Class 4 NICs). Make sure to set aside at least 30% of your income for tax payments.';
  if (lower.includes('mortgage'))
    return "As a self-employed individual, lenders typically want 2-3 years of accounts. Your SA302 forms are key. I'd recommend keeping your credit score above 700 and having at least a 10% deposit saved.";
  if (lower.includes('expense'))
    return "I can help categorise your expenses! Common deductible categories for self-employed include: office costs, travel, clothing (uniforms), staff costs, and professional fees. Would you like me to review your recent transactions?";
  return "I'm here to help with your financial questions. You can ask me about tax estimates, mortgage readiness, expense tracking, or general business finance advice.";
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.bg,
  },
  header: {
    padding: spacing.md,
    paddingBottom: spacing.sm,
    borderBottomWidth: 1,
    borderBottomColor: colors.border,
  },
  title: {
    fontSize: fontSize.xl,
    fontWeight: '700',
    color: colors.text,
  },
  subtitle: {
    fontSize: fontSize.sm,
    color: colors.textMuted,
    marginTop: spacing.xs,
  },
  messageList: {
    padding: spacing.md,
    flexGrow: 1,
  },
  bubble: {
    maxWidth: '80%',
    borderRadius: 16,
    padding: spacing.md,
    marginBottom: spacing.sm,
  },
  userBubble: {
    backgroundColor: colors.accentTeal,
    alignSelf: 'flex-end',
    borderBottomRightRadius: 4,
  },
  aiBubble: {
    backgroundColor: colors.bgElevated,
    alignSelf: 'flex-start',
    borderBottomLeftRadius: 4,
    borderWidth: 1,
    borderColor: colors.border,
  },
  bubbleText: {
    fontSize: fontSize.sm,
    lineHeight: 20,
  },
  userText: {
    color: colors.text,
  },
  aiText: {
    color: colors.text,
  },
  typingRow: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: spacing.md,
    paddingBottom: spacing.sm,
  },
  typingText: {
    fontSize: fontSize.sm,
    color: colors.textMuted,
    marginLeft: spacing.sm,
  },
  quickActions: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    paddingHorizontal: spacing.md,
    gap: spacing.sm,
    paddingBottom: spacing.md,
  },
  quickAction: {
    backgroundColor: colors.bgElevated,
    borderRadius: 20,
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm,
    borderWidth: 1,
    borderColor: colors.border,
  },
  quickActionText: {
    fontSize: fontSize.sm,
    color: colors.text,
    fontWeight: '500',
  },
  inputRow: {
    flexDirection: 'row',
    alignItems: 'flex-end',
    padding: spacing.md,
    borderTopWidth: 1,
    borderTopColor: colors.border,
    backgroundColor: colors.bgElevated,
  },
  input: {
    flex: 1,
    backgroundColor: colors.bgCard,
    borderRadius: 20,
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm,
    color: colors.text,
    fontSize: fontSize.md,
    maxHeight: 100,
    borderWidth: 1,
    borderColor: colors.border,
  },
  sendButton: {
    backgroundColor: colors.accentTeal,
    width: 40,
    height: 40,
    borderRadius: 20,
    alignItems: 'center',
    justifyContent: 'center',
    marginLeft: spacing.sm,
  },
  sendButtonDisabled: {
    backgroundColor: colors.bgCard,
  },
  sendButtonText: {
    color: colors.text,
    fontSize: 18,
    fontWeight: '600',
  },
  emptyContainer: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: spacing.xl * 2,
  },
  emptyTitle: {
    fontSize: fontSize.lg,
    fontWeight: '600',
    color: colors.text,
    marginBottom: spacing.sm,
  },
  emptyText: {
    fontSize: fontSize.sm,
    color: colors.textMuted,
    textAlign: 'center',
    paddingHorizontal: spacing.lg,
  },
});
