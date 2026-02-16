import NetInfo from "@react-native-community/netinfo";
import { Ionicons } from "@expo/vector-icons";
import * as Device from "expo-device";
import * as Haptics from "expo-haptics";
import { LinearGradient } from "expo-linear-gradient";
import * as LocalAuthentication from "expo-local-authentication";
import * as Notifications from "expo-notifications";
import * as SecureStore from "expo-secure-store";
import { StatusBar } from "expo-status-bar";
import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  ActivityIndicator,
  Animated,
  BackHandler,
  Easing,
  Linking,
  Platform,
  Pressable,
  SafeAreaView,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from "react-native";
import LottieView from "lottie-react-native";
import { WebView } from "react-native-webview";

const DEFAULT_WEB_PORTAL_URL =
  Platform.select({
    android: "http://10.0.2.2:3000",
    ios: "http://localhost:3000",
    default: "http://localhost:3000",
  }) ?? "http://localhost:3000";

const WEB_PORTAL_URL =
  process.env.EXPO_PUBLIC_WEB_PORTAL_URL?.trim() || DEFAULT_WEB_PORTAL_URL;

const APP_USER_AGENT_SUFFIX = "SelfMonitorMobile/0.1";
const AUTH_TOKEN_KEY = "authToken";
const AUTH_EMAIL_KEY = "authUserEmail";
const THEME_KEY = "appTheme";
const MOBILE_PUSH_TOKEN_KEY = "mobilePushToken";

const SECURE_AUTH_TOKEN_KEY = "selfmonitor.authToken";
const SECURE_AUTH_EMAIL_KEY = "selfmonitor.authUserEmail";
const SECURE_THEME_KEY = "selfmonitor.theme";
const SECURE_PUSH_TOKEN_KEY = "selfmonitor.pushToken";
const SECURE_ONBOARDING_DONE_KEY = "selfmonitor.onboardingDone";

const PUSH_ROUTE_MAP: Record<string, string> = {
  dashboard: "/dashboard",
  documents: "/documents",
  invoices: "/dashboard?section=invoices",
  reports: "/reports",
  submission: "/submission",
  transactions: "/transactions",
};

Notifications.setNotificationHandler({
  handleNotification: async () => ({
    shouldPlaySound: false,
    shouldSetBadge: false,
    shouldShowAlert: true,
    shouldShowBanner: true,
    shouldShowList: true,
  }),
});

type BridgeMessage = {
  payload?: Record<string, string | null | undefined>;
  type?: string;
};

type DockAction = {
  icon: keyof typeof Ionicons.glyphMap;
  id: "dashboard" | "documents" | "scan" | "push";
  isPrimary?: boolean;
  label: string;
  onPress: () => void;
};

type NotificationPayloadLike = {
  deeplink?: unknown;
  path?: unknown;
  route?: unknown;
  screen?: unknown;
  url?: unknown;
};

function toStorageStatement(key: string, value: string | null): string {
  if (value) {
    return `window.localStorage.setItem(${JSON.stringify(key)}, ${JSON.stringify(value)});`;
  }
  return `window.localStorage.removeItem(${JSON.stringify(key)});`;
}

function buildBootstrapScript(payload: {
  email: string | null;
  pushToken: string | null;
  theme: string | null;
  token: string | null;
}): string {
  return `
    (function() {
      try {
        ${toStorageStatement(AUTH_TOKEN_KEY, payload.token)}
        ${toStorageStatement(AUTH_EMAIL_KEY, payload.email)}
        ${toStorageStatement(THEME_KEY, payload.theme)}
        ${toStorageStatement(MOBILE_PUSH_TOKEN_KEY, payload.pushToken)}
        window.dispatchEvent(new CustomEvent("selfmonitor-native-bootstrap", {
          detail: ${JSON.stringify(payload)}
        }));
      } catch (error) {
        console.error("selfmonitor-native-bootstrap-failed", error);
      }
    })();
    true;
  `;
}

