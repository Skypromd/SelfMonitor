import { useEffect, useState, type FormEvent } from 'react';
import { useRouter } from 'next/router';
import { useTranslation } from '../hooks/useTranslation';
import styles from '../styles/Home.module.css';

const ANALYTICS_SERVICE_URL = process.env.NEXT_PUBLIC_ANALYTICS_SERVICE_URL || 'http://localhost:8011';

type DashboardPageProps = {
  token: string;
};

type AdviceResponse = {
  details: string;
  headline: string;
};

type ForecastPoint = {
  balance: number;
  date: string;
};

type TaxEstimateResult = {
  end_date: string;
  estimated_tax_due: number;
  start_date: string;
  total_expenses: number;
  total_income: number;
};

function TaxCalculator({ token }: { token: string }) {
  const [result, setResult] = useState<TaxEstimateResult | null>(null);
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [startDate, setStartDate] = useState('2023-01-01');
  const [endDate, setEndDate] = useState('2023-12-31');

  const handleCalculate = async (event: FormEvent) => {
    event.preventDefault();
    setError('');
    setResult(null);
    setIsLoading(true);
    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_TAX_ENGINE_URL || 'http://localhost:8007'}/calculate`, {
        body: JSON.stringify({ end_date: endDate, jurisdiction: 'UK', start_date: startDate }),
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        method: 'POST',
      });
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.detail || 'Failed to calculate tax');
      }
      setResult(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unexpected error');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className={styles.subContainer}>
      <h2>Tax Estimator (UK)</h2>
      <form onSubmit={handleCalculate}>
        <div className={styles.dateInputs}>
          <input className={styles.input} onChange={(event) => setStartDate(event.target.value)} type="date" value={startDate} />
          <input className={styles.input} onChange={(event) => setEndDate(event.target.value)} type="date" value={endDate} />
        </div>
        <button className={styles.button} disabled={isLoading} type="submit">
          {isLoading ? 'Calculating...' : 'Calculate Tax'}
        </button>
      </form>
      {error && <p className={styles.error}>{error}</p>}
      {result && (
        <div className={styles.resultsContainer}>
          <h3>
            Estimated Tax for {result.start_date} to {result.end_date}
          </h3>
          <div className={styles.resultItem}>
            <span>Total Income:</span> <span className={styles.positive}>£{result.total_income.toFixed(2)}</span>
          </div>
          <div className={styles.resultItem}>
            <span>Deductible Expenses:</span> <span className={styles.negative}>£{result.total_expenses.toFixed(2)}</span>
          </div>
          <div className={styles.resultItemMain}>
            <span>Estimated Tax Due:</span> <span>£{result.estimated_tax_due.toFixed(2)}</span>
          </div>
        </div>
      )}
    </div>
  );
}

function CashFlowPreview({ token }: { token: string }) {
  const [data, setData] = useState<ForecastPoint[]>([]);
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const fetchForecast = async () => {
      setIsLoading(true);
      try {
        const response = await fetch(`${ANALYTICS_SERVICE_URL}/forecast/cash-flow`, {
          body: JSON.stringify({ days_to_forecast: 14 }),
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${token}`,
          },
          method: 'POST',
        });
        if (!response.ok) {
          throw new Error('Failed to fetch cash flow forecast');
        }
        const result = await response.json();
        setData(result.forecast || []);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Unexpected error');
      } finally {
        setIsLoading(false);
      }
    };
    fetchForecast();
  }, [token]);

  const maxAbsBalance = data.reduce((max, point) => Math.max(max, Math.abs(point.balance)), 0) || 1;

  return (
    <div className={styles.subContainer}>
      <h2>Cash Flow Forecast (Next 14 Days)</h2>
      {error && <p className={styles.error}>{error}</p>}
      {isLoading && (
        <div className={styles.skeletonTable}>
          {Array.from({ length: 4 }).map((_, index) => (
            <div className={styles.skeletonRow} key={index}>
              <div className={styles.skeletonCell} />
              <div className={styles.skeletonCell} />
              <div className={styles.skeletonCell} />
            </div>
          ))}
        </div>
      )}
      {!error && !isLoading && data.length === 0 && <p className={styles.emptyState}>No forecast data available yet.</p>}
      {data.length > 0 && (
        <>
          <table className={styles.table}>
            <thead>
              <tr>
                <th>Date</th>
                <th>Projected Balance</th>
                <th>Trend</th>
              </tr>
            </thead>
            <tbody>
              {data.map((point) => {
                const normalizedWidth = Math.max(8, Math.round((Math.abs(point.balance) / maxAbsBalance) * 100));
                return (
                  <tr key={point.date}>
                    <td>{point.date}</td>
                    <td className={point.balance >= 0 ? styles.positive : styles.negative}>£{point.balance.toFixed(2)}</td>
                    <td className={styles.tableTrendCell}>
                      <div className={styles.trendTrack}>
                        <span
                          className={`${styles.trendFill} ${point.balance >= 0 ? styles.trendPositive : styles.trendNegative}`}
                          style={{ width: `${normalizedWidth}%` }}
                        />
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
          <p className={styles.tableCaption}>Spark bars show relative daily balance movement within the current forecast window.</p>
        </>
      )}
    </div>
  );
}

function ActionCenter({ token }: { token: string }) {
  const [advice, setAdvice] = useState<AdviceResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const router = useRouter();

  useEffect(() => {
    const fetchAdvice = async () => {
      setIsLoading(true);
      try {
        const response = await fetch(`${process.env.NEXT_PUBLIC_ADVICE_SERVICE_URL || 'http://localhost:8008'}/generate`, {
          body: JSON.stringify({ topic: 'income_protection' }),
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${token}`,
          },
          method: 'POST',
        });
        if (!response.ok) {
          return;
        }
        setAdvice(await response.json());
      } catch (err) {
        console.error(err);
      } finally {
        setIsLoading(false);
      }
    };
    fetchAdvice();
  }, [token]);

  if (isLoading) {
    return (
      <div className={`${styles.subContainer} ${styles.actionableAdviceCard}`}>
        <div>
          <div className={`${styles.skeletonLine} ${styles.skeletonLineShort}`} />
          <div className={`${styles.skeletonLine} ${styles.skeletonLineLong}`} />
          <div className={`${styles.skeletonLine} ${styles.skeletonLineMedium}`} />
        </div>
        <div>
          <div className={`${styles.skeletonLine} ${styles.skeletonLineMedium}`} />
          <div className={`${styles.skeletonLine} ${styles.skeletonLineLong}`} />
        </div>
      </div>
    );
  }

  if (!advice) {
    return null;
  }

  return (
    <div className={`${styles.subContainer} ${styles.actionableAdviceCard}`}>
      <div className={styles.adviceTextContent}>
        <h3>{advice.headline}</h3>
        <p>{advice.details}</p>
      </div>
      <div className={styles.advicePartnerList}>
        <h4>What&apos;s Next?</h4>
        <p>Explore our marketplace of trusted partners for insurance, accounting, and more.</p>
        <button className={styles.button} onClick={() => router.push('/marketplace')} type="button">
          Explore Partner Services
        </button>
      </div>
    </div>
  );
}

export default function DashboardPage({ token }: DashboardPageProps) {
  const { t } = useTranslation();

  return (
    <div className={styles.dashboard}>
      <h1>{t('dashboard.title')}</h1>
      <p>{t('dashboard.description')}</p>
      <ActionCenter token={token} />
      <CashFlowPreview token={token} />
      <TaxCalculator token={token} />
    </div>
  );
}
