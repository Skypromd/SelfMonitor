import { useState, FormEvent, useEffect, ChangeEvent } from 'react';
import styles from '../styles/Home.module.css';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_GATEWAY_URL || 'http://localhost:8000/api';
const PROFILE_SERVICE_BASE_URL = process.env.NEXT_PUBLIC_PROFILE_SERVICE_URL || 'http://localhost:8001';
const TRANSACTIONS_SERVICE_BASE_URL = process.env.NEXT_PUBLIC_TRANSACTIONS_SERVICE_URL || 'http://localhost:8002';
const BANKING_CONNECTOR_BASE_URL = process.env.NEXT_PUBLIC_BANKING_CONNECTOR_URL || 'http://localhost:8005';

// --- User Profile Component ---
function UserProfile({ token }: { token: string }) {
  const [profile, setProfile] = useState({ first_name: '', last_name: '', date_of_birth: '' });
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');

  const fetchProfile = async () => {
    setMessage('');
    setError('');
    try {
      const response = await fetch(`${PROFILE_SERVICE_BASE_URL}/profiles/me`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (response.status === 404) {
        setMessage('No profile found. Create one by saving.');
        setProfile({ first_name: '', last_name: '', date_of_birth: '' });
        return;
      }
      if (!response.ok) throw new Error('Failed to fetch profile');
      const data = await response.json();
      setProfile({ first_name: data.first_name || '', last_name: data.last_name || '', date_of_birth: data.date_of_birth || '' });
    } catch (err: any) { setError(err.message); }
  };

  useEffect(() => { fetchProfile(); }, [token]);

  const handleProfileChange = (e: ChangeEvent<HTMLInputElement>) => setProfile({ ...profile, [e.target.name]: e.target.value });

  const handleSaveProfile = async (e: FormEvent) => {
    e.preventDefault();
    setMessage('');
    setError('');
    try {
      const response = await fetch(`${PROFILE_SERVICE_BASE_URL}/profiles/me`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
        body: JSON.stringify({ ...profile, date_of_birth: profile.date_of_birth || null })
      });
      if (!response.ok) throw new Error('Failed to save profile');
      setMessage('Profile saved successfully!');
    } catch (err: any) { setError(err.message); }
  };

  return (
    <div className={styles.subContainer}>
      <h2>Your Profile</h2>
      <form onSubmit={handleSaveProfile}>
        <input type="text" name="first_name" placeholder="First Name" value={profile.first_name} onChange={handleProfileChange} className={styles.input} />
        <input type="text" name="last_name" placeholder="Last Name" value={profile.last_name} onChange={handleProfileChange} className={styles.input} />
        <input type="date" name="date_of_birth" placeholder="Date of Birth" value={profile.date_of_birth} onChange={handleProfileChange} className={styles.input} />
        <button type="submit" className={styles.button}>Save Profile</button>
      </form>
      {message && <p className={styles.message}>{message}</p>}
      {error && <p className={styles.error}>{error}</p>}
    </div>
  );
}

