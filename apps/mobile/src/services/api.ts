const API_GATEWAY_URL = process.env.EXPO_PUBLIC_API_GATEWAY_URL || 'http://localhost:8000/api';

type RequestOptions = RequestInit & { token?: string | null };

export async function apiRequest(path: string, options: RequestOptions = {}) {
  const headers = new Headers(options.headers || {});
  if (options.token) {
    headers.set('Authorization', `Bearer ${options.token}`);
  }
  if (!headers.has('Content-Type') && !(options.body instanceof FormData)) {
    headers.set('Content-Type', 'application/json');
  }

  const response = await fetch(`${API_GATEWAY_URL}${path}`, {
    ...options,
    headers,
  });
  return response;
}
