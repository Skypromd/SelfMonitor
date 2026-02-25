import { FormEvent, useEffect, useState } from 'react';
import { useRouter } from 'next/router';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import styles from '../styles/Home.module.css';
import { useTranslation } from '../hooks/useTranslation';

const API_GATEWAY_URL = process.env.NEXT_PUBLIC_API_GATEWAY_URL || 'http://localhost:8000/api';

type DashboardPageProps = {
  token: string;
};

type ForecastPoint = {
  date: string;
  balance: number;
};

type TaxResult = {
  start_date: string;
  end_date: string;
  total_income: number;
  total_expenses: number;
  estimated_tax_due: number;
};

type AdviceItem = {
  headline: string;
  details: string;
};

function TaxCalculator({ token }: { token: string }) {
  const [result, setResult] = useState<TaxResult | null>(null);
  const [error, setError] = useState('');
  const [startDate, setStartDate] = useState('2023-01-01');
  const [endDate, setEndDate] = useState('2023-12-31');

  const handleCalculate = async (e: FormEvent) => {
    e.preventDefault();
    setError('');
    setResult(null);

    try {
      const response = await fetch(`${API_GATEWAY_URL}/tax/calculate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({ start_date: startDate, end_date: endDate, jurisdiction: 'UK' }),
      });
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.detail || 'Failed to calculate tax');
      }
      setResult(data);
    } catch (err: unknown) {
      const details = err instanceof Error ? err.message : 'Failed to calculate tax';
      setError(details);
    }
  };

  return (
    <div className={styles.subContainer}>
      <h2>Tax Estimator (UK)</h2>
      <form onSubmit={handleCalculate}>
        <div className={styles.dateInputs}>
          <input type="date" value={startDate} onChange={(e) => setStartDate(e.target.value)} className={styles.input} />
          <input type="date" value={endDate} onChange={(e) => setEndDate(e.target.value)} className={styles.input} />
        </div>
        <button type="submit" className={styles.button}>
          Calculate Tax
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

function CashFlowChart({ token }: { token: string }) {
  const [data, setData] = useState<ForecastPoint[]>([]);
  const [error, setError] = useState('');

  useEffect(() => {
    const fetchForecast = async () => {
      try {
        const response = await fetch(`${API_GATEWAY_URL}/analytics/forecast/cash-flow`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
          body: JSON.stringify({ days_to_forecast: 30 }),
        });
        if (!response.ok) {
          throw new Error('Failed to fetch cash flow forecast');
        }
        const result = await response.json();
        setData(result.forecast);
      } catch (err: unknown) {
        const details = err instanceof Error ? err.message : 'Failed to fetch cash flow forecast';
        setError(details);
      }
    };

    fetchForecast();
  }, [token]);

  if (error) {
    return <p className={styles.error}>{error}</p>;
  }
  if (!data.length) {
    return <p>Generating forecast...</p>;
  }

  return (
    <div className={styles.subContainer}>
      <h2>Cash Flow Forecast (Next 30 Days)</h2>
      <ResponsiveContainer width="100%" height={300}>
        <LineChart data={data}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="date" />
          <YAxis />
          <Tooltip />
          <Legend />
          <Line type="monotone" dataKey="balance" stroke="#8884d8" activeDot={{ r: 8 }} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

function ActionCenter({ token }: { token: string }) {
  const [advice, setAdvice] = useState<AdviceItem | null>(null);
  const router = useRouter();

  useEffect(() => {
    const fetchAdvice = async () => {
      try {
        const response = await fetch(`${API_GATEWAY_URL}/advice/generate`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
          body: JSON.stringify({ topic: 'income_protection' }),
        });
        if (!response.ok) {
          return;
        }
        setAdvice(await response.json());
      } catch (err) {
        console.error(err);
      }
    };

    fetchAdvice();
  }, [token]);

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
        <p>Explore our marketplace of trusted partners to get help with insurance, accounting, and more.</p>
        <button onClick={() => router.push('/marketplace')} className={styles.button}>
          Explore Partner Services
        </button>
      </div>
    </div>
  );
}

export default function DashboardPage({ token }: DashboardPageProps) {
  const { t } = useTranslation();

  return (
    <div>
      <h1>{t('dashboard.title')}</h1>
      <p>{t('dashboard.description')}</p>
      <ActionCenter token={token} />
      <CashFlowChart token={token} />
      <TaxCalculator token={token} />
    </div>
  );
}
