import { useState, useEffect, ChangeEvent } from 'react';
import styles from '../styles/Home.module.css';
import { useTranslation } from '../hooks/useTranslation';

const API_GATEWAY_URL = process.env.NEXT_PUBLIC_API_GATEWAY_URL || 'http://localhost:8000/api';

type TransactionsPageProps = {
  token: string;
};

function BankConnection({ token, onConnectionComplete }: { token: string, onConnectionComplete: (accountId: string) => void }) {
  const [consentUrl, setConsentUrl] = useState('');
  const [error, setError] = useState('');
  const { t } = useTranslation();

  const handleInitiate = async () => {
    setError('');
    try {
      const response = await fetch(`${API_GATEWAY_URL}/banking/connections/initiate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
        body: JSON.stringify({ provider_id: 'mock_bank', redirect_uri: 'http://localhost:3000' })
      });
      if (!response.ok) throw new Error('Failed to initiate connection');
      const data = await response.json();
      setConsentUrl(data.consent_url);
    } catch (err: any) { setError(err.message); }
  };

  const handleGrant = async () => {
    setError('');
    try {
      const response = await fetch(`${API_GATEWAY_URL}/banking/connections/callback?code=fake_auth_code`);
      if (!response.ok) throw new Error('Failed to complete connection');
      const data = await response.json();
      onConnectionComplete(data.account_id || data.connection_id);
    } catch (err: any) { setError(err.message); }
  };

  return (
    <div className={styles.subContainer} style={{ marginTop: 0 }}>
      <h2>{t('transactions.bank_connections_title')}</h2>
      {!consentUrl ? (
        <button onClick={handleInitiate} className={styles.button}>{t('transactions.connect_button')}</button>
      ) : (
        <div>
          <p>{t('transactions.consent_prompt')}</p>
          <a href="#" onClick={handleGrant} className={styles.link}>{consentUrl}</a>
        </div>
      )}
      {error && <p className={styles.error}>{error}</p>}
    </div>
  );
}

function TransactionsList({ token, accountId }: { token: string, accountId: string }) {
  const [transactions, setTransactions] = useState<any[]>([]);
  const [error, setError] = useState('');
  const { t } = useTranslation();

  const availableCategories = ['groceries', 'transport', 'income', 'food_and_drink', 'subscriptions'];

  useEffect(() => {
    if (!accountId) return;
    const fetchTransactions = async () => {
      setTimeout(async () => {
        try {
          const response = await fetch(`${API_GATEWAY_URL}/transactions/accounts/${accountId}/transactions`, {
            headers: { 'Authorization': `Bearer ${token}` }
          });
          if (!response.ok) throw new Error('Failed to fetch transactions');
          const data = await response.json();
          setTransactions(data);
        } catch (err: any) { setError(err.message); }
      }, 1000);
    };
    fetchTransactions();
  }, [accountId, token]);

  const handleCategoryChange = async (transactionId: string, newCategory: string) => {
    try {
      const response = await fetch(`${API_GATEWAY_URL}/transactions/transactions/${transactionId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
        body: JSON.stringify({ category: newCategory })
      });
      if (!response.ok) throw new Error('Failed to update category');
      setTransactions(transactions.map(t => t.id === transactionId ? { ...t, category: newCategory } : t));
    } catch (err: any) { console.error("Failed to update category:", err); }
  };

  if (!accountId) return null;
  if (!transactions.length && !error) return <p>{t('transactions.loading')}</p>;
  if (error) return <p className={styles.error}>{error}</p>;

  return (
    <div className={styles.subContainer}>
      <h2>{t('transactions.recent_title')}</h2>
      <table className={styles.table}>
        <thead><tr><th>{t('transactions.col_date')}</th><th>{t('transactions.col_description')}</th><th>{t('transactions.col_amount')}</th><th>{t('transactions.col_category')}</th></tr></thead>
        <tbody>
          {transactions.map(t => (
            <tr key={t.id}>
              <td>{t.date}</td>
              <td>{t.description}</td>
              <td className={t.amount > 0 ? styles.positive : styles.negative}>{t.amount.toFixed(2)} {t.currency}</td>
              <td>
                <select value={t.category || ''} onChange={(e) => handleCategoryChange(t.id, e.target.value)} className={styles.categorySelect}>
                  <option value="" disabled>{t('transactions.select_placeholder')}</option>
                  {availableCategories.map(cat => <option key={cat} value={cat}>{cat}</option>)}
                </select>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function CsvImport({
  token,
  accountId,
  onAccountChange,
}: {
  token: string;
  accountId: string;
  onAccountChange: (value: string) => void;
}) {
  const [file, setFile] = useState<File | null>(null);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [isUploading, setIsUploading] = useState(false);
  const { t } = useTranslation();

  const handleUpload = async () => {
    setMessage('');
    setError('');
    if (!accountId) {
      setError(t('transactions.csv_account_error'));
      return;
    }
    if (!file) {
      setError(t('transactions.csv_select_error'));
      return;
    }

    const formData = new FormData();
    formData.append('account_id', accountId);
    formData.append('file', file);

    try {
      setIsUploading(true);
      const response = await fetch(`${API_GATEWAY_URL}/transactions/import/csv`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` },
        body: formData,
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || 'CSV import failed');
      setMessage(
        `${t('transactions.csv_success')} ${data.imported_count}. ${t('transactions.csv_skipped_label')} ${data.skipped_count}.`
      );
      setFile(null);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <div className={styles.subContainer}>
      <h2>{t('transactions.csv_title')}</h2>
      <p>{t('transactions.csv_description')}</p>
      <div style={{ marginBottom: '1rem' }}>
        <div style={{ marginBottom: '0.5rem', color: '#4a5568' }}>{t('transactions.csv_account_label')}</div>
        <input
          type="text"
          value={accountId}
          onChange={(e) => onAccountChange(e.target.value)}
          placeholder={t('transactions.csv_account_placeholder')}
          className={styles.input}
        />
      </div>
      <div className={styles.fileInputContainer}>
        <input type="file" accept=".csv,text/csv" onChange={(e) => setFile(e.target.files?.[0] || null)} />
        <button type="button" className={styles.button} disabled={isUploading} onClick={handleUpload}>
          {isUploading ? t('transactions.csv_uploading') : t('transactions.csv_upload_button')}
        </button>
      </div>
      {message && <p className={styles.message}>{message}</p>}
      {error && <p className={styles.error}>{error}</p>}
    </div>
  );
}

export default function TransactionsPage({ token }: TransactionsPageProps) {
  const [connectedAccountId, setConnectedAccountId] = useState('');
  const [manualAccountId, setManualAccountId] = useState('');
  const { t } = useTranslation();
  const effectiveAccountId = manualAccountId || connectedAccountId;
  return (
    <div>
      <h1>{t('transactions.title')}</h1>
      <p>{t('transactions.description')}</p>
      <BankConnection token={token} onConnectionComplete={setConnectedAccountId} />
      <CsvImport
        token={token}
        accountId={effectiveAccountId}
        onAccountChange={setManualAccountId}
      />
      <TransactionsList token={token} accountId={effectiveAccountId} />
    </div>
  );
}