import AsyncStorage from '@react-native-async-storage/async-storage';

const API_GATEWAY_URL = process.env.EXPO_PUBLIC_API_GATEWAY_URL || 'http://localhost:8000/api';
const CACHE_PREFIX = 'api.cache.v1.';
const DEFAULT_CACHE_TTL_MS = 5 * 60 * 1000;

type RequestOptions = RequestInit & {
  token?: string | null;
  cacheKey?: string;
  cacheTtlMs?: number;
};

type CacheEntry = {
  timestamp: number;
  data: unknown;
};

const loadCache = async (key: string, ttlMs: number) => {
  try {
    const stored = await AsyncStorage.getItem(`${CACHE_PREFIX}${key}`);
    if (!stored) return null;
    const parsed = JSON.parse(stored) as CacheEntry;
    if (!parsed.timestamp || Date.now() - parsed.timestamp > ttlMs) return null;
    return parsed.data;
  } catch {
    return null;
  }
};

const storeCache = async (key: string, data: unknown) => {
  try {
    const payload: CacheEntry = { timestamp: Date.now(), data };
    await AsyncStorage.setItem(`${CACHE_PREFIX}${key}`, JSON.stringify(payload));
  } catch {
    return;
  }
};

const cachedResponse = (data: unknown) => {
  const response = new Response(JSON.stringify(data), {
    status: 200,
    headers: { 'Content-Type': 'application/json' },
  }) as Response & { cached?: boolean };
  response.cached = true;
  return response;
};

const errorResponse = () => new Response(null, { status: 503 });

export async function apiRequest(path: string, options: RequestOptions = {}) {
  const headers = new Headers(options.headers || {});
  if (options.token) {
    headers.set('Authorization', `Bearer ${options.token}`);
  }
  if (!headers.has('Content-Type') && !(options.body instanceof FormData)) {
    headers.set('Content-Type', 'application/json');
  }

  const method = (options.method || 'GET').toUpperCase();
  const cacheKey = options.cacheKey;
  const cacheTtlMs = options.cacheTtlMs ?? DEFAULT_CACHE_TTL_MS;
  const shouldCache = Boolean(cacheKey && method === 'GET');

  try {
    const response = await fetch(`${API_GATEWAY_URL}${path}`, {
      ...options,
      headers,
    });
    if (shouldCache && response.ok) {
      try {
        const snapshot = await response.clone().json();
        await storeCache(cacheKey as string, snapshot);
      } catch {
        return response;
      }
    }
    return response;
  } catch {
    if (shouldCache) {
      const cached = await loadCache(cacheKey as string, cacheTtlMs);
      if (cached !== null) {
        return cachedResponse(cached);
      }
    }
    return errorResponse();
  }
}
