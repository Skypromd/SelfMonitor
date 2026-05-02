import Link from 'next/link';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { transactionsBearerHeaders, useTransactionsBusinessScope } from '../lib/transactionsBusinessScope';
import styles from '../styles/Home.module.css';

const API_GATEWAY_ROOT = (process.env.NEXT_PUBLIC_API_GATEWAY_URL || '/api').replace(/\/$/, '');
const TRANSACTIONS_API_BASE = `${API_GATEWAY_ROOT}/transactions`;
const BANKING_SERVICE_URL =
  process.env.NEXT_PUBLIC_BANKING_SERVICE_URL || '/api/banking';
const OPEN_BANKING_PROVIDER =
  (process.env.NEXT_PUBLIC_OPEN_BANKING_PROVIDER || 'saltedge').trim().toLowerCase();
const CATEGORIZATION_SERVICE_URL =
  process.env.NEXT_PUBLIC_CATEGORIZATION_SERVICE_URL || '/api/categorization';

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

type CISReviewTask = {
  id: string;
  user_id: string;
  status: string;
  suspected_transaction_id: string | null;
  cis_record_id: string | null;
  payer_label: string | null;
  suspect_reason: string | null;
  next_reminder_at: string | null;
  created_at: string;
  updated_at: string;
};

const CIS_API = `${TRANSACTIONS_API_BASE}/cis`;

function monthBoundsFromDate(isoDate: string): { period_start: string; period_end: string } {
  const [yStr, mStr] = isoDate.split('-');
  const y = Number(yStr);
  const m = Number(mStr) - 1;
  if (!y || m < 0 || m > 11) {
    const t = new Date();
    const yy = t.getFullYear();
    const mm = t.getMonth();
    const start = `${yy}-${String(mm + 1).padStart(2, '0')}-01`;
    const last = new Date(yy, mm + 1, 0).getDate();
    const end = `${yy}-${String(mm + 1).padStart(2, '0')}-${String(last).padStart(2, '0')}`;
    return { period_start: start, period_end: end };
  }
  const last = new Date(y, m + 1, 0).getDate();
  const period_start = `${y}-${String(m + 1).padStart(2, '0')}-01`;
  const period_end = `${y}-${String(m + 1).padStart(2, '0')}-${String(last).padStart(2, '0')}`;
  return { period_start, period_end };
}

