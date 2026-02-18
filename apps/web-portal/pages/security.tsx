import { useCallback, useEffect, useMemo, useState, type FormEvent } from 'react';
import Image from 'next/image';
import styles from '../styles/Home.module.css';

const AUTH_SERVICE_BASE_URL = process.env.NEXT_PUBLIC_AUTH_SERVICE_URL || 'http://localhost:8000';

type SecurityPageProps = {
  onAuthSessionUpdated?: (accessToken: string, refreshToken?: string | null) => void;
  onLogout?: () => void;
  refreshToken?: string | null;
  token: string;
  userEmail?: string | null;
};

type SecurityState = {
  email: string;
  email_verified: boolean;
  failed_login_attempts: number;
  is_two_factor_enabled: boolean;
  last_login_at: string | null;
  locked_until: string | null;
  max_failed_login_attempts: number;
  password_changed_at: string | null;
};

type SecurityEvent = {
  details: Record<string, unknown>;
  event_id: string;
  event_type: string;
  ip: string | null;
  occurred_at: string;
  user_agent: string | null;
};

type SecurityEventsResponse = {
  items: SecurityEvent[];
  total: number;
};

type SecuritySessionItem = {
  expires_at: string;
  ip: string | null;
  issued_at: string;
  revocation_reason: string | null;
  revoked_at: string | null;
  session_id: string;
  user_agent: string | null;
};

type SecuritySessionsResponse = {
  active_sessions: number;
  items: SecuritySessionItem[];
  total_sessions: number;
};

type EmailVerificationRequestResponse = {
  code_sent: boolean;
  debug_code?: string | null;
  expires_at: string;
  message: string;
};

type TokenPairResponse = {
  access_token: string;
  expires_in_seconds: number;
  refresh_token: string;
  token_type: string;
};

type RiskBadge = {
  hint: string;
  id: string;
  label: string;
  severity: 'healthy' | 'attention' | 'critical';
};

type RealtimeAlert = {
  hint: string;
  id: string;
  label: string;
  severity: 'attention' | 'critical';
};

type AlertDeliveryChannel = {
  detail?: string;
  provider_message_id?: string;
  receipt_at?: string;
  receipt_reason?: string;
  receipt_status?: string;
  status?: string;
};

type AlertDeliveryItem = {
  alert_key?: string;
  channels?: {
    email?: AlertDeliveryChannel;
    push?: AlertDeliveryChannel;
  };
  dispatch_id: string;
  last_receipt_at?: string;
  occurred_at?: string;
  severity?: string;
  status?: string;
  title?: string;
};

type AlertDeliveriesResponse = {
  items: AlertDeliveryItem[];
  total: number;
};

type DeliveryStatusFilter = 'all' | 'failed' | 'delivered' | 'pending';
type DeliveryChannelFilter = 'all' | 'email' | 'push';

const DELIVERY_FILTERS_STORAGE_KEY = 'selfmonitor.security.deliveries.filters.v1';

function formatDateTime(value: string | null): string {
  if (!value) {
    return '—';
  }
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return value;
  }
  return parsed.toLocaleString();
}

function resolveDeliveryStatusLabel(channel: AlertDeliveryChannel | undefined): string {
  if (!channel) {
    return '—';
  }
  const receiptStatus = typeof channel.receipt_status === 'string' ? channel.receipt_status.trim() : '';
  if (receiptStatus) {
    return receiptStatus;
  }
  const baseStatus = typeof channel.status === 'string' ? channel.status.trim() : '';
  return baseStatus || 'pending';
}

function normalizeDeliveryStatus(value: string | undefined): string {
  return (value || '').trim().toLowerCase();
}

function isSuccessfulDeliveryStatus(status: string): boolean {
  return ['sent', 'delivered', 'opened', 'clicked', 'partial_delivery'].includes(status);
}

function isFailedDeliveryStatus(status: string): boolean {
  return ['failed', 'bounced'].includes(status);
}

function isDeliveryStatusFilter(value: unknown): value is DeliveryStatusFilter {
  return value === 'all' || value === 'failed' || value === 'delivered' || value === 'pending';
}

function isDeliveryChannelFilter(value: unknown): value is DeliveryChannelFilter {
  return value === 'all' || value === 'email' || value === 'push';
}

function normalizeDeliveryWindowHours(value: unknown): number {
  const parsed =
    typeof value === 'number'
      ? value
      : Number.parseInt(typeof value === 'string' ? value : '', 10);
  if (parsed === 24 || parsed === 72 || parsed === 168) {
    return parsed;
  }
  return 0;
}

function classifyDeliveryBucket(delivery: AlertDeliveryItem): Exclude<DeliveryStatusFilter, 'all'> {
  const overallStatus = normalizeDeliveryStatus(delivery.status || 'pending');
  const emailStatus = normalizeDeliveryStatus(resolveDeliveryStatusLabel(delivery.channels?.email));
  const pushStatus = normalizeDeliveryStatus(resolveDeliveryStatusLabel(delivery.channels?.push));
  const statuses = [overallStatus, emailStatus, pushStatus];
  const hasSuccess = statuses.some((statusItem) => isSuccessfulDeliveryStatus(statusItem));
  const hasFailure = statuses.some((statusItem) => isFailedDeliveryStatus(statusItem));
  if (overallStatus === 'failed' || (hasFailure && !hasSuccess)) {
    return 'failed';
  }
  if (overallStatus === 'delivered' || overallStatus === 'partial_delivery' || hasSuccess) {
    return 'delivered';
  }
  return 'pending';
}

