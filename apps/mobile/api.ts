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