function escapeCsvField(value: string): string {
  if (/[",\n\r]/.test(value)) {
    return `"${value.replace(/"/g, '""')}"`;
  }
  return value;
}

function downloadTransactionsCsv(rows: TransactionRecord[]): void {
  const header = ['id', 'date', 'description', 'amount', 'currency', 'category', 'reconciliation_status'];
  const lines = [
    header.join(','),
    ...rows.map((t) =>
      [
        escapeCsvField(t.id),
        escapeCsvField(t.date),
        escapeCsvField(t.description),
        String(t.amount),
        escapeCsvField(t.currency),
        escapeCsvField(t.category || ''),
        escapeCsvField(t.reconciliation_status || ''),
      ].join(','),
    ),
  ];
  const blob = new Blob([`\uFEFF${lines.join('\n')}`], { type: 'text/csv;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `transactions-${new Date().toISOString().slice(0, 10)}.csv`;
  a.click();
  URL.revokeObjectURL(url);
}

type SyncQuota = { daily_limit: number; used_today: number; remaining: number };

function BankConnection({ token, onConnectionComplete }: { token: string, onConnectionComplete: (accountId: string) => void }) {
  const [error, setError] = useState('');
  const [isConnecting, setIsConnecting] = useState(false);
  const [syncQuota, setSyncQuota] = useState<SyncQuota | null>(null);

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      try {
        const res = await fetch(`${BANKING_SERVICE_URL}/connections/sync-quota`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (!res.ok) return;
        const data = (await res.json()) as SyncQuota;
        if (!cancelled && typeof data.daily_limit === 'number') setSyncQuota(data);
      } catch {
        /* ignore */
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [token]);

  const handleConnectBank = async () => {
    setError('');
    setIsConnecting(true);
    try {
      const callbackUrl = typeof window !== 'undefined'
        ? `${window.location.origin}/connect-bank/callback`
        : 'http://localhost:3000/connect-bank/callback';

      const response = await fetch(`${BANKING_SERVICE_URL}/connections/initiate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
        body: JSON.stringify({ provider_id: OPEN_BANKING_PROVIDER, redirect_uri: callbackUrl }),
      });
      if (!response.ok) throw new Error((await response.json()).detail || 'Failed to initiate connection');
      const data = await response.json();

      // Store token so the callback page can use it
      if (typeof window !== 'undefined') {
        sessionStorage.setItem('bankingToken', token);
        sessionStorage.setItem('bankingProviderId', OPEN_BANKING_PROVIDER);
      }
      // Real OAuth redirect to TrueLayer
      window.location.href = data.consent_url;
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unexpected error');
      setIsConnecting(false);
    }
  };

  return (
    <div className={styles.subContainer}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
        <h2 style={{ margin: 0 }}>Bank Connections</h2>
        <span style={{ fontSize: '0.78rem', color: 'var(--lp-muted)', background: 'rgba(13,148,136,0.1)', border: '1px solid rgba(13,148,136,0.3)', borderRadius: 999, padding: '2px 10px' }}>
          {OPEN_BANKING_PROVIDER === 'truelayer'
            ? 'Powered by TrueLayer Open Banking'
            : 'Powered by Salt Edge Open Banking'}
        </span>
      </div>
      <p style={{ color: 'var(--lp-muted)', fontSize: '0.9rem', marginBottom: '1.25rem' }}>
        Connect your bank account to automatically import transactions. You control when data syncs — we never fetch automatically.{' '}
        <Link href="/connect-bank" style={{ color: 'var(--lp-accent-teal)', fontWeight: 600 }}>
          Browse Open Banking providers
        </Link>
      </p>
      {syncQuota && (
        <p style={{ color: 'var(--lp-muted)', fontSize: '0.85rem', marginBottom: '1rem' }}>
          {syncQuota.daily_limit <= 0
            ? 'Manual bank sync is not included in your current plan (UTC daily limits).'
            : `Manual syncs left today (UTC): ${syncQuota.remaining} of ${syncQuota.daily_limit}`}
        </p>
      )}
      <button
        onClick={handleConnectBank}
        disabled={isConnecting}
        style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', padding: '0.75rem 1.5rem', background: 'var(--lp-accent-teal)', color: '#fff', border: 'none', borderRadius: 10, fontWeight: 700, cursor: isConnecting ? 'wait' : 'pointer', opacity: isConnecting ? 0.7 : 1, fontSize: '0.95rem' }}
        type="button"
      >
        🏦 {isConnecting ? 'Redirecting to your bank…' : 'Connect Bank Account'}
      </button>
      {error && <p className={styles.error} style={{ marginTop: '0.75rem' }}>{error}</p>}
    </div>
  );
}

function TransactionsList({ token, accountId, businessId }: { token: string; accountId: string; businessId: string | null }) {
  const [transactions, setTransactions] = useState<TransactionRecord[]>([]);
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [cisTasks, setCisTasks] = useState<CISReviewTask[]>([]);
  const [cisBusy, setCisBusy] = useState(false);
  const [modalTask, setModalTask] = useState<CISReviewTask | null>(null);
  const [cisModalError, setCisModalError] = useState('');
  const [cisResolveBusy, setCisResolveBusy] = useState(false);
  const [flaggingTxn, setFlaggingTxn] = useState('');
  const [cisZipBusy, setCisZipBusy] = useState(false);
  const [cisShareBusy, setCisShareBusy] = useState(false);
  const [cisShareMsg, setCisShareMsg] = useState('');
  const [cisForm, setCisForm] = useState({
    mode: 'self_attest' as 'verified' | 'self_attest',
    contractorName: '',
    cisDeducted: '',
    documentId: '',
    ackUnderstand: false,
    ackAccuracy: false,
  });

  const availableCategories = [
  'groceries', 'transport', 'income', 'food_and_drink', 'subscriptions',
  'office_supplies', 'utilities', 'rent', 'insurance', 'professional_services',
  'advertising', 'entertainment', 'travel', 'equipment', 'software', 'other',
];

  const reloadCisTasks = useCallback(async () => {
    try {
      const res = await fetch(`${CIS_API}/tasks?status=open`, {
        headers: transactionsBearerHeaders(token, businessId),
      });
      if (res.ok) setCisTasks((await res.json()) as CISReviewTask[]);
    } catch { /* ignore */ }
  }, [token, businessId]);

  useEffect(() => {
    void reloadCisTasks();
  }, [reloadCisTasks]);

  const openTaskByTxnId = useMemo(() => {
    const m = new Map<string, CISReviewTask>();
    for (const t of cisTasks) {
      if (t.status === 'open' && t.suspected_transaction_id) m.set(t.suspected_transaction_id, t);
    }
    return m;
  }, [cisTasks]);

  const modalTxn = useMemo(() => {
    if (!modalTask?.suspected_transaction_id) return null;
    return transactions.find((x) => x.id === modalTask.suspected_transaction_id) ?? null;
  }, [modalTask, transactions]);

  const cisFormInitKeyRef = useRef<string | null>(null);

  const [txnFilterDateFrom, setTxnFilterDateFrom] = useState('');
  const [txnFilterDateTo, setTxnFilterDateTo] = useState('');
  const [txnFilterCategory, setTxnFilterCategory] = useState('');
  const [inboxFilter, setInboxFilter] = useState<'all' | 'uncategorised' | 'no_receipt' | 'cis_unverified'>('all');

  const displayedTransactions = useMemo(() => {
    return transactions.filter((t) => {
      if (txnFilterDateFrom && t.date < txnFilterDateFrom) return false;
      if (txnFilterDateTo && t.date > txnFilterDateTo) return false;
      if (txnFilterCategory === '__uncategorized__') {
        if (t.category) return false;
      } else if (txnFilterCategory && (t.category || '') !== txnFilterCategory) return false;
      if (inboxFilter === 'uncategorised' && t.category) return false;
      if (inboxFilter === 'no_receipt' && t.reconciliation_status !== 'unmatched') return false;
      if (inboxFilter === 'cis_unverified' && !openTaskByTxnId.has(t.id)) return false;
      return true;
    });
  }, [transactions, txnFilterDateFrom, txnFilterDateTo, txnFilterCategory, inboxFilter, openTaskByTxnId]);

  useEffect(() => {
    if (!modalTask || !modalTxn) {
      cisFormInitKeyRef.current = null;
      return;
    }
    const key = `${modalTask.id}:${modalTxn.id}`;
    if (cisFormInitKeyRef.current === key) return;
    cisFormInitKeyRef.current = key;
    setCisModalError('');
    setCisForm({
      mode: 'self_attest',
      contractorName: modalTask.payer_label || modalTxn.description.slice(0, 120),
      cisDeducted: '',
      documentId: '',
      ackUnderstand: false,
      ackAccuracy: false,
    });
  }, [modalTask, modalTxn]);

  const handleCisScan = async () => {
    setCisBusy(true);
    try {
      await fetch(`${CIS_API}/tasks/scan`, { method: 'POST', headers: transactionsBearerHeaders(token, businessId) });
      await reloadCisTasks();
    } finally {
      setCisBusy(false);
    }
  };

  const handleCisEvidenceZip = async () => {
    setCisZipBusy(true);
    try {
      const res = await fetch(`${CIS_API}/evidence-pack/zip`, {
        headers: transactionsBearerHeaders(token, businessId),
      });
      if (!res.ok) return;
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'mynettax-cis-evidence-pack.zip';
      a.click();
      URL.revokeObjectURL(url);
    } finally {
      setCisZipBusy(false);
    }
  };

  const handleAccountantEvidenceLink = async () => {
    setCisShareBusy(true);
    setCisShareMsg('');
    try {
      const res = await fetch(`${CIS_API}/evidence-pack/share-token`, {
        method: 'POST',
        headers: transactionsBearerHeaders(token, businessId),
      });
      if (res.status === 403) {
        setCisShareMsg('Evidence pack requires Growth or higher.');
        return;
      }
      if (!res.ok) {
        setCisShareMsg('Could not create accountant link.');
        return;
      }
      const data = (await res.json()) as {
        token: string;
        relative_download_path: string;
      };
      const path = `${TRANSACTIONS_API_BASE}${data.relative_download_path}?token=${encodeURIComponent(
        data.token,
      )}`;
      const absolute =
        typeof window !== 'undefined' ? `${window.location.origin}${path}` : path;
      try {
        await navigator.clipboard.writeText(absolute);
        setCisShareMsg(
          'Accountant link copied. It expires after the hours set on the server — share only over a secure channel.',
        );
      } catch {
        window.prompt('Copy this link for your accountant:', absolute);
        setCisShareMsg('');
      }
    } catch {
      setCisShareMsg('Could not copy link. Try again or use Download evidence ZIP.');
    } finally {
      setCisShareBusy(false);
    }
  };

  const flagCisSuspect = async (transactionId: string) => {
    setFlaggingTxn(transactionId);
    try {
      const res = await fetch(`${CIS_API}/tasks/suspect`, {
        method: 'POST',
        headers: transactionsBearerHeaders(token, businessId, { 'Content-Type': 'application/json' }),
        body: JSON.stringify({ transaction_id: transactionId, reason: 'user_flagged' }),
      });
      if (res.ok) await reloadCisTasks();
    } catch { /* ignore */ } finally {
      setFlaggingTxn('');
    }
  };

  const closeCisModal = () => {
    setModalTask(null);
    setCisModalError('');
  };

  const resolveNotCis = async () => {
    if (!modalTask) return;
    setCisResolveBusy(true);
    setCisModalError('');
    try {
      const res = await fetch(`${CIS_API}/tasks/${modalTask.id}`, {
        method: 'PATCH',
        headers: transactionsBearerHeaders(token, businessId, { 'Content-Type': 'application/json' }),
        body: JSON.stringify({ status: 'dismissed_not_cis' }),
      });
      if (!res.ok) {
        const j = await res.json().catch(() => ({}));
        throw new Error((j as { detail?: string }).detail || 'Could not update task');
      }
      await reloadCisTasks();
      closeCisModal();
    } catch (e) {
      setCisModalError(e instanceof Error ? e.message : 'Failed');
    } finally {
      setCisResolveBusy(false);
    }
  };

  const snoozeCisTask = async () => {
    if (!modalTask) return;
    setCisResolveBusy(true);
    setCisModalError('');
    try {
      const res = await fetch(`${CIS_API}/tasks/${modalTask.id}/snooze-reminder?days=30`, {
        method: 'POST',
        headers: transactionsBearerHeaders(token, businessId),
      });
      if (!res.ok) throw new Error('Snooze failed');
      await reloadCisTasks();
      closeCisModal();
    } catch (e) {
      setCisModalError(e instanceof Error ? e.message : 'Failed');
    } finally {
      setCisResolveBusy(false);
    }
  };

  const submitCisResolution = async () => {
    if (!modalTask || !modalTxn) return;
    const name = cisForm.contractorName.trim();
    if (!name) {
      setCisModalError('Enter contractor / payer name.');
      return;
    }
    const cisDed = parseFloat(cisForm.cisDeducted) || 0;
    if (cisDed < 0) {
      setCisModalError('CIS deducted cannot be negative.');
      return;
    }
    const netPaid = modalTxn.amount;
    const gross = Math.max(0, netPaid + cisDed);
    const { period_start, period_end } = monthBoundsFromDate(modalTxn.date);

    if (cisForm.mode === 'self_attest') {
      if (!cisForm.ackUnderstand || !cisForm.ackAccuracy) {
        setCisModalError('Confirm both declarations to save a self-attested CIS record.');
        return;
      }
    }

    setCisResolveBusy(true);
    setCisModalError('');
    try {
      const evidenceStatus =
        cisForm.mode === 'verified' ? 'verified_with_statement' : 'self_attested_no_statement';
      const docId = cisForm.documentId.trim() || undefined;
      if (cisForm.mode === 'verified' && !docId) {
        setCisModalError('Enter a document ID for verified CIS, or choose self-attested.');
        setCisResolveBusy(false);
        return;
      }

      const attestation =
        cisForm.mode === 'self_attest'
          ? {
              attestation_version: 'mynettax_cis_v1',
              attestation_text: [
                'User confirmed:',
                `understands_unverified_cis_risk=${cisForm.ackUnderstand}`,
                `figures_accurate_best_knowledge=${cisForm.ackAccuracy}`,
                `bank_transaction_id=${modalTxn.id}`,
              ].join('\n'),
              client_context: { task_id: modalTask.id },
            }
          : undefined;

      const recordBody: Record<string, unknown> = {
        contractor_name: name,
        period_start,
        period_end,
        gross_total: gross,
        materials_total: 0,
        cis_deducted_total: cisDed,
        net_paid_total: netPaid,
        evidence_status: evidenceStatus,
        document_id: docId ?? null,
        source: 'manual_attested',
        matched_bank_transaction_ids: [modalTxn.id],
        report_status: 'draft',
      };
      if (attestation) recordBody.attestation = attestation;

      const recRes = await fetch(`${CIS_API}/records`, {
        method: 'POST',
        headers: transactionsBearerHeaders(token, businessId, { 'Content-Type': 'application/json' }),
        body: JSON.stringify(recordBody),
      });
      const recJson = await recRes.json().catch(() => ({}));
      if (!recRes.ok) {
        throw new Error((recJson as { detail?: string }).detail || 'Could not create CIS record');
      }
      const recordId = (recJson as { id: string }).id;
      const patchStatus = cisForm.mode === 'verified' ? 'resolved_verified' : 'resolved_unverified';
      const patchRes = await fetch(`${CIS_API}/tasks/${modalTask.id}`, {
        method: 'PATCH',
        headers: transactionsBearerHeaders(token, businessId, { 'Content-Type': 'application/json' }),
        body: JSON.stringify({ status: patchStatus, cis_record_id: recordId, payer_label: name }),
      });
      if (!patchRes.ok) {
        const pj = await patchRes.json().catch(() => ({}));
        throw new Error((pj as { detail?: string }).detail || 'Could not close CIS task');
      }
      await reloadCisTasks();
      closeCisModal();
    } catch (e) {
      setCisModalError(e instanceof Error ? e.message : 'Failed');
    } finally {
      setCisResolveBusy(false);
    }
  };

  useEffect(() => {
    if (!accountId) return;
    setIsLoading(true);
    setError('');
    const timeoutId = window.setTimeout(async () => {
      try {
        const response = await fetch(`${TRANSACTIONS_API_BASE}/accounts/${accountId}/transactions`, {
          headers: transactionsBearerHeaders(token, businessId),
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
  }, [accountId, token, businessId]);

  const [isAutoCategorizing, setIsAutoCategorizing] = useState(false);

  const handleAutoCategorize = async () => {
    const uncategorized = transactions.filter((t) => !t.category);
    if (uncategorized.length === 0) return;
    setIsAutoCategorizing(true);
    try {
      const results = await Promise.all(
        uncategorized.map(async (t) => {
          try {
            const res = await fetch(`${CATEGORIZATION_SERVICE_URL}/categorize`, {
              method: 'POST',
              headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
              body: JSON.stringify({ description: t.description }),
            });
            if (res.ok) {
              const data = await res.json();
              return { id: t.id, category: data.category as string | null };
            }
          } catch { /* ignore */ }
          return { id: t.id, category: null };
        })
      );
      setTransactions((prev) =>
        prev.map((t) => {
          const hit = results.find((r) => r.id === t.id);
          return hit?.category ? { ...t, category: hit.category } : t;
        })
      );
    } finally {
      setIsAutoCategorizing(false);
    }
  };

  const handleCategoryChange = async (transactionId: string, newCategory: string) => {
    const row = transactions.find((t) => t.id === transactionId);
    try {
      const response = await fetch(`${TRANSACTIONS_API_BASE}/transactions/${transactionId}`, {
        method: 'PATCH',
        headers: transactionsBearerHeaders(token, businessId, { 'Content-Type': 'application/json' }),
        body: JSON.stringify({ category: newCategory })
      });
      if (!response.ok) throw new Error('Failed to update category');
      setTransactions(transactions.map(t => t.id === transactionId ? { ...t, category: newCategory } : t));
      if (row?.description) {
        void fetch(`${CATEGORIZATION_SERVICE_URL}/learn`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
          body: JSON.stringify({ description: row.description, category: newCategory }),
        }).catch(() => {});
      }
    } catch (err) {
      console.error('Failed to update category:', err);
    }
  };

  const cisBanner = (
    <div
      style={{
        marginBottom: '1rem',
        padding: '0.75rem 1rem',
        borderRadius: 10,
        border: '1px solid rgba(245,158,11,0.35)',
        background: 'rgba(245,158,11,0.08)',
        display: 'flex',
        flexWrap: 'wrap',
        gap: '0.5rem',
        alignItems: 'center',
        justifyContent: 'space-between',
      }}
    >
      <span style={{ fontSize: '0.88rem' }}>
        <strong>CIS reviews:</strong>{' '}
        {cisTasks.length === 0
          ? 'No open CIS tasks. Scan imports for possible CIS income.'
          : `${cisTasks.length} open — use Review on the row or resolve below.`}
      </span>
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem' }}>
        <button
          type="button"
          disabled={cisBusy}
          onClick={() => void handleCisScan()}
          style={{
            padding: '0.35rem 0.85rem',
            borderRadius: 8,
            border: '1px solid var(--lp-accent-teal)',
            background: 'rgba(13,148,136,0.12)',
            color: 'var(--lp-accent-teal)',
            fontWeight: 600,
            fontSize: '0.82rem',
            cursor: cisBusy ? 'wait' : 'pointer',
          }}
        >
          {cisBusy ? 'Scanning…' : 'Scan for CIS suspects'}
        </button>
        <button
          type="button"
          disabled={cisZipBusy}
          onClick={() => void handleCisEvidenceZip()}
          style={{
            padding: '0.35rem 0.85rem',
            borderRadius: 8,
            border: '1px solid var(--lp-border)',
            background: 'transparent',
            color: 'var(--lp-muted)',
            fontWeight: 600,
            fontSize: '0.82rem',
            cursor: cisZipBusy ? 'wait' : 'pointer',
          }}
        >
          {cisZipBusy ? 'ZIP…' : 'Download evidence ZIP'}
        </button>
        <button
          type="button"
          disabled={cisShareBusy}
          onClick={() => void handleAccountantEvidenceLink()}
          style={{
            padding: '0.35rem 0.85rem',
            borderRadius: 8,
            border: '1px solid rgba(59,130,246,0.45)',
            background: 'rgba(59,130,246,0.1)',
            color: 'rgb(96,165,250)',
            fontWeight: 600,
            fontSize: '0.82rem',
            cursor: cisShareBusy ? 'wait' : 'pointer',
          }}
        >
          {cisShareBusy ? 'Link…' : 'Accountant download link'}
        </button>
      </div>
      {cisShareMsg ? (
        <p style={{ margin: '0.35rem 0 0', fontSize: '0.78rem', color: 'var(--lp-muted)', width: '100%' }}>
          {cisShareMsg}
        </p>
      ) : null}
    </div>
  );

  const cisModal = modalTask && modalTxn && (
    <div
      role="dialog"
      aria-modal="true"
      style={{
        position: 'fixed',
        inset: 0,
        background: 'rgba(15,23,42,0.55)',
        zIndex: 1000,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '1rem',
      }}
      onClick={cisResolveBusy ? undefined : closeCisModal}
    >
      <div
        style={{
          background: 'var(--lp-bg-elevated)',
          borderRadius: 16,
          maxWidth: 520,
          width: '100%',
          padding: '1.5rem',
          border: '1px solid var(--lp-border)',
          boxShadow: '0 20px 50px rgba(0,0,0,0.35)',
        }}
        onClick={(e) => e.stopPropagation()}
      >
        <h3 style={{ marginTop: 0 }}>Confirm CIS</h3>
        <p style={{ color: 'var(--lp-muted)', fontSize: '0.88rem', lineHeight: 1.5 }}>
          {modalTxn.date} · {modalTxn.description} ·{' '}
          <strong>{modalTxn.amount.toFixed(2)} {modalTxn.currency}</strong>
        </p>
        <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '1rem', flexWrap: 'wrap' }}>
          <button
            type="button"
            onClick={() => setCisForm((f) => ({ ...f, mode: 'verified' }))}
            style={{
              padding: '0.4rem 0.75rem',
              borderRadius: 8,
              border: cisForm.mode === 'verified' ? '2px solid var(--lp-accent-teal)' : '1px solid var(--lp-border)',
              background: cisForm.mode === 'verified' ? 'rgba(13,148,136,0.15)' : 'transparent',
              cursor: 'pointer',
              fontSize: '0.82rem',
            }}
          >
            Statement on file
          </button>
          <button
            type="button"
            onClick={() => setCisForm((f) => ({ ...f, mode: 'self_attest' }))}
            style={{
              padding: '0.4rem 0.75rem',
              borderRadius: 8,
              border: cisForm.mode === 'self_attest' ? '2px solid var(--lp-accent-teal)' : '1px solid var(--lp-border)',
              background: cisForm.mode === 'self_attest' ? 'rgba(13,148,136,0.15)' : 'transparent',
              cursor: 'pointer',
              fontSize: '0.82rem',
            }}
          >
            Self-attested (no statement)
          </button>
        </div>
        <label style={{ display: 'block', marginBottom: '0.75rem', fontSize: '0.85rem' }}>
          Contractor / payer name
          <input
            className={styles.input}
            style={{ width: '100%', marginTop: 6 }}
            value={cisForm.contractorName}
            onChange={(e) => setCisForm((f) => ({ ...f, contractorName: e.target.value }))}
          />
        </label>
        <label style={{ display: 'block', marginBottom: '0.75rem', fontSize: '0.85rem' }}>
          CIS tax deducted (optional, GBP)
          <input
            className={styles.input}
            type="number"
            step="0.01"
            style={{ width: '100%', marginTop: 6 }}
            value={cisForm.cisDeducted}
            onChange={(e) => setCisForm((f) => ({ ...f, cisDeducted: e.target.value }))}
          />
        </label>
        {cisForm.mode === 'verified' && (
          <label style={{ display: 'block', marginBottom: '0.75rem', fontSize: '0.85rem' }}>
            Document ID (CIS statement already uploaded)
            <input
              className={styles.input}
              style={{ width: '100%', marginTop: 6 }}
              value={cisForm.documentId}
              onChange={(e) => setCisForm((f) => ({ ...f, documentId: e.target.value }))}
              placeholder="UUID from Documents"
            />
          </label>
        )}
        {cisForm.mode === 'self_attest' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', marginBottom: '1rem', fontSize: '0.84rem' }}>
            <label style={{ display: 'flex', gap: '0.5rem', alignItems: 'flex-start', cursor: 'pointer' }}>
              <input
                type="checkbox"
                checked={cisForm.ackUnderstand}
                onChange={(e) => setCisForm((f) => ({ ...f, ackUnderstand: e.target.checked }))}
              />
              <span>I understand HMRC may disallow CIS credits without matching statements.</span>
            </label>
            <label style={{ display: 'flex', gap: '0.5rem', alignItems: 'flex-start', cursor: 'pointer' }}>
              <input
                type="checkbox"
                checked={cisForm.ackAccuracy}
                onChange={(e) => setCisForm((f) => ({ ...f, ackAccuracy: e.target.checked }))}
              />
              <span>The amounts I enter match my records to the best of my knowledge.</span>
            </label>
          </div>
        )}
        {cisModalError && <p className={styles.error}>{cisModalError}</p>}
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem', marginTop: '1rem' }}>
          <button
            type="button"
            className={styles.secondaryButton}
            disabled={cisResolveBusy}
            onClick={() => void resolveNotCis()}
          >
            Not CIS
          </button>
          <button
            type="button"
            className={styles.secondaryButton}
            disabled={cisResolveBusy}
            onClick={() => void snoozeCisTask()}
          >
            Remind in 30 days
          </button>
          <button
            type="button"
            disabled={cisResolveBusy}
            onClick={() => void submitCisResolution()}
            style={{
              marginLeft: 'auto',
              padding: '0.5rem 1rem',
              borderRadius: 8,
              border: 'none',
              background: 'var(--lp-accent-teal)',
              color: '#fff',
              fontWeight: 700,
              cursor: cisResolveBusy ? 'wait' : 'pointer',
            }}
          >
            {cisResolveBusy ? 'Saving…' : 'Save & resolve'}
          </button>
        </div>
      </div>
    </div>
  );

  if (!accountId) {
    return (
      <div className={styles.subContainer}>
        <h2 style={{ marginTop: 0 }}>Recent Transactions</h2>
        {cisBanner}
        <p className={styles.emptyState}>Connect a bank account to load transactions for this view.</p>
        {cisModal}
      </div>
    );
  }
  if (isLoading) {
    return (
      <div className={styles.subContainer}>
        <h2>Recent Transactions</h2>
        {cisBanner}
        <div className={styles.skeletonTable}>
          {Array.from({ length: 6 }).map((_, index) => (
            <div className={styles.skeletonRow} key={index}>
              <div className={styles.skeletonCell} />
              <div className={styles.skeletonCell} />
              <div className={styles.skeletonCell} />
            </div>
          ))}
        </div>
        {cisModal}
      </div>
    );
  }
  if (error) {
    return (
      <div className={styles.subContainer}>
        <h2>Recent Transactions</h2>
        {cisBanner}
        <p className={styles.error}>{error}</p>
        {cisModal}
      </div>
    );
  }
  if (!transactions.length) {
    return (
      <div className={styles.subContainer}>
        <h2>Recent Transactions</h2>
        {cisBanner}
        <p className={styles.emptyState}>No transactions available for this connection yet.</p>
        {cisModal}
      </div>
    );
  }

  const filterInputStyle = {
    padding: '0.35rem 0.5rem',
    borderRadius: 8,
    border: '1px solid var(--lp-border)',
    background: 'var(--lp-bg-elevated)',
    color: 'var(--text-primary)',
    fontSize: '0.82rem',
  };

  return (
    <div className={styles.subContainer}>
      {cisModal}
      {cisBanner}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem', flexWrap: 'wrap', gap: '0.5rem' }}>
        <h2 style={{ margin: 0 }}>Recent Transactions</h2>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem', marginLeft: 'auto' }}>
          <button
            type="button"
            onClick={() => downloadTransactionsCsv(displayedTransactions)}
            disabled={displayedTransactions.length === 0}
            style={{
              padding: '0.35rem 0.85rem', borderRadius: 8, border: '1px solid var(--lp-border)',
              background: 'var(--lp-bg-elevated)', color: 'var(--lp-muted)',
              cursor: displayedTransactions.length === 0 ? 'not-allowed' : 'pointer', fontSize: '0.82rem', fontWeight: 600,
              opacity: displayedTransactions.length === 0 ? 0.5 : 1,
            }}
          >
            Export CSV
          </button>
          {transactions.some((t) => !t.category) && (
            <button
              type="button"
              onClick={handleAutoCategorize}
              disabled={isAutoCategorizing}
              style={{
                padding: '0.35rem 0.85rem', borderRadius: 8, border: '1px solid var(--lp-accent-teal)',
                background: 'rgba(13,148,136,0.1)', color: 'var(--lp-accent-teal)',
                cursor: 'pointer', fontSize: '0.82rem', fontWeight: 600,
              }}
            >
              {isAutoCategorizing ? 'Categorizing…' : '✦ Auto-Categorize'}
            </button>
          )}
        </div>
      </div>
      <div
        style={{
          display: 'flex',
          flexWrap: 'wrap',
          gap: '0.35rem',
          marginBottom: '0.75rem',
        }}
      >
        {(
          [
            { key: 'all', label: 'All' },
            { key: 'uncategorised', label: `Uncategorised (${transactions.filter((t) => !t.category).length})` },
            { key: 'no_receipt', label: `No Receipt (${transactions.filter((t) => t.reconciliation_status === 'unmatched').length})` },
            { key: 'cis_unverified', label: `CIS Unverified (${transactions.filter((t) => openTaskByTxnId.has(t.id)).length})` },
          ] as const
        ).map(({ key, label }) => (
          <button
            key={key}
            type="button"
            onClick={() => setInboxFilter(key)}
            style={{
              padding: '0.28rem 0.8rem',
              borderRadius: 999,
              border: `1px solid ${inboxFilter === key ? 'var(--lp-accent-teal)' : 'var(--lp-border)'}`,
              background: inboxFilter === key ? 'rgba(13,148,136,0.12)' : 'transparent',
              color: inboxFilter === key ? 'var(--lp-accent-teal)' : 'var(--lp-muted)',
              fontSize: '0.78rem',
              fontWeight: inboxFilter === key ? 700 : 400,
              cursor: 'pointer',
              transition: 'all 0.15s',
            }}
          >
            {label}
          </button>
        ))}
      </div>
      <div
        style={{
          display: 'flex',
          flexWrap: 'wrap',
          gap: '0.5rem',
          alignItems: 'center',
          marginBottom: '0.85rem',
        }}
      >
        <label style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', fontSize: '0.8rem', color: 'var(--lp-muted)' }}>
          From
          <input
            type="date"
            value={txnFilterDateFrom}
            onChange={(e) => setTxnFilterDateFrom(e.target.value)}
            style={filterInputStyle}
          />
        </label>
        <label style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', fontSize: '0.8rem', color: 'var(--lp-muted)' }}>
          To
          <input
            type="date"
            value={txnFilterDateTo}
            onChange={(e) => setTxnFilterDateTo(e.target.value)}
            style={filterInputStyle}
          />
        </label>
        <label style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', fontSize: '0.8rem', color: 'var(--lp-muted)' }}>
          Category
          <select
            value={txnFilterCategory}
            onChange={(e) => setTxnFilterCategory(e.target.value)}
            style={{ ...filterInputStyle, minWidth: 140 }}
          >
            <option value="">All</option>
            <option value="__uncategorized__">Uncategorized</option>
            {availableCategories.map((c) => (
              <option key={c} value={c}>{c}</option>
            ))}
          </select>
        </label>
        {(txnFilterDateFrom || txnFilterDateTo || txnFilterCategory) && (
          <button
            type="button"
            onClick={() => {
              setTxnFilterDateFrom('');
              setTxnFilterDateTo('');
              setTxnFilterCategory('');
            }}
            style={{
              padding: '0.35rem 0.65rem',
              borderRadius: 8,
              border: '1px solid var(--lp-border)',
              background: 'transparent',
              color: 'var(--lp-muted)',
              fontSize: '0.78rem',
              cursor: 'pointer',
            }}
          >
            Clear filters
          </button>
        )}
        <span style={{ fontSize: '0.78rem', color: 'var(--lp-muted)', marginLeft: 'auto' }}>
          Showing {displayedTransactions.length} of {transactions.length}
        </span>
      </div>
      {!displayedTransactions.length ? (
        <p className={styles.emptyState}>No transactions match the current filters.</p>
      ) : (
        <table className={styles.table}>
          <thead><tr><th>Date</th><th>Description</th><th>Amount</th><th>Category</th><th>CIS</th></tr></thead>
          <tbody>
            {displayedTransactions.map((t) => (
              <tr key={t.id} style={openTaskByTxnId.has(t.id) ? { background: 'rgba(245,158,11,0.06)' } : undefined}>
                <td>{t.date}</td>
                <td>{t.description}</td>
                <td className={t.amount > 0 ? styles.positive : styles.negative}>{t.amount.toFixed(2)} {t.currency}</td>
                <td>
                  <select value={t.category || ''} onChange={(e) => handleCategoryChange(t.id, e.target.value)} className={styles.categorySelect}>
                    <option value="" disabled>Select...</option>
                    {availableCategories.map((cat) => <option key={cat} value={cat}>{cat}</option>)}
                  </select>
                </td>
                <td>
                  {openTaskByTxnId.has(t.id) ? (
                    <button
                      type="button"
                      onClick={() => setModalTask(openTaskByTxnId.get(t.id)!)}
                      style={{
                        padding: '0.25rem 0.6rem',
                        borderRadius: 8,
                        border: '1px solid rgba(245,158,11,0.5)',
                        background: 'rgba(245,158,11,0.12)',
                        fontSize: '0.78rem',
                        fontWeight: 600,
                        cursor: 'pointer',
                      }}
                    >
                      Review
                    </button>
                  ) : t.amount > 0 ? (
                    <button
                      type="button"
                      disabled={flaggingTxn === t.id}
                      onClick={() => void flagCisSuspect(t.id)}
                      style={{
                        padding: '0.25rem 0.5rem',
                        borderRadius: 8,
                        border: '1px solid var(--lp-border)',
                        background: 'transparent',
                        fontSize: '0.75rem',
                        cursor: flaggingTxn === t.id ? 'wait' : 'pointer',
                        color: 'var(--lp-muted)',
                      }}
                    >
                      {flaggingTxn === t.id ? '…' : 'Flag'}
                    </button>
                  ) : (
                    '—'
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}

function ReceiptDraftManualMatching({ token, businessId }: { token: string; businessId: string | null }) {
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
      const response = await fetch(`${TRANSACTIONS_API_BASE}/transactions/receipt-drafts/unmatched?${params.toString()}`, {
        headers: transactionsBearerHeaders(token, businessId),
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
  }, [includeIgnoredDrafts, searchAmount, searchDate, searchProviderTransactionId, token, businessId]);

  useEffect(() => {
    void loadUnmatchedDrafts();
  }, [loadUnmatchedDrafts]);

  const handleMatch = async (draftId: string, targetId: string) => {
    const actionKey = `${draftId}:${targetId}`;
    setActiveActionKey(actionKey);
    setError('');
    setMessage('');
    try {
      const response = await fetch(`${TRANSACTIONS_API_BASE}/transactions/receipt-drafts/${draftId}/reconcile`, {
        method: 'POST',
        headers: transactionsBearerHeaders(token, businessId, { 'Content-Type': 'application/json' }),
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
      const response = await fetch(`${TRANSACTIONS_API_BASE}/transactions/receipt-drafts/${draftId}/ignore-candidate`, {
        method: 'POST',
        headers: transactionsBearerHeaders(token, businessId, { 'Content-Type': 'application/json' }),
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
      const response = await fetch(`${TRANSACTIONS_API_BASE}/transactions/receipt-drafts/${draftId}/${action}`, {
        method: 'POST',
        headers: transactionsBearerHeaders(token, businessId),
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
    const { businesses, loadError, selectedBusinessId, setSelectedBusinessId } = useTransactionsBusinessScope(
      token,
      TRANSACTIONS_API_BASE,
    );
    return (
        <div className={styles.pageContainer}>
            <h1>Transactions</h1>
            <p>Connect your bank account to import and categorize your transactions.</p>
            {businesses.length > 0 && (
              <div className={styles.subContainer} style={{ marginBottom: '1rem', padding: '0.75rem 1rem' }}>
                <label style={{ display: 'block', fontSize: '0.82rem', color: 'var(--lp-muted)', marginBottom: 6 }}>
                  Business
                </label>
                <select
                  className={styles.input}
                  onChange={(e) => setSelectedBusinessId(e.target.value)}
                  value={selectedBusinessId ?? businesses[0]?.id ?? ''}
                  style={{ maxWidth: 360, width: '100%' }}
                >
                  {businesses.map((b) => (
                    <option key={b.id} value={b.id}>
                      {b.display_name}
                    </option>
                  ))}
                </select>
              </div>
            )}
            {loadError ? <p className={styles.error} style={{ marginBottom: '1rem', fontSize: '0.88rem' }}>{loadError}</p> : null}
            <BankConnection token={token} onConnectionComplete={setConnectedAccountId} />
            <TransactionsList token={token} accountId={connectedAccountId} businessId={selectedBusinessId} />
            <ReceiptDraftManualMatching token={token} businessId={selectedBusinessId} />
        </div>
    );
}
