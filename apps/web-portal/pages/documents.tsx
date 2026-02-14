import { Fragment, useCallback, useEffect, useState, type ChangeEvent, type FormEvent } from 'react';
import { useTranslation } from '../hooks/useTranslation';
import styles from '../styles/Home.module.css';

const DOCUMENTS_SERVICE_URL = process.env.NEXT_PUBLIC_DOCUMENTS_SERVICE_URL || 'http://localhost:8006';
const QNA_SERVICE_URL = process.env.NEXT_PUBLIC_QNA_SERVICE_URL || 'http://localhost:8014';

type DocumentsPageProps = {
  token: string;
};

type ReviewChangeValue = string | number | boolean | null;

type ReviewFieldChange = {
  after?: ReviewChangeValue;
  before?: ReviewChangeValue;
};

type ReviewChanges = Record<string, ReviewFieldChange>;

type DocumentRecord = {
  extracted_data?: {
    ocr_confidence?: number | null;
    needs_review?: boolean | null;
    review_reason?: string | null;
    review_status?: string | null;
    reviewed_at?: string | null;
    review_notes?: string | null;
    review_changes?: ReviewChanges | null;
    expense_article?: string | null;
    is_potentially_deductible?: boolean | null;
    receipt_draft_transaction_id?: string | null;
    suggested_category?: string | null;
    total_amount?: number | null;
    transaction_date?: string | null;
    vendor_name?: string | null;
  } | null;
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

type DeductibleSelection = 'unknown' | 'true' | 'false';

type ReviewDraft = {
  expense_article: string;
  is_potentially_deductible: DeductibleSelection;
  review_notes: string;
  suggested_category: string;
  total_amount: string;
  transaction_date: string;
  vendor_name: string;
};

const REVIEW_FIELD_LABELS: Record<string, string> = {
  expense_article: 'Expense article',
  is_potentially_deductible: 'Deductible',
  suggested_category: 'Category',
  total_amount: 'Amount',
  transaction_date: 'Date',
  vendor_name: 'Vendor',
};

const REVIEW_FIELD_ORDER = [
  'vendor_name',
  'total_amount',
  'transaction_date',
  'suggested_category',
  'expense_article',
  'is_potentially_deductible',
];

function toReviewDraft(document: DocumentRecord): ReviewDraft {
  const extracted = document.extracted_data;
  const transactionDateRaw = extracted?.transaction_date ?? '';
  return {
    vendor_name: extracted?.vendor_name ?? '',
    total_amount: typeof extracted?.total_amount === 'number' ? extracted.total_amount.toFixed(2) : '',
    transaction_date: transactionDateRaw.includes('T') ? transactionDateRaw.slice(0, 10) : transactionDateRaw,
    suggested_category: extracted?.suggested_category ?? '',
    expense_article: extracted?.expense_article ?? '',
    is_potentially_deductible:
      extracted?.is_potentially_deductible === true
        ? 'true'
        : extracted?.is_potentially_deductible === false
          ? 'false'
          : 'unknown',
    review_notes: extracted?.review_notes ?? '',
  };
}

function formatReviewValue(field: string, value: ReviewChangeValue): string {
  if (value === null || value === undefined || value === '') {
    return '—';
  }
  if (field === 'total_amount' && typeof value === 'number') {
    return `£${value.toFixed(2)}`;
  }
  if (field === 'is_potentially_deductible' && typeof value === 'boolean') {
    return value ? 'Yes' : 'No';
  }
  if (field === 'transaction_date' && typeof value === 'string') {
    return value.includes('T') ? value.slice(0, 10) : value;
  }
  return String(value);
}

function getReviewChangeEntries(reviewChanges: ReviewChanges | null | undefined): Array<[string, ReviewFieldChange]> {
  if (!reviewChanges) {
    return [];
  }
  const entries = Object.entries(reviewChanges).filter(([, change]) => change && (change.before !== change.after));
  const order = new Map(REVIEW_FIELD_ORDER.map((field, index) => [field, index]));
  return entries.sort((first, second) => {
    const firstOrder = order.get(first[0]) ?? 999;
    const secondOrder = order.get(second[0]) ?? 999;
    return firstOrder - secondOrder;
  });
}

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
              <p>&quot;{result.content}&quot;</p>
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
  const [reviewQueue, setReviewQueue] = useState<DocumentRecord[]>([]);
  const [reviewDrafts, setReviewDrafts] = useState<Record<string, ReviewDraft>>({});
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');
  const [isLoadingDocuments, setIsLoadingDocuments] = useState(true);
  const [isLoadingReviewQueue, setIsLoadingReviewQueue] = useState(true);
  const [isUploading, setIsUploading] = useState(false);
  const [reviewActionDocumentId, setReviewActionDocumentId] = useState<string | null>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const { t } = useTranslation();

  const fetchDocuments = useCallback(async () => {
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
  }, [token]);

  const fetchReviewQueue = useCallback(async () => {
    setIsLoadingReviewQueue(true);
    try {
      const response = await fetch(`${DOCUMENTS_SERVICE_URL}/documents/review-queue?limit=50&offset=0`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!response.ok) {
        throw new Error('Failed to fetch review queue');
      }
      const payload = (await response.json()) as { items?: DocumentRecord[] };
      const items = payload.items ?? [];
      setReviewQueue(items);
      setReviewDrafts((previous) => {
        const next: Record<string, ReviewDraft> = {};
        items.forEach((document) => {
          next[document.id] = previous[document.id] ?? toReviewDraft(document);
        });
        return next;
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unexpected error');
    } finally {
      setIsLoadingReviewQueue(false);
    }
  }, [token]);

  useEffect(() => {
    fetchDocuments();
  }, [fetchDocuments]);

  useEffect(() => {
    fetchReviewQueue();
  }, [fetchReviewQueue]);

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
      await Promise.all([fetchDocuments(), fetchReviewQueue()]);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unexpected error');
    } finally {
      setIsUploading(false);
    }
  };

  const handleReviewDraftChange = useCallback(
    (documentId: string, field: keyof ReviewDraft, value: string) => {
      setReviewDrafts((previous) => ({
        ...previous,
        [documentId]: {
          ...(previous[documentId] ?? {
            expense_article: '',
            is_potentially_deductible: 'unknown',
            review_notes: '',
            suggested_category: '',
            total_amount: '',
            transaction_date: '',
            vendor_name: '',
          }),
          [field]: value,
        },
      }));
    },
    []
  );

  const handleReviewAction = useCallback(
    async (document: DocumentRecord, reviewStatus: 'confirmed' | 'corrected' | 'ignored') => {
      setError('');
      setReviewActionDocumentId(document.id);
      try {
        const draft = reviewDrafts[document.id] ?? toReviewDraft(document);
        const payload: Record<string, boolean | number | string> = { review_status: reviewStatus };
        const reviewNotes = draft.review_notes.trim();
        if (reviewNotes) {
          payload.review_notes = reviewNotes;
        }

        if (reviewStatus === 'corrected') {
          const vendorName = draft.vendor_name.trim();
          const suggestedCategory = draft.suggested_category.trim();
          const expenseArticle = draft.expense_article.trim();
          const totalAmount = draft.total_amount.trim();
          const transactionDate = draft.transaction_date.trim();

          if (vendorName) {
            payload.vendor_name = vendorName;
          }
          if (suggestedCategory) {
            payload.suggested_category = suggestedCategory;
          }
          if (expenseArticle) {
            payload.expense_article = expenseArticle;
          }
          if (transactionDate) {
            payload.transaction_date = transactionDate;
          }
          if (totalAmount) {
            const parsedAmount = Number(totalAmount);
            if (!Number.isFinite(parsedAmount) || parsedAmount <= 0) {
              throw new Error('Amount must be a positive number.');
            }
            payload.total_amount = parsedAmount;
          }
          if (draft.is_potentially_deductible === 'true' || draft.is_potentially_deductible === 'false') {
            payload.is_potentially_deductible = draft.is_potentially_deductible === 'true';
          }
        }

        const response = await fetch(`${DOCUMENTS_SERVICE_URL}/documents/${document.id}/review`, {
          method: 'PATCH',
          headers: {
            Authorization: `Bearer ${token}`,
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(payload),
        });
        const responsePayload = await response.json();
        if (!response.ok) {
          throw new Error(responsePayload.detail || 'Failed to update OCR review');
        }
        setMessage(`Review status saved for '${document.filename}'.`);
        await Promise.all([fetchDocuments(), fetchReviewQueue()]);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Unexpected error');
      } finally {
        setReviewActionDocumentId(null);
      }
    },
    [token, fetchDocuments, fetchReviewQueue, reviewDrafts]
  );

  const renderReviewBadge = (document: DocumentRecord) => {
    if (document.extracted_data?.needs_review === true) {
      return <span className={`${styles.reviewBadge} ${styles.reviewBadgePending}`}>Needs review</span>;
    }
    if (document.extracted_data?.review_status) {
      return <span className={`${styles.reviewBadge} ${styles.reviewBadgeDone}`}>{document.extracted_data.review_status}</span>;
    }
    return <span className={styles.reviewBadge}>—</span>;
  };

  const renderConfidence = (document: DocumentRecord) => {
    const confidence = document.extracted_data?.ocr_confidence;
    if (typeof confidence !== 'number') {
      return '—';
    }
    return `${Math.round(confidence * 100)}%`;
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

        <div className={styles.subContainer}>
          <h2>Manual OCR review queue</h2>
          <p>Low-confidence or incomplete receipt extractions are routed here for manual confirmation.</p>
          {isLoadingReviewQueue ? (
            <p>Loading review queue...</p>
          ) : reviewQueue.length === 0 ? (
            <p className={styles.emptyState}>No documents need manual OCR review right now.</p>
          ) : (
            <table className={styles.table}>
              <thead>
                <tr>
                  <th>Filename</th>
                  <th>Confidence</th>
                  <th>Reason</th>
                  <th>Vendor</th>
                  <th>Amount</th>
                  <th>Date</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {reviewQueue.map((document) => {
                  const draft = reviewDrafts[document.id] ?? toReviewDraft(document);
                  const isSavingThisDocument = reviewActionDocumentId === document.id;
                  const disableReviewActions = reviewActionDocumentId !== null;
                  return (
                    <Fragment key={`review-${document.id}`}>
                      <tr>
                        <td>{document.filename}</td>
                        <td>{renderConfidence(document)}</td>
                        <td>{document.extracted_data?.review_reason || '—'}</td>
                        <td>{document.extracted_data?.vendor_name || '—'}</td>
                        <td>
                          {typeof document.extracted_data?.total_amount === 'number'
                            ? `£${document.extracted_data.total_amount.toFixed(2)}`
                            : '—'}
                        </td>
                        <td>{document.extracted_data?.transaction_date || '—'}</td>
                        <td>
                          <div className={styles.reviewQueueActions}>
                            <button
                              className={styles.tableActionButton}
                              disabled={disableReviewActions}
                              onClick={() => handleReviewAction(document, 'confirmed')}
                              type="button"
                            >
                              {isSavingThisDocument ? 'Saving...' : 'Confirm'}
                            </button>
                            <button
                              className={`${styles.tableActionButton} ${styles.reviewDangerAction}`}
                              disabled={disableReviewActions}
                              onClick={() => handleReviewAction(document, 'ignored')}
                              type="button"
                            >
                              Ignore
                            </button>
                          </div>
                        </td>
                      </tr>
                      <tr className={styles.reviewEditorRow}>
                        <td className={styles.reviewEditorCell} colSpan={7}>
                          <div className={styles.reviewEditorGrid}>
                            <label className={styles.reviewField}>
                              <span>Vendor</span>
                              <input
                                className={`${styles.input} ${styles.reviewInput}`}
                                onChange={(event) => handleReviewDraftChange(document.id, 'vendor_name', event.target.value)}
                                type="text"
                                value={draft.vendor_name}
                              />
                            </label>
                            <label className={styles.reviewField}>
                              <span>Amount</span>
                              <input
                                className={`${styles.input} ${styles.reviewInput}`}
                                min="0"
                                onChange={(event) => handleReviewDraftChange(document.id, 'total_amount', event.target.value)}
                                step="0.01"
                                type="number"
                                value={draft.total_amount}
                              />
                            </label>
                            <label className={styles.reviewField}>
                              <span>Date</span>
                              <input
                                className={`${styles.input} ${styles.reviewInput}`}
                                onChange={(event) =>
                                  handleReviewDraftChange(document.id, 'transaction_date', event.target.value)
                                }
                                type="date"
                                value={draft.transaction_date}
                              />
                            </label>
                            <label className={styles.reviewField}>
                              <span>Category</span>
                              <input
                                className={`${styles.input} ${styles.reviewInput}`}
                                onChange={(event) =>
                                  handleReviewDraftChange(document.id, 'suggested_category', event.target.value)
                                }
                                type="text"
                                value={draft.suggested_category}
                              />
                            </label>
                            <label className={styles.reviewField}>
                              <span>Expense article</span>
                              <input
                                className={`${styles.input} ${styles.reviewInput}`}
                                onChange={(event) =>
                                  handleReviewDraftChange(document.id, 'expense_article', event.target.value)
                                }
                                type="text"
                                value={draft.expense_article}
                              />
                            </label>
                            <label className={styles.reviewField}>
                              <span>Deductible</span>
                              <select
                                className={`${styles.categorySelect} ${styles.reviewSelect}`}
                                onChange={(event) =>
                                  handleReviewDraftChange(
                                    document.id,
                                    'is_potentially_deductible',
                                    event.target.value as DeductibleSelection
                                  )
                                }
                                value={draft.is_potentially_deductible}
                              >
                                <option value="unknown">Unknown</option>
                                <option value="true">Yes</option>
                                <option value="false">No</option>
                              </select>
                            </label>
                          </div>
                          <label className={styles.reviewField}>
                            <span>Review notes</span>
                            <textarea
                              className={`${styles.input} ${styles.reviewTextarea}`}
                              onChange={(event) => handleReviewDraftChange(document.id, 'review_notes', event.target.value)}
                              rows={2}
                              value={draft.review_notes}
                            />
                          </label>
                          <div className={styles.reviewEditorActions}>
                            <button
                              className={styles.tableActionButton}
                              disabled={disableReviewActions}
                              onClick={() => handleReviewAction(document, 'corrected')}
                              type="button"
                            >
                              {isSavingThisDocument ? 'Saving...' : 'Save correction'}
                            </button>
                          </div>
                        </td>
                      </tr>
                    </Fragment>
                  );
                })}
              </tbody>
            </table>
          )}
        </div>

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
                <th>{t('documents.col_vendor')}</th>
                <th>{t('documents.col_amount')}</th>
                <th>{t('documents.col_category')}</th>
                <th>{t('documents.col_expense_article')}</th>
                <th>{t('documents.col_deductible')}</th>
                <th>{t('documents.col_receipt_draft')}</th>
                <th>OCR confidence</th>
                <th>Review</th>
                <th>{t('documents.col_uploaded_at')}</th>
              </tr>
            </thead>
            <tbody>
              {documents.map((document) => {
                const reviewChangeEntries = getReviewChangeEntries(document.extracted_data?.review_changes);
                return (
                  <Fragment key={document.id}>
                    <tr>
                      <td>{document.filename}</td>
                      <td>
                        <span className={`${styles.status} ${styles[document.status]}`}>{document.status}</span>
                      </td>
                      <td>{document.extracted_data?.vendor_name || '—'}</td>
                      <td>
                        {typeof document.extracted_data?.total_amount === 'number'
                          ? `£${document.extracted_data.total_amount.toFixed(2)}`
                          : '—'}
                      </td>
                      <td>{document.extracted_data?.suggested_category || '—'}</td>
                      <td>{document.extracted_data?.expense_article || '—'}</td>
                      <td>
                        {document.extracted_data?.is_potentially_deductible === true
                          ? 'Yes'
                          : document.extracted_data?.is_potentially_deductible === false
                            ? 'No'
                            : '—'}
                      </td>
                      <td>{document.extracted_data?.receipt_draft_transaction_id || '—'}</td>
                      <td>{renderConfidence(document)}</td>
                      <td>{renderReviewBadge(document)}</td>
                      <td>{new Date(document.uploaded_at).toLocaleString()}</td>
                    </tr>
                    {reviewChangeEntries.length > 0 ? (
                      <tr className={styles.reviewDiffRow}>
                        <td className={styles.reviewDiffCell} colSpan={11}>
                          <div className={styles.reviewDiffHeader}>Manual review changes</div>
                          <div className={styles.reviewDiffList}>
                            {reviewChangeEntries.map(([field, change]) => (
                              <div className={styles.reviewDiffItem} key={`${document.id}-${field}`}>
                                <span className={styles.reviewDiffField}>{REVIEW_FIELD_LABELS[field] || field}</span>
                                <span className={styles.reviewDiffBefore}>{formatReviewValue(field, change.before ?? null)}</span>
                                <span className={styles.reviewDiffArrow}>→</span>
                                <span className={styles.reviewDiffAfter}>{formatReviewValue(field, change.after ?? null)}</span>
                              </div>
                            ))}
                          </div>
                        </td>
                      </tr>
                    ) : null}
                  </Fragment>
                );
              })}
            </tbody>
          </table>
        )}
      </div>

      <SemanticSearch token={token} />
    </div>
  );
}
