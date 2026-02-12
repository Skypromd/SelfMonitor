import { useEffect, useState, type ChangeEvent, type FormEvent } from 'react';
import { useTranslation } from '../hooks/useTranslation';
import styles from '../styles/Home.module.css';

const DOCUMENTS_SERVICE_URL = process.env.NEXT_PUBLIC_DOCUMENTS_SERVICE_URL || 'http://localhost:8006';
const QNA_SERVICE_URL = process.env.NEXT_PUBLIC_QNA_SERVICE_URL || 'http://localhost:8014';

type DocumentsPageProps = {
  token: string;
};

type DocumentRecord = {
  filename: string;
  id: string;
  status: string;
  uploaded_at: string;
};

type SearchResult = {
  content: string;
  filename: string;
  score: number;
};

function SemanticSearch({ token }: { token: string }) {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<SearchResult[]>([]);
  const [error, setError] = useState('');
  const [isSearching, setIsSearching] = useState(false);
  const { t } = useTranslation();

  const handleSearch = async (event: FormEvent) => {
    event.preventDefault();
    setError('');
    if (!query) {
      return;
    }

    setIsSearching(true);
    try {
      const response = await fetch(`${QNA_SERVICE_URL}/search`, {
        body: JSON.stringify({ query, user_id: 'fake-user-123' }),
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        method: 'POST',
      });
      if (!response.ok) {
        throw new Error('Search failed');
      }
      setResults(await response.json());
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unexpected error');
    } finally {
      setIsSearching(false);
    }
  };

  return (
    <div className={styles.subContainer}>
      <h2>{t('documents.search_title')}</h2>
      <p>{t('documents.search_description')}</p>
      <form onSubmit={handleSearch}>
        <div className={styles.fileInputContainer}>
          <input
            className={styles.input}
            onChange={(event) => setQuery(event.target.value)}
            placeholder={t('documents.search_placeholder')}
            type="text"
            value={query}
          />
          <button className={styles.button} type="submit">
            {t('documents.search_button')}
          </button>
        </div>
      </form>

      {error && <p className={styles.error}>{error}</p>}
      {isSearching && (
        <div className={styles.searchResults}>
          {Array.from({ length: 3 }).map((_, index) => (
            <div className={styles.searchResultItem} key={index}>
              <div className={`${styles.skeletonLine} ${styles.skeletonLineShort}`} />
              <div className={`${styles.skeletonLine} ${styles.skeletonLineLong}`} />
              <div className={`${styles.skeletonLine} ${styles.skeletonLineMedium}`} />
            </div>
          ))}
        </div>
      )}
      {results.length > 0 && (
        <div className={styles.searchResults}>
          <h4>Search Results:</h4>
          {results.map((result, index) => (
            <div key={`${result.filename}-${index}`} className={styles.searchResultItem}>
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

export default function DocumentsPage({ token }: DocumentsPageProps) {
  const [documents, setDocuments] = useState<DocumentRecord[]>([]);
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');
  const [isLoadingDocuments, setIsLoadingDocuments] = useState(true);
  const [isUploading, setIsUploading] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const { t } = useTranslation();

  const fetchDocuments = async () => {
    setIsLoadingDocuments(true);
    try {
      const response = await fetch(`${DOCUMENTS_SERVICE_URL}/documents`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!response.ok) {
        throw new Error('Failed to fetch documents');
      }
      setDocuments(await response.json());
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unexpected error');
    } finally {
      setIsLoadingDocuments(false);
    }
  };

  useEffect(() => {
    fetchDocuments();
  }, [token]);

  const handleFileSelect = (event: ChangeEvent<HTMLInputElement>) => {
    if (event.target.files?.length) {
      setSelectedFile(event.target.files[0]);
    }
  };

  const handleUpload = async (event: FormEvent) => {
    event.preventDefault();
    setError('');
    setMessage('');
    if (!selectedFile) {
      setError('Please select a file first.');
      return;
    }

    setIsUploading(true);
    const formData = new FormData();
    formData.append('file', selectedFile);

    try {
      const response = await fetch(`${DOCUMENTS_SERVICE_URL}/documents/upload`, {
        body: formData,
        headers: { Authorization: `Bearer ${token}` },
        method: 'POST',
      });
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.detail || 'Failed to upload file');
      }

      setMessage(`File '${data.filename}' uploaded successfully!`);
      setSelectedFile(null);
      await fetchDocuments();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unexpected error');
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <div className={styles.dashboard}>
      <h1>{t('nav.documents')}</h1>
      <p>{t('documents.description')}</p>
      <div className={styles.subContainer}>
        <h2>{t('documents.upload_title')}</h2>
        <form onSubmit={handleUpload}>
          <div className={styles.fileInputContainer}>
            <input onChange={handleFileSelect} type="file" />
            <button className={styles.button} disabled={!selectedFile || isUploading} type="submit">
              {isUploading ? 'Uploading...' : t('documents.upload_button')}
            </button>
          </div>
        </form>
        {message && <p className={styles.message}>{message}</p>}
        {error && <p className={styles.error}>{error}</p>}

        {isLoadingDocuments ? (
          <div className={styles.skeletonTable}>
            {Array.from({ length: 4 }).map((_, index) => (
              <div className={styles.skeletonRow} key={index}>
                <div className={styles.skeletonCell} />
                <div className={styles.skeletonCell} />
                <div className={styles.skeletonCell} />
              </div>
            ))}
          </div>
        ) : documents.length === 0 ? (
          <p className={styles.emptyState}>No documents uploaded yet.</p>
        ) : (
          <table className={styles.table}>
            <thead>
              <tr>
                <th>{t('documents.col_filename')}</th>
                <th>{t('documents.col_status')}</th>
                <th>{t('documents.col_uploaded_at')}</th>
              </tr>
            </thead>
            <tbody>
              {documents.map((document) => (
                <tr key={document.id}>
                  <td>{document.filename}</td>
                  <td>
                    <span className={`${styles.status} ${styles[document.status]}`}>{document.status}</span>
                  </td>
                  <td>{new Date(document.uploaded_at).toLocaleString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      <SemanticSearch token={token} />
    </div>
  );
}