// --- Bank Connection and Transactions Components ---
function BankConnection({ token, onConnectionComplete }: { token: string, onConnectionComplete: (accountId: string) => void }) {
  const [consentUrl, setConsentUrl] = useState('');
  const [error, setError] = useState('');

  const handleInitiate = async () => {
    setError('');
    try {
      const response = await fetch(`${BANKING_CONNECTOR_BASE_URL}/connections/initiate`, {
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
      const response = await fetch(`${BANKING_CONNECTOR_BASE_URL}/connections/callback?code=fake_auth_code`);
      if (!response.ok) throw new Error('Failed to complete connection');
      const data = await response.json();
      onConnectionComplete(data.connection_id);
    } catch (err: any) { setError(err.message); }
  };

  return (
    <div className={styles.subContainer}>
      <h2>Bank Connections</h2>
      {!consentUrl ? (
        <button onClick={handleInitiate} className={styles.button}>Connect a Bank Account</button>
      ) : (
        <div>
          <p>Click the link to grant access at your bank:</p>
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

  const availableCategories = ['groceries', 'transport', 'income', 'food_and_drink', 'subscriptions'];

  useEffect(() => {
    if (!accountId) return;
    const fetchTransactions = async () => {
      // Small delay to allow the background task in banking-connector to finish
      setTimeout(async () => {
        try {
          const response = await fetch(`${TRANSACTIONS_SERVICE_BASE_URL}/accounts/${accountId}/transactions`, {
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
      const response = await fetch(`${TRANSACTIONS_SERVICE_BASE_URL}/transactions/${transactionId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
        body: JSON.stringify({ category: newCategory })
      });
      if (!response.ok) throw new Error('Failed to update category');

      // Update local state for immediate UI feedback
      setTransactions(transactions.map(t => 
        t.id === transactionId ? { ...t, category: newCategory } : t
      ));
    } catch (err: any) {
      // In a real app, you might want to show a more specific error
      console.error("Failed to update category:", err);
    }
  };

  if (!transactions.length && !error) return <p>Loading transactions...</p>;
  if (error) return <p className={styles.error}>{error}</p>;

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
                <select 
                  value={t.category || ''} 
                  onChange={(e) => handleCategoryChange(t.id, e.target.value)}
                  className={styles.categorySelect}
                >
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

// --- Tax Calculator Component ---
function TaxCalculator({ token }: { token: string }) {
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState('');
  const [startDate, setStartDate] = useState('2023-01-01');
  const [endDate, setEndDate] = useState('2023-12-31');
import { useState, FormEvent, useEffect, ChangeEvent } from 'react';
import styles from '../styles/Home.module.css';

const AUTH_SERVICE_BASE_URL = process.env.NEXT_PUBLIC_AUTH_SERVICE_URL || 'http://localhost:8000';
const PROFILE_SERVICE_BASE_URL = process.env.NEXT_PUBLIC_PROFILE_SERVICE_URL || 'http://localhost:8001';
const TRANSACTIONS_SERVICE_BASE_URL = process.env.NEXT_PUBLIC_TRANSACTIONS_SERVICE_URL || 'http://localhost:8002';
const BANKING_CONNECTOR_BASE_URL = process.env.NEXT_PUBLIC_BANKING_CONNECTOR_URL || 'http://localhost:8005';

// --- User Profile Component ---
function UserProfile({ token }: { token: string }) {
  const [profile, setProfile] = useState({ first_name: '', last_name: '', date_of_birth: '' });
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');

  const fetchProfile = async () => {
    setMessage('');
    setError('');
    try {
      const response = await fetch(`${PROFILE_SERVICE_BASE_URL}/profiles/me`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (response.status === 404) {
        setMessage('No profile found. Create one by saving.');
        setProfile({ first_name: '', last_name: '', date_of_birth: '' });
        return;
      }
      if (!response.ok) throw new Error('Failed to fetch profile');
      const data = await response.json();
      setProfile({ first_name: data.first_name || '', last_name: data.last_name || '', date_of_birth: data.date_of_birth || '' });
    } catch (err: any) { setError(err.message); }
  };

  useEffect(() => { fetchProfile(); }, [token]);

  const handleProfileChange = (e: ChangeEvent<HTMLInputElement>) => setProfile({ ...profile, [e.target.name]: e.target.value });

  const handleSaveProfile = async (e: FormEvent) => {
    e.preventDefault();
    setMessage('');
    setError('');
    try {
      const response = await fetch(`${PROFILE_SERVICE_BASE_URL}/profiles/me`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
        body: JSON.stringify({ ...profile, date_of_birth: profile.date_of_birth || null })
      });
      if (!response.ok) throw new Error('Failed to save profile');
      setMessage('Profile saved successfully!');
    } catch (err: any) { setError(err.message); }
  };

  return (
    <div className={styles.subContainer}>
      <h2>Your Profile</h2>
      <form onSubmit={handleSaveProfile}>
        <input type="text" name="first_name" placeholder="First Name" value={profile.first_name} onChange={handleProfileChange} className={styles.input} />
        <input type="text" name="last_name" placeholder="Last Name" value={profile.last_name} onChange={handleProfileChange} className={styles.input} />
        <input type="date" name="date_of_birth" placeholder="Date of Birth" value={profile.date_of_birth} onChange={handleProfileChange} className={styles.input} />
        <button type="submit" className={styles.button}>Save Profile</button>
      </form>
      {message && <p className={styles.message}>{message}</p>}
      {error && <p className={styles.error}>{error}</p>}
    </div>
  );
}

// --- Bank Connection and Transactions Components ---
function BankConnection({ token, onConnectionComplete }: { token: string, onConnectionComplete: (accountId: string) => void }) {
  const [consentUrl, setConsentUrl] = useState('');
  const [error, setError] = useState('');

  const handleInitiate = async () => {
    setError('');
    try {
      const response = await fetch(`${BANKING_CONNECTOR_BASE_URL}/connections/initiate`, {
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
      const response = await fetch(`${BANKING_CONNECTOR_BASE_URL}/connections/callback?code=fake_auth_code`);
      if (!response.ok) throw new Error('Failed to complete connection');
      const data = await response.json();
      onConnectionComplete(data.connection_id);
    } catch (err: any) { setError(err.message); }
  };

  return (
    <div className={styles.subContainer}>
      <h2>Bank Connections</h2>
      {!consentUrl ? (
        <button onClick={handleInitiate} className={styles.button}>Connect a Bank Account</button>
      ) : (
        <div>
          <p>Click the link to grant access at your bank:</p>
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

  const availableCategories = ['groceries', 'transport', 'income', 'food_and_drink', 'subscriptions'];

  useEffect(() => {
    if (!accountId) return;
    const fetchTransactions = async () => {
      // Small delay to allow the background task in banking-connector to finish
      setTimeout(async () => {
        try {
          const response = await fetch(`${TRANSACTIONS_SERVICE_BASE_URL}/accounts/${accountId}/transactions`, {
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
      const response = await fetch(`${TRANSACTIONS_SERVICE_BASE_URL}/transactions/${transactionId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
        body: JSON.stringify({ category: newCategory })
      });
      if (!response.ok) throw new Error('Failed to update category');

      // Update local state for immediate UI feedback
      setTransactions(transactions.map(t => 
        t.id === transactionId ? { ...t, category: newCategory } : t
      ));
    } catch (err: any) {
      // In a real app, you might want to show a more specific error
      console.error("Failed to update category:", err);
    }
  };

  if (!transactions.length && !error) return <p>Loading transactions...</p>;
  if (error) return <p className={styles.error}>{error}</p>;

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
                <select 
                  value={t.category || ''} 
                  onChange={(e) => handleCategoryChange(t.id, e.target.value)}
                  className={styles.categorySelect}
                >
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


// --- Main Page Component ---
export default function HomePage() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [token, setToken] = useState('');
  const [connectedAccountId, setConnectedAccountId] = useState('');

  const clearMessages = () => { setMessage(''); setError(''); };

  const handleRegister = async (e: FormEvent) => {
    e.preventDefault();
    clearMessages();
    try {
      const response = await fetch(`${API_BASE_URL}/auth/register`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || 'Registration failed');
      setMessage(`User ${data.email} registered successfully! You can now log in.`);
    } catch (err: any) { setError(err.message); }
  };

  const handleLogin = async (e: FormEvent) => {
    e.preventDefault();
    clearMessages();
    setToken('');
    try {
      const formData = new URLSearchParams();
      formData.append('username', email);
      formData.append('password', password);
      const response = await fetch(`${AUTH_SERVICE_BASE_URL}/token`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: formData,
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || 'Login failed');
      setToken(data.access_token);
    } catch (err: any) { setError(err.message); }
  };

  const handleLogout = () => {
    setToken('');
    setConnectedAccountId('');
    setMessage('You have been logged out.');
  };

  return (
    <div className={styles.container}>
      <main className={styles.main}>
        {token ? (
          <div className={styles.dashboard}>
            <div className={styles.dashboardHeader}>
              <h1>Dashboard</h1>
              <button onClick={handleLogout} className={styles.logoutButton}>Logout</button>
            </div>
            <UserProfile token={token} />
            <BankConnection token={token} onConnectionComplete={setConnectedAccountId} />
            {connectedAccountId && <TransactionsList token={token} accountId={connectedAccountId} />}
            <DocumentsManager token={token} />
            <TaxCalculator token={token} />
          </div>
        ) : (
          <>
            <h1 className={styles.title}>Welcome!</h1>
            <p className={styles.description}>Register or log in to continue</p>
            <div className={styles.formContainer}>
              <form>
                <input type="email" placeholder="Email" value={email} onChange={(e) => setEmail(e.target.value)} className={styles.input} />
                <input type="password" placeholder="Password" value={password} onChange={(e) => setPassword(e.target.value)} className={styles.input} />
                <div className={styles.buttonGroup}>
                  <button onClick={handleRegister} className={styles.button}>Register</button>
                  <button onClick={handleLogin} className={styles.button}>Login</button>
                </div>
              </form>
            </div>
            {message && <p className={styles.message}>{message}</p>}
            {error && <p className={styles.error}>{error}</p>}
          </>
        )}
      </main>
    </div>
  );
}
  const handleCalculate = async (e: FormEvent) => {
    e.preventDefault();
    setError('');
    setResult(null);
    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_TAX_ENGINE_URL || 'http://localhost:8007'}/calculate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
        body: JSON.stringify({ start_date: startDate, end_date: endDate, jurisdiction: 'UK' })
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || 'Failed to calculate tax');
      setResult(data);
    } catch (err: any) { setError(err.message); }
  };

  return (
    <div className={styles.subContainer}>
      <h2>Tax Estimator (UK)</h2>
      <form onSubmit={handleCalculate}>
        <div className={styles.dateInputs}>
          <input type="date" value={startDate} onChange={e => setStartDate(e.target.value)} className={styles.input} />
          <input type="date" value={endDate} onChange={e => setEndDate(e.target.value)} className={styles.input} />
        </div>
        <button type="submit" className={styles.button}>Calculate Tax</button>
      </form>
      {error && <p className={styles.error}>{error}</p>}
      {result && (
        <div className={styles.resultsContainer}>
          <h3>Estimated Tax for {result.start_date} to {result.end_date}</h3>
          <div className={styles.resultItem}><span>Total Income:</span> <span className={styles.positive}>£{result.total_income.toFixed(2)}</span></div>
          <div className={styles.resultItem}><span>Deductible Expenses:</span> <span className={styles.negative}>£{result.total_expenses.toFixed(2)}</span></div>
          <div className={styles.resultItemMain}><span>Estimated Tax Due:</span> <span>£{result.estimated_tax_due.toFixed(2)}</span></div>
        </div>
      )}
    </div>
  );
}


// --- Documents Manager Component ---
function DocumentsManager({ token }: { token: string }) {
  const [documents, setDocuments] = useState<any[]>([]);
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');
  const [selectedFile, setSelectedFile] = useState<File | null>(null);

  const fetchDocuments = async () => {
    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_DOCUMENTS_SERVICE_URL || 'http://localhost:8006'}/documents`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (!response.ok) throw new Error('Failed to fetch documents');
      const data = await response.json();
      setDocuments(data);
    } catch (err: any) { setError(err.message); }
  };

  useEffect(() => { fetchDocuments(); }, [token]);

  const handleFileSelect = (e: ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      setSelectedFile(e.target.files[0]);
    }
  };

  const handleUpload = async (e: FormEvent) => {
    e.preventDefault();
    setError('');
    setMessage('');
    if (!selectedFile) {
      setError('Please select a file first.');
      return;
    }

    const formData = new FormData();
    formData.append('file', selectedFile);

    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_DOCUMENTS_SERVICE_URL || 'http://localhost:8006'}/documents/upload`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` },
        body: formData,
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || 'Failed to upload file');

      setMessage(`File '${data.filename}' uploaded successfully!`);
      setSelectedFile(null); // Reset file input
      fetchDocuments(); // Refresh the list
    } catch (err: any) { setError(err.message); }
  };

  return (
    <div className={styles.subContainer}>
      <h2>Documents</h2>
      <form onSubmit={handleUpload}>
        <div className={styles.fileInputContainer}>
          <input type="file" onChange={handleFileSelect} />
          <button type="submit" className={styles.button} disabled={!selectedFile}>Upload</button>
        </div>
      </form>
      {message && <p className={styles.message}>{message}</p>}
      {error && <p className={styles.error}>{error}</p>}

      <table className={styles.table}>
        <thead><tr><th>Filename</th><th>Status</th><th>Uploaded At</th></tr></thead>
        <tbody>
          {documents.map(doc => (
            <tr key={doc.id}>
              <td>{doc.filename}</td>
              <td><span className={`${styles.status} ${styles[doc.status]}`}>{doc.status}</span></td>
              <td>{new Date(doc.uploaded_at).toLocaleString()}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// --- Tax Calculator Component ---
function TaxCalculator({ token }: { token: string }) {
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState('');
  const [startDate, setStartDate] = useState('2023-01-01');
  const [endDate, setEndDate] = useState('2023-12-31');

  const handleCalculate = async (e: FormEvent) => {
    e.preventDefault();
    setError('');
    setResult(null);
    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_TAX_ENGINE_URL || 'http://localhost:8007'}/calculate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
        body: JSON.stringify({ start_date: startDate, end_date: endDate, jurisdiction: 'UK' })
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || 'Failed to calculate tax');
      setResult(data);
    } catch (err: any) { setError(err.message); }
  };

  return (
    <div className={styles.subContainer}>
      <h2>Tax Estimator (UK)</h2>
      <form onSubmit={handleCalculate}>
        <div className={styles.dateInputs}>
          <input type="date" value={startDate} onChange={e => setStartDate(e.target.value)} className={styles.input} />
          <input type="date" value={endDate} onChange={e => setEndDate(e.target.value)} className={styles.input} />
        </div>
        <button type="submit" className={styles.button}>Calculate Tax</button>
      </form>
      {error && <p className={styles.error}>{error}</p>}
      {result && (
        <div className={styles.resultsContainer}>
          <h3>Estimated Tax for {result.start_date} to {result.end_date}</h3>
          <div className={styles.resultItem}><span>Total Income:</span> <span className={styles.positive}>£{result.total_income.toFixed(2)}</span></div>
          <div className={styles.resultItem}><span>Deductible Expenses:</span> <span className={styles.negative}>£{result.total_expenses.toFixed(2)}</span></div>
          <div className={styles.resultItemMain}><span>Estimated Tax Due:</span> <span>£{result.estimated_tax_due.toFixed(2)}</span></div>
        </div>
      )}
    </div>
  );
}


// --- Documents Manager Component ---
function DocumentsManager({ token }: { token: string }) {
  const [documents, setDocuments] = useState<any[]>([]);
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');
  const [selectedFile, setSelectedFile] = useState<File | null>(null);

  const fetchDocuments = async () => {
    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_DOCUMENTS_SERVICE_URL || 'http://localhost:8006'}/documents`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (!response.ok) throw new Error('Failed to fetch documents');
      const data = await response.json();
      setDocuments(data);
    } catch (err: any) { setError(err.message); }
  };

  useEffect(() => { fetchDocuments(); }, [token]);

  const handleFileSelect = (e: ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      setSelectedFile(e.target.files[0]);
    }
  };

  const handleUpload = async (e: FormEvent) => {
    e.preventDefault();
    setError('');
    setMessage('');
    if (!selectedFile) {
      setError('Please select a file first.');
      return;
    }

    const formData = new FormData();
    formData.append('file', selectedFile);

    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_DOCUMENTS_SERVICE_URL || 'http://localhost:8006'}/documents/upload`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` },
        body: formData,
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || 'Failed to upload file');

      setMessage(`File '${data.filename}' uploaded successfully!`);
      setSelectedFile(null); // Reset file input
      fetchDocuments(); // Refresh the list
    } catch (err: any) { setError(err.message); }
  };

  return (
    <div className={styles.subContainer}>
      <h2>Documents</h2>
      <form onSubmit={handleUpload}>
        <div className={styles.fileInputContainer}>
          <input type="file" onChange={handleFileSelect} />
          <button type="submit" className={styles.button} disabled={!selectedFile}>Upload</button>
        </div>
      </form>
      {message && <p className={styles.message}>{message}</p>}
      {error && <p className={styles.error}>{error}</p>}

      <table className={styles.table}>
        <thead><tr><th>Filename</th><th>Status</th><th>Uploaded At</th></tr></thead>
        <tbody>
          {documents.map(doc => (
            <tr key={doc.id}>
              <td>{doc.filename}</td>
              <td><span className={`${styles.status} ${styles[doc.status]}`}>{doc.status}</span></td>
              <td>{new Date(doc.uploaded_at).toLocaleString()}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}


// --- Main Page Component ---
export default function HomePage() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [token, setToken] = useState('');
  const [connectedAccountId, setConnectedAccountId] = useState('');

  const clearMessages = () => { setMessage(''); setError(''); };

  const handleRegister = async (e: FormEvent) => {
    e.preventDefault();
    clearMessages();
    try {
      const response = await fetch(`${AUTH_SERVICE_BASE_URL}/register`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || 'Registration failed');
      setMessage(`User ${data.email} registered successfully! You can now log in.`);
    } catch (err: any) { setError(err.message); }
  };

  const handleLogin = async (e: FormEvent) => {
    e.preventDefault();
    clearMessages();
    setToken('');
    try {
      const formData = new URLSearchParams();
      formData.append('username', email);
      formData.append('password', password);
      const response = await fetch(`${AUTH_SERVICE_BASE_URL}/token`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: formData,
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || 'Login failed');
      setToken(data.access_token);
    } catch (err: any) { setError(err.message); }
  };

  const handleLogout = () => {
    setToken('');
    setConnectedAccountId('');
    setMessage('You have been logged out.');
  };

  return (
    <div className={styles.container}>
      <main className={styles.main}>
        {token ? (
          <div className={styles.dashboard}>
            <div className={styles.dashboardHeader}>
              <h1>Dashboard</h1>
              <button onClick={handleLogout} className={styles.logoutButton}>Logout</button>
            </div>
            <UserProfile token={token} />
            <BankConnection token={token} onConnectionComplete={setConnectedAccountId} />
            {connectedAccountId && <TransactionsList token={token} accountId={connectedAccountId} />}
            <DocumentsManager token={token} />
            <TaxCalculator token={token} />
          </div>
        ) : (
          <>
            <h1 className={styles.title}>Welcome!</h1>
            <p className={styles.description}>Register or log in to continue</p>
            <div className={styles.formContainer}>
              <form>
                <input type="email" placeholder="Email" value={email} onChange={(e) => setEmail(e.target.value)} className={styles.input} />
                <input type="password" placeholder="Password" value={password} onChange={(e) => setPassword(e.target.value)} className={styles.input} />
                <div className={styles.buttonGroup}>
                  <button onClick={handleRegister} className={styles.button}>Register</button>
                  <button onClick={handleLogin} className={styles.button}>Login</button>
                </div>
              </form>
            </div>
            {message && <p className={styles.message}>{message}</p>}
            {error && <p className={styles.error}>{error}</p>}
          </>
        )}
      </main>
    </div>
  );
}
