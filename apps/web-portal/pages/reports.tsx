import { useState } from 'react';
import { useTranslation } from '../hooks/useTranslation';
import styles from '../styles/Home.module.css';

const ANALYTICS_SERVICE_URL = process.env.NEXT_PUBLIC_ANALYTICS_SERVICE_URL || 'http://localhost:8011';

type ReportsPageProps = {
  token: string;
};

export default function ReportsPage({ token }: ReportsPageProps) {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const { t } = useTranslation();

  const handleGenerateReport = async () => {
    setIsLoading(true);
    setError('');

    try {
      const response = await fetch(`${ANALYTICS_SERVICE_URL}/reports/mortgage-readiness`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!response.ok) {
        throw new Error('Failed to generate report');
      }

      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const anchor = document.createElement('a');
      anchor.href = url;
      anchor.download = `mortgage-readiness-report-${new Date().toISOString().split('T')[0]}.pdf`;
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unexpected error');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div>
      <h1>{t('nav.reports')}</h1>
      <p>{t('reports.description')}</p>
      <div className={styles.subContainer}>
        <h2>{t('reports.mortgage_title')}</h2>
        <p>{t('reports.mortgage_description')}</p>
        <button className={styles.button} disabled={isLoading} onClick={handleGenerateReport}>
          {isLoading ? t('reports.generating_button') : t('reports.generate_button')}
        </button>
        {error && <p className={styles.error}>{error}</p>}
      </div>
    </div>
  );
}
