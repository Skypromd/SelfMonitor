import React from 'react';
import { useNavigation } from '@react-navigation/native';

import SectionHeader from '../components/SectionHeader';
import Card from '../components/Card';
import Screen from '../components/Screen';
import ListItem from '../components/ListItem';
import FadeInView from '../components/FadeInView';
import { useTranslation } from '../hooks/useTranslation';
import { useAuth } from '../context/AuthContext';

export default function MoreScreen() {
  const navigation = useNavigation();
  const { t } = useTranslation();
  const { signOut } = useAuth();

  return (
    <Screen>
      <SectionHeader title={t('nav.more')} subtitle={t('more.subtitle')} />
      <FadeInView>
        <Card>
          <ListItem title={t('profile.title')} icon="person-outline" onPress={() => navigation.navigate('Profile' as never)} />
          <ListItem title={t('subscription.title')} icon="ribbon-outline" onPress={() => navigation.navigate('Subscription' as never)} />
          <ListItem title={t('sync.center_title')} icon="sync-outline" onPress={() => navigation.navigate('SyncCenter' as never)} />
          <ListItem title={t('marketplace.title')} icon="grid-outline" onPress={() => navigation.navigate('Marketplace' as never)} />
          <ListItem title={t('settings.title')} icon="settings-outline" onPress={() => navigation.navigate('Settings' as never)} />
          <ListItem title={t('support.title')} icon="help-circle-outline" onPress={() => navigation.navigate('Support' as never)} />
          <ListItem title={t('common.logout')} icon="log-out-outline" onPress={() => signOut()} />
        </Card>
      </FadeInView>
    </Screen>
  );
}

