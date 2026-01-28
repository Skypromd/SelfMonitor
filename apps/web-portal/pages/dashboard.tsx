import { useState, FormEvent, useEffect, useMemo } from 'react';
import { useRouter } from 'next/router';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import styles from '../styles/Home.module.css';
import { useTranslation } from '../hooks/useTranslation';

const ANALYTICS_SERVICE_URL = process.env.NEXT_PUBLIC_ANALYTICS_SERVICE_URL || 'http://localhost:8011';
const TAX_ENGINE_URL = process.env.NEXT_PUBLIC_TAX_ENGINE_URL || 'http://localhost:8007';
const TRANSACTIONS_SERVICE_URL = process.env.NEXT_PUBLIC_TRANSACTIONS_SERVICE_URL || 'http://localhost:8002';

type DashboardPageProps = {
  token: string;
};

type Transaction = {
  amount: number;
  category?: string | null;
  tax_category?: string | null;
  business_use_percent?: number | null;
};

function TaxReadiness({ token }: { token: string }) {
  const [score, setScore] = useState<number | null>(null);
  const [stats, setStats] = useState({ total: 0, missingCategories: 0, missingBusinessUse: 0 });
  const [error, setError] = useState('');
  const { t } = useTranslation();

  useEffect(() => {
    const fetchTransactions = async () => {
      try {
        const response = await fetch(`${TRANSACTIONS_SERVICE_URL}/transactions/me`, {
          headers: { 'Authorization': `Bearer ${token}` }
        });
        if (!response.ok) throw new Error('Failed to fetch transactions');
        const data: Transaction[] = await response.json();

        const total = data.length;
        if (total === 0) {
          setStats({ total, missingCategories: 0, missingBusinessUse: 0 });
          setScore(0);
          return;
        }

        const missingCategories = data.filter(item => !item.tax_category && !item.category).length;
        const missingBusinessUse = data.filter(item => item.amount < 0 && (item.business_use_percent == null)).length;
        const categoryScore = (total - missingCategories) / total;
        const businessScore = (total - missingBusinessUse) / total;
        const readiness = Math.round((categoryScore * 0.6 + businessScore * 0.4) * 100);

        setStats({ total, missingCategories, missingBusinessUse });
        setScore(readiness);
      } catch (err: any) {
        setError(err.message);
      }
    };

    fetchTransactions();
  }, [token]);

  const readinessLabel = useMemo(() => {
    if (score === null) return '';
    if (score >= 80) return t('dashboard.readiness_high');
    if (score >= 50) return t('dashboard.readiness_medium');
    return t('dashboard.readiness_low');
  }, [score, t]);

  if (error) return <p className={styles.error}>{error}</p>;
  if (score === null) return <p>{t('dashboard.readiness_loading')}</p>;

  return (
    <div className={styles.subContainer}>
      <div className={styles.readinessHeader}>
        <div>
          <h2>{t('dashboard.readiness_title')}</h2>
          <p>{t('dashboard.readiness_description')}</p>
        </div>
        <span className={styles.readinessBadge}>{readinessLabel}</span>
      </div>
      <p className={styles.readinessScore}>
        {t('dashboard.readiness_score_label')} <strong>{score}%</strong>
      </p>
      <div className={styles.readinessBar}>
        <div className={styles.readinessBarFill} style={{ width: `${score}%` }} />
      </div>
      {stats.total === 0 ? (
        <p className={styles.message}>{t('dashboard.readiness_no_transactions')}</p>
      ) : (
        <>
          <ul className={styles.readinessList}>
            <li>{t('dashboard.readiness_missing_categories')} {stats.missingCategories}</li>
            <li>{t('dashboard.readiness_missing_business_use')} {stats.missingBusinessUse}</li>
          </ul>
          <p className={styles.readinessActionsTitle}>{t('dashboard.readiness_actions_title')}</p>
          <ul className={styles.readinessActions}>
            <li>{t('dashboard.readiness_action_categories')}</li>
            <li>{t('dashboard.readiness_action_business_use')}</li>
          </ul>
        </>
      )}
    </div>
  );
}

