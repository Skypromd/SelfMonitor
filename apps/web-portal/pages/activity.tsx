import { useState, useEffect } from 'react';
import styles from '../styles/Home.module.css';
import { useTranslation } from '../hooks/useTranslation';

const COMPLIANCE_SERVICE_URL = process.env.NEXT_PUBLIC_COMPLIANCE_SERVICE_URL || 'http://localhost:8003';

type ActivityPageProps = {
  token: string;
  user: { email: string };
};

export default function ActivityPage({ token, user }: ActivityPageProps) {
  const [events, setEvents] = useState<any[]>([]);
  const [error, setError] = useState('');
  const { t } = useTranslation();

  useEffect(() => {
    const fetchActivity = async () => {
      try {
        // The compliance service endpoint is protected, but our fake_auth_check
        // on other services doesn't use the token. Here, we'd pass a real token.
        const response = await fetch(`${COMPLIANCE_SERVICE_URL}/audit-events?user_id=${user.email}`, {
          headers: { 'Authorization': `Bearer ${token}` }
        });
        if (!response.ok) throw new Error('Failed to fetch activity log');
        const data = await response.json();
        setEvents(data);
      } catch (err: any) {
        setError(err.message);
      }
    };
    fetchActivity();
  }, [token, user.email]);
import { useState, useEffect } from 'react';
import styles from '../styles/Home.module.css';
import { useTranslation } from '../hooks/useTranslation';

const COMPLIANCE_SERVICE_URL = process.env.NEXT_PUBLIC_COMPLIANCE_SERVICE_URL || 'http://localhost:8003';

type ActivityPageProps = {
  token: string;
  user: { email: string };
};

export default function ActivityPage({ token, user }: ActivityPageProps) {
  const [events, setEvents] = useState<any[]>([]);
  const [error, setError] = useState('');
  const { t } = useTranslation();

  useEffect(() => {
    const fetchActivity = async () => {
      try {
        // The compliance service endpoint is protected, but our fake_auth_check
        // on other services doesn't use the token. Here, we'd pass a real token.
        const response = await fetch(`${COMPLIANCE_SERVICE_URL}/audit-events?user_id=${user.email}`, {
          headers: { 'Authorization': `Bearer ${token}` }
        });
        if (!response.ok) throw new Error('Failed to fetch activity log');
        const data = await response.json();
        setEvents(data);
      } catch (err: any) {
        setError(err.message);
      }
    };
    fetchActivity();
  }, [token, user.email]);

  const formatEventDetails = (event: any) => {
    switch (event.action) {
      case 'consent.granted':
        return `Consent granted for provider '${event.details.provider}' with scopes: ${event.details.scopes.join(', ')}`;
      case 'consent.revoked':
        return `Consent revoked.`;
      case 'partner.handoff.initiated':
        return `Handoff initiated to partner '${event.details.partner_name}'`;
      default:
        return JSON.stringify(event.details);
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
            {events.map(event => (
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
  const formatEventDetails = (event: any) => {
    switch (event.action) {
      case 'consent.granted':
        return `Consent granted for provider '${event.details.provider}' with scopes: ${event.details.scopes.join(', ')}`;
      case 'consent.revoked':
        return `Consent revoked.`;
      case 'partner.handoff.initiated':
        return `Handoff initiated to partner '${event.details.partner_name}'`;
      default:
        return JSON.stringify(event.details);
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
            {events.map(event => (
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
