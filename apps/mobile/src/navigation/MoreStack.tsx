import React from 'react';
import { createNativeStackNavigator } from '@react-navigation/native-stack';

import MoreScreen from '../screens/MoreScreen';
import ProfileScreen from '../screens/ProfileScreen';
import SubscriptionScreen from '../screens/SubscriptionScreen';
import MarketplaceScreen from '../screens/MarketplaceScreen';
import SettingsScreen from '../screens/SettingsScreen';
import SupportScreen from '../screens/SupportScreen';
import SyncCenterScreen from '../screens/SyncCenterScreen';
import TaxSummaryScreen from '../screens/TaxSummaryScreen';
import MileageLogScreen from '../screens/MileageLogScreen';
import { useTranslation } from '../hooks/useTranslation';
import { colors } from '../theme';

export type MoreStackParamList = {
  MoreHome: undefined;
  Profile: undefined;
  Subscription: undefined;
  Marketplace: undefined;
  Settings: undefined;
  Support: undefined;
  SyncCenter: undefined;
  TaxSummary: undefined;
  MileageLog: undefined;
};

const Stack = createNativeStackNavigator<MoreStackParamList>();

export default function MoreStack() {
  const { t } = useTranslation();
  return (
    <Stack.Navigator
      screenOptions={{
        headerStyle: { backgroundColor: colors.surface },
        headerTitleStyle: { color: colors.textPrimary },
        headerTintColor: colors.textPrimary,
        contentStyle: { backgroundColor: colors.background },
      }}
    >
      <Stack.Screen name="MoreHome" component={MoreScreen} options={{ headerShown: false, title: t('nav.more') }} />
      <Stack.Screen name="Profile" component={ProfileScreen} options={{ title: t('profile.title') }} />
      <Stack.Screen name="Subscription" component={SubscriptionScreen} options={{ title: t('subscription.title') }} />
      <Stack.Screen name="Marketplace" component={MarketplaceScreen} options={{ title: t('marketplace.title') }} />
      <Stack.Screen name="Settings" component={SettingsScreen} options={{ title: t('settings.title') }} />
      <Stack.Screen name="Support" component={SupportScreen} options={{ title: t('support.title') }} />
      <Stack.Screen name="SyncCenter" component={SyncCenterScreen} options={{ title: t('sync.center_title') }} />
      <Stack.Screen name="TaxSummary" component={TaxSummaryScreen} options={{ title: t('tax.title') }} />
      <Stack.Screen name="MileageLog" component={MileageLogScreen} options={{ title: t('mileage.title') }} />
    </Stack.Navigator>
  );
}
