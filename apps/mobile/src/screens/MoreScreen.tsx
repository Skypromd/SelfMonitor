import React from 'react';
import { View, Text, StyleSheet, Pressable } from 'react-native';
import { useNavigation } from '@react-navigation/native';

import SectionHeader from '../components/SectionHeader';
import Card from '../components/Card';
import Screen from '../components/Screen';
import { useTranslation } from '../hooks/useTranslation';
import { useAuth } from '../context/AuthContext';
import { colors, spacing } from '../theme';

type ItemProps = {
  label: string;
  onPress: () => void;
};

function MoreItem({ label, onPress }: ItemProps) {
  return (
    <Pressable onPress={onPress} style={styles.item}>
      <Text style={styles.itemText}>{label}</Text>
    </Pressable>
  );
}

export default function MoreScreen() {
  const navigation = useNavigation();
  const { t } = useTranslation();
  const { signOut } = useAuth();

  return (
    <Screen>
      <SectionHeader title={t('nav.more')} subtitle={t('more.subtitle')} />
      <Card>
        <MoreItem label={t('profile.title')} onPress={() => navigation.navigate('Profile' as never)} />
        <MoreItem label={t('subscription.title')} onPress={() => navigation.navigate('Subscription' as never)} />
        <MoreItem label={t('marketplace.title')} onPress={() => navigation.navigate('Marketplace' as never)} />
        <MoreItem label={t('settings.title')} onPress={() => navigation.navigate('Settings' as never)} />
        <MoreItem label={t('support.title')} onPress={() => navigation.navigate('Support' as never)} />
        <MoreItem label={t('common.logout')} onPress={() => signOut()} />
      </Card>
    </Screen>
  );
}

const styles = StyleSheet.create({
  item: {
    paddingVertical: spacing.md,
    borderBottomWidth: 1,
    borderBottomColor: colors.border,
  },
  itemText: {
    fontSize: 16,
    color: colors.textPrimary,
    fontWeight: '500',
  },
});
