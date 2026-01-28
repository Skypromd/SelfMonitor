import React from 'react';
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';
import { Ionicons } from '@expo/vector-icons';

import DashboardScreen from '../screens/DashboardScreen';
import TransactionsScreen from '../screens/TransactionsScreen';
import DocumentsScreen from '../screens/DocumentsScreen';
import ReportsScreen from '../screens/ReportsScreen';
import MoreStack from './MoreStack';
import { useTranslation } from '../hooks/useTranslation';

export type MainTabParamList = {
  Dashboard: undefined;
  Transactions: undefined;
  Documents: undefined;
  Reports: undefined;
  More: undefined;
};

const Tab = createBottomTabNavigator<MainTabParamList>();

export default function MainTabs() {
  const { t } = useTranslation();

  return (
    <Tab.Navigator
      screenOptions={({ route }) => ({
        headerShown: false,
        tabBarIcon: ({ color, size }) => {
          let iconName: keyof typeof Ionicons.glyphMap = 'home-outline';
          switch (route.name) {
            case 'Dashboard':
              iconName = 'home-outline';
              break;
            case 'Transactions':
              iconName = 'card-outline';
              break;
            case 'Documents':
              iconName = 'document-text-outline';
              break;
            case 'Reports':
              iconName = 'bar-chart-outline';
              break;
            case 'More':
              iconName = 'menu-outline';
              break;
          }
          return <Ionicons name={iconName} size={size} color={color} />;
        },
      })}
    >
      <Tab.Screen name="Dashboard" component={DashboardScreen} options={{ title: t('nav.dashboard') }} />
      <Tab.Screen name="Transactions" component={TransactionsScreen} options={{ title: t('nav.transactions') }} />
      <Tab.Screen name="Documents" component={DocumentsScreen} options={{ title: t('nav.documents') }} />
      <Tab.Screen name="Reports" component={ReportsScreen} options={{ title: t('nav.reports') }} />
      <Tab.Screen name="More" component={MoreStack} options={{ title: t('nav.more') }} />
    </Tab.Navigator>
  );
}
