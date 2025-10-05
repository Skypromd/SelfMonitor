import { useState, FormEvent } from 'react';
import styles from '../styles/Home.module.css';
import { useTranslation } from '../hooks/useTranslation';

const TAX_ENGINE_URL = process.env.NEXT_PUBLIC_TAX_ENGINE_URL || 'http://localhost:8007';

type SubmissionPageProps = {
  token: string;
};

export default function SubmissionPage({ token }: SubmissionPageProps) {
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');
  const [startDate, setStartDate] = useState('2023-04-06');
  const [endDate, setEndDate] = useState('2024-04-05');
  const { t } = useTranslation();
import { useState, FormEvent } from 'react';
import styles from '../styles/Home.module.css';
import { useTranslation } from '../hooks/useTranslation';

const TAX_ENGINE_URL = process.env.NEXT_PUBLIC_TAX_ENGINE_URL || 'http://localhost:8007';

type SubmissionPageProps = {
  token: string;
};

export default function SubmissionPage({ token }: SubmissionPageProps) {
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');
  const [startDate, setStartDate] = useState('2023-04-06');
  const [endDate, setEndDate] = useState('2024-04-05');
  const { t } = useTranslation();

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError('');
    setResult(null);
    setMessage('Submitting...');
    try {
      const response = await fetch(`${TAX_ENGINE_URL}/calculate-and-submit`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
        body: JSON.stringify({ start_date: startDate, end_date: endDate, jurisdiction: 'UK' })
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || 'Failed to submit tax return');
      setResult(data);
      setMessage('');
    } catch (err: any) {
        setMessage('');
        setError(err.message);
    }
  };

  return (
    <div>
      <h1>{t('nav.submission')}</h1>
      <p>{t('submission.description')}</p>
      <div className={styles.subContainer}>
        <h2>{t('submission.form_title')}</h2>
        <form onSubmit={handleSubmit}>
          <div className={styles.dateInputs}>
            <input type="date" value={startDate} onChange={e => setStartDate(e.target.value)} className={styles.input} />
            <input type="date" value={endDate} onChange={e => setEndDate(e.target.value)} className={styles.input} />
          </div>
          <button type="submit" className={styles.button}>{t('submission.submit_button')}</button>
        </form>
        {message && <p className={styles.message}>{message}</p>}
        {error && <p className={styles.error}>{error}</p>}
        {result && (
          <div className={styles.resultsContainer}>
            <h3>{t('submission.success_title')}</h3>
            <div className={styles.resultItem}><span>Submission Status:</span> <span>{result.message}</span></div>
            <div className={styles.resultItem}><span>HMRC Submission ID:</span> <span>{result.submission_id}</span></div>
            <p className={styles.message} style={{marginTop: '1rem'}}>
              We've also (simulated) adding a reminder to your calendar for the payment deadline on 31st January.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError('');
    setResult(null);
    setMessage('Submitting...');
    try {
      const response = await fetch(`${TAX_ENGINE_URL}/calculate-and-submit`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
        body: JSON.stringify({ start_date: startDate, end_date: endDate, jurisdiction: 'UK' })
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || 'Failed to submit tax return');
      setResult(data);
      setMessage('');
    } catch (err: any) {
        setMessage('');
        setError(err.message);
    }
  };

  return (
    <div>
      <h1>{t('nav.submission')}</h1>
      <p>{t('submission.description')}</p>
      <div className={styles.subContainer}>
        <h2>{t('submission.form_title')}</h2>
        <form onSubmit={handleSubmit}>
          <div className={styles.dateInputs}>
            <input type="date" value={startDate} onChange={e => setStartDate(e.target.value)} className={styles.input} />
            <input type="date" value={endDate} onChange={e => setEndDate(e.target.value)} className={styles.input} />
          </div>
          <button type="submit" className={styles.button}>{t('submission.submit_button')}</button>
        </form>
        {message && <p className={styles.message}>{message}</p>}
        {error && <p className={styles.error}>{error}</p>}
        {result && (
          <div className={styles.resultsContainer}>
            <h3>{t('submission.success_title')}</h3>
            <div className={styles.resultItem}><span>Submission Status:</span> <span>{result.message}</span></div>
            <div className={styles.resultItem}><span>HMRC Submission ID:</span> <span>{result.submission_id}</span></div>
            <p className={styles.message} style={{marginTop: '1rem'}}>
              We've also (simulated) adding a reminder to your calendar for the payment deadline on 31st January.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
