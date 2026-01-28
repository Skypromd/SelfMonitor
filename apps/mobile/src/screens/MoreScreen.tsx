import React from 'react';
import { View, Text, StyleSheet, Pressable } from 'react-native';
import { useNavigation } from '@react-navigation/native';

import SectionHeader from '../components/SectionHeader';
import Card from '../components/Card';
import { useTranslation } from '../hooks/useTranslation';
import { useAuth } from '../context/AuthContext';

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
    <View style={styles.container}>
      <SectionHeader title={t('nav.more')} subtitle="Manage your account and tools." />
      <Card>
        <MoreItem label={t('profile.title')} onPress={() => navigation.navigate('Profile' as never)} />
        <MoreItem label={t('subscription.title')} onPress={() => navigation.navigate('Subscription' as never)} />
        <MoreItem label={t('marketplace.title')} onPress={() => navigation.navigate('Marketplace' as never)} />
        <MoreItem label={t('settings.title')} onPress={() => navigation.navigate('Settings' as never)} />
        <MoreItem label={t('support.title')} onPress={() => navigation.navigate('Support' as never)} />
        <MoreItem label={t('common.logout')} onPress={() => signOut()} />
      </Card>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    padding: 16,
  },
  item: {
    paddingVertical: 12,
    borderBottomWidth: 1,
    borderBottomColor: '#e2e8f0',
  },
  itemText: {
    fontSize: 16,
    color: '#0f172a',
    fontWeight: '500',
  },
});