async function getErrorDetail(response: Response, fallback: string): Promise<string> {
  try {
    const payload = (await response.json()) as { detail?: unknown };
    if (typeof payload.detail === 'string' && payload.detail.trim()) {
      return payload.detail.trim();
    }
    if (Array.isArray(payload.detail) && payload.detail.length > 0) {
      return String(payload.detail[0]);
    }
  } catch {
    // fallback below.
  }
  return fallback;
}

export default function SecurityPage({
  onAuthSessionUpdated,
  onLogout,
  refreshToken,
  token,
  userEmail,
}: SecurityPageProps) {
  const [securityState, setSecurityState] = useState<SecurityState | null>(null);
  const [events, setEvents] = useState<SecurityEvent[]>([]);
  const [deliveries, setDeliveries] = useState<AlertDeliveryItem[]>([]);
  const [sessions, setSessions] = useState<SecuritySessionItem[]>([]);
  const [sessionSummary, setSessionSummary] = useState<{ active: number; total: number }>({
    active: 0,
    total: 0,
  });
  const [verificationCode, setVerificationCode] = useState('');
  const [verificationDebugCode, setVerificationDebugCode] = useState<string | null>(null);
  const [verificationExpiresAt, setVerificationExpiresAt] = useState<string | null>(null);
  const [passwordCurrent, setPasswordCurrent] = useState('');
  const [passwordNext, setPasswordNext] = useState('');
  const [twoFactorVerifyCode, setTwoFactorVerifyCode] = useState('');
  const [twoFactorDisableCode, setTwoFactorDisableCode] = useState('');
  const [twoFactorQrUrl, setTwoFactorQrUrl] = useState<string | null>(null);
  const [includeRevokedSessions, setIncludeRevokedSessions] = useState(false);
  const [deliveryStatusFilter, setDeliveryStatusFilter] = useState<DeliveryStatusFilter>('all');
  const [deliveryChannelFilter, setDeliveryChannelFilter] = useState<DeliveryChannelFilter>('all');
  const [deliveryWindowHours, setDeliveryWindowHours] = useState<number>(0);
  const [isDeliveryFiltersHydrated, setIsDeliveryFiltersHydrated] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [isRefreshingSession, setIsRefreshingSession] = useState(false);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');

  const clearNotices = () => {
    setMessage('');
    setError('');
  };

  const replaceQrUrl = useCallback((nextUrl: string | null) => {
    setTwoFactorQrUrl((previousUrl) => {
      if (previousUrl) {
        URL.revokeObjectURL(previousUrl);
      }
      return nextUrl;
    });
  }, []);

  useEffect(() => {
    return () => {
      if (twoFactorQrUrl) {
        URL.revokeObjectURL(twoFactorQrUrl);
      }
    };
  }, [twoFactorQrUrl]);

  useEffect(() => {
    try {
      const rawValue = window.localStorage.getItem(DELIVERY_FILTERS_STORAGE_KEY);
      if (!rawValue) {
        return;
      }
      const parsed = JSON.parse(rawValue) as {
        channel?: unknown;
        status?: unknown;
        windowHours?: unknown;
      };
      if (isDeliveryStatusFilter(parsed.status)) {
        setDeliveryStatusFilter(parsed.status);
      }
      if (isDeliveryChannelFilter(parsed.channel)) {
        setDeliveryChannelFilter(parsed.channel);
      }
      setDeliveryWindowHours(normalizeDeliveryWindowHours(parsed.windowHours));
    } catch {
      // Keep default filters when localStorage payload is malformed.
    } finally {
      setIsDeliveryFiltersHydrated(true);
    }
  }, []);

  useEffect(() => {
    if (!isDeliveryFiltersHydrated) {
      return;
    }
    try {
      window.localStorage.setItem(
        DELIVERY_FILTERS_STORAGE_KEY,
        JSON.stringify({
          status: deliveryStatusFilter,
          channel: deliveryChannelFilter,
          windowHours: deliveryWindowHours,
        })
      );
    } catch {
      // Persistence is best-effort and should never block security UI.
    }
  }, [deliveryChannelFilter, deliveryStatusFilter, deliveryWindowHours, isDeliveryFiltersHydrated]);

  const fetchSecurityState = useCallback(async () => {
    const response = await fetch(`${AUTH_SERVICE_BASE_URL}/security/state`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!response.ok) {
      throw new Error(await getErrorDetail(response, 'Failed to fetch security state.'));
    }
    const payload = (await response.json()) as SecurityState;
    setSecurityState(payload);
  }, [token]);

  const fetchSecurityEvents = useCallback(async () => {
    const response = await fetch(`${AUTH_SERVICE_BASE_URL}/security/events?limit=25`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!response.ok) {
      throw new Error(await getErrorDetail(response, 'Failed to fetch security events.'));
    }
    const payload = (await response.json()) as SecurityEventsResponse;
    setEvents(Array.isArray(payload.items) ? payload.items : []);
  }, [token]);

  const fetchSecurityAlertDeliveries = useCallback(async () => {
    const response = await fetch(`${AUTH_SERVICE_BASE_URL}/security/alerts/deliveries?limit=25`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!response.ok) {
      throw new Error(await getErrorDetail(response, 'Failed to fetch security alert deliveries.'));
    }
    const payload = (await response.json()) as AlertDeliveriesResponse;
    setDeliveries(Array.isArray(payload.items) ? payload.items : []);
  }, [token]);

  const fetchSecuritySessions = useCallback(async () => {
    const query = includeRevokedSessions ? '?include_revoked=true&limit=80' : '?limit=80';
    const response = await fetch(`${AUTH_SERVICE_BASE_URL}/security/sessions${query}`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!response.ok) {
      throw new Error(await getErrorDetail(response, 'Failed to fetch security sessions.'));
    }
    const payload = (await response.json()) as SecuritySessionsResponse;
    setSessions(Array.isArray(payload.items) ? payload.items : []);
    setSessionSummary({
      active: Number.isFinite(payload.active_sessions) ? payload.active_sessions : 0,
      total: Number.isFinite(payload.total_sessions) ? payload.total_sessions : 0,
    });
  }, [includeRevokedSessions, token]);

  const reloadSecurityCenter = useCallback(async () => {
    clearNotices();
    setIsLoading(true);
    try {
      await Promise.all([
        fetchSecurityState(),
        fetchSecurityEvents(),
        fetchSecurityAlertDeliveries(),
        fetchSecuritySessions(),
      ]);
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : 'Failed to load security center.');
    } finally {
      setIsLoading(false);
    }
  }, [fetchSecurityAlertDeliveries, fetchSecurityEvents, fetchSecuritySessions, fetchSecurityState]);

  useEffect(() => {
    void reloadSecurityCenter();
  }, [reloadSecurityCenter]);

  useEffect(() => {
    const syncSessionsView = async () => {
      try {
        await fetchSecuritySessions();
      } catch (sessionError) {
        setError(sessionError instanceof Error ? sessionError.message : 'Failed to refresh sessions view.');
      }
    };
    void syncSessionsView();
  }, [fetchSecuritySessions]);

  const handleRefreshSession = useCallback(async () => {
    clearNotices();
    if (!refreshToken) {
      setError('No refresh token found. Log in again to restore your session.');
      return;
    }
    setIsRefreshingSession(true);
    try {
      const response = await fetch(`${AUTH_SERVICE_BASE_URL}/token/refresh`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh_token: refreshToken }),
      });
      if (!response.ok) {
        throw new Error(await getErrorDetail(response, 'Failed to refresh auth session.'));
      }
      const payload = (await response.json()) as TokenPairResponse;
      onAuthSessionUpdated?.(payload.access_token, payload.refresh_token);
      setMessage(`Session refreshed (expires in ${Math.round(payload.expires_in_seconds / 60)} minutes).`);
    } catch (refreshError) {
      setError(refreshError instanceof Error ? refreshError.message : 'Failed to refresh auth session.');
    } finally {
      setIsRefreshingSession(false);
    }
  }, [onAuthSessionUpdated, refreshToken]);

  const handleRevokeCurrentRefreshToken = useCallback(async () => {
    clearNotices();
    if (!refreshToken) {
      setError('No refresh token available to revoke.');
      return;
    }
    try {
      const response = await fetch(`${AUTH_SERVICE_BASE_URL}/token/revoke`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ refresh_token: refreshToken }),
      });
      if (!response.ok) {
        throw new Error(await getErrorDetail(response, 'Failed to revoke current refresh token.'));
      }
      onAuthSessionUpdated?.(token, null);
      setMessage('Current refresh token revoked. Re-login is recommended before token expiry.');
      await fetchSecuritySessions();
    } catch (revokeError) {
      setError(revokeError instanceof Error ? revokeError.message : 'Failed to revoke current refresh token.');
    }
  }, [fetchSecuritySessions, onAuthSessionUpdated, refreshToken, token]);

  const handleRequestEmailVerification = useCallback(async () => {
    clearNotices();
    try {
      const response = await fetch(`${AUTH_SERVICE_BASE_URL}/verify-email/request`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!response.ok) {
        throw new Error(await getErrorDetail(response, 'Failed to request email verification.'));
      }
      const payload = (await response.json()) as EmailVerificationRequestResponse;
      setVerificationDebugCode(payload.debug_code || null);
      setVerificationExpiresAt(payload.expires_at || null);
      if (payload.debug_code) {
        setVerificationCode(payload.debug_code);
      }
      setMessage(payload.message || 'Verification code sent.');
      await fetchSecurityState();
      await fetchSecurityEvents();
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : 'Failed to request email verification.');
    }
  }, [fetchSecurityEvents, fetchSecurityState, token]);

  const handleConfirmEmailVerification = useCallback(
    async (event: FormEvent) => {
      event.preventDefault();
      clearNotices();
      if (!verificationCode.trim()) {
        setError('Enter verification code first.');
        return;
      }
      try {
        const response = await fetch(`${AUTH_SERVICE_BASE_URL}/verify-email/confirm`, {
          method: 'POST',
          headers: {
            Authorization: `Bearer ${token}`,
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ code: verificationCode.trim() }),
        });
        if (!response.ok) {
          throw new Error(await getErrorDetail(response, 'Failed to verify email.'));
        }
        setMessage('Email verified successfully.');
        setVerificationCode('');
        setVerificationDebugCode(null);
        setVerificationExpiresAt(null);
        await Promise.all([fetchSecurityState(), fetchSecurityEvents()]);
      } catch (verifyError) {
        setError(verifyError instanceof Error ? verifyError.message : 'Failed to verify email.');
      }
    },
    [fetchSecurityEvents, fetchSecurityState, token, verificationCode]
  );

  const handleStartTwoFactorSetup = useCallback(async () => {
    clearNotices();
    try {
      const response = await fetch(`${AUTH_SERVICE_BASE_URL}/2fa/setup`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!response.ok) {
        throw new Error(await getErrorDetail(response, 'Failed to start 2FA setup.'));
      }
      const qrBlob = await response.blob();
      replaceQrUrl(URL.createObjectURL(qrBlob));
      setMessage('Scan QR in authenticator app, then submit the generated code.');
      await fetchSecurityEvents();
    } catch (setupError) {
      setError(setupError instanceof Error ? setupError.message : 'Failed to start 2FA setup.');
    }
  }, [fetchSecurityEvents, replaceQrUrl, token]);

  const handleVerifyTwoFactor = useCallback(
    async (event: FormEvent) => {
      event.preventDefault();
      clearNotices();
      if (!twoFactorVerifyCode.trim()) {
        setError('Enter authenticator code.');
        return;
      }
      try {
        const response = await fetch(
          `${AUTH_SERVICE_BASE_URL}/2fa/verify?totp_code=${encodeURIComponent(twoFactorVerifyCode.trim())}`,
          {
            method: 'POST',
            headers: { Authorization: `Bearer ${token}` },
          }
        );
        if (!response.ok) {
          throw new Error(await getErrorDetail(response, 'Failed to enable 2FA.'));
        }
        setMessage('2FA enabled. Refresh your auth session to continue sensitive actions.');
        setTwoFactorVerifyCode('');
        replaceQrUrl(null);
        await Promise.all([fetchSecurityState(), fetchSecurityEvents()]);
      } catch (verifyError) {
        setError(verifyError instanceof Error ? verifyError.message : 'Failed to enable 2FA.');
      }
    },
    [fetchSecurityEvents, fetchSecurityState, replaceQrUrl, token, twoFactorVerifyCode]
  );

  const handleDisableTwoFactor = useCallback(
    async (event: FormEvent) => {
      event.preventDefault();
      clearNotices();
      if (!twoFactorDisableCode.trim()) {
        setError('Enter current authenticator code to disable 2FA.');
        return;
      }
      try {
        const response = await fetch(
          `${AUTH_SERVICE_BASE_URL}/2fa/disable?totp_code=${encodeURIComponent(twoFactorDisableCode.trim())}`,
          {
            method: 'DELETE',
            headers: { Authorization: `Bearer ${token}` },
          }
        );
        if (!response.ok) {
          throw new Error(await getErrorDetail(response, 'Failed to disable 2FA.'));
        }
        setMessage('2FA disabled.');
        setTwoFactorDisableCode('');
        await Promise.all([fetchSecurityState(), fetchSecurityEvents()]);
      } catch (disableError) {
        setError(disableError instanceof Error ? disableError.message : 'Failed to disable 2FA.');
      }
    },
    [fetchSecurityEvents, fetchSecurityState, token, twoFactorDisableCode]
  );

  const handleChangePassword = useCallback(
    async (event: FormEvent) => {
      event.preventDefault();
      clearNotices();
      if (!passwordCurrent || !passwordNext) {
        setError('Fill both current and new password.');
        return;
      }
      try {
        const response = await fetch(`${AUTH_SERVICE_BASE_URL}/password/change`, {
          method: 'POST',
          headers: {
            Authorization: `Bearer ${token}`,
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            current_password: passwordCurrent,
            new_password: passwordNext,
          }),
        });
        if (!response.ok) {
          throw new Error(await getErrorDetail(response, 'Failed to change password.'));
        }
        setMessage('Password changed successfully. Sign in again with the new password.');
        setPasswordCurrent('');
        setPasswordNext('');
        onLogout?.();
      } catch (changeError) {
        setError(changeError instanceof Error ? changeError.message : 'Failed to change password.');
      }
    },
    [onLogout, passwordCurrent, passwordNext, token]
  );

  const handleRevokeSession = useCallback(
    async (sessionId: string) => {
      clearNotices();
      try {
        const response = await fetch(`${AUTH_SERVICE_BASE_URL}/security/sessions/${encodeURIComponent(sessionId)}`, {
          method: 'DELETE',
          headers: { Authorization: `Bearer ${token}` },
        });
        if (!response.ok) {
          throw new Error(await getErrorDetail(response, 'Failed to revoke session.'));
        }
        setMessage('Session revoked.');
        await Promise.all([fetchSecuritySessions(), fetchSecurityEvents()]);
      } catch (sessionError) {
        setError(sessionError instanceof Error ? sessionError.message : 'Failed to revoke session.');
      }
    },
    [fetchSecurityEvents, fetchSecuritySessions, token]
  );

  const handleRevokeAllSessions = useCallback(async () => {
    clearNotices();
    try {
      const response = await fetch(`${AUTH_SERVICE_BASE_URL}/security/sessions/revoke-all`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!response.ok) {
        throw new Error(await getErrorDetail(response, 'Failed to revoke sessions.'));
      }
      setMessage('All sessions revoked.');
      onAuthSessionUpdated?.(token, null);
      await Promise.all([fetchSecuritySessions(), fetchSecurityEvents()]);
    } catch (revokeError) {
      setError(revokeError instanceof Error ? revokeError.message : 'Failed to revoke sessions.');
    }
  }, [fetchSecurityEvents, fetchSecuritySessions, onAuthSessionUpdated, token]);

  const handleEmergencyLockdown = useCallback(async () => {
    clearNotices();
    const confirmed = window.confirm(
      'Activate emergency lockdown for 30 minutes? This revokes active sessions and signs you out.'
    );
    if (!confirmed) {
      return;
    }
    try {
      const response = await fetch(`${AUTH_SERVICE_BASE_URL}/security/lockdown`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ lock_minutes: 30 }),
      });
      if (!response.ok) {
        throw new Error(await getErrorDetail(response, 'Failed to activate emergency lockdown.'));
      }
      setMessage('Emergency lockdown activated. Signing out...');
      onLogout?.();
    } catch (lockdownError) {
      setError(lockdownError instanceof Error ? lockdownError.message : 'Failed to activate emergency lockdown.');
    }
  }, [onLogout, token]);

  const stateMetrics = useMemo(
    () => [
      {
        label: 'Email',
        value: securityState?.email_verified ? 'Verified' : 'Not verified',
      },
      {
        label: '2FA',
        value: securityState?.is_two_factor_enabled ? 'Enabled' : 'Disabled',
      },
      {
        label: 'Failed logins',
        value:
          securityState && Number.isFinite(securityState.failed_login_attempts)
            ? `${securityState.failed_login_attempts}/${securityState.max_failed_login_attempts}`
            : '—',
      },
      {
        label: 'Active sessions',
        value: `${sessionSummary.active}/${sessionSummary.total}`,
      },
    ],
    [securityState, sessionSummary.active, sessionSummary.total]
  );

  const riskBadges = useMemo<RiskBadge[]>(() => {
    const badges: RiskBadge[] = [];
    const nowMs = Date.now();
    const recentEvents = events.filter((event) => {
      const timestamp = new Date(event.occurred_at).getTime();
      return Number.isFinite(timestamp) && nowMs - timestamp <= 24 * 60 * 60 * 1000;
    });
    const recentFailedLogins = recentEvents.filter((event) => event.event_type === 'auth.login_failed').length;
    const recentLoginIpSet = new Set(
      recentEvents
        .filter((event) => event.event_type === 'auth.login_succeeded' && typeof event.ip === 'string' && event.ip)
        .map((event) => event.ip as string)
    );
    const recentDeviceSet = new Set(
      recentEvents
        .filter(
          (event) =>
            event.event_type === 'auth.login_succeeded' &&
            typeof event.user_agent === 'string' &&
            event.user_agent.trim().length > 0
        )
        .map((event) => (event.user_agent as string).slice(0, 80))
    );

    if (!securityState?.email_verified) {
      badges.push({
        id: 'email_verification',
        label: 'Email not verified',
        severity: 'attention',
        hint: 'Complete email verification to strengthen account recovery and sensitive operations.',
      });
    }
    if (!securityState?.is_two_factor_enabled) {
      badges.push({
        id: 'two_factor',
        label: '2FA disabled',
        severity: 'attention',
        hint: 'Enable TOTP 2FA to reduce account takeover risk.',
      });
    }
    if (securityState?.locked_until) {
      badges.push({
        id: 'lockout',
        label: 'Account lockout active',
        severity: 'critical',
        hint: `Account is currently locked until ${formatDateTime(securityState.locked_until)}.`,
      });
    }
    if (recentFailedLogins >= 3) {
      badges.push({
        id: 'failed_login_spike',
        label: 'Failed login spike',
        severity: 'critical',
        hint: `${recentFailedLogins} failed login attempts detected in the last 24h.`,
      });
    } else if (recentFailedLogins > 0) {
      badges.push({
        id: 'failed_login_activity',
        label: 'Failed login activity',
        severity: 'attention',
        hint: `${recentFailedLogins} failed login attempt(s) detected in the last 24h.`,
      });
    }
    if (recentLoginIpSet.size > 1) {
      badges.push({
        id: 'new_ip',
        label: 'Multiple recent login IPs',
        severity: 'attention',
        hint: `${recentLoginIpSet.size} distinct IPs were used for recent successful logins.`,
      });
    }
    if (recentDeviceSet.size > 1) {
      badges.push({
        id: 'new_device',
        label: 'Multiple recent device fingerprints',
        severity: 'attention',
        hint: `${recentDeviceSet.size} different user-agent fingerprints were detected recently.`,
      });
    }
    if (sessionSummary.active > 5) {
      badges.push({
        id: 'sessions_high',
        label: 'High active session count',
        severity: 'critical',
        hint: `${sessionSummary.active} active sessions detected. Revoke unknown devices.`,
      });
    } else if (sessionSummary.active > 2) {
      badges.push({
        id: 'sessions_moderate',
        label: 'Multiple active sessions',
        severity: 'attention',
        hint: `${sessionSummary.active} active sessions detected. Review session list.`,
      });
    }
    if (badges.length === 0) {
      badges.push({
        id: 'healthy',
        label: 'No critical risk signals',
        severity: 'healthy',
        hint: 'Current telemetry does not indicate elevated account risk.',
      });
    }
    return badges;
  }, [events, securityState, sessionSummary.active]);

  const realtimeAlerts = useMemo<RealtimeAlert[]>(() => {
    const alerts: RealtimeAlert[] = [];
    const nowMs = Date.now();
    const recentEvents = events.filter((event) => {
      const timestamp = new Date(event.occurred_at).getTime();
      return Number.isFinite(timestamp) && nowMs - timestamp <= 60 * 60 * 1000;
    });
    const failedLoginsLastHour = recentEvents.filter((event) => event.event_type === 'auth.login_failed').length;
    const recentLoginIpSet = new Set(
      recentEvents
        .filter((event) => event.event_type === 'auth.login_succeeded' && typeof event.ip === 'string' && event.ip)
        .map((event) => event.ip as string)
    );
    const recentLoginDeviceSet = new Set(
      recentEvents
        .filter(
          (event) =>
            event.event_type === 'auth.login_succeeded' &&
            typeof event.user_agent === 'string' &&
            event.user_agent.trim().length > 0
        )
        .map((event) => (event.user_agent as string).slice(0, 80))
    );

    if (securityState?.locked_until) {
      alerts.push({
        id: 'lockout_active',
        label: 'Account lockout is active',
        severity: 'critical',
        hint: `Locked until ${formatDateTime(securityState.locked_until)}.`,
      });
    }
    if (failedLoginsLastHour >= 3) {
      alerts.push({
        id: 'failed_logins_critical',
        label: 'Failed login spike in the last hour',
        severity: 'critical',
        hint: `${failedLoginsLastHour} failed login attempts detected in the last 60 minutes.`,
      });
    } else if (failedLoginsLastHour > 0) {
      alerts.push({
        id: 'failed_logins_attention',
        label: 'Failed logins in the last hour',
        severity: 'attention',
        hint: `${failedLoginsLastHour} failed login attempt(s) detected in the last 60 minutes.`,
      });
    }
    if (recentLoginIpSet.size > 1) {
      alerts.push({
        id: 'new_ip_last_hour',
        label: 'Multiple login IPs in the last hour',
        severity: 'attention',
        hint: `${recentLoginIpSet.size} distinct IPs seen in recent successful logins.`,
      });
    }
    if (recentLoginDeviceSet.size > 1) {
      alerts.push({
        id: 'new_device_last_hour',
        label: 'Multiple device fingerprints in the last hour',
        severity: 'attention',
        hint: `${recentLoginDeviceSet.size} user-agent fingerprints seen in recent successful logins.`,
      });
    }
    if (sessionSummary.active > 5) {
      alerts.push({
        id: 'active_sessions_critical',
        label: 'High active session count',
        severity: 'critical',
        hint: `${sessionSummary.active} active sessions currently exist.`,
      });
    }
    return alerts;
  }, [events, securityState, sessionSummary.active]);

  const filteredDeliveries = useMemo(() => {
    const nowMs = Date.now();
    return deliveries.filter((delivery) => {
      const bucket = classifyDeliveryBucket(delivery);
      if (deliveryStatusFilter !== 'all' && bucket !== deliveryStatusFilter) {
        return false;
      }
      const hasEmailChannel = Boolean(delivery.channels?.email);
      const hasPushChannel = Boolean(delivery.channels?.push);
      if (deliveryChannelFilter === 'email' && !hasEmailChannel) {
        return false;
      }
      if (deliveryChannelFilter === 'push' && !hasPushChannel) {
        return false;
      }
      if (deliveryWindowHours > 0) {
        const anchorDate = delivery.occurred_at || delivery.last_receipt_at || null;
        const anchorMs = anchorDate ? new Date(anchorDate).getTime() : Number.NaN;
        if (!Number.isFinite(anchorMs)) {
          return false;
        }
        if (nowMs - anchorMs > deliveryWindowHours * 60 * 60 * 1000) {
          return false;
        }
      }
      return true;
    });
  }, [deliveries, deliveryChannelFilter, deliveryStatusFilter, deliveryWindowHours]);

  const filteredDeliveriesSummary = useMemo(() => {
    return filteredDeliveries.reduce(
      (summary, item) => {
        const bucket = classifyDeliveryBucket(item);
        summary[bucket] += 1;
        return summary;
      },
      { delivered: 0, failed: 0, pending: 0 }
    );
  }, [filteredDeliveries]);

  return (
    <div className={styles.dashboard}>
      <header className={styles.pageHeader}>
        <p className={styles.pageEyebrow}>Account protection</p>
        <h1 className={styles.pageTitle}>Security Center</h1>
        <p className={styles.pageLead}>
          Manage verification, 2FA, password safety, and active sessions from one place.
          {userEmail ? ` Signed in as ${userEmail}.` : ''}
        </p>
      </header>

      {message ? <p className={styles.message}>{message}</p> : null}
      {error ? <p className={styles.error}>{error}</p> : null}

      <section className={styles.subContainer}>
        <h2>Realtime alerts (last 60 minutes)</h2>
        {realtimeAlerts.length === 0 ? (
          <p className={styles.emptyState}>No active high-priority alerts in the last hour.</p>
        ) : (
          <div className={styles.riskBadgeRow}>
            {realtimeAlerts.map((alert) => (
              <article
                className={`${styles.riskBadge} ${
                  alert.severity === 'critical' ? styles.riskBadgeCritical : styles.riskBadgeAttention
                }`}
                key={alert.id}
              >
                <strong>{alert.label}</strong>
                <p>{alert.hint}</p>
              </article>
            ))}
          </div>
        )}
      </section>

      <section className={styles.subContainer}>
        <h2>Security posture</h2>
        <div className={styles.metricsGrid}>
          {stateMetrics.map((metric) => (
            <article className={styles.metricCard} key={metric.label}>
              <h4>{metric.label}</h4>
              <p>{metric.value}</p>
            </article>
          ))}
        </div>
        <p className={styles.tableCaption}>
          Last login: {formatDateTime(securityState?.last_login_at ?? null)} • Password changed:{' '}
          {formatDateTime(securityState?.password_changed_at ?? null)} • Locked until:{' '}
          {formatDateTime(securityState?.locked_until ?? null)}
        </p>
        <div className={styles.riskBadgeRow}>
          {riskBadges.map((risk) => (
            <article
              className={`${styles.riskBadge} ${
                risk.severity === 'critical'
                  ? styles.riskBadgeCritical
                  : risk.severity === 'attention'
                    ? styles.riskBadgeAttention
                    : styles.riskBadgeHealthy
              }`}
              key={risk.id}
            >
              <strong>{risk.label}</strong>
              <p>{risk.hint}</p>
            </article>
          ))}
        </div>
        <div className={styles.adminActionsRow}>
          <button className={styles.button} disabled={isLoading} onClick={() => void reloadSecurityCenter()} type="button">
            {isLoading ? 'Refreshing...' : 'Refresh security data'}
          </button>
          <button
            className={`${styles.button} ${styles.secondaryButton}`}
            disabled={isRefreshingSession}
            onClick={() => void handleRefreshSession()}
            type="button"
          >
            {isRefreshingSession ? 'Refreshing session...' : 'Refresh auth session'}
          </button>
          <button
            className={`${styles.button} ${styles.secondaryButton}`}
            onClick={() => void handleRevokeCurrentRefreshToken()}
            type="button"
          >
            Revoke current refresh token
          </button>
          <button className={`${styles.button} ${styles.dangerButton}`} onClick={() => void handleEmergencyLockdown()} type="button">
            Emergency lock account (30m)
          </button>
        </div>
      </section>

      <section className={styles.subContainer}>
        <h2>Alert delivery receipts</h2>
        <p>Track if security alerts were dispatched and delivered over email/push channels.</p>
        <div className={styles.adminActionsRow}>
          <label className={styles.filterField}>
            <span>Status</span>
            <select
              className={styles.categorySelect}
              onChange={(event) => setDeliveryStatusFilter(event.target.value as DeliveryStatusFilter)}
              value={deliveryStatusFilter}
            >
              <option value="all">All</option>
              <option value="failed">Failed only</option>
              <option value="delivered">Delivered only</option>
              <option value="pending">Pending only</option>
            </select>
          </label>
          <label className={styles.filterField}>
            <span>Channel</span>
            <select
              className={styles.categorySelect}
              onChange={(event) => setDeliveryChannelFilter(event.target.value as DeliveryChannelFilter)}
              value={deliveryChannelFilter}
            >
              <option value="all">All channels</option>
              <option value="email">Email</option>
              <option value="push">Push</option>
            </select>
          </label>
          <label className={styles.filterField}>
            <span>Window</span>
            <select
              className={styles.categorySelect}
              onChange={(event) => setDeliveryWindowHours(Number.parseInt(event.target.value, 10) || 0)}
              value={String(deliveryWindowHours)}
            >
              <option value="0">All time</option>
              <option value="24">Last 24h</option>
              <option value="72">Last 72h</option>
              <option value="168">Last 7d</option>
            </select>
          </label>
          <button
            className={`${styles.button} ${styles.secondaryButton}`}
            onClick={() => void fetchSecurityAlertDeliveries()}
            type="button"
          >
            Reload receipts
          </button>
        </div>
        <p className={styles.tableCaption}>
          Showing {filteredDeliveries.length} of {deliveries.length} deliveries • Failed: {filteredDeliveriesSummary.failed} •
          Delivered: {filteredDeliveriesSummary.delivered} • Pending: {filteredDeliveriesSummary.pending}
        </p>
        {filteredDeliveries.length === 0 ? (
          <p className={styles.emptyState}>No alert deliveries recorded yet.</p>
        ) : (
          <div className={styles.tableResponsive}>
            <table className={styles.table}>
              <thead>
                <tr>
                  <th>Time</th>
                  <th>Alert</th>
                  <th>Overall</th>
                  <th>Email</th>
                  <th>Push</th>
                  <th>Receipt</th>
                </tr>
              </thead>
              <tbody>
                {filteredDeliveries.map((delivery) => {
                  const emailStatus = resolveDeliveryStatusLabel(delivery.channels?.email);
                  const pushStatus = resolveDeliveryStatusLabel(delivery.channels?.push);
                  const overallStatus = delivery.status || 'pending';
                  const emailStatusClass =
                    emailStatus === 'delivered' || emailStatus === 'sent'
                      ? styles.deliveryStatusHealthy
                      : emailStatus === 'failed' || emailStatus === 'bounced'
                        ? styles.deliveryStatusCritical
                        : styles.deliveryStatusAttention;
                  const pushStatusClass =
                    pushStatus === 'delivered' || pushStatus === 'sent'
                      ? styles.deliveryStatusHealthy
                      : pushStatus === 'failed' || pushStatus === 'bounced'
                        ? styles.deliveryStatusCritical
                        : styles.deliveryStatusAttention;
                  const overallStatusClass =
                    overallStatus === 'delivered' || overallStatus === 'dispatched'
                      ? styles.deliveryStatusHealthy
                      : overallStatus === 'failed'
                        ? styles.deliveryStatusCritical
                        : styles.deliveryStatusAttention;
                  return (
                    <tr key={delivery.dispatch_id}>
                      <td>{formatDateTime(delivery.occurred_at || null)}</td>
                      <td>{delivery.title || delivery.alert_key || delivery.dispatch_id.slice(0, 12)}</td>
                      <td>
                        <span className={`${styles.deliveryStatusPill} ${overallStatusClass}`}>{overallStatus}</span>
                      </td>
                      <td>
                        <span className={`${styles.deliveryStatusPill} ${emailStatusClass}`}>{emailStatus}</span>
                      </td>
                      <td>
                        <span className={`${styles.deliveryStatusPill} ${pushStatusClass}`}>{pushStatus}</span>
                      </td>
                      <td>{formatDateTime(delivery.last_receipt_at || null)}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <section className={styles.subContainer}>
        <h2>Email verification</h2>
        <p>
          Verification strengthens account recovery and is required for advanced security actions.
        </p>
        <div className={styles.adminActionsRow}>
          <button className={styles.button} onClick={() => void handleRequestEmailVerification()} type="button">
            Request verification code
          </button>
        </div>
        {verificationExpiresAt ? (
          <p className={styles.tableCaption}>Code expires at: {formatDateTime(verificationExpiresAt)}</p>
        ) : null}
        {verificationDebugCode ? (
          <p className={styles.tableCaption}>Debug code (dev only): {verificationDebugCode}</p>
        ) : null}
        <form onSubmit={handleConfirmEmailVerification}>
          <input
            className={styles.input}
            onChange={(event) => setVerificationCode(event.target.value)}
            placeholder="Verification code"
            type="text"
            value={verificationCode}
          />
          <button className={styles.button} type="submit">
            Confirm email verification
          </button>
        </form>
      </section>

      <section className={styles.subContainer}>
        <h2>Password management</h2>
        <p>Changing password revokes previous sessions and forces re-authentication.</p>
        <form onSubmit={handleChangePassword}>
          <input
            className={styles.input}
            onChange={(event) => setPasswordCurrent(event.target.value)}
            placeholder="Current password"
            type="password"
            value={passwordCurrent}
          />
          <input
            className={styles.input}
            onChange={(event) => setPasswordNext(event.target.value)}
            placeholder="New password"
            type="password"
            value={passwordNext}
          />
          <button className={styles.button} type="submit">
            Change password
          </button>
        </form>
      </section>

      <section className={styles.subContainer}>
        <h2>Two-factor authentication (TOTP)</h2>
        {securityState?.is_two_factor_enabled ? (
          <>
            <p>2FA is enabled. Disabling requires current authenticator code.</p>
            <form onSubmit={handleDisableTwoFactor}>
              <input
                className={styles.input}
                onChange={(event) => setTwoFactorDisableCode(event.target.value)}
                placeholder="Current authenticator code"
                type="text"
                value={twoFactorDisableCode}
              />
              <button className={styles.button} type="submit">
                Disable 2FA
              </button>
            </form>
          </>
        ) : (
          <>
            <p>Enable 2FA to harden login and admin operations.</p>
            <div className={styles.adminActionsRow}>
              <button className={styles.button} onClick={() => void handleStartTwoFactorSetup()} type="button">
                Generate 2FA QR
              </button>
            </div>
            {twoFactorQrUrl ? (
              <div className={styles.resultsContainer}>
                <Image
                  alt="2FA setup QR"
                  height={220}
                  src={twoFactorQrUrl}
                  style={{ height: 'auto', maxWidth: 220, width: '100%' }}
                  unoptimized
                  width={220}
                />
              </div>
            ) : null}
            <form onSubmit={handleVerifyTwoFactor}>
              <input
                className={styles.input}
                onChange={(event) => setTwoFactorVerifyCode(event.target.value)}
                placeholder="Authenticator code"
                type="text"
                value={twoFactorVerifyCode}
              />
              <button className={styles.button} type="submit">
                Verify and enable 2FA
              </button>
            </form>
          </>
        )}
      </section>

      <section className={styles.subContainer}>
        <div className={styles.dashboardHeader}>
          <h2>Security sessions</h2>
          <label className={styles.checkboxPill}>
            <input
              checked={includeRevokedSessions}
              onChange={(event) => setIncludeRevokedSessions(event.target.checked)}
              type="checkbox"
            />
            Include revoked
          </label>
        </div>
        <div className={styles.adminActionsRow}>
          <button className={`${styles.button} ${styles.secondaryButton}`} onClick={() => void fetchSecuritySessions()} type="button">
            Reload sessions
          </button>
          <button className={styles.button} onClick={() => void handleRevokeAllSessions()} type="button">
            Revoke all sessions
          </button>
        </div>
        {sessions.length === 0 ? (
          <p className={styles.emptyState}>No sessions found.</p>
        ) : (
          <div className={styles.tableResponsive}>
            <table className={styles.table}>
              <thead>
                <tr>
                  <th>Session</th>
                  <th>Issued</th>
                  <th>Expires</th>
                  <th>Status</th>
                  <th>IP</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {sessions.map((session) => (
                  <tr key={session.session_id}>
                    <td>{session.session_id.slice(0, 10)}...</td>
                    <td>{formatDateTime(session.issued_at)}</td>
                    <td>{formatDateTime(session.expires_at)}</td>
                    <td>{session.revoked_at ? `revoked (${session.revocation_reason || 'manual'})` : 'active'}</td>
                    <td>{session.ip || '—'}</td>
                    <td>
                      {session.revoked_at ? (
                        <span className={styles.tableCaption}>Already revoked</span>
                      ) : (
                        <button
                          className={styles.tableActionButton}
                          onClick={() => void handleRevokeSession(session.session_id)}
                          type="button"
                        >
                          Revoke
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <section className={styles.subContainer}>
        <h2>Recent security events</h2>
        {events.length === 0 ? (
          <p className={styles.emptyState}>No security events captured yet.</p>
        ) : (
          <div className={styles.tableResponsive}>
            <table className={styles.table}>
              <thead>
                <tr>
                  <th>Time</th>
                  <th>Event</th>
                  <th>IP</th>
                  <th>User-Agent</th>
                  <th>Details</th>
                </tr>
              </thead>
              <tbody>
                {events.map((event) => (
                  <tr key={event.event_id}>
                    <td>{formatDateTime(event.occurred_at)}</td>
                    <td>{event.event_type}</td>
                    <td>{event.ip || '—'}</td>
                    <td>{event.user_agent ? event.user_agent.slice(0, 44) : '—'}</td>
                    <td>{Object.keys(event.details || {}).length > 0 ? JSON.stringify(event.details) : '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}
