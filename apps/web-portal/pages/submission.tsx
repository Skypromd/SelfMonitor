import { useState, type FormEvent } from 'react';
import { useTranslation } from '../hooks/useTranslation';
import styles from '../styles/Home.module.css';

const TAX_ENGINE_URL = process.env.NEXT_PUBLIC_TAX_ENGINE_URL || 'http://localhost:8007';

type SubmissionPageProps = {
  token: string;
};

type SubmissionResponse = {
  message: string;
  mtd_obligation?: {
    next_deadline?: string | null;
    reporting_required: boolean;
    tax_year_end: string;
    tax_year_start: string;
  };
  submission_id: string;
};

export default function SubmissionPage({ token }: SubmissionPageProps) {
  const [result, setResult] = useState<SubmissionResponse | null>(null);
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');
  const [startDate, setStartDate] = useState('2023-04-06');
  const [endDate, setEndDate] = useState('2024-04-05');
  const { t } = useTranslation();

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    setError('');
    setResult(null);
    setMessage('Submitting...');

    try {
      const response = await fetch(`${TAX_ENGINE_URL}/calculate-and-submit`, {
        body: JSON.stringify({ end_date: endDate, jurisdiction: 'UK', start_date: startDate }),
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        method: 'POST',
      });
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.detail || 'Failed to submit tax return');
      }
      setResult(data);
      setMessage('');
    } catch (err) {
      setMessage('');
      setError(err instanceof Error ? err.message : 'Unexpected error');
    }
  };

  return (
    <div className={styles.dashboard}>
      <h1>{t('nav.submission')}</h1>
      <p>{t('submission.description')}</p>
      <div className={styles.subContainer}>
        <h2>{t('submission.form_title')}</h2>
        <form onSubmit={handleSubmit}>
          <div className={styles.dateInputs}>
            <input
              className={styles.input}
              onChange={(event) => setStartDate(event.target.value)}
              type="date"
              value={startDate}
            />
            <input
              className={styles.input}
              onChange={(event) => setEndDate(event.target.value)}
              type="date"
              value={endDate}
            />
          </div>
          <button className={styles.button} type="submit">
            {t('submission.submit_button')}
          </button>
        </form>
        {message && <p className={styles.message}>{message}</p>}
        {error && <p className={styles.error}>{error}</p>}
        {result && (
          <div className={styles.resultsContainer}>
            <h3>{t('submission.success_title')}</h3>
            <div className={styles.resultItem}>
              <span>Submission Status:</span> <span>{result.message}</span>
            </div>
            <div className={styles.resultItem}>
              <span>HMRC Submission ID:</span> <span>{result.submission_id}</span>
            </div>
            {result.mtd_obligation && (
              <div className={styles.resultItem}>
                <span>MTD quarterly updates required:</span>
                <span>{result.mtd_obligation.reporting_required ? 'Yes' : 'No'}</span>
              </div>
            )}
            <p className={styles.message} style={{ marginTop: '1rem' }}>
              We also attempted to add a calendar reminder for the payment deadline.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
