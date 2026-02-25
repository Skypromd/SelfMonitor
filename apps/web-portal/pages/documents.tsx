import { ChangeEvent, FormEvent, useEffect, useState } from 'react';
import styles from '../styles/Home.module.css';
import { useTranslation } from '../hooks/useTranslation';

const API_GATEWAY_URL = process.env.NEXT_PUBLIC_API_GATEWAY_URL || 'http://localhost:8000/api';

type DocumentsPageProps = {
  token: string;
};

type DocumentItem = {
  id: string;
  filename: string;
  status: string;
  uploaded_at: string;
};

function SemanticSearch({ token }: { token: string }) {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<any[]>([]);
  const [error, setError] = useState('');
  const { t } = useTranslation();

  const handleSearch = async (e: FormEvent) => {
    e.preventDefault();
    setError('');
    if (!query) {
      return;
    }

    try {
      const response = await fetch(`${API_GATEWAY_URL}/qna/search`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({ query }),
      });
      if (!response.ok) {
        throw new Error('Search failed');
      }
      setResults(await response.json());
    } catch (err: unknown) {
      const details = err instanceof Error ? err.message : 'Search failed';
      setError(details);
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
          <button type="submit" className={styles.button}>
            {t('documents.search_button')}
          </button>
        </div>
      </form>
      {error && <p className={styles.error}>{error}</p>}
      {results.length > 0 && (
        <div className={styles.searchResults}>
          <h4>Search Results:</h4>
          {results.map((result, index) => (
            <div key={`${result.document_id}-${index}`} className={styles.searchResultItem}>
              <strong>{result.filename}</strong>
              <p>&quot;{result.content}&quot;</p>
              <small>Similarity score: {Number(result.score).toFixed(4)}</small>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default function DocumentsPage({ token }: DocumentsPageProps) {
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const { t } = useTranslation();

  const fetchDocuments = async () => {
    try {
      const response = await fetch(`${API_GATEWAY_URL}/documents/documents`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!response.ok) {
        throw new Error('Failed to fetch documents');
      }
      setDocuments(await response.json());
    } catch (err: unknown) {
      const details = err instanceof Error ? err.message : 'Failed to fetch documents';
      setError(details);
    }
  };

  useEffect(() => {
    fetchDocuments();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token]);

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
      const response = await fetch(`${API_GATEWAY_URL}/documents/documents/upload`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
        body: formData,
      });
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.detail || 'Failed to upload file');
      }

      setMessage(`File '${data.filename}' uploaded successfully!`);
      setSelectedFile(null);
      fetchDocuments();
    } catch (err: unknown) {
      const details = err instanceof Error ? err.message : 'Failed to upload file';
      setError(details);
    }
  };

  return (
    <div>
      <h1>{t('nav.documents')}</h1>
      <p>{t('documents.description')}</p>
      <div className={styles.subContainer}>
        <h2>{t('documents.upload_title')}</h2>
        <form onSubmit={handleUpload}>
          <div className={styles.fileInputContainer}>
            <input type="file" onChange={handleFileSelect} />
            <button type="submit" className={styles.button} disabled={!selectedFile}>
              {t('documents.upload_button')}
            </button>
          </div>
        </form>
        {message && <p className={styles.message}>{message}</p>}
        {error && <p className={styles.error}>{error}</p>}

        <table className={styles.table}>
          <thead>
            <tr>
              <th>{t('documents.col_filename')}</th>
              <th>{t('documents.col_status')}</th>
              <th>{t('documents.col_uploaded_at')}</th>
            </tr>
          </thead>
          <tbody>
            {documents.map((doc) => (
              <tr key={doc.id}>
                <td>{doc.filename}</td>
                <td>
                  <span className={`${styles.status} ${styles[doc.status]}`}>{doc.status}</span>
                </td>
                <td>{new Date(doc.uploaded_at).toLocaleString()}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <SemanticSearch token={token} />
    </div>
  );
}