function TaxCalculator({ token }: { token: string }) {
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState('');
  const [startDate, setStartDate] = useState('2023-01-01');
  const [endDate, setEndDate] = useState('2023-12-31');
  const { t } = useTranslation();

  const handleCalculate = async (e: FormEvent) => {
    e.preventDefault();
    setError('');
    setResult(null);
    try {
      const response = await fetch(`${TAX_ENGINE_URL}/calculate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
        body: JSON.stringify({ start_date: startDate, end_date: endDate, jurisdiction: 'UK' })
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || 'Failed to calculate tax');
      setResult(data);
    } catch (err: any) {
      setError(err.message);
    }
  };

  return (
    <div className={styles.subContainer}>
      <h2>{t('dashboard.tax_estimator_title')}</h2>
      <form onSubmit={handleCalculate}>
        <div className={styles.dateInputs}>
          <input type="date" value={startDate} onChange={e => setStartDate(e.target.value)} className={styles.input} />
          <input type="date" value={endDate} onChange={e => setEndDate(e.target.value)} className={styles.input} />
        </div>
        <button type="submit" className={styles.button}>{t('dashboard.tax_estimator_button')}</button>
      </form>
      {error && <p className={styles.error}>{error}</p>}
      {result && (
        <div className={styles.resultsContainer}>
          <h3>{t('dashboard.tax_estimator_result_title')} {result.start_date} - {result.end_date}</h3>
          <div className={styles.resultItem}><span>{t('dashboard.total_income_label')}:</span> <span className={styles.positive}>£{result.total_income.toFixed(2)}</span></div>
          <div className={styles.resultItem}><span>{t('dashboard.allowable_expenses_label')}:</span> <span className={styles.negative}>£{result.total_allowable_expenses.toFixed(2)}</span></div>
          <div className={styles.resultItem}><span>{t('dashboard.disallowable_expenses_label')}:</span> <span className={styles.negative}>£{result.total_disallowable_expenses.toFixed(2)}</span></div>
          <div className={styles.resultItem}><span>{t('dashboard.taxable_profit_label')}:</span> <span>£{result.taxable_profit.toFixed(2)}</span></div>
          <div className={styles.resultItem}><span>{t('dashboard.income_tax_due_label')}:</span> <span>£{result.income_tax_due.toFixed(2)}</span></div>
          <div className={styles.resultItem}><span>{t('dashboard.class2_nic_label')}:</span> <span>£{result.class2_nic.toFixed(2)}</span></div>
          <div className={styles.resultItem}><span>{t('dashboard.class4_nic_label')}:</span> <span>£{result.class4_nic.toFixed(2)}</span></div>
          <div className={styles.resultItemMain}><span>{t('dashboard.estimated_tax_due_label')}:</span> <span>£{result.estimated_tax_due.toFixed(2)}</span></div>
        </div>
      )}
    </div>
  );
}

function CashFlowChart({ token }: { token: string }) {
  const [data, setData] = useState([]);
  const [error, setError] = useState('');
  const { t } = useTranslation();

  useEffect(() => {
    const fetchForecast = async () => {
      try {
        const response = await fetch(`${ANALYTICS_SERVICE_URL}/forecast/cash-flow`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
          body: JSON.stringify({ days_to_forecast: 30 })
        });
        if (!response.ok) throw new Error('Failed to fetch cash flow forecast');
        const result = await response.json();
        setData(result.forecast);
      } catch (err: any) {
        setError(err.message);
      }
    };
    fetchForecast();
  }, [token]);

  if (error) return <p className={styles.error}>{error}</p>;
  if (!data.length) return <p>{t('dashboard.cashflow_loading')}</p>;

  return (
    <div className={styles.subContainer}>
      <h2>{t('dashboard.cashflow_title')}</h2>
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
  const [advice, setAdvice] = useState<any>(null);
  const router = useRouter();
  const { t } = useTranslation();

  useEffect(() => {
    const fetchAdvice = async () => {
      try {
        const response = await fetch(`${process.env.NEXT_PUBLIC_ADVICE_SERVICE_URL || 'http://localhost:8008'}/generate`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
          body: JSON.stringify({ topic: 'income_protection' })
        });
        if (!response.ok) return;
        setAdvice(await response.json());
      } catch (err) {
        console.error(err);
      }
    };
    fetchAdvice();
  }, [token]);

  if (!advice) return null;

  return (
    <div className={`${styles.subContainer} ${styles.actionableAdviceCard}`}>
      <div className={styles.adviceTextContent}>
        <h3>{advice.headline}</h3>
        <p>{advice.details}</p>
      </div>
      <div className={styles.advicePartnerList}>
        <h4>{t('dashboard.action_next_title')}</h4>
        <p>{t('dashboard.action_next_description')}</p>
        <button onClick={() => router.push('/marketplace')} className={styles.button}>{t('dashboard.action_next_button')}</button>
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
      <TaxReadiness token={token} />
      <ActionCenter token={token} />
      <CashFlowChart token={token} />
      <TaxCalculator token={token} />
    </div>
  );
}
