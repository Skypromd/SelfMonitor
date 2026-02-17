import { useCallback, useEffect, useMemo, useState, type FormEvent } from 'react';
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
      await Promise.all([fetchSecurityState(), fetchSecurityEvents(), fetchSecuritySessions()]);
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : 'Failed to load security center.');
    } finally {
      setIsLoading(false);
    }
  }, [fetchSecurityEvents, fetchSecuritySessions, fetchSecurityState]);

  useEffect(() => {
    void reloadSecurityCenter();
  }, [reloadSecurityCenter]);

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
        </div>
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
                <img alt="2FA setup QR" src={twoFactorQrUrl} style={{ maxWidth: 220, width: '100%' }} />
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
