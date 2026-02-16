import NetInfo from "@react-native-community/netinfo";
import { StatusBar } from "expo-status-bar";
import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  ActivityIndicator,
  BackHandler,
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

export default function App(): React.JSX.Element {
  const webRef = useRef<WebView>(null);
  const [isConnected, setIsConnected] = useState(true);
  const [canGoBack, setCanGoBack] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [hasError, setHasError] = useState(false);

  useEffect(() => {
    const subscription = NetInfo.addEventListener((state) => {
      setIsConnected(Boolean(state.isConnected));
    });
    return () => subscription();
  }, []);

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

  const onRetry = useCallback(() => {
    setHasError(false);
    webRef.current?.reload();
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
      {!isConnected ? (
        <View style={styles.offlineBanner}>
          <Text style={styles.offlineBannerText}>
            Нет сети. Проверьте подключение и повторите.
          </Text>
        </View>
      ) : null}
      {hasError ? (
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
      ) : (
        <View style={styles.webViewWrapper}>
          <WebView
            ref={webRef}
            source={{ uri: WEB_PORTAL_URL }}
            userAgent={webUserAgent}
            startInLoadingState
            pullToRefreshEnabled
            setSupportMultipleWindows={false}
            sharedCookiesEnabled
            thirdPartyCookiesEnabled
            javaScriptEnabled
            domStorageEnabled
            allowsBackForwardNavigationGestures
            onLoadStart={() => {
              setIsLoading(true);
              setHasError(false);
            }}
            onLoadEnd={() => setIsLoading(false)}
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
        </View>
      )}
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
