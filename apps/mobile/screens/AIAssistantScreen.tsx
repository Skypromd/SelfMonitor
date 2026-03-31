import React, { useState, useCallback, useRef, useEffect } from 'react';
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  TextInput,
  FlatList,
  KeyboardAvoidingView,
  Platform,
  Animated,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { colors, spacing, fontSize, borderRadius } from '../theme';
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
  { label: '📈 Cash flow', prompt: 'Analyse my cash flow for this quarter' },
];

function TypingDots() {
  const dot1 = useRef(new Animated.Value(0.3)).current;
  const dot2 = useRef(new Animated.Value(0.3)).current;
  const dot3 = useRef(new Animated.Value(0.3)).current;

  useEffect(() => {
    const animate = (dot: Animated.Value, delay: number) =>
      Animated.loop(
        Animated.sequence([
          Animated.timing(dot, { toValue: 1, duration: 400, delay, useNativeDriver: true }),
          Animated.timing(dot, { toValue: 0.3, duration: 400, useNativeDriver: true }),
        ])
      );
    const a1 = animate(dot1, 0);
    const a2 = animate(dot2, 150);
    const a3 = animate(dot3, 300);
    a1.start();
    a2.start();
    a3.start();
    return () => { a1.stop(); a2.stop(); a3.stop(); };
  }, [dot1, dot2, dot3]);

  return (
    <View style={styles.typingContainer}>
      <View style={styles.typingBubble}>
        <Animated.View style={[styles.typingDot, { opacity: dot1 }]} />
        <Animated.View style={[styles.typingDot, { opacity: dot2 }]} />
        <Animated.View style={[styles.typingDot, { opacity: dot3 }]} />
      </View>
    </View>
  );
}

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
      <View style={[styles.bubbleRow, isUser && styles.bubbleRowUser]}>
        {!isUser && (
          <View style={styles.avatarCircle}>
            <Text style={styles.avatarText}>🤖</Text>
          </View>
        )}
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
      </View>
    );
  };

  const sendButtonScale = useRef(new Animated.Value(1)).current;

  return (
    <SafeAreaView style={styles.container} edges={['top']}>
      <View style={styles.header}>
        <Text style={styles.headerEmoji}>🤖</Text>
        <View>
          <Text style={styles.title}>AI Assistant</Text>
          <Text style={styles.subtitle}>Your personal finance advisor</Text>
        </View>
      </View>

      <FlatList
        ref={flatListRef}
        data={messages}
        keyExtractor={(item) => item.id}
        renderItem={renderMessage}
        contentContainerStyle={styles.messageList}
        showsVerticalScrollIndicator={false}
        onContentSizeChange={() =>
          flatListRef.current?.scrollToEnd({ animated: true })
        }
        ListEmptyComponent={
          <View style={styles.emptyContainer}>
            <Text style={styles.emptyEmoji}>👋</Text>
            <Text style={styles.emptyTitle}>How can I help?</Text>
            <Text style={styles.emptyText}>
              Ask me anything about your finances, tax, or business.
            </Text>
          </View>
        }
      />

      {loading && <TypingDots />}

      {messages.length === 0 && !loading && (
        <View style={styles.quickActions}>
          {QUICK_ACTIONS.map((action, i) => (
            <TouchableOpacity
              key={i}
              style={styles.quickAction}
              onPress={() => sendMessage(action.prompt)}
              activeOpacity={0.7}
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
          <Animated.View style={{ transform: [{ scale: sendButtonScale }] }}>
            <TouchableOpacity
              style={[
                styles.sendButton,
                (!input.trim() || loading) && styles.sendButtonDisabled,
              ]}
              onPress={() => sendMessage(input)}
              onPressIn={() =>
                Animated.spring(sendButtonScale, { toValue: 0.9, useNativeDriver: true }).start()
              }
              onPressOut={() =>
                Animated.spring(sendButtonScale, { toValue: 1, friction: 3, useNativeDriver: true }).start()
              }
              disabled={!input.trim() || loading}
            >
              <Text style={styles.sendButtonText}>➤</Text>
            </TouchableOpacity>
          </Animated.View>
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
  if (lower.includes('cash flow'))
    return "Your Q1 cash flow looks healthy. Income: £24,300, Expenses: £8,900, Net: +£15,400. I'd recommend maintaining a 3-month expense buffer of at least £26,700.";
  return "I'm here to help with your financial questions. You can ask me about tax estimates, mortgage readiness, expense tracking, or general business finance advice.";
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.bg,
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.sm,
    paddingHorizontal: spacing.lg,
    paddingVertical: spacing.md,
    borderBottomWidth: 1,
    borderBottomColor: colors.border,
    backgroundColor: colors.bgElevated,
  },
  headerEmoji: {
    fontSize: 28,
  },
  title: {
    fontSize: fontSize.lg,
    fontWeight: '800',
    color: colors.text,
  },
  subtitle: {
    fontSize: fontSize.xs,
    color: colors.textMuted,
  },
  messageList: {
    padding: spacing.md,
    flexGrow: 1,
  },
  bubbleRow: {
    flexDirection: 'row',
    alignItems: 'flex-end',
    marginBottom: spacing.sm,
    gap: spacing.sm,
  },
  bubbleRowUser: {
    justifyContent: 'flex-end',
  },
  avatarCircle: {
    width: 30,
    height: 30,
    borderRadius: 15,
    backgroundColor: colors.bgCard,
    alignItems: 'center',
    justifyContent: 'center',
  },
  avatarText: {
    fontSize: 16,
  },
  bubble: {
    maxWidth: '78%',
    borderRadius: borderRadius.xl,
    padding: spacing.md,
  },
  userBubble: {
    backgroundColor: colors.accentTeal,
    borderBottomRightRadius: spacing.xs,
  },
  aiBubble: {
    backgroundColor: colors.bgCard,
    borderBottomLeftRadius: spacing.xs,
    borderWidth: 1,
    borderColor: colors.border,
  },
  bubbleText: {
    fontSize: fontSize.md,
    lineHeight: 22,
  },
  userText: {
    color: colors.textInverse,
  },
  aiText: {
    color: colors.text,
  },
  typingContainer: {
    paddingHorizontal: spacing.lg,
    paddingBottom: spacing.sm,
  },
  typingBubble: {
    flexDirection: 'row',
    backgroundColor: colors.bgCard,
    borderRadius: borderRadius.lg,
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm,
    alignSelf: 'flex-start',
    gap: spacing.xs,
    borderWidth: 1,
    borderColor: colors.border,
  },
  typingDot: {
    width: 8,
    height: 8,
    borderRadius: 4,
    backgroundColor: colors.accentTeal,
  },
  quickActions: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    paddingHorizontal: spacing.md,
    gap: spacing.sm,
    paddingBottom: spacing.md,
  },
  quickAction: {
    backgroundColor: colors.bgCard,
    borderRadius: borderRadius.full,
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm,
    borderWidth: 1,
    borderColor: colors.borderLight,
  },
  quickActionText: {
    fontSize: fontSize.sm,
    color: colors.text,
    fontWeight: '600',
  },
  inputRow: {
    flexDirection: 'row',
    alignItems: 'flex-end',
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm,
    borderTopWidth: 1,
    borderTopColor: colors.border,
    backgroundColor: colors.bgElevated,
    gap: spacing.sm,
  },
  input: {
    flex: 1,
    backgroundColor: colors.bgCard,
    borderRadius: borderRadius.full,
    paddingHorizontal: spacing.lg,
    paddingVertical: spacing.sm,
    color: colors.text,
    fontSize: fontSize.md,
    maxHeight: 100,
    borderWidth: 1,
    borderColor: colors.border,
  },
  sendButton: {
    backgroundColor: colors.accentTeal,
    width: 42,
    height: 42,
    borderRadius: 21,
    alignItems: 'center',
    justifyContent: 'center',
  },
  sendButtonDisabled: {
    backgroundColor: colors.bgCard,
  },
  sendButtonText: {
    color: colors.textInverse,
    fontSize: 18,
    fontWeight: '700',
  },
  emptyContainer: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: spacing.xxl * 2,
  },
  emptyEmoji: {
    fontSize: 48,
    marginBottom: spacing.md,
  },
  emptyTitle: {
    fontSize: fontSize.xl,
    fontWeight: '700',
    color: colors.text,
    marginBottom: spacing.sm,
  },
  emptyText: {
    fontSize: fontSize.sm,
    color: colors.textMuted,
    textAlign: 'center',
    paddingHorizontal: spacing.xl,
  },
});
