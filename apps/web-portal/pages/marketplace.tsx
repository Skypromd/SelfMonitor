import { useEffect, useMemo, useState } from 'react';
import styles from '../styles/Home.module.css';
import { useTranslation } from '../hooks/useTranslation';

const PARTNER_REGISTRY_URL = process.env.NEXT_PUBLIC_PARTNER_REGISTRY_URL || 'http://localhost:8009';

type MarketplacePageProps = {
  token: string;
};

type Partner = {
  id: string;
  name: string;
  description: string;
  services_offered: string[];
};

export default function MarketplacePage({ token }: MarketplacePageProps) {
  const [partners, setPartners] = useState<Partner[]>([]);
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');
  const { t } = useTranslation();

  useEffect(() => {
    const fetchPartners = async () => {
      try {
        const response = await fetch(`${PARTNER_REGISTRY_URL}/partners`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (!response.ok) {
          throw new Error('Failed to fetch partners');
        }
        setPartners(await response.json());
      } catch (err: unknown) {
        const details = err instanceof Error ? err.message : 'Failed to fetch partners';
        setError(details);
      }
    };

    fetchPartners();
  }, [token]);

  const groupedPartners = useMemo(() => {
    return partners.reduce((acc, partner) => {
      partner.services_offered.forEach((service) => {
        if (!acc[service]) {
          acc[service] = [];
        }
        acc[service].push(partner);
      });
      return acc;
    }, {} as Record<string, Partner[]>);
  }, [partners]);

  const handleHandoff = async (partnerId: string, partnerName: string) => {
    setMessage('');
    try {
      const response = await fetch(`${PARTNER_REGISTRY_URL}/partners/${partnerId}/handoff`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!response.ok) {
        throw new Error('Handoff failed');
      }
      setMessage(`Your request has been sent to ${partnerName}. They will be in touch shortly.`);
    } catch (err: unknown) {
      const details = err instanceof Error ? err.message : 'Handoff failed';
      setMessage(details);
    }
  };

  const serviceTitles: Record<string, string> = {
    accounting: 'Accounting & Tax Filing',
    tax_filing: 'Accounting & Tax Filing',
    income_protection: 'Insurance',
    mortgage_advice: 'Mortgage Advice',
    pension_advice: 'Financial Planning',
    investment_management: 'Financial Planning',
  };

  const groupedByTitle = useMemo(() => {
    return Object.entries(groupedPartners).reduce((acc, [service, grouped]) => {
      const title = serviceTitles[service] || 'Other Services';
      if (!acc[title]) {
        acc[title] = [];
      }
      acc[title] = [...new Set([...acc[title], ...grouped])];
      return acc;
    }, {} as Record<string, Partner[]>);
  }, [groupedPartners]);

  return (
    <div>
      <h1>{t('nav.marketplace')}</h1>
      <p>{t('marketplace.description')}</p>
      {message && <p className={styles.message}>{message}</p>}
      {error && <p className={styles.error}>{error}</p>}

      {Object.entries(groupedByTitle).map(([title, grouped]) => (
        <div key={title} className={styles.subContainer}>
          <h2>{title}</h2>
          <div className={styles.partnersGrid}>
            {grouped.map((partner) => (
              <div key={partner.id} className={styles.partnerItem}>
                <strong>{partner.name}</strong>
                <p>{partner.description}</p>
                <button onClick={() => handleHandoff(partner.id, partner.name)} className={styles.button}>
                  Request Contact
                </button>
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}
