import { useCallback, useEffect, useState } from 'react';
import styles from '../styles/Home.module.css';

const API_GATEWAY_URL = process.env.NEXT_PUBLIC_API_GATEWAY_URL || 'http://localhost:8000/api';

type Transaction = {
  id: string;
  date: string;
  description: string;
  amount: number;
  currency: string;
  category?: string;
};

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
  ignored_candidate_ids?: string[] | null;
  reconciliation_status?: string | null;
};

type ReceiptDraftCandidate = {
  account_id: string;
  amount: number;
  confidence_score: number;
  currency: string;
  date: string;
  description: string;
  ignored: boolean;
  provider_transaction_id: string;
  transaction_id: string;
};

type UnmatchedReceiptDraftItem = {
  candidates: ReceiptDraftCandidate[];
  draft_transaction: TransactionRecord;
};

type UnmatchedReceiptDraftsResponse = {
  items: UnmatchedReceiptDraftItem[];
  total: number;
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

function ReceiptDraftManualMatching({ token }: { token: string }) {
  const [rows, setRows] = useState<UnmatchedReceiptDraftItem[]>([]);
  const [total, setTotal] = useState(0);
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [activeActionKey, setActiveActionKey] = useState('');
  const [searchProviderTransactionId, setSearchProviderTransactionId] = useState('');
  const [searchAmount, setSearchAmount] = useState('');
  const [searchDate, setSearchDate] = useState('');
  const [includeIgnoredDrafts, setIncludeIgnoredDrafts] = useState(false);

  const loadUnmatchedDrafts = useCallback(async () => {
    setIsLoading(true);
    setError('');
    try {
      const params = new URLSearchParams({
        limit: '25',
        candidate_limit: '5',
        include_ignored: includeIgnoredDrafts ? 'true' : 'false',
      });
      if (searchProviderTransactionId) {
        params.set('search_provider_transaction_id', searchProviderTransactionId);
      }
      if (searchAmount) {
        params.set('search_amount', searchAmount);
      }
      if (searchDate) {
        params.set('search_date', searchDate);
      }
      const response = await fetch(`${API_GATEWAY_URL}/transactions/transactions/receipt-drafts/unmatched?${params.toString()}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!response.ok) throw new Error('Failed to load unmatched receipt drafts');
      const data: UnmatchedReceiptDraftsResponse = await response.json();
      setRows(data.items);
      setTotal(data.total);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unexpected error');
    } finally {
      setIsLoading(false);
    }
  }, [includeIgnoredDrafts, searchAmount, searchDate, searchProviderTransactionId, token]);

  useEffect(() => {
    void loadUnmatchedDrafts();
  }, [loadUnmatchedDrafts]);

  const handleMatch = async (draftId: string, targetId: string) => {
    const actionKey = `${draftId}:${targetId}`;
    setActiveActionKey(actionKey);
    setError('');
    setMessage('');
    try {
      const response = await fetch(`${API_GATEWAY_URL}/transactions/transactions/receipt-drafts/${draftId}/reconcile`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ target_transaction_id: targetId }),
      });
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.detail || 'Failed to reconcile draft transaction');
      setMessage(`Draft ${payload.reconciled_transaction.id} matched successfully.`);
      await loadUnmatchedDrafts();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unexpected error');
    } finally {
      setActiveActionKey('');
    }
  };

  const handleIgnoreCandidate = async (draftId: string, targetId: string) => {
    const actionKey = `ignore-candidate:${draftId}:${targetId}`;
    setActiveActionKey(actionKey);
    setError('');
    setMessage('');
    try {
      const response = await fetch(`${API_GATEWAY_URL}/transactions/transactions/receipt-drafts/${draftId}/ignore-candidate`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ target_transaction_id: targetId }),
      });
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.detail || 'Failed to ignore candidate');
      setMessage(`Candidate ignored for draft ${payload.draft_transaction.id}.`);
      await loadUnmatchedDrafts();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unexpected error');
    } finally {
      setActiveActionKey('');
    }
  };

  const handleDraftState = async (draftId: string, action: 'ignore' | 'reopen') => {
    const actionKey = `${action}:${draftId}`;
    setActiveActionKey(actionKey);
    setError('');
    setMessage('');
    try {
      const response = await fetch(`${API_GATEWAY_URL}/transactions/transactions/receipt-drafts/${draftId}/${action}`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.detail || `Failed to ${action} draft`);
      setMessage(`Draft ${payload.draft_transaction.id} ${action === 'ignore' ? 'ignored' : 'reopened'}.`);
      await loadUnmatchedDrafts();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unexpected error');
    } finally {
      setActiveActionKey('');
    }
  };

  return (
    <div className={styles.subContainer}>
      <h2>Manual Receipt Matching</h2>
      <p>Unmatched receipt drafts: {total}</p>
      <div className={styles.adminFiltersGrid}>
        <label className={styles.filterField}>
          <span>Provider Tx ID</span>
          <input
            className={styles.input}
            onChange={(event) => setSearchProviderTransactionId(event.target.value)}
            placeholder="bank-txn-..."
            type="text"
            value={searchProviderTransactionId}
          />
        </label>
        <label className={styles.filterField}>
          <span>Amount</span>
          <input
            className={styles.input}
            onChange={(event) => setSearchAmount(event.target.value)}
            placeholder="28.45"
            step="0.01"
            type="number"
            value={searchAmount}
          />
        </label>
        <label className={styles.filterField}>
          <span>Date</span>
          <input
            className={styles.input}
            onChange={(event) => setSearchDate(event.target.value)}
            type="date"
            value={searchDate}
          />
        </label>
      </div>
      <div className={styles.statusPillsRow}>
        <label className={styles.checkboxPill}>
          <input checked={includeIgnoredDrafts} onChange={(event) => setIncludeIgnoredDrafts(event.target.checked)} type="checkbox" />
          <span>Include ignored drafts</span>
        </label>
      </div>
      <div className={styles.adminActionsRow}>
        <button className={styles.secondaryButton} onClick={() => void loadUnmatchedDrafts()} type="button" disabled={isLoading}>
          {isLoading ? 'Refreshing...' : 'Refresh suggestions'}
        </button>
        <button
          className={styles.secondaryButton}
          onClick={() => {
            setSearchProviderTransactionId('');
            setSearchAmount('');
            setSearchDate('');
          }}
          type="button"
        >
          Clear search
        </button>
      </div>
      {message && <p className={styles.message}>{message}</p>}
      {error && <p className={styles.error}>{error}</p>}
      {rows.length === 0 ? (
        <p className={styles.emptyState}>No unmatched receipt drafts. Auto-reconciliation is up to date.</p>
      ) : (
        <div className={styles.tableResponsive}>
          <table className={styles.table}>
            <thead>
              <tr>
                <th>Draft</th>
                <th>Amount</th>
                <th>Date</th>
                <th>Status</th>
                <th>Draft actions</th>
                <th>Candidate bank transactions</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr key={row.draft_transaction.id}>
                  <td>{row.draft_transaction.description}</td>
                  <td className={row.draft_transaction.amount > 0 ? styles.positive : styles.negative}>
                    {row.draft_transaction.amount.toFixed(2)} {row.draft_transaction.currency}
                  </td>
                  <td>{row.draft_transaction.date}</td>
                  <td>{row.draft_transaction.reconciliation_status || 'open'}</td>
                  <td>
                    {(row.draft_transaction.reconciliation_status || 'open') === 'ignored' ? (
                      <button
                        className={styles.tableActionButton}
                        disabled={activeActionKey === `reopen:${row.draft_transaction.id}`}
                        onClick={() => void handleDraftState(row.draft_transaction.id, 'reopen')}
                        type="button"
                      >
                        {activeActionKey === `reopen:${row.draft_transaction.id}` ? 'Reopening...' : 'Reopen draft'}
                      </button>
                    ) : (
                      <button
                        className={styles.tableActionButton}
                        disabled={activeActionKey === `ignore:${row.draft_transaction.id}`}
                        onClick={() => void handleDraftState(row.draft_transaction.id, 'ignore')}
                        type="button"
                      >
                        {activeActionKey === `ignore:${row.draft_transaction.id}` ? 'Ignoring...' : 'Ignore draft'}
                      </button>
                    )}
                  </td>
                  <td>
                    {row.candidates.length === 0 ? (
                      <span className={styles.emptyState}>No strong candidates yet.</span>
                    ) : (
                      <div className={styles.invoiceExportGroup}>
                        {row.candidates.map((candidate) => (
                          <div key={candidate.transaction_id} className={styles.invoiceActionGroup}>
                            <button
                              className={styles.tableActionButton}
                              disabled={activeActionKey === `${row.draft_transaction.id}:${candidate.transaction_id}`}
                              onClick={() => void handleMatch(row.draft_transaction.id, candidate.transaction_id)}
                              type="button"
                            >
                              {activeActionKey === `${row.draft_transaction.id}:${candidate.transaction_id}`
                                ? 'Matching...'
                                : `Match ${candidate.description} (${(candidate.confidence_score * 100).toFixed(0)}%)`}
                            </button>
                            <button
                              className={styles.tableActionButton}
                              disabled={activeActionKey === `ignore-candidate:${row.draft_transaction.id}:${candidate.transaction_id}`}
                              onClick={() => void handleIgnoreCandidate(row.draft_transaction.id, candidate.transaction_id)}
                              type="button"
                            >
                              {activeActionKey === `ignore-candidate:${row.draft_transaction.id}:${candidate.transaction_id}`
                                ? 'Ignoring...'
                                : candidate.ignored
                                  ? 'Ignored'
                                  : 'Ignore candidate'}
                            </button>
                          </div>
                        ))}
                      </div>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
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
            <ReceiptDraftManualMatching token={token} />
        </div>
    );
}