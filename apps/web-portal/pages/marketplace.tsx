import { useEffect, useMemo, useState } from 'react';
import { useTranslation } from '../hooks/useTranslation';
import styles from '../styles/Home.module.css';

const PARTNER_REGISTRY_URL = process.env.NEXT_PUBLIC_PARTNER_REGISTRY_URL || 'http://localhost:8009';

type MarketplacePageProps = {
  token: string;
};

type Partner = {
  description: string;
  id: string;
  name: string;
  services_offered: string[];
  website: string;
};

const serviceTitles: Record<string, string> = {
  accounting: 'Accounting & Tax Filing',
  income_protection: 'Insurance',
  investment_management: 'Financial Planning',
  mortgage_advice: 'Mortgage Advice',
  pension_advice: 'Financial Planning',
  tax_filing: 'Accounting & Tax Filing',
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
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Unexpected error');
      }
    };

    fetchPartners();
  }, [token]);

  const groupedByTitle = useMemo(() => {
    const grouped: Record<string, Partner[]> = {};
    const seenByTitle: Record<string, Record<string, boolean>> = {};

    for (const partner of partners) {
      for (const service of partner.services_offered) {
        const title = serviceTitles[service] || 'Other Services';
        if (!grouped[title]) {
          grouped[title] = [];
          seenByTitle[title] = {};
        }
        if (!seenByTitle[title][partner.id]) {
          grouped[title].push(partner);
          seenByTitle[title][partner.id] = true;
        }
      }
    }
    return grouped;
  }, [partners]);

  const handleHandoff = async (partnerId: string, partnerName: string) => {
    setMessage('');
    try {
      const response = await fetch(`${PARTNER_REGISTRY_URL}/partners/${partnerId}/handoff`, {
        headers: { Authorization: `Bearer ${token}` },
        method: 'POST',
      });
      const payload = await response.json();
      if (!response.ok) {
        throw new Error(payload.detail || 'Handoff failed');
      }
      setMessage(payload.message || `Your request has been sent to ${partnerName}. They will be in touch shortly.`);
    } catch (err) {
      setMessage(err instanceof Error ? err.message : 'Unexpected error');
    }
  };

  return (
    <div>
      <h1>{t('nav.marketplace')}</h1>
      <p>{t('marketplace.description')}</p>
      {message && <p className={styles.message}>{message}</p>}
      {error && <p className={styles.error}>{error}</p>}

      {Object.entries(groupedByTitle).map(([title, groupedPartners]) => (
        <div key={title} className={styles.subContainer}>
          <h2>{title}</h2>
          <div className={styles.partnersGrid}>
            {groupedPartners.map((partner) => (
              <div key={partner.id} className={styles.partnerItem}>
                <strong>{partner.name}</strong>
                <p>{partner.description}</p>
                <a href={partner.website} rel="noopener noreferrer" target="_blank">
                  Visit website
                </a>
                <button className={styles.button} onClick={() => handleHandoff(partner.id, partner.name)}>
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
