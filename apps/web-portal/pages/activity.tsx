import { useEffect, useState } from 'react';
import { useTranslation } from '../hooks/useTranslation';
import styles from '../styles/Home.module.css';

const COMPLIANCE_SERVICE_URL = process.env.NEXT_PUBLIC_COMPLIANCE_SERVICE_URL || 'http://localhost:8003';
const FALLBACK_USER_ID = 'fake-user-123';

type ActivityPageProps = {
  token: string;
  userEmail?: string | null;
};

type AuditEvent = {
  id: string;
  action: string;
  details: Record<string, unknown>;
  timestamp: string;
};

export default function ActivityPage({ token, userEmail }: ActivityPageProps) {
  const [events, setEvents] = useState<AuditEvent[]>([]);
  const [error, setError] = useState('');
  const { t } = useTranslation();

  useEffect(() => {
    const fetchActivity = async () => {
      try {
        const userId = userEmail || FALLBACK_USER_ID;
        const response = await fetch(
          `${COMPLIANCE_SERVICE_URL}/audit-events?user_id=${encodeURIComponent(userId)}`,
          { headers: { Authorization: `Bearer ${token}` } },
        );
        if (!response.ok) {
          throw new Error('Failed to fetch activity log');
        }
        setEvents(await response.json());
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Unexpected error');
      }
    };

    fetchActivity();
  }, [token, userEmail]);

  const formatEventDetails = (event: AuditEvent) => {
    if (event.action === 'consent.granted') {
      const provider = String(event.details.provider ?? 'unknown');
      const scopes = Array.isArray(event.details.scopes) ? event.details.scopes.join(', ') : '';
      return `Consent granted for provider '${provider}' with scopes: ${scopes}`;
    }
    if (event.action === 'consent.revoked') {
      return 'Consent revoked.';
    }
    if (event.action === 'partner.handoff.initiated') {
      return `Handoff initiated to partner '${String(event.details.partner_name ?? 'unknown')}'`;
    }
    return JSON.stringify(event.details);
  };

  return (
    <div>
      <h1>{t('nav.activity')}</h1>
      <p>{t('activity.description')}</p>
      {error && <p className={styles.error}>{error}</p>}
      <div className={styles.subContainer}>
        <table className={styles.table}>
          <thead>
            <tr>
              <th>{t('activity.col_date')}</th>
              <th>{t('activity.col_action')}</th>
              <th>{t('activity.col_details')}</th>
            </tr>
          </thead>
          <tbody>
            {events.map((event) => (
              <tr key={event.id}>
                <td>{new Date(event.timestamp).toLocaleString()}</td>
                <td>{event.action}</td>
                <td>{formatEventDetails(event)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
