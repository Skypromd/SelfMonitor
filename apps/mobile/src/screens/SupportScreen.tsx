import React from 'react';
import { Linking } from 'react-native';

import SectionHeader from '../components/SectionHeader';
import Card from '../components/Card';
import Screen from '../components/Screen';
import ListItem from '../components/ListItem';
import FadeInView from '../components/FadeInView';
import { useTranslation } from '../hooks/useTranslation';

export default function SupportScreen() {
  const { t } = useTranslation();

  return (
    <Screen>
      <SectionHeader title={t('support.title')} subtitle={t('support.subtitle')} />
      <FadeInView>
        <Card>
          <ListItem
            title={t('support.email_label')}
            subtitle="support@selfmonitor.app"
            icon="mail-outline"
            onPress={() => Linking.openURL('mailto:support@selfmonitor.app')}
          />
          <ListItem
            title={t('support.help_label')}
            subtitle="selfmonitor.app/help"
            icon="globe-outline"
            onPress={() => Linking.openURL('https://selfmonitor.app/help')}
          />
        </Card>
      </FadeInView>
    </Screen>
  );
}

