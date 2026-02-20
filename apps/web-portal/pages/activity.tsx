import { useEffect, useState } from 'react';
import styles from '../styles/Home.module.css';
import { useTranslation } from '../hooks/useTranslation';

const API_GATEWAY_URL = process.env.NEXT_PUBLIC_API_GATEWAY_URL || 'http://localhost:8000/api';

type ActivityPageProps = {
  token: string;
  user: { email: string };
};

type AuditEvent = {
  id: string;
  action: string;
  timestamp: string;
  details?: Record<string, unknown>;
};

export default function ActivityPage({ token, user }: ActivityPageProps) {
  const [events, setEvents] = useState<AuditEvent[]>([]);
  const [error, setError] = useState('');
  const { t } = useTranslation();

  useEffect(() => {
    const fetchActivity = async () => {
      if (!user.email) {
        return;
      }

      try {
        const response = await fetch(`${API_GATEWAY_URL}/compliance/audit-events`, {
          headers: { Authorization: `Bearer ${token}` },
        });

        if (!response.ok) {
          throw new Error('Failed to fetch activity log');
        }

        const data = await response.json();
        setEvents(data);
      } catch (err: unknown) {
        const details = err instanceof Error ? err.message : 'Failed to fetch activity log';
        setError(details);
      }
    };

    fetchActivity();
  }, [token, user.email]);

  const formatEventDetails = (event: AuditEvent) => {
    const details = event.details || {};
    const provider = typeof details.provider === 'string' ? details.provider : 'unknown';
    const partnerName = typeof details.partner_name === 'string' ? details.partner_name : 'unknown';
    const scopes = Array.isArray(details.scopes)
      ? details.scopes.filter((item): item is string => typeof item === 'string')
      : [];

    switch (event.action) {
      case 'consent.granted':
        return `Consent granted for provider '${provider}' with scopes: ${scopes.join(', ')}`;
      case 'consent.revoked':
        return 'Consent revoked.';
      case 'partner.handoff.initiated':
        return `Handoff initiated to partner '${partnerName}'`;
      default:
        return JSON.stringify(details);
    }
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
