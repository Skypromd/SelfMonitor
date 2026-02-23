import { useEffect, useState } from 'react';
import styles from '../styles/Home.module.css';
import { useTranslation } from '../hooks/useTranslation';

const ANALYTICS_SERVICE_URL = process.env.NEXT_PUBLIC_ANALYTICS_SERVICE_URL || 'http://localhost:8011';

type ReportsPageProps = {
  token: string;
};

type Cadence = {
  cadence: string;
  turnover_last_12_months: number;
  threshold: number;
  quarterly_required: boolean;
};

export default function ReportsPage({ token }: ReportsPageProps) {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const [cadence, setCadence] = useState<Cadence | null>(null);
  const [monthlySummary, setMonthlySummary] = useState<any>(null);
  const [quarterlySummary, setQuarterlySummary] = useState<any>(null);
  const [profitLoss, setProfitLoss] = useState<any>(null);
  const [taxYearSummary, setTaxYearSummary] = useState<any>(null);
  const { t } = useTranslation();

  const handleError = (err: any) => {
    if (err?.status === 402) {
      setError(t('reports.pro_required'));
    } else {
      setError(err?.message || t('reports.error_generic'));
    }
  };

  useEffect(() => {
    const fetchCadence = async () => {
      try {
        const response = await fetch(`${ANALYTICS_SERVICE_URL}/reports/reporting-cadence`, {
          headers: { 'Authorization': `Bearer ${token}` }
        });
        if (!response.ok) throw new Error(t('reports.error_generic'));
        const data = await response.json();
        setCadence(data);
      } catch (err: any) {
        setError(err.message);
      }
    };
    fetchCadence();
  }, [token, t]);

  const fetchReport = async (url: string, setter: (data: any) => void) => {
    setError('');
    try {
      const response = await fetch(url, { headers: { 'Authorization': `Bearer ${token}` } });
      if (!response.ok) {
        const err: any = new Error(t('reports.error_generic'));
        err.status = response.status;
        throw err;
      }
      const data = await response.json();
      setter(data);
    } catch (err: any) {
      handleError(err);
    }
  };

  const handleGenerateMortgageReport = async () => {
    setIsLoading(true);
    setError('');
    try {
      const response = await fetch(`${ANALYTICS_SERVICE_URL}/reports/mortgage-readiness`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (!response.ok) {
        const err: any = new Error(t('reports.error_generic'));
        err.status = response.status;
        throw err;
      }

      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `mortgage-readiness-report-${new Date().toISOString().split('T')[0]}.pdf`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
    } catch (err: any) {
      handleError(err);
    } finally {
      setIsLoading(false);
    }
  };

  const handleMonthlySummary = () => {
    const today = new Date();
    const month = today.getMonth() + 1;
    const year = today.getFullYear();
    fetchReport(`${ANALYTICS_SERVICE_URL}/reports/monthly-summary?year=${year}&month=${month}`, setMonthlySummary);
  };

  const handleQuarterlySummary = () => {
    const today = new Date();
    const quarter = Math.floor(today.getMonth() / 3) + 1;
    const year = today.getFullYear();
    fetchReport(`${ANALYTICS_SERVICE_URL}/reports/quarterly-summary?year=${year}&quarter=${quarter}`, setQuarterlySummary);
  };

  const handleProfitLoss = () => {
    const end = new Date();
    const start = new Date(end);
    start.setMonth(start.getMonth() - 3);
    const startDate = start.toISOString().split('T')[0];
    const endDate = end.toISOString().split('T')[0];
    fetchReport(`${ANALYTICS_SERVICE_URL}/reports/profit-loss?start_date=${startDate}&end_date=${endDate}`, setProfitLoss);
  };

  const handleTaxYearSummary = () => {
    fetchReport(`${ANALYTICS_SERVICE_URL}/reports/tax-year-summary`, setTaxYearSummary);
  };

  return (
    <div>
      <h1>{t('nav.reports')}</h1>
      <p>{t('reports.description')}</p>
      {cadence && (
        <div className={styles.subContainer}>
          <h2>{t('reports.cadence_title')}</h2>
          <p>{t('reports.cadence_description')}</p>
          <p>
            <strong>{t('reports.cadence_turnover_label')}:</strong> £{cadence.turnover_last_12_months.toFixed(2)}
          </p>
          <p>
            <strong>{t('reports.cadence_threshold_label')}:</strong> £{cadence.threshold.toFixed(2)}
          </p>
          <p className={cadence.quarterly_required ? styles.error : styles.message}>
            {cadence.quarterly_required ? t('reports.cadence_quarterly_required') : t('reports.cadence_monthly_ok')}
          </p>
        </div>
      )}
      <div className={styles.subContainer}>
        <h2>{t('reports.monthly_title')}</h2>
        <p>{t('reports.monthly_description')}</p>
        <button onClick={handleMonthlySummary} className={styles.button}>{t('reports.monthly_button')}</button>
        {monthlySummary && <pre className={styles.tokenDisplay}>{JSON.stringify(monthlySummary, null, 2)}</pre>}
      </div>
      <div className={styles.subContainer}>
        <h2>{t('reports.quarterly_title')}</h2>
        <p>{t('reports.quarterly_description')}</p>
        <button onClick={handleQuarterlySummary} className={styles.button}>{t('reports.quarterly_button')}</button>
        {quarterlySummary && <pre className={styles.tokenDisplay}>{JSON.stringify(quarterlySummary, null, 2)}</pre>}
      </div>
      <div className={styles.subContainer}>
        <h2>{t('reports.profit_loss_title')}</h2>
        <p>{t('reports.profit_loss_description')}</p>
        <button onClick={handleProfitLoss} className={styles.button}>{t('reports.profit_loss_button')}</button>
        {profitLoss && <pre className={styles.tokenDisplay}>{JSON.stringify(profitLoss, null, 2)}</pre>}
      </div>
      <div className={styles.subContainer}>
        <h2>{t('reports.tax_year_title')}</h2>
        <p>{t('reports.tax_year_description')}</p>
        <button onClick={handleTaxYearSummary} className={styles.button}>{t('reports.tax_year_button')}</button>
        {taxYearSummary && <pre className={styles.tokenDisplay}>{JSON.stringify(taxYearSummary, null, 2)}</pre>}
      </div>
      <div className={styles.subContainer}>
        <h2>{t('reports.mortgage_title')}</h2>
        <p>{t('reports.mortgage_description')}</p>
        <button onClick={handleGenerateMortgageReport} className={styles.button} disabled={isLoading}>
          {isLoading ? t('reports.generating_button') : t('reports.generate_button')}
        </button>
      </div>
      {error && <p className={styles.error}>{error}</p>}
    </div>
  );
}
