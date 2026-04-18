import * as SecureStore from 'expo-secure-store';

const DEFAULT_EMULATOR_API = 'http://10.0.2.2:8000/api';

function stripTrailingSlashes(s: string): string {
  return s.replace(/\/+$/, '');
}

/** Nginx API prefix including `/api` (paths are like `/documents/upload`). */
export const API_URL = stripTrailingSlashes(
  process.env.EXPO_PUBLIC_API_URL ||
    process.env.EXPO_PUBLIC_API_GATEWAY_URL ||
    DEFAULT_EMULATOR_API
);

/** Host origin for `/api/auth/*` when `EXPO_PUBLIC_AUTH_SERVICE_URL` is unset. */
export function getAuthServiceOrigin(): string {
  const explicit = process.env.EXPO_PUBLIC_AUTH_SERVICE_URL?.trim();
  if (explicit) return stripTrailingSlashes(explicit);
  if (API_URL.endsWith('/api')) return stripTrailingSlashes(API_URL.slice(0, -4));
  return stripTrailingSlashes(API_URL);
}

/**
 * REST base for voice-gateway behind nginx (`/api/voice/...`).
 * Set `EXPO_PUBLIC_VOICE_HTTP_URL` (e.g. `http://10.0.2.2:8000/api/voice`) or it is derived from `API_URL`.
 */
export function getVoiceHttpBase(): string {
  const explicit = process.env.EXPO_PUBLIC_VOICE_HTTP_URL?.trim();
  if (explicit) return stripTrailingSlashes(explicit);
  if (API_URL.endsWith('/api')) return stripTrailingSlashes(`${API_URL}/voice`);
  return stripTrailingSlashes(`${API_URL}/api/voice`);
}

/**
 * WebSocket URL for `/ws/voice` (nginx: `/api/voice/ws/voice`).
 * Set `EXPO_PUBLIC_VOICE_WS_URL` to the prefix `ws://host:port/api/voice/ws` (no trailing slash).
 */
export function getVoiceWebSocketUrl(): string {
  const explicit = process.env.EXPO_PUBLIC_VOICE_WS_URL?.trim();
  const prefix = explicit
    ? stripTrailingSlashes(explicit)
    : (() => {
        const origin = getAuthServiceOrigin();
        const wsScheme = origin.startsWith('https') ? 'wss' : 'ws';
        const hostAndPath = origin.replace(/^https?:\/\//i, '');
        return `${wsScheme}://${hostAndPath}/api/voice/ws`;
      })();
  return `${prefix}/voice`;
}

export async function getToken(): Promise<string | null> {
  return await SecureStore.getItemAsync('authToken');
}

export async function setToken(token: string): Promise<void> {
  await SecureStore.setItemAsync('authToken', token);
}

export async function removeToken(): Promise<void> {
  await SecureStore.deleteItemAsync('authToken');
}

export async function apiCall(
  path: string,
  options: RequestInit = {}
): Promise<Response> {
  const token = await getToken();
  const headers: Record<string, string> = {
    ...(options.headers as Record<string, string> || {}),
  };
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  if (!headers['Content-Type'] && !(options.body instanceof FormData)) {
    headers['Content-Type'] = 'application/json';
  }
  return fetch(`${API_URL}${path}`, { ...options, headers });
}
