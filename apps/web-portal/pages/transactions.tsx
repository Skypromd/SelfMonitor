import { useEffect, useState } from 'react';
import styles from '../styles/Home.module.css';

const API_GATEWAY_URL = process.env.NEXT_PUBLIC_API_GATEWAY_URL || 'http://localhost:8000/api';

type TransactionsPageProps = {
  token: string;
};

type TransactionRecord = {
  amount: number;
  category?: string;
  currency: string;
  date: string;
  description: string;
  id: string;
};

function BankConnection({ token, onConnectionComplete }: { token: string, onConnectionComplete: (accountId: string) => void }) {
  const [consentUrl, setConsentUrl] = useState('');
  const [error, setError] = useState('');
  const [isConnecting, setIsConnecting] = useState(false);
  const [isGranting, setIsGranting] = useState(false);

  const handleInitiate = async () => {
    setError('');
    setIsConnecting(true);
    try {
      const response = await fetch(`${API_GATEWAY_URL}/banking/connections/initiate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
        body: JSON.stringify({ provider_id: 'mock_bank', redirect_uri: 'http://localhost:3000' })
      });
      if (!response.ok) throw new Error('Failed to initiate connection');
      const data = await response.json();
      setConsentUrl(data.consent_url);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unexpected error');
    } finally {
      setIsConnecting(false);
    }
  };

  const handleGrant = async () => {
    setError('');
    setIsGranting(true);
    try {
      const response = await fetch(`${API_GATEWAY_URL}/banking/connections/callback?code=fake_auth_code`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (!response.ok) throw new Error('Failed to complete connection');
      const data = await response.json();
      onConnectionComplete(data.connection_id);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unexpected error');
    } finally {
      setIsGranting(false);
    }
  };

  return (
    <div className={styles.subContainer}>
      <h2>Bank Connections</h2>
      {!consentUrl ? (
        <button onClick={handleInitiate} className={styles.button} disabled={isConnecting} type="button">
          {isConnecting ? 'Starting connection...' : 'Connect a Bank Account'}
        </button>
      ) : (
        <div>
          <p>Click the link to grant access at your bank:</p>
          <button className={styles.inlineLinkButton} disabled={isGranting} onClick={handleGrant} type="button">
            {consentUrl}
          </button>
        </div>
      )}
      {error && <p className={styles.error}>{error}</p>}
    </div>
  );
}

function TransactionsList({ token, accountId }: { token: string, accountId: string }) {
  const [transactions, setTransactions] = useState<TransactionRecord[]>([]);
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const availableCategories = ['groceries', 'transport', 'income', 'food_and_drink', 'subscriptions'];

  useEffect(() => {
    if (!accountId) return;
    setIsLoading(true);
    setError('');
    const timeoutId = window.setTimeout(async () => {
      try {
        const response = await fetch(`${API_GATEWAY_URL}/transactions/accounts/${accountId}/transactions`, {
          headers: { 'Authorization': `Bearer ${token}` }
        });
        if (!response.ok) throw new Error('Failed to fetch transactions');
        const data = await response.json();
        setTransactions(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Unexpected error');
      } finally {
        setIsLoading(false);
      }
    }, 1000);

    return () => {
      window.clearTimeout(timeoutId);
    };
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
    } catch (err) {
      console.error('Failed to update category:', err);
    }
  };

  if (!accountId) return null;
  if (isLoading) {
    return (
      <div className={styles.subContainer}>
        <h2>Recent Transactions</h2>
        <div className={styles.skeletonTable}>
          {Array.from({ length: 6 }).map((_, index) => (
            <div className={styles.skeletonRow} key={index}>
              <div className={styles.skeletonCell} />
              <div className={styles.skeletonCell} />
              <div className={styles.skeletonCell} />
            </div>
          ))}
        </div>
      </div>
    );
  }
  if (error) return <p className={styles.error}>{error}</p>;
  if (!transactions.length) {
    return (
      <div className={styles.subContainer}>
        <h2>Recent Transactions</h2>
        <p className={styles.emptyState}>No transactions available for this connection yet.</p>
      </div>
    );
  }

  return (
    <div className={styles.subContainer}>
      <h2>Recent Transactions</h2>
      <table className={styles.table}>
        <thead><tr><th>Date</th><th>Description</th><th>Amount</th><th>Category</th></tr></thead>
        <tbody>
          {transactions.map(t => (
            <tr key={t.id}>
              <td>{t.date}</td>
              <td>{t.description}</td>
              <td className={t.amount > 0 ? styles.positive : styles.negative}>{t.amount.toFixed(2)} {t.currency}</td>
              <td>
                <select value={t.category || ''} onChange={(e) => handleCategoryChange(t.id, e.target.value)} className={styles.categorySelect}>
                  <option value="" disabled>Select...</option>
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

export default function TransactionsPage({ token }: TransactionsPageProps) {
    const [connectedAccountId, setConnectedAccountId] = useState('');
    return (
        <div className={styles.dashboard}>
            <h1>Transactions</h1>
            <p>Connect your bank account to import and categorize your transactions.</p>
            <BankConnection token={token} onConnectionComplete={setConnectedAccountId} />
            <TransactionsList token={token} accountId={connectedAccountId} />
        </div>
    );
}