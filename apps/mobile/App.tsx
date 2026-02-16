import NetInfo from "@react-native-community/netinfo";
import * as Device from "expo-device";
import * as Notifications from "expo-notifications";
import * as SecureStore from "expo-secure-store";
import { StatusBar } from "expo-status-bar";
import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  ActivityIndicator,
  BackHandler,
  Linking,
  Platform,
  Pressable,
  SafeAreaView,
  StyleSheet,
  Text,
  View,
} from "react-native";
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

type BridgeMessage = {
  payload?: Record<string, string | null | undefined>;
  type?: string;
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
  const [canGoBack, setCanGoBack] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [hasError, setHasError] = useState(false);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [bootstrapScript, setBootstrapScript] = useState("true;");
  const [storedPushToken, setStoredPushToken] = useState<string | null>(null);

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
        const [token, email, theme, pushToken] = await Promise.all([
          SecureStore.getItemAsync(SECURE_AUTH_TOKEN_KEY),
          SecureStore.getItemAsync(SECURE_AUTH_EMAIL_KEY),
          SecureStore.getItemAsync(SECURE_THEME_KEY),
          SecureStore.getItemAsync(SECURE_PUSH_TOKEN_KEY),
        ]);
        if (!isMounted) {
          return;
        }
        setStoredPushToken(pushToken ?? null);
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
    if (!statusMessage) {
      return;
    }
    const timeout = setTimeout(() => setStatusMessage(null), 4200);
    return () => clearTimeout(timeout);
  }, [statusMessage]);

  useEffect(() => {
    const onBackPress = () => {
      if (canGoBack && webRef.current) {
        webRef.current.goBack();
        return true;
      }
      return false;
    };
    const subscription = BackHandler.addEventListener("hardwareBackPress", onBackPress);
    return () => subscription.remove();
  }, [canGoBack]);

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
      setStatusMessage("Push token успешно подключен.");
    } catch (error) {
      setStatusMessage(
        error instanceof Error
          ? `Не удалось включить push: ${error.message}`
          : "Не удалось включить push."
      );
    }
  }, [syncPushTokenToWeb]);

  const normalizePortalPath = useCallback((path: string) => {
    const base = WEB_PORTAL_URL.replace(/\/+$/, "");
    const normalized = path.startsWith("/") ? path : `/${path}`;
    return `${base}${normalized}`;
  }, []);

  const navigateInsidePortal = useCallback(
    (path: string) => {
      const targetUrl = normalizePortalPath(path);
      webRef.current?.injectJavaScript(
        `
          (function() {
            window.location.assign(${JSON.stringify(targetUrl)});
          })();
          true;
        `
      );
    },
    [normalizePortalPath]
  );

  const openReceiptCapture = useCallback(() => {
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
  }, [normalizePortalPath]);

  const onRetry = useCallback(() => {
    setHasError(false);
    webRef.current?.reload();
  }, []);

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

  const webUserAgent = useMemo(() => {
    if (Platform.OS === "ios") {
      return `Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile ${APP_USER_AGENT_SUFFIX}`;
    }
    if (Platform.OS === "android") {
      return `Mozilla/5.0 (Linux; Android 14) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Mobile Safari/537.36 ${APP_USER_AGENT_SUFFIX}`;
    }
    return APP_USER_AGENT_SUFFIX;
  }, []);

  return (
    <SafeAreaView style={styles.container}>
      <StatusBar style="dark" />
      {isHydrating ? (
        <View style={styles.errorContainer}>
          <ActivityIndicator size="large" color="#2563eb" />
          <Text style={styles.errorSubtitle}>Подготовка защищенной мобильной сессии...</Text>
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
      ) : !isHydrating ? (
        <View style={styles.webViewWrapper}>
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
            }}
            onError={() => {
              setHasError(true);
              setIsLoading(false);
            }}
          />
          {isLoading ? (
            <View style={styles.loadingOverlay}>
              <ActivityIndicator size="large" color="#2563eb" />
              <Text style={styles.loadingText}>Загружаем SelfMonitor...</Text>
            </View>
          ) : null}
          <View style={styles.actionBar}>
            <Pressable
              accessibilityRole="button"
              onPress={() => navigateInsidePortal("/dashboard")}
              style={styles.actionButton}
            >
              <Text style={styles.actionButtonText}>Главная</Text>
            </Pressable>
            <Pressable
              accessibilityRole="button"
              onPress={() => navigateInsidePortal("/documents")}
              style={styles.actionButton}
            >
              <Text style={styles.actionButtonText}>Документы</Text>
            </Pressable>
            <Pressable accessibilityRole="button" onPress={openReceiptCapture} style={styles.actionButtonPrimary}>
              <Text style={styles.actionButtonTextPrimary}>Скан чека</Text>
            </Pressable>
            <Pressable
              accessibilityRole="button"
              onPress={registerPushNotifications}
              style={styles.actionButton}
            >
              <Text style={styles.actionButtonText}>Push</Text>
            </Pressable>
          </View>
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
  webViewWrapper: {
    flex: 1,
  },
  actionBar: {
    position: "absolute",
    bottom: 12,
    left: 10,
    right: 10,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    backgroundColor: "rgba(15,23,42,0.9)",
    borderRadius: 14,
    paddingHorizontal: 10,
    paddingVertical: 8,
    gap: 8,
  },
  actionButton: {
    borderRadius: 10,
    borderWidth: 1,
    borderColor: "rgba(255,255,255,0.28)",
    paddingHorizontal: 10,
    paddingVertical: 8,
    minWidth: 68,
  },
  actionButtonPrimary: {
    borderRadius: 10,
    backgroundColor: "#2563eb",
    paddingHorizontal: 10,
    paddingVertical: 8,
    minWidth: 86,
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
