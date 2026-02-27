import * as SecureStore from 'expo-secure-store';

const API_URL = 'http://10.0.2.2:8000/api';

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
