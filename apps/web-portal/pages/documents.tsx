import { useState, FormEvent, useEffect, ChangeEvent } from 'react';
import styles from '../styles/Home.module.css';
import { useState, FormEvent, useEffect, ChangeEvent } from 'react';
import styles from '../styles/Home.module.css';

const DOCUMENTS_SERVICE_URL = process.env.NEXT_PUBLIC_DOCUMENTS_SERVICE_URL || 'http://localhost:8006';
const QNA_SERVICE_URL = process.env.NEXT_PUBLIC_QNA_SERVICE_URL || 'http://localhost:8014';

function SemanticSearch({ token }: { token: string }) {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<any[]>([]);
  const [error, setError] = useState('');
  const { t } = useTranslation();

  const handleSearch = async (e: FormEvent) => {
    e.preventDefault();
    setError('');
    if (!query) return;

    try {
      const response = await fetch(`${QNA_SERVICE_URL}/search`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
        body: JSON.stringify({ query, user_id: 'fake-user-123' }), // Pass real user_id in prod
      });
      if (!response.ok) throw new Error('Search failed');
      const data = await response.json();
      setResults(data);
    } catch (err: any) {
      setError(err.message);
    }
  };

  return (
    <div className={styles.subContainer}>
      <h2>{t('documents.search_title')}</h2>
      <p>{t('documents.search_description')}</p>
      <form onSubmit={handleSearch}>
        <div className={styles.fileInputContainer}>
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder={t('documents.search_placeholder')}
            className={styles.input}
          />
          <button type="submit" className={styles.button}>{t('documents.search_button')}</button>
        </div>
      </form>
      {error && <p className={styles.error}>{error}</p>}
      {results.length > 0 && (
        <div className={styles.searchResults}>
          <h4>Search Results:</h4>
          {results.map((result, index) => (
            <div key={index} className={styles.searchResultItem}>
              <strong>{result.filename}</strong>
              <p>"{result.content}"</p>
              <small>Similarity score: {result.score.toFixed(4)}</small>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

type DocumentsPageProps = {
  token: string;
};

export default function DocumentsPage({ token }: DocumentsPageProps) {
  const [documents, setDocuments] = useState<any[]>([]);
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');
  const [selectedFile, setSelectedFile] = useState<File | null>(null);

  const fetchDocuments = async () => {
    try {
      const response = await fetch(`${DOCUMENTS_SERVICE_URL}/documents`, {
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
      const response = await fetch(`${DOCUMENTS_SERVICE_URL}/documents/upload`, {
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
    <div>
        <h1>Documents</h1>
        <p>Upload and manage your receipts and invoices.</p>
        <div className={styles.subContainer}>
            <h2>Upload a Document</h2>
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
    </div>
  );
}
const DOCUMENTS_SERVICE_URL = process.env.NEXT_PUBLIC_DOCUMENTS_SERVICE_URL || 'http://localhost:8006';
const QNA_SERVICE_URL = process.env.NEXT_PUBLIC_QNA_SERVICE_URL || 'http://localhost:8014';

function SemanticSearch({ token }: { token: string }) {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<any[]>([]);
  const [error, setError] = useState('');
  const { t } = useTranslation();

  const handleSearch = async (e: FormEvent) => {
    e.preventDefault();
    setError('');
    if (!query) return;

    try {
      const response = await fetch(`${QNA_SERVICE_URL}/search`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
        body: JSON.stringify({ query, user_id: 'fake-user-123' }), // Pass real user_id in prod
      });
      if (!response.ok) throw new Error('Search failed');
      const data = await response.json();
      setResults(data);
    } catch (err: any) {
      setError(err.message);
    }
  };

  return (
    <div className={styles.subContainer}>
      <h2>{t('documents.search_title')}</h2>
      <p>{t('documents.search_description')}</p>
      <form onSubmit={handleSearch}>
        <div className={styles.fileInputContainer}>
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder={t('documents.search_placeholder')}
            className={styles.input}
          />
          <button type="submit" className={styles.button}>{t('documents.search_button')}</button>
        </div>
      </form>
      {error && <p className={styles.error}>{error}</p>}
      {results.length > 0 && (
        <div className={styles.searchResults}>
          <h4>Search Results:</h4>
          {results.map((result, index) => (
            <div key={index} className={styles.searchResultItem}>
              <strong>{result.filename}</strong>
              <p>"{result.content}"</p>
              <small>Similarity score: {result.score.toFixed(4)}</small>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

type DocumentsPageProps = {
  token: string;
};

export default function DocumentsPage({ token }: DocumentsPageProps) {
  const [documents, setDocuments] = useState<any[]>([]);
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');
  const [selectedFile, setSelectedFile] = useState<File | null>(null);

  const fetchDocuments = async () => {
    try {
      const response = await fetch(`${DOCUMENTS_SERVICE_URL}/documents`, {
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
      const response = await fetch(`${DOCUMENTS_SERVICE_URL}/documents/upload`, {
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
    <div>
        <h1>Documents</h1>
        <p>Upload and manage your receipts and invoices.</p>
        <div className={styles.subContainer}>
            <h2>Upload a Document</h2>
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
    </div>
  );
}