export default function App(): React.JSX.Element {
  const webRef = useRef<WebView>(null);
  const [isConnected, setIsConnected] = useState(true);
  const [isHydrating, setIsHydrating] = useState(true);
  const [isOnboardingDone, setIsOnboardingDone] = useState(true);
  const [biometricRequired, setBiometricRequired] = useState(false);
  const [biometricUnlocked, setBiometricUnlocked] = useState(false);
  const [biometricLabel, setBiometricLabel] = useState("биометрии");
  const [isAuthenticatingBiometric, setIsAuthenticatingBiometric] = useState(false);
  const [canGoBack, setCanGoBack] = useState(false);
  const [activePath, setActivePath] = useState("/dashboard");
  const [isLoading, setIsLoading] = useState(true);
  const [hasError, setHasError] = useState(false);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [bootstrapScript, setBootstrapScript] = useState("true;");
  const [storedPushToken, setStoredPushToken] = useState<string | null>(null);
  const [clock, setClock] = useState(() => new Date());
  const pulseAnim = useRef(new Animated.Value(0)).current;
  const dockFloatAnim = useRef(new Animated.Value(0)).current;
  const glowAnim = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    const subscription = NetInfo.addEventListener((state) => {
      setIsConnected(Boolean(state.isConnected));
    });
    return () => subscription();
  }, []);

  useEffect(() => {
    let isMounted = true;
    const hydrateSecureSession = async () => {
      try {
        const [token, email, theme, pushToken, onboardingFlag] = await Promise.all([
          SecureStore.getItemAsync(SECURE_AUTH_TOKEN_KEY),
          SecureStore.getItemAsync(SECURE_AUTH_EMAIL_KEY),
          SecureStore.getItemAsync(SECURE_THEME_KEY),
          SecureStore.getItemAsync(SECURE_PUSH_TOKEN_KEY),
          SecureStore.getItemAsync(SECURE_ONBOARDING_DONE_KEY),
        ]);
        if (!isMounted) {
          return;
        }
        setStoredPushToken(pushToken ?? null);
        setIsOnboardingDone(onboardingFlag === "1");
        const hasAuthSession = Boolean(token);
        if (hasAuthSession) {
          const [hasBiometricHardware, biometricEnrolled, biometricTypes] = await Promise.all([
            LocalAuthentication.hasHardwareAsync(),
            LocalAuthentication.isEnrolledAsync(),
            LocalAuthentication.supportedAuthenticationTypesAsync(),
          ]);
          if (!isMounted) {
            return;
          }
          const firstType = biometricTypes[0];
          if (firstType === LocalAuthentication.AuthenticationType.FACIAL_RECOGNITION) {
            setBiometricLabel("Face ID / распознаванию лица");
          } else if (firstType === LocalAuthentication.AuthenticationType.FINGERPRINT) {
            setBiometricLabel("Touch ID / отпечатку пальца");
          } else {
            setBiometricLabel("биометрии");
          }
          if (hasBiometricHardware && biometricEnrolled) {
            setBiometricRequired(true);
            setBiometricUnlocked(false);
          } else {
            setBiometricRequired(false);
            setBiometricUnlocked(true);
          }
        } else {
          setBiometricRequired(false);
          setBiometricUnlocked(true);
        }
        setBootstrapScript(
          buildBootstrapScript({
            token: token ?? null,
            email: email ?? null,
            theme: theme ?? null,
            pushToken: pushToken ?? null,
          })
        );
      } catch (error) {
        if (isMounted) {
          setStatusMessage(
            error instanceof Error
              ? `Secure session bootstrap failed: ${error.message}`
              : "Secure session bootstrap failed."
          );
        }
      } finally {
        if (isMounted) {
          setIsHydrating(false);
        }
      }
    };
    void hydrateSecureSession();
    return () => {
      isMounted = false;
    };
  }, []);

  useEffect(() => {
    const interval = setInterval(() => setClock(new Date()), 30_000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    const pulseLoop = Animated.loop(
      Animated.sequence([
        Animated.timing(pulseAnim, {
          duration: 1200,
          toValue: 1,
          useNativeDriver: true,
          easing: Easing.out(Easing.quad),
        }),
        Animated.timing(pulseAnim, {
          duration: 1200,
          toValue: 0,
          useNativeDriver: true,
          easing: Easing.in(Easing.quad),
        }),
      ])
    );
    pulseLoop.start();
    return () => pulseLoop.stop();
  }, [pulseAnim]);

  useEffect(() => {
    const floatLoop = Animated.loop(
      Animated.sequence([
        Animated.timing(dockFloatAnim, {
          duration: 1800,
          toValue: 1,
          useNativeDriver: true,
          easing: Easing.inOut(Easing.sin),
        }),
        Animated.timing(dockFloatAnim, {
          duration: 1800,
          toValue: 0,
          useNativeDriver: true,
          easing: Easing.inOut(Easing.sin),
        }),
      ])
    );
    floatLoop.start();
    return () => floatLoop.stop();
  }, [dockFloatAnim]);

  useEffect(() => {
    const glowLoop = Animated.loop(
      Animated.sequence([
        Animated.timing(glowAnim, {
          duration: 1000,
          toValue: 1,
          useNativeDriver: true,
          easing: Easing.out(Easing.exp),
        }),
        Animated.timing(glowAnim, {
          duration: 1000,
          toValue: 0,
          useNativeDriver: true,
          easing: Easing.in(Easing.exp),
        }),
      ])
    );
    glowLoop.start();
    return () => glowLoop.stop();
  }, [glowAnim]);

  useEffect(() => {
    if (!statusMessage) {
      return;
    }
    const timeout = setTimeout(() => setStatusMessage(null), 4200);
    return () => clearTimeout(timeout);
  }, [statusMessage]);

  useEffect(() => {
    const onBackPress = () => {
      if (canGoBack && webRef.current) {
        void Haptics.selectionAsync();
        webRef.current.goBack();
        return true;
      }
      return false;
    };
    const subscription = BackHandler.addEventListener("hardwareBackPress", onBackPress);
    return () => subscription.remove();
  }, [canGoBack]);

  const runHaptic = useCallback(async (intensity: "light" | "medium" | "heavy") => {
    if (Platform.OS === "web") {
      return;
    }
    const style =
      intensity === "light"
        ? Haptics.ImpactFeedbackStyle.Light
        : intensity === "heavy"
          ? Haptics.ImpactFeedbackStyle.Heavy
          : Haptics.ImpactFeedbackStyle.Medium;
    await Haptics.impactAsync(style);
  }, []);

  const resolveNotificationPath = useCallback((payload: unknown): string | null => {
    if (!payload || typeof payload !== "object") {
      return null;
    }
    const candidate = payload as NotificationPayloadLike;
    const rawPath = candidate.path ?? candidate.deeplink ?? candidate.url ?? candidate.route ?? candidate.screen;
    if (typeof rawPath !== "string" || !rawPath.trim()) {
      return null;
    }
    if (rawPath.startsWith("/")) {
      return rawPath;
    }
    const mapped = PUSH_ROUTE_MAP[rawPath.toLowerCase()];
    if (mapped) {
      return mapped;
    }
    try {
      const rawUrl = new URL(rawPath);
      const allowedOrigin = new URL(WEB_PORTAL_URL).origin;
      if (rawUrl.origin !== allowedOrigin) {
        return null;
      }
      const nextPath = `${rawUrl.pathname}${rawUrl.search || ""}`;
      return nextPath || "/dashboard";
    } catch {
      return null;
    }
  }, []);

  const notifyAction = useCallback((message: string) => {
    setStatusMessage(message);
  }, []);

  const derivePathFromUrl = useCallback((url: string) => {
    if (!url || url.startsWith("about:blank")) {
      return null;
    }
    try {
      return new URL(url).pathname || null;
    } catch {
      const base = WEB_PORTAL_URL.replace(/\/+$/, "");
      if (!url.startsWith(base)) {
        return null;
      }
      const pathPart = url.slice(base.length) || "/";
      return pathPart.startsWith("/") ? pathPart : `/${pathPart}`;
    }
  }, []);

  const syncPushTokenToWeb = useCallback((token: string) => {
    webRef.current?.injectJavaScript(
      `
        (function() {
          try {
            window.localStorage.setItem(${JSON.stringify(MOBILE_PUSH_TOKEN_KEY)}, ${JSON.stringify(token)});
            window.dispatchEvent(new CustomEvent("selfmonitor-mobile-push-token", {
              detail: { token: ${JSON.stringify(token)} }
            }));
          } catch (error) {
            console.error("selfmonitor-mobile-push-token-sync-failed", error);
          }
        })();
        true;
      `
    );
  }, []);

  const setSecureAuthState = useCallback(async (token: string | null, email: string | null) => {
    if (token) {
      await SecureStore.setItemAsync(SECURE_AUTH_TOKEN_KEY, token);
    } else {
      await SecureStore.deleteItemAsync(SECURE_AUTH_TOKEN_KEY);
    }
    if (email) {
      await SecureStore.setItemAsync(SECURE_AUTH_EMAIL_KEY, email);
    } else {
      await SecureStore.deleteItemAsync(SECURE_AUTH_EMAIL_KEY);
    }
  }, []);

  const handleWebMessage = useCallback(
    async (rawData: string) => {
      let parsed: BridgeMessage | null = null;
      try {
        parsed = JSON.parse(rawData) as BridgeMessage;
      } catch {
        return;
      }
      if (!parsed?.type) {
        return;
      }

      if (parsed.type === "WEB_AUTH_STATE") {
        const token = parsed.payload?.token ?? null;
        const email = parsed.payload?.email ?? null;
        try {
          await setSecureAuthState(token ?? null, email ?? null);
          if (!token) {
            setBiometricRequired(false);
            setBiometricUnlocked(true);
          }
        } catch (error) {
          setStatusMessage(
            error instanceof Error
              ? `Secure auth sync failed: ${error.message}`
              : "Secure auth sync failed."
          );
        }
        return;
      }

      if (parsed.type === "WEB_THEME_STATE") {
        const theme = parsed.payload?.theme ?? null;
        try {
          if (theme) {
            await SecureStore.setItemAsync(SECURE_THEME_KEY, theme);
          } else {
            await SecureStore.deleteItemAsync(SECURE_THEME_KEY);
          }
        } catch (error) {
          setStatusMessage(
            error instanceof Error
              ? `Theme sync failed: ${error.message}`
              : "Theme sync failed."
          );
        }
      }
    },
    [setSecureAuthState]
  );

  const registerPushNotifications = useCallback(async () => {
    try {
      await runHaptic("medium");
      if (!Device.isDevice) {
        setStatusMessage("Push notifications работают только на физическом устройстве.");
        return;
      }
      const permission = await Notifications.getPermissionsAsync();
      let finalStatus = permission.status;
      if (finalStatus !== "granted") {
        const requested = await Notifications.requestPermissionsAsync();
        finalStatus = requested.status;
      }
      if (finalStatus !== "granted") {
        setStatusMessage("Разрешение на push не выдано.");
        return;
      }
      const projectId = process.env.EXPO_PUBLIC_EAS_PROJECT_ID;
      const tokenResponse = await Notifications.getExpoPushTokenAsync(
        projectId ? { projectId } : undefined
      );
      await SecureStore.setItemAsync(SECURE_PUSH_TOKEN_KEY, tokenResponse.data);
      setStoredPushToken(tokenResponse.data);
      syncPushTokenToWeb(tokenResponse.data);
      notifyAction("Push token успешно подключен.");
      await runHaptic("heavy");
    } catch (error) {
      setStatusMessage(
        error instanceof Error
          ? `Не удалось включить push: ${error.message}`
          : "Не удалось включить push."
      );
      await runHaptic("heavy");
    }
  }, [notifyAction, runHaptic, syncPushTokenToWeb]);

  const normalizePortalPath = useCallback((path: string) => {
    const base = WEB_PORTAL_URL.replace(/\/+$/, "");
    const normalized = path.startsWith("/") ? path : `/${path}`;
    return `${base}${normalized}`;
  }, []);

  const navigateInsidePortal = useCallback(
    async (path: string) => {
      await runHaptic("light");
      const targetUrl = normalizePortalPath(path);
      webRef.current?.injectJavaScript(
        `
          (function() {
            window.location.assign(${JSON.stringify(targetUrl)});
          })();
          true;
        `
      );
      notifyAction(`Переход: ${path}`);
    },
    [normalizePortalPath, notifyAction, runHaptic]
  );

  const openReceiptCapture = useCallback(async () => {
    await runHaptic("medium");
    const captureUrl = normalizePortalPath("/documents?mobile_capture=1");
    webRef.current?.injectJavaScript(
      `
        (function() {
          if (window.location.pathname !== "/documents") {
            window.location.assign(${JSON.stringify(captureUrl)});
            return;
          }
          var input = document.querySelector('input[type="file"]');
          if (input) {
            input.click();
            return;
          }
          window.location.assign(${JSON.stringify(captureUrl)});
        })();
        true;
      `
    );
    notifyAction("Открываем быстрый скан чека...");
  }, [normalizePortalPath, notifyAction, runHaptic]);

  const onRetry = useCallback(async () => {
    await runHaptic("medium");
    setHasError(false);
    webRef.current?.reload();
  }, [runHaptic]);

  const shouldAllowNavigation = useCallback((url: string) => {
    if (!url || url.startsWith("about:blank")) {
      return true;
    }
    try {
      const allowedOrigin = new URL(WEB_PORTAL_URL).origin;
      const targetOrigin = new URL(url).origin;
      if (targetOrigin === allowedOrigin) {
        return true;
      }
      void Linking.openURL(url);
      return false;
    } catch {
      if (url.startsWith(WEB_PORTAL_URL)) {
        return true;
      }
      void Linking.openURL(url);
      return false;
    }
  }, []);

  const requestBiometricUnlock = useCallback(async () => {
    if (!biometricRequired || biometricUnlocked || isAuthenticatingBiometric) {
      return;
    }
    try {
      setIsAuthenticatingBiometric(true);
      const result = await LocalAuthentication.authenticateAsync({
        promptMessage: "Разблокируйте SelfMonitor",
        cancelLabel: "Позже",
        fallbackLabel: "Ввести код устройства",
      });
      if (result.success) {
        await runHaptic("heavy");
        setBiometricUnlocked(true);
        notifyAction("Приложение разблокировано.");
      } else if (result.error !== "user_cancel") {
        await runHaptic("medium");
        notifyAction("Не удалось подтвердить биометрию. Повторите попытку.");
      }
    } catch (error) {
      notifyAction(
        error instanceof Error
          ? `Ошибка биометрии: ${error.message}`
          : "Ошибка биометрической проверки."
      );
    } finally {
      setIsAuthenticatingBiometric(false);
    }
  }, [biometricRequired, biometricUnlocked, isAuthenticatingBiometric, notifyAction, runHaptic]);

  const completeOnboarding = useCallback(async () => {
    await runHaptic("heavy");
    await SecureStore.setItemAsync(SECURE_ONBOARDING_DONE_KEY, "1");
    setIsOnboardingDone(true);
    notifyAction("Добро пожаловать в SelfMonitor Mobile.");
  }, [notifyAction, runHaptic]);

  useEffect(() => {
    if (!isHydrating && biometricRequired && !biometricUnlocked) {
      void requestBiometricUnlock();
    }
  }, [biometricRequired, biometricUnlocked, isHydrating, requestBiometricUnlock]);

  useEffect(() => {
    const receivedSubscription = Notifications.addNotificationReceivedListener((notification) => {
      const title = notification.request.content.title;
      if (title) {
        notifyAction(`Push: ${title}`);
      }
    });
    const responseSubscription = Notifications.addNotificationResponseReceivedListener((response) => {
      const maybePath = resolveNotificationPath(response.notification.request.content.data);
      if (maybePath) {
        void navigateInsidePortal(maybePath);
      }
    });
    void Notifications.getLastNotificationResponseAsync().then((response) => {
      if (!response) {
        return;
      }
      const maybePath = resolveNotificationPath(response.notification.request.content.data);
      if (maybePath) {
        void navigateInsidePortal(maybePath);
      }
    });
    return () => {
      receivedSubscription.remove();
      responseSubscription.remove();
    };
  }, [navigateInsidePortal, notifyAction, resolveNotificationPath]);

  const isRouteActive = useCallback(
    (route: string) => activePath === route || activePath.startsWith(`${route}/`),
    [activePath]
  );

  const webUserAgent = useMemo(() => {
    if (Platform.OS === "ios") {
      return `Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile ${APP_USER_AGENT_SUFFIX}`;
    }
    if (Platform.OS === "android") {
      return `Mozilla/5.0 (Linux; Android 14) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Mobile Safari/537.36 ${APP_USER_AGENT_SUFFIX}`;
    }
    return APP_USER_AGENT_SUFFIX;
  }, []);

  const pulseScale = pulseAnim.interpolate({
    inputRange: [0, 1],
    outputRange: [1, 1.24],
  });
  const pulseOpacity = pulseAnim.interpolate({
    inputRange: [0, 1],
    outputRange: [0.28, 0.78],
  });
  const dockTranslateY = dockFloatAnim.interpolate({
    inputRange: [0, 1],
    outputRange: [0, -4],
  });
  const glowOpacity = glowAnim.interpolate({
    inputRange: [0, 1],
    outputRange: [0.16, 0.42],
  });

  const greeting = useMemo(() => {
    const hour = clock.getHours();
    if (hour < 12) {
      return "Доброе утро";
    }
    if (hour < 18) {
      return "Добрый день";
    }
    return "Добрый вечер";
  }, [clock]);

  const connectionLabel = isConnected ? "Online" : "Offline";
  const sessionLabel = storedPushToken ? "Secure + Push ready" : "Secure session";

  const dockActions = useMemo<DockAction[]>(
    () => [
      {
        id: "dashboard",
        label: "Главная",
        icon: "home-outline",
        onPress: () => {
          void navigateInsidePortal("/dashboard");
        },
      },
      {
        id: "documents",
        label: "Документы",
        icon: "folder-open-outline",
        onPress: () => {
          void navigateInsidePortal("/documents");
        },
      },
      {
        id: "scan",
        label: "Скан",
        icon: "scan-circle-outline",
        isPrimary: true,
        onPress: () => {
          void openReceiptCapture();
        },
      },
      {
        id: "push",
        label: "Push",
        icon: "notifications-outline",
        onPress: () => {
          void registerPushNotifications();
        },
      },
    ],
    [navigateInsidePortal, openReceiptCapture, registerPushNotifications]
  );

  return (
    <SafeAreaView style={styles.container}>
      <LinearGradient
        colors={["#020617", "#0f172a", "#1d4ed8"]}
        end={{ x: 1, y: 1 }}
        pointerEvents="none"
        start={{ x: 0, y: 0 }}
        style={styles.backgroundAura}
      />
      <StatusBar style="dark" />
      {isHydrating ? (
        <View style={styles.errorContainer}>
          <Animated.View
            style={[
              styles.hydratingOrb,
              {
                opacity: pulseOpacity,
                transform: [{ scale: pulseScale }],
              },
            ]}
          />
          <ActivityIndicator size="large" color="#2563eb" />
          <Text style={styles.errorSubtitle}>Подготовка защищенной мобильной сессии...</Text>
        </View>
      ) : null}
      {!isHydrating && !isOnboardingDone ? (
        <ScrollView contentContainerStyle={styles.onboardingContainer} style={styles.onboardingScroll}>
          <LinearGradient
            colors={["#1d4ed8", "#312e81", "#020617"]}
            end={{ x: 1, y: 1 }}
            start={{ x: 0, y: 0 }}
            style={styles.onboardingHero}
          >
            <LottieView
              autoPlay
              loop
              source={require("./assets/lottie/onboarding-spark.json")}
              style={styles.onboardingAnimation}
            />
            <Text style={styles.onboardingTitle}>SelfMonitor Mobile</Text>
            <Text style={styles.onboardingSubtitle}>
              Финансовый помощник премиум-уровня для самозанятых в UK — теперь в формате top mobile app.
            </Text>
          </LinearGradient>
          <View style={styles.onboardingFeatureList}>
            <View style={styles.onboardingFeatureItem}>
              <Ionicons color="#1d4ed8" name="flash-outline" size={18} />
              <Text style={styles.onboardingFeatureText}>Мгновенный скан чеков и умная обработка.</Text>
            </View>
            <View style={styles.onboardingFeatureItem}>
              <Ionicons color="#1d4ed8" name="shield-checkmark-outline" size={18} />
              <Text style={styles.onboardingFeatureText}>Защищенная сессия + биометрический unlock.</Text>
            </View>
            <View style={styles.onboardingFeatureItem}>
              <Ionicons color="#1d4ed8" name="notifications-outline" size={18} />
              <Text style={styles.onboardingFeatureText}>Push дедлайны HMRC и напоминания по инвойсам.</Text>
            </View>
          </View>
          <Pressable
            accessibilityRole="button"
            onPress={() => {
              void completeOnboarding();
            }}
            style={styles.onboardingPrimaryButton}
          >
            <Text style={styles.onboardingPrimaryButtonText}>Начать</Text>
          </Pressable>
        </ScrollView>
      ) : null}
      {!isHydrating && isOnboardingDone && biometricRequired && !biometricUnlocked ? (
        <View style={styles.biometricGateContainer}>
          <LinearGradient
            colors={["#0f172a", "#1e3a8a", "#0f172a"]}
            end={{ x: 1, y: 1 }}
            start={{ x: 0, y: 0 }}
            style={styles.biometricCard}
          >
            <Ionicons color="#93c5fd" name="lock-closed-outline" size={40} />
            <Text style={styles.biometricTitle}>Защищенный вход</Text>
            <Text style={styles.biometricSubtitle}>
              Подтвердите доступ по {biometricLabel}, чтобы продолжить работу.
            </Text>
            <Pressable
              accessibilityRole="button"
              onPress={() => {
                void requestBiometricUnlock();
              }}
              style={styles.biometricButton}
            >
              <Text style={styles.biometricButtonText}>
                {isAuthenticatingBiometric ? "Проверяем..." : "Разблокировать"}
              </Text>
            </Pressable>
          </LinearGradient>
        </View>
      ) : null}
      {statusMessage ? (
        <View style={styles.statusBanner}>
          <Text style={styles.statusBannerText}>{statusMessage}</Text>
        </View>
      ) : null}
      {!isConnected ? (
        <View style={styles.offlineBanner}>
          <Text style={styles.offlineBannerText}>
            Нет сети. Проверьте подключение и повторите.
          </Text>
        </View>
      ) : null}
      {hasError && !isHydrating ? (
        <View style={styles.errorContainer}>
          <Text style={styles.errorTitle}>Не удалось открыть приложение</Text>
          <Text style={styles.errorSubtitle}>
            Проверьте адрес web-портала и сетевой доступ, затем попробуйте снова.
          </Text>
          <Pressable onPress={onRetry} style={styles.retryButton}>
            <Text style={styles.retryButtonText}>Повторить</Text>
          </Pressable>
          <Text style={styles.hintText}>Текущий URL: {WEB_PORTAL_URL}</Text>
        </View>
      ) : !isHydrating && isOnboardingDone && (!biometricRequired || biometricUnlocked) ? (
        <View style={styles.webViewWrapper}>
          <View style={styles.topOverlay}>
            <LinearGradient
              colors={["rgba(30,64,175,0.92)", "rgba(15,23,42,0.92)"]}
              end={{ x: 1, y: 1 }}
              start={{ x: 0, y: 0 }}
              style={styles.commandCard}
            >
              <View style={styles.commandCardHeader}>
                <View>
                  <Text style={styles.commandGreeting}>{greeting}</Text>
                  <Text style={styles.commandTitle}>SelfMonitor Mobile</Text>
                </View>
                <View style={styles.clockChip}>
                  <Ionicons color="#dbeafe" name="time-outline" size={14} />
                  <Text style={styles.clockChipText}>
                    {clock.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                  </Text>
                </View>
              </View>
              <View style={styles.commandMetricsRow}>
                <View style={styles.metricPill}>
                  <View style={styles.onlineDotWrapper}>
                    <Animated.View
                      style={[
                        styles.onlineDotPulse,
                        {
                          opacity: pulseOpacity,
                          transform: [{ scale: pulseScale }],
                        },
                      ]}
                    />
                    <View style={[styles.onlineDotCore, !isConnected && styles.onlineDotOffline]} />
                  </View>
                  <Text style={styles.metricPillText}>{connectionLabel}</Text>
                </View>
                <View style={styles.metricPill}>
                  <Ionicons color="#bfdbfe" name="shield-checkmark-outline" size={14} />
                  <Text style={styles.metricPillText}>{sessionLabel}</Text>
                </View>
                {canGoBack ? (
                  <Pressable
                    accessibilityRole="button"
                    onPress={() => {
                      void runHaptic("light");
                      webRef.current?.goBack();
                    }}
                    style={styles.backChipButton}
                  >
                    <Ionicons color="#e2e8f0" name="arrow-back-outline" size={16} />
                    <Text style={styles.backChipText}>Назад</Text>
                  </Pressable>
                ) : null}
              </View>
            </LinearGradient>
          </View>

          <WebView
            ref={webRef}
            source={{ uri: WEB_PORTAL_URL }}
            userAgent={webUserAgent}
            injectedJavaScriptBeforeContentLoaded={bootstrapScript}
            startInLoadingState
            pullToRefreshEnabled
            setSupportMultipleWindows={false}
            sharedCookiesEnabled
            thirdPartyCookiesEnabled
            javaScriptEnabled
            domStorageEnabled
            allowsBackForwardNavigationGestures
            onShouldStartLoadWithRequest={(request) => shouldAllowNavigation(request.url)}
            onMessage={(event) => {
              void handleWebMessage(event.nativeEvent.data);
            }}
            onLoadStart={() => {
              setIsLoading(true);
              setHasError(false);
            }}
            onLoadEnd={() => {
              setIsLoading(false);
              if (storedPushToken) {
                syncPushTokenToWeb(storedPushToken);
              }
            }}
            onNavigationStateChange={(navigationState) => {
              setCanGoBack(navigationState.canGoBack);
              const path = derivePathFromUrl(navigationState.url);
              if (path) {
                setActivePath(path);
              }
            }}
            onError={() => {
              setHasError(true);
              setIsLoading(false);
            }}
          />
          {isLoading ? (
            <View style={styles.loadingOverlay}>
              <Animated.View style={[styles.loadingGlow, { opacity: glowOpacity }]} />
              <ActivityIndicator size="large" color="#2563eb" />
              <Text style={styles.loadingText}>Загружаем SelfMonitor...</Text>
            </View>
          ) : null}
          <Animated.View
            style={[
              styles.actionBar,
              {
                transform: [{ translateY: dockTranslateY }],
              },
            ]}
          >
            <LinearGradient
              colors={["rgba(15,23,42,0.94)", "rgba(30,41,59,0.92)", "rgba(37,99,235,0.82)"]}
              end={{ x: 1, y: 1 }}
              start={{ x: 0, y: 0 }}
              style={styles.actionBarGradient}
            >
              {dockActions.map((action) => {
                const selected =
                  action.id === "dashboard"
                    ? isRouteActive("/dashboard")
                    : action.id === "documents" || action.id === "scan"
                      ? isRouteActive("/documents")
                      : false;
                return (
                  <Pressable
                    accessibilityRole="button"
                    key={action.id}
                    onPress={action.onPress}
                    style={({ pressed }) => [
                      action.isPrimary ? styles.actionButtonPrimary : styles.actionButton,
                      selected ? styles.actionButtonActive : null,
                      pressed ? styles.actionButtonPressed : null,
                    ]}
                  >
                    <Ionicons
                      color={action.isPrimary ? "#ffffff" : selected ? "#93c5fd" : "#e2e8f0"}
                      name={action.icon}
                      size={16}
                    />
                    <Text style={action.isPrimary ? styles.actionButtonTextPrimary : styles.actionButtonText}>
                      {action.label}
                    </Text>
                  </Pressable>
                );
              })}
            </LinearGradient>
          </Animated.View>
        </View>
      ) : null}
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: "#f8fafc",
  },
  backgroundAura: {
    ...StyleSheet.absoluteFillObject,
    opacity: 0.2,
  },
  onboardingScroll: {
    flex: 1,
  },
  onboardingContainer: {
    padding: 18,
    paddingTop: 28,
    gap: 16,
  },
  onboardingHero: {
    alignItems: "center",
    borderRadius: 18,
    gap: 10,
    overflow: "hidden",
    paddingHorizontal: 18,
    paddingVertical: 20,
  },
  onboardingAnimation: {
    height: 180,
    width: 180,
  },
  onboardingTitle: {
    color: "#ffffff",
    fontSize: 24,
    fontWeight: "800",
  },
  onboardingSubtitle: {
    color: "#cbd5e1",
    fontSize: 14,
    lineHeight: 20,
    textAlign: "center",
  },
  onboardingFeatureList: {
    backgroundColor: "rgba(255,255,255,0.92)",
    borderColor: "rgba(148,163,184,0.35)",
    borderRadius: 16,
    borderWidth: 1,
    gap: 12,
    padding: 14,
  },
  onboardingFeatureItem: {
    alignItems: "center",
    flexDirection: "row",
    gap: 10,
  },
  onboardingFeatureText: {
    color: "#1e293b",
    flex: 1,
    fontSize: 14,
    lineHeight: 20,
  },
  onboardingPrimaryButton: {
    alignItems: "center",
    backgroundColor: "#1d4ed8",
    borderRadius: 14,
    paddingVertical: 14,
  },
  onboardingPrimaryButtonText: {
    color: "#ffffff",
    fontSize: 16,
    fontWeight: "700",
  },
  biometricGateContainer: {
    ...StyleSheet.absoluteFillObject,
    alignItems: "center",
    backgroundColor: "rgba(2,6,23,0.82)",
    justifyContent: "center",
    padding: 24,
    zIndex: 30,
  },
  biometricCard: {
    alignItems: "center",
    borderColor: "rgba(147,197,253,0.4)",
    borderRadius: 18,
    borderWidth: 1,
    gap: 12,
    maxWidth: 420,
    paddingHorizontal: 20,
    paddingVertical: 24,
    width: "100%",
  },
  biometricTitle: {
    color: "#ffffff",
    fontSize: 22,
    fontWeight: "700",
  },
  biometricSubtitle: {
    color: "#cbd5e1",
    fontSize: 14,
    lineHeight: 20,
    textAlign: "center",
  },
  biometricButton: {
    backgroundColor: "#2563eb",
    borderRadius: 12,
    marginTop: 4,
    paddingHorizontal: 20,
    paddingVertical: 12,
  },
  biometricButtonText: {
    color: "#ffffff",
    fontSize: 15,
    fontWeight: "700",
  },
  topOverlay: {
    left: 12,
    position: "absolute",
    right: 12,
    top: 10,
    zIndex: 12,
  },
  commandCard: {
    borderColor: "rgba(148,163,184,0.32)",
    borderRadius: 16,
    borderWidth: 1,
    gap: 10,
    paddingHorizontal: 14,
    paddingVertical: 12,
    shadowColor: "#1d4ed8",
    shadowOffset: {
      width: 0,
      height: 6,
    },
    shadowOpacity: 0.25,
    shadowRadius: 10,
  },
  commandCardHeader: {
    alignItems: "center",
    flexDirection: "row",
    justifyContent: "space-between",
  },
  commandGreeting: {
    color: "#bfdbfe",
    fontSize: 12,
    fontWeight: "500",
  },
  commandTitle: {
    color: "#ffffff",
    fontSize: 19,
    fontWeight: "700",
    marginTop: 2,
  },
  clockChip: {
    alignItems: "center",
    backgroundColor: "rgba(30,41,59,0.68)",
    borderColor: "rgba(191,219,254,0.35)",
    borderRadius: 999,
    borderWidth: 1,
    flexDirection: "row",
    gap: 5,
    paddingHorizontal: 10,
    paddingVertical: 6,
  },
  clockChipText: {
    color: "#dbeafe",
    fontSize: 12,
    fontWeight: "600",
  },
  commandMetricsRow: {
    alignItems: "center",
    flexDirection: "row",
    flexWrap: "wrap",
    gap: 8,
  },
  metricPill: {
    alignItems: "center",
    backgroundColor: "rgba(15,23,42,0.55)",
    borderColor: "rgba(191,219,254,0.3)",
    borderRadius: 999,
    borderWidth: 1,
    flexDirection: "row",
    gap: 6,
    paddingHorizontal: 10,
    paddingVertical: 6,
  },
  metricPillText: {
    color: "#e2e8f0",
    fontSize: 12,
    fontWeight: "600",
  },
  onlineDotWrapper: {
    alignItems: "center",
    height: 12,
    justifyContent: "center",
    width: 12,
  },
  onlineDotPulse: {
    backgroundColor: "#22c55e",
    borderRadius: 999,
    height: 12,
    position: "absolute",
    width: 12,
  },
  onlineDotCore: {
    backgroundColor: "#22c55e",
    borderRadius: 999,
    height: 6,
    width: 6,
  },
  onlineDotOffline: {
    backgroundColor: "#ef4444",
  },
  backChipButton: {
    alignItems: "center",
    backgroundColor: "rgba(15,23,42,0.55)",
    borderColor: "rgba(191,219,254,0.3)",
    borderRadius: 999,
    borderWidth: 1,
    flexDirection: "row",
    gap: 4,
    paddingHorizontal: 10,
    paddingVertical: 6,
  },
  backChipText: {
    color: "#e2e8f0",
    fontSize: 12,
    fontWeight: "600",
  },
  webViewWrapper: {
    flex: 1,
  },
  hydratingOrb: {
    backgroundColor: "#3b82f6",
    borderRadius: 999,
    height: 64,
    marginBottom: 8,
    width: 64,
  },
  actionBar: {
    bottom: 12,
    left: 10,
    position: "absolute",
    right: 10,
    zIndex: 11,
  },
  actionBarGradient: {
    alignItems: "center",
    borderRadius: 14,
    borderWidth: 1,
    borderColor: "rgba(191,219,254,0.3)",
    flexDirection: "row",
    gap: 8,
    justifyContent: "space-between",
    overflow: "hidden",
    paddingHorizontal: 10,
    paddingVertical: 8,
  },
  actionButton: {
    alignItems: "center",
    backgroundColor: "rgba(15,23,42,0.34)",
    borderRadius: 10,
    borderWidth: 1,
    borderColor: "rgba(255,255,255,0.28)",
    flexDirection: "row",
    gap: 4,
    paddingHorizontal: 10,
    paddingVertical: 8,
    minWidth: 68,
  },
  actionButtonPrimary: {
    alignItems: "center",
    borderRadius: 10,
    borderWidth: 1,
    borderColor: "rgba(147,197,253,0.65)",
    backgroundColor: "#2563eb",
    flexDirection: "row",
    gap: 4,
    paddingHorizontal: 10,
    paddingVertical: 8,
    minWidth: 86,
  },
  actionButtonActive: {
    borderColor: "rgba(147,197,253,0.9)",
    backgroundColor: "rgba(37,99,235,0.28)",
  },
  actionButtonPressed: {
    opacity: 0.72,
    transform: [{ scale: 0.97 }],
  },
  actionButtonText: {
    color: "#f8fafc",
    fontSize: 12,
    textAlign: "center",
    fontWeight: "600",
  },
  actionButtonTextPrimary: {
    color: "#ffffff",
    fontSize: 12,
    textAlign: "center",
    fontWeight: "700",
  },
  loadingOverlay: {
    ...StyleSheet.absoluteFillObject,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: "rgba(248,250,252,0.92)",
    gap: 12,
  },
  loadingGlow: {
    backgroundColor: "#60a5fa",
    borderRadius: 999,
    height: 120,
    position: "absolute",
    width: 120,
  },
  loadingText: {
    color: "#1e293b",
    fontSize: 15,
    fontWeight: "500",
  },
  offlineBanner: {
    backgroundColor: "#fef2f2",
    borderBottomWidth: 1,
    borderBottomColor: "#fecaca",
    paddingHorizontal: 16,
    paddingVertical: 10,
  },
  offlineBannerText: {
    color: "#991b1b",
    fontSize: 13,
    textAlign: "center",
  },
  statusBanner: {
    backgroundColor: "#eff6ff",
    borderBottomWidth: 1,
    borderBottomColor: "#bfdbfe",
    paddingHorizontal: 16,
    paddingVertical: 8,
  },
  statusBannerText: {
    color: "#1d4ed8",
    textAlign: "center",
    fontSize: 13,
  },
  errorContainer: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
    paddingHorizontal: 24,
    gap: 10,
  },
  errorTitle: {
    fontSize: 20,
    fontWeight: "700",
    color: "#111827",
    textAlign: "center",
  },
  errorSubtitle: {
    color: "#475569",
    fontSize: 15,
    textAlign: "center",
  },
  retryButton: {
    marginTop: 8,
    backgroundColor: "#2563eb",
    borderRadius: 10,
    paddingHorizontal: 18,
    paddingVertical: 10,
  },
  retryButtonText: {
    color: "#ffffff",
    fontSize: 15,
    fontWeight: "600",
  },
  hintText: {
    marginTop: 8,
    color: "#64748b",
    fontSize: 12,
    textAlign: "center",
  },
});
