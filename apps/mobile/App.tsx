import React, { useState, useEffect } from 'react';
import { ActivityIndicator, View, Text, StyleSheet } from 'react-native';
import { NavigationContainer, DefaultTheme } from '@react-navigation/native';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';
import { SafeAreaProvider } from 'react-native-safe-area-context';
import { StatusBar } from 'expo-status-bar';
import AsyncStorage from '@react-native-async-storage/async-storage';

import { AuthProvider, useAuth } from './context/AuthContext';
import { colors, fontSize } from './theme';

import LoginScreen from './screens/LoginScreen';
import RegisterScreen from './screens/RegisterScreen';
import OnboardingScreen from './screens/OnboardingScreen';
import DashboardScreen from './screens/DashboardScreen';
import MoneyScreen from './screens/MoneyScreen';
import ReceiptScanScreen from './screens/ReceiptScanScreen';
import TaxScreen from './screens/TaxScreen';
import ProfileScreen from './screens/ProfileScreen';
import CisRefundTrackerScreen from './screens/CisRefundTrackerScreen';
import MortgageScreen from './screens/MortgageScreen';
import AIAssistantScreen from './screens/AIAssistantScreen';
import ReferralsScreen from './screens/ReferralsScreen';
import ActivityScreen from './screens/ActivityScreen';

const Stack = createNativeStackNavigator();
const AuthStack = createNativeStackNavigator();
const Tab = createBottomTabNavigator();
const MeStack = createNativeStackNavigator();

const DarkTheme = {
  ...DefaultTheme,
  dark: true,
  colors: {
    ...DefaultTheme.colors,
    primary: colors.accentTeal,
    background: colors.bg,
    card: colors.bgElevated,
    text: colors.text,
    border: colors.border,
    notification: colors.warning,
  },
};

const TAB_ICONS: Record<string, { active: string; inactive: string }> = {
  Home: { active: '🏠', inactive: '🏠' },
  Money: { active: '💰', inactive: '💰' },
  Scan: { active: '📸', inactive: '📸' },
  Tax: { active: '🇬🇧', inactive: '🇬🇧' },
  Me: { active: '👤', inactive: '👤' },
};

function TabIcon({ name, focused }: { name: string; focused: boolean }) {
  const icons = TAB_ICONS[name] || { active: '•', inactive: '•' };
  return (
    <Text style={{ fontSize: focused ? 22 : 20, opacity: focused ? 1 : 0.5 }}>
      {focused ? icons.active : icons.inactive}
    </Text>
  );
}

function MeNavigator() {
  return (
    <MeStack.Navigator
      screenOptions={{
        headerStyle: { backgroundColor: colors.bgElevated },
        headerTintColor: colors.text,
        headerTitleStyle: { fontWeight: '600' },
      }}
    >
      <MeStack.Screen name="Profile" component={ProfileScreen} />
      <MeStack.Screen name="CisRefundTracker" component={CisRefundTrackerScreen} options={{ title: 'CIS refund tracker' }} />
      <MeStack.Screen name="Mortgage" component={MortgageScreen} options={{ title: 'Mortgage' }} />
      <MeStack.Screen name="AIAssistant" component={AIAssistantScreen} options={{ title: 'AI Assistant' }} />
      <MeStack.Screen name="Referrals" component={ReferralsScreen} />
      <MeStack.Screen name="Activity" component={ActivityScreen} />
    </MeStack.Navigator>
  );
}

function AuthNavigator() {
  return (
    <AuthStack.Navigator screenOptions={{ headerShown: false }}>
      <AuthStack.Screen name="Register" component={RegisterScreen} />
      <AuthStack.Screen name="Login" component={LoginScreen} />
    </AuthStack.Navigator>
  );
}

function MainTabs() {
  return (
    <Tab.Navigator
      screenOptions={({ route }) => ({
        headerStyle: { backgroundColor: colors.bgElevated },
        headerTintColor: colors.text,
        headerTitleStyle: { fontWeight: '700', fontSize: fontSize.lg },
        tabBarStyle: {
          backgroundColor: colors.bgElevated,
          borderTopColor: colors.border,
          borderTopWidth: 1,
          paddingTop: 4,
          height: 60,
        },
        tabBarActiveTintColor: colors.accentTeal,
        tabBarInactiveTintColor: colors.textMuted,
        tabBarLabelStyle: {
          fontSize: fontSize.xs,
          fontWeight: '600',
          marginTop: -2,
        },
        tabBarIcon: ({ focused }) => (
          <TabIcon name={route.name} focused={focused} />
        ),
        tabBarShowLabel: true,
      })}
    >
      <Tab.Screen
        name="Home"
        component={DashboardScreen}
        options={{ tabBarLabel: 'Home', headerShown: false }}
      />
      <Tab.Screen
        name="Money"
        component={MoneyScreen}
        options={{ tabBarLabel: 'Money', headerShown: false }}
      />
      <Tab.Screen
        name="Scan"
        component={ReceiptScanScreen}
        options={{ tabBarLabel: 'Scan', headerShown: false }}
      />
      <Tab.Screen
        name="Tax"
        component={TaxScreen}
        options={{ tabBarLabel: 'Tax', headerShown: false }}
      />
      <Tab.Screen
        name="Me"
        component={MeNavigator}
        options={{ headerShown: false, tabBarLabel: 'Me' }}
      />
    </Tab.Navigator>
  );
}

function RootNavigator() {
  const { token, loading } = useAuth();
  const [isFirstLaunch, setIsFirstLaunch] = useState<boolean | null>(null);
  const [checkingOnboarding, setCheckingOnboarding] = useState(true);

  useEffect(() => {
    (async () => {
      try {
        const completed = await AsyncStorage.getItem('onboarding_complete');
        setIsFirstLaunch(completed !== 'true');
      } catch {
        setIsFirstLaunch(false);
      } finally {
        setCheckingOnboarding(false);
      }
    })();
  }, []);

  if (loading || checkingOnboarding) {
    return (
      <View style={styles.loadingContainer}>
        <ActivityIndicator size="large" color={colors.accentTeal} />
      </View>
    );
  }

  if (!token) {
    return (
      <Stack.Navigator screenOptions={{ headerShown: false }}>
        <Stack.Screen name="Auth" component={AuthNavigator} />
      </Stack.Navigator>
    );
  }

  if (isFirstLaunch) {
    return (
      <OnboardingScreen
        onComplete={() => setIsFirstLaunch(false)}
      />
    );
  }

  return (
    <Stack.Navigator screenOptions={{ headerShown: false }}>
      <Stack.Screen name="Main" component={MainTabs} />
    </Stack.Navigator>
  );
}

export default function App() {
  return (
    <SafeAreaProvider>
      <AuthProvider>
        <NavigationContainer theme={DarkTheme}>
          <StatusBar style="light" />
          <RootNavigator />
        </NavigationContainer>
      </AuthProvider>
    </SafeAreaProvider>
  );
}

const styles = StyleSheet.create({
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: colors.bg,
  },
});
