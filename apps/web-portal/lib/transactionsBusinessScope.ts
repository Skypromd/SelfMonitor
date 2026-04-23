import { useCallback, useEffect, useMemo, useState } from 'react';

export type UserBusinessRow = {
  id: string;
  user_id: string;
  display_name: string;
  created_at: string;
};

export function jwtSubFromAccessToken(token: string): string {
  try {
    const part = token.split('.')[1];
    if (!part) return '';
    const b64 = part.replace(/-/g, '+').replace(/_/g, '/');
    const pad = b64.length % 4 ? '='.repeat(4 - (b64.length % 4)) : '';
    return (JSON.parse(atob(b64 + pad)) as { sub?: string }).sub ?? '';
  } catch {
    return '';
  }
}

export function txActiveBusinessStorageKey(sub: string): string {
  return `mynettax.txActiveBusiness.${sub}`;
}

export function transactionsBearerHeaders(
  token: string,
  businessId: string | null,
  extra?: Record<string, string>,
): Record<string, string> {
  const headers: Record<string, string> = {
    Authorization: `Bearer ${token}`,
    ...(extra ?? {}),
  };
  if (businessId) headers['X-Business-Id'] = businessId;
  return headers;
}

export function useTransactionsBusinessScope(token: string, transactionsBaseUrl: string) {
  const base = transactionsBaseUrl.replace(/\/$/, '');
  const userSub = useMemo(() => jwtSubFromAccessToken(token), [token]);
  const [businesses, setBusinesses] = useState<UserBusinessRow[]>([]);
  const [loadError, setLoadError] = useState('');
  const [selectedBusinessId, setSelectedBusinessIdState] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      setLoadError('');
      try {
        const res = await fetch(`${base}/businesses`, {
          headers: transactionsBearerHeaders(token, null),
        });
        if (!res.ok) {
          const j = (await res.json().catch(() => ({}))) as { detail?: string };
          throw new Error(j.detail || 'Failed to load businesses');
        }
        const rows = (await res.json()) as UserBusinessRow[];
        if (cancelled) return;
        setBusinesses(rows);
        const key = userSub ? txActiveBusinessStorageKey(userSub) : '';
        const stored = key && typeof window !== 'undefined' ? window.localStorage.getItem(key) : null;
        const ids = new Set(rows.map((r) => r.id));
        const initial = stored && ids.has(stored) ? stored : rows[0]?.id ?? null;
        setSelectedBusinessIdState(initial);
      } catch (e) {
        if (!cancelled) {
          setLoadError(e instanceof Error ? e.message : 'Failed to load businesses');
          setBusinesses([]);
          setSelectedBusinessIdState(null);
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [base, token, userSub]);

  const setSelectedBusinessId = useCallback(
    (id: string) => {
      setSelectedBusinessIdState(id);
      if (typeof window !== 'undefined' && userSub) {
        window.localStorage.setItem(txActiveBusinessStorageKey(userSub), id);
      }
    },
    [userSub],
  );

  return {
    businesses,
    loadError,
    selectedBusinessId,
    setSelectedBusinessId,
    userSub,
  };
}
