import {
  AlertTriangle,
  ArrowDownUp,
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  ChevronUp,
  Download,
  FilePlus,
  FileText,
  Plus,
  Search,
  Send,
  Trash2,
  X,
} from 'lucide-react';
import Link from 'next/link';
import { useCallback, useEffect, useRef, useState } from 'react';
import styles from '../styles/Home.module.css';

const INVOICE_SERVICE_URL =
  process.env.NEXT_PUBLIC_INVOICE_SERVICE_URL || '/api/invoices';

const PAGE_SIZE = 25;

type InvoiceStatus = 'draft' | 'sent' | 'paid' | 'overdue' | 'cancelled' | 'partially_paid';
type SortField = 'created_at' | 'due_date' | 'total_amount' | 'client_name' | 'status';
type SortOrder = 'asc' | 'desc';

type LineItem = {
  description: string;
  quantity: number;
  unit_price: number;
  vat_rate: number;
  category?: string;
};

type Invoice = {
  id: string;
  invoice_number: string;
  client_name: string;
  client_email?: string;
  issue_date: string;
  due_date: string;
  status: InvoiceStatus;
  currency: string;
  total_amount: number;
  vat_amount: number;
  subtotal: number;
  line_items: LineItem[];
};

type ReportSummary = {
  total_invoices: number;
  total_revenue: number;
  total_vat: number;
  paid_count: number;
  overdue_count: number;
  draft_count: number;
};

const STATUS_META: Record<InvoiceStatus, { color: string; label: string }> = {
  draft:         { color: '#94a3b8', label: 'Draft' },
  sent:          { color: '#60a5fa', label: 'Sent' },
  paid:          { color: '#34d399', label: 'Paid' },
  overdue:       { color: '#f87171', label: 'Overdue' },
  cancelled:     { color: '#6b7280', label: 'Cancelled' },
  partially_paid:{ color: '#fbbf24', label: 'Part. paid' },
};

const ALL_STATUSES = ['all', 'draft', 'sent', 'paid', 'overdue', 'partially_paid', 'cancelled'] as const;

type InvoicesPageProps = { token: string };

export default function InvoicesPage({ token }: InvoicesPageProps) {
  const [invoices, setInvoices] = useState<Invoice[]>([]);
  const [summary, setSummary] = useState<ReportSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [showForm, setShowForm] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [formMsg, setFormMsg] = useState('');

  // Filters
  const [statusFilter, setStatusFilter] = useState<InvoiceStatus | 'all'>('all');
  const [search, setSearch] = useState('');
  const [debouncedSearch, setDebouncedSearch] = useState('');

  // Sort
  const [sortField, setSortField] = useState<SortField>('created_at');
  const [sortOrder, setSortOrder] = useState<SortOrder>('desc');

  // Pagination
  const [page, setPage] = useState(0);
  const [hasMore, setHasMore] = useState(false);

  // Delete confirm
  const [confirmDeleteId, setConfirmDeleteId] = useState<string | null>(null);

  // Form
  const [clientName, setClientName] = useState('');
  const [clientEmail, setClientEmail] = useState('');
  const [dueDate, setDueDate] = useState('');
  const [currency, setCurrency] = useState('GBP');
  const [notes, setNotes] = useState('');
  const [lineItems, setLineItems] = useState<LineItem[]>([
    { description: '', quantity: 1, unit_price: 0, vat_rate: 20 },
  ]);

  const searchRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const headers = useCallback(
    () => ({ Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' }),
    [token],
  );

  // Debounce search
  useEffect(() => {
    if (searchRef.current) clearTimeout(searchRef.current);
    searchRef.current = setTimeout(() => {
      setDebouncedSearch(search);
      setPage(0);
    }, 350);
    return () => { if (searchRef.current) clearTimeout(searchRef.current); };
  }, [search]);

  const fetchInvoices = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const params = new URLSearchParams({
        skip: String(page * PAGE_SIZE),
        limit: String(PAGE_SIZE + 1),
        sort_by: sortField,
        sort_order: sortOrder,
      });
      if (statusFilter !== 'all') params.set('status', statusFilter);
      if (debouncedSearch) params.set('search', debouncedSearch);

      const [invRes, sumRes] = await Promise.all([
        fetch(`${INVOICE_SERVICE_URL}/invoices?${params}`, { headers: headers() }),
        fetch(`${INVOICE_SERVICE_URL}/reports/summary`, { headers: headers() }),
      ]);

      if (invRes.ok) {
        const data: Invoice[] = await invRes.json();
        setHasMore(data.length > PAGE_SIZE);
        setInvoices(data.slice(0, PAGE_SIZE));
      } else {
        setError(`Invoice service error (${invRes.status})`);
      }
      if (sumRes.ok) setSummary(await sumRes.json());
    } catch {
      setError('Unable to reach the invoice service.');
    } finally {
      setLoading(false);
    }
  }, [token, statusFilter, debouncedSearch, sortField, sortOrder, page, headers]);

  useEffect(() => { fetchInvoices(); }, [fetchInvoices]);

  // Sort toggle
  const handleSort = (field: SortField) => {
    if (field === sortField) {
      setSortOrder(o => o === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      setSortOrder('desc');
    }
    setPage(0);
  };

  const SortIcon = ({ field }: { field: SortField }) => {
    if (sortField !== field) return <ArrowDownUp size={13} style={{ opacity: 0.4 }} />;
    return sortOrder === 'asc' ? <ChevronUp size={13} /> : <ChevronDown size={13} />;
  };

  // Line item helpers
  const updateLine = (i: number, f: keyof LineItem, v: string | number) =>
    setLineItems(prev => prev.map((li, idx) => (idx === i ? { ...li, [f]: v } : li)));
  const addLine = () =>
    setLineItems(prev => [...prev, { description: '', quantity: 1, unit_price: 0, vat_rate: 20 }]);
  const removeLine = (i: number) =>
    setLineItems(prev => prev.filter((_, idx) => idx !== i));

  const lineTotal = (li: LineItem) => li.quantity * li.unit_price * (1 + li.vat_rate / 100);
  const grandTotal = lineItems.reduce((s, li) => s + lineTotal(li), 0);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setFormMsg('');
    try {
      const body = {
        client_name: clientName,
        client_email: clientEmail || undefined,
        due_date: new Date(dueDate).toISOString(),
        currency,
        notes: notes || undefined,
        vat_rate: 20,
        line_items: lineItems.map(li => ({
          description: li.description,
          quantity: String(li.quantity),
          unit_price: String(li.unit_price),
          vat_rate: String(li.vat_rate),
        })),
      };
      const res = await fetch(`${INVOICE_SERVICE_URL}/invoices`, {
        method: 'POST',
        headers: headers(),
        body: JSON.stringify(body),
      });
      if (res.ok) {
        setFormMsg('Invoice created!');
        setShowForm(false);
        setClientName(''); setClientEmail(''); setDueDate(''); setNotes('');
        setLineItems([{ description: '', quantity: 1, unit_price: 0, vat_rate: 20 }]);
        setPage(0);
        fetchInvoices();
      } else {
        const d = await res.json();
        setFormMsg(`Error: ${d.detail || res.statusText}`);
      }
    } catch {
      setFormMsg('Network error.');
    } finally {
      setSubmitting(false);
    }
  };

  const sendInvoice = async (id: string) => {
    await fetch(`${INVOICE_SERVICE_URL}/invoices/${id}/send`, { method: 'POST', headers: headers() });
    fetchInvoices();
  };

  const downloadPDF = async (id: string, num: string) => {
    const res = await fetch(`${INVOICE_SERVICE_URL}/invoices/${id}/pdf/download`, { headers: headers() });
    if (res.ok) {
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url; a.download = `invoice-${num}.pdf`; a.click();
      URL.revokeObjectURL(url);
    }
  };

  const confirmDelete = async () => {
    if (!confirmDeleteId) return;
    await fetch(`${INVOICE_SERVICE_URL}/invoices/${confirmDeleteId}`, { method: 'DELETE', headers: headers() });
    setConfirmDeleteId(null);
    fetchInvoices();
  };

  const fmt = (v: number, c = 'GBP') =>
    new Intl.NumberFormat('en-GB', { style: 'currency', currency: c }).format(v);

  const overdueCount = summary?.overdue_count ?? 0;

  return (
    <div className={styles.pageContainer}>
      {/* Header */}
      <div className={styles.header}>
        <h1 className={styles.title}>Invoices</h1>
        <button className={styles.btn} onClick={() => setShowForm(!showForm)}>
          <Plus size={15} style={{ marginRight: 5 }} /> New Invoice
        </button>
      </div>

      {/* Overdue Banner */}
      {overdueCount > 0 && (
        <div style={{
          display: 'flex', alignItems: 'center', gap: 10,
          background: 'rgba(239,68,68,0.1)', border: '1px solid rgba(239,68,68,0.35)',
          borderRadius: 'var(--radius-md)', padding: '0.65rem 1rem',
          marginBottom: '1.25rem', color: '#f87171',
        }}>
          <AlertTriangle size={16} />
          <span style={{ fontSize: '0.88rem', fontWeight: 500 }}>
            {overdueCount} invoice{overdueCount > 1 ? 's' : ''} overdue
          </span>
          <button
            onClick={() => setStatusFilter('overdue')}
            style={{ marginLeft: 'auto', fontSize: '0.8rem', background: 'none', border: 'none', color: '#f87171', cursor: 'pointer', textDecoration: 'underline' }}
          >
            View
          </button>
        </div>
      )}

      {/* KPI Cards */}
      {summary && (
        <div className={styles.grid} style={{ marginBottom: '1.5rem' }}>
          {[
            { label: 'Total Revenue', value: fmt(summary.total_revenue), icon: <FileText size={18} /> },
            { label: 'VAT Collected', value: fmt(summary.total_vat), icon: <FilePlus size={18} /> },
            { label: 'Paid', value: `${summary.paid_count} invoices`, icon: <Download size={18} /> },
            { label: 'Overdue', value: `${summary.overdue_count} invoices`, icon: <AlertTriangle size={18} />, warn: overdueCount > 0 },
          ].map(c => (
            <div key={c.label} className={styles.card}
              style={c.warn ? { borderColor: 'rgba(239,68,68,0.45)', cursor: 'pointer' } : {}}
              onClick={c.warn ? () => setStatusFilter('overdue') : undefined}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: 7, marginBottom: 6, color: c.warn ? '#f87171' : 'var(--text-secondary)' }}>
                {c.icon} <span style={{ fontSize: '0.82rem' }}>{c.label}</span>
              </div>
              <div style={{ fontSize: '1.4rem', fontWeight: 700, color: c.warn ? '#f87171' : 'var(--text-primary)' }}>{c.value}</div>
            </div>
          ))}
        </div>
      )}

      {/* Search + Filter row */}
      <div style={{ display: 'flex', gap: 10, marginBottom: '1rem', flexWrap: 'wrap', alignItems: 'center' }}>
        {/* Search */}
        <div style={{ position: 'relative', flex: '1 1 220px', minWidth: 160 }}>
          <Search size={14} style={{ position: 'absolute', left: 10, top: '50%', transform: 'translateY(-50%)', color: 'var(--text-tertiary)' }} />
          <input
            value={search}
            onChange={e => setSearch(e.target.value)}
            placeholder="Search client or invoice #…"
            className={styles.input}
            style={{ paddingLeft: 32, paddingTop: '0.45rem', paddingBottom: '0.45rem', margin: 0, fontSize: '0.85rem' }}
          />
          {search && (
            <button onClick={() => setSearch('')}
              style={{ position: 'absolute', right: 8, top: '50%', transform: 'translateY(-50%)', background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-tertiary)' }}>
              <X size={13} />
            </button>
          )}
        </div>

        {/* Status pills */}
        <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
          {ALL_STATUSES.map(s => (
            <button key={s} onClick={() => { setStatusFilter(s as typeof statusFilter); setPage(0); }}
              style={{
                padding: '0.3rem 0.75rem', borderRadius: 'var(--radius-full)', border: 'none', cursor: 'pointer', fontSize: '0.78rem', fontWeight: 500,
                background: statusFilter === s ? 'var(--accent)' : 'var(--bg-card)',
                color: statusFilter === s ? '#fff' : 'var(--text-secondary)',
                transition: 'background var(--ease-fast)',
              }}>
              {s === 'all' ? 'All' : (STATUS_META[s as InvoiceStatus]?.label ?? s)}
            </button>
          ))}
        </div>
      </div>

      {/* New Invoice Form */}
      {showForm && (
        <div className={styles.card} style={{ marginBottom: '1.5rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
            <h3 style={{ margin: 0, color: 'var(--text-primary)', fontSize: '1rem', fontWeight: 600 }}>New Invoice</h3>
            <button onClick={() => setShowForm(false)} style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-tertiary)' }}>
              <X size={16} />
            </button>
          </div>
          <form onSubmit={handleCreate}>
            <div className={styles.grid} style={{ marginBottom: '1rem' }}>
              <div>
                <label className={styles.label}>Client Name *</label>
                <input className={styles.input} value={clientName} onChange={e => setClientName(e.target.value)} required />
              </div>
              <div>
                <label className={styles.label}>Client Email</label>
                <input type="email" className={styles.input} value={clientEmail} onChange={e => setClientEmail(e.target.value)} />
              </div>
              <div>
                <label className={styles.label}>Due Date *</label>
                <input type="date" className={styles.input} value={dueDate} onChange={e => setDueDate(e.target.value)} required />
              </div>
              <div>
                <label className={styles.label}>Currency</label>
                <select className={styles.input} value={currency} onChange={e => setCurrency(e.target.value)}>
                  {['GBP', 'EUR', 'USD', 'PLN', 'RON', 'UAH'].map(c => <option key={c} value={c}>{c}</option>)}
                </select>
              </div>
            </div>

            {/* Line Items */}
            <div style={{ marginBottom: '1rem' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                <label className={styles.label} style={{ margin: 0 }}>Line Items</label>
                <button type="button" onClick={addLine}
                  style={{ fontSize: '0.8rem', background: 'none', border: '1px solid var(--border)', borderRadius: 'var(--radius-sm)', padding: '0.2rem 0.6rem', color: 'var(--accent)', cursor: 'pointer' }}>
                  + Add Line
                </button>
              </div>

              {/* Header row — hidden on mobile */}
              <div style={{ display: 'grid', gridTemplateColumns: '2fr 0.7fr 1fr 0.7fr auto', gap: 8, marginBottom: 4 }}
                className="invoiceLineHeader">
                {['Description', 'Qty', 'Unit Price', 'VAT %', ''].map(h => (
                  <span key={h} style={{ fontSize: '0.75rem', color: 'var(--text-tertiary)', fontWeight: 500 }}>{h}</span>
                ))}
              </div>

              {lineItems.map((li, i) => (
                <div key={i} style={{ display: 'grid', gridTemplateColumns: '2fr 0.7fr 1fr 0.7fr auto', gap: 8, marginBottom: 6, alignItems: 'center' }}>
                  <input className={styles.input} placeholder="Description" value={li.description}
                    onChange={e => updateLine(i, 'description', e.target.value)} required style={{ margin: 0 }} />
                  <input type="number" className={styles.input} placeholder="1" value={li.quantity} min={0} step={0.01}
                    onChange={e => updateLine(i, 'quantity', parseFloat(e.target.value) || 0)} style={{ margin: 0 }} />
                  <input type="number" className={styles.input} placeholder="0.00" value={li.unit_price} min={0} step={0.01}
                    onChange={e => updateLine(i, 'unit_price', parseFloat(e.target.value) || 0)} style={{ margin: 0 }} />
                  <input type="number" className={styles.input} placeholder="20" value={li.vat_rate} min={0} max={100}
                    onChange={e => updateLine(i, 'vat_rate', parseFloat(e.target.value) || 0)} style={{ margin: 0 }} />
                  <button type="button" onClick={() => removeLine(i)}
                    style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#f87171', visibility: lineItems.length > 1 ? 'visible' : 'hidden' }}>
                    <Trash2 size={15} />
                  </button>
                </div>
              ))}

              <div style={{ textAlign: 'right', color: 'var(--text-primary)', fontWeight: 600, fontSize: '0.95rem', marginTop: 8 }}>
                Total: {fmt(grandTotal, currency)}
              </div>
            </div>

            <div style={{ marginBottom: '1rem' }}>
              <label className={styles.label}>Notes</label>
              <textarea className={styles.input} value={notes} onChange={e => setNotes(e.target.value)} rows={2} style={{ resize: 'vertical' }} />
            </div>

            {formMsg && (
              <p style={{ color: formMsg.startsWith('Error') ? '#f87171' : '#34d399', marginBottom: 8, fontSize: '0.88rem' }}>{formMsg}</p>
            )}

            <div style={{ display: 'flex', gap: 8 }}>
              <button type="submit" className={styles.btn} disabled={submitting}>
                {submitting ? 'Creating…' : 'Create Invoice'}
              </button>
              <button type="button" onClick={() => setShowForm(false)}
                style={{ padding: '0.45rem 1rem', borderRadius: 'var(--radius-md)', border: '1px solid var(--border)', background: 'none', color: 'var(--text-secondary)', cursor: 'pointer', fontSize: '0.88rem' }}>
                Cancel
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Invoice List */}
      {loading ? (
        /* Skeleton */
        <div>
          {[1, 2, 3, 4, 5].map(i => (
            <div key={i} className="skeleton" style={{ height: 48, borderRadius: 'var(--radius-md)', marginBottom: 6 }} />
          ))}
        </div>
      ) : error ? (
        <div className={styles.card} style={{ textAlign: 'center', padding: '1.5rem' }}>
          <p className={styles.error}>{error}</p>
          <button className={styles.btn} onClick={fetchInvoices} style={{ marginTop: 8 }}>Retry</button>
        </div>
      ) : invoices.length === 0 ? (
        <div className={styles.card} style={{ textAlign: 'center', padding: '2.5rem' }}>
          <FileText size={40} style={{ color: 'var(--text-tertiary)', marginBottom: 12 }} />
          <p style={{ color: 'var(--text-secondary)', margin: 0 }}>
            {debouncedSearch || statusFilter !== 'all'
              ? 'No invoices match your filters.'
              : 'No invoices yet. Create your first invoice above.'}
          </p>
        </div>
      ) : (
        <>
          {/* Desktop Table */}
          <div style={{ overflowX: 'auto', display: 'block' }} className="desktopOnly">
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.875rem' }}>
              <thead>
                <tr style={{ borderBottom: '1px solid var(--border)', color: 'var(--text-tertiary)', textAlign: 'left' }}>
                  {([
                    { key: 'invoice_number', label: 'Invoice #', sortable: false },
                    { key: 'client_name',    label: 'Client',    sortable: true },
                    { key: 'issue_date',     label: 'Issued',    sortable: false },
                    { key: 'due_date',       label: 'Due',       sortable: true },
                    { key: 'total_amount',   label: 'Amount',    sortable: true },
                    { key: 'status',         label: 'Status',    sortable: true },
                    { key: 'actions',        label: '',          sortable: false },
                  ] as const).map(col => (
                    <th key={col.key}
                      onClick={col.sortable ? () => handleSort(col.key as SortField) : undefined}
                      style={{
                        padding: '0.65rem 0.9rem', fontWeight: 500, fontSize: '0.8rem',
                        cursor: col.sortable ? 'pointer' : 'default',
                        userSelect: 'none',
                        whiteSpace: 'nowrap',
                      }}>
                      <span style={{ display: 'inline-flex', alignItems: 'center', gap: 4 }}>
                        {col.label}
                        {col.sortable && <SortIcon field={col.key as SortField} />}
                      </span>
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {invoices.map(inv => {
                  const isOverdue = inv.status !== 'paid' && inv.status !== 'cancelled' && new Date(inv.due_date) < new Date();
                  const meta = STATUS_META[inv.status];
                  return (
                    <tr key={inv.id}
                      style={{ borderBottom: '1px solid var(--border)', transition: 'background var(--ease-fast)' }}
                      onMouseEnter={e => (e.currentTarget.style.background = 'var(--bg-card-hover)')}
                      onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}>
                      <td style={{ padding: '0.7rem 0.9rem', color: 'var(--accent)', fontWeight: 600, fontFamily: 'monospace', fontSize: '0.82rem' }}>
                        {inv.invoice_number}
                      </td>
                      <td style={{ padding: '0.7rem 0.9rem' }}>
                        <div style={{ fontWeight: 500, color: 'var(--text-primary)' }}>{inv.client_name}</div>
                        {inv.client_email && <div style={{ fontSize: '0.77rem', color: 'var(--text-tertiary)' }}>{inv.client_email}</div>}
                      </td>
                      <td style={{ padding: '0.7rem 0.9rem', color: 'var(--text-tertiary)', fontSize: '0.82rem' }}>
                        {new Date(inv.issue_date).toLocaleDateString('en-GB')}
                      </td>
                      <td style={{ padding: '0.7rem 0.9rem', color: isOverdue ? '#f87171' : 'var(--text-tertiary)', fontSize: '0.82rem', fontWeight: isOverdue ? 600 : 400 }}>
                        {new Date(inv.due_date).toLocaleDateString('en-GB')}
                      </td>
                      <td style={{ padding: '0.7rem 0.9rem', fontWeight: 600, color: 'var(--text-primary)' }}>
                        {fmt(inv.total_amount ?? 0, inv.currency)}
                      </td>
                      <td style={{ padding: '0.7rem 0.9rem' }}>
                        <span style={{
                          display: 'inline-block', padding: '0.18rem 0.6rem', borderRadius: 'var(--radius-full)', fontSize: '0.74rem', fontWeight: 600,
                          background: meta.color + '22', color: meta.color,
                        }}>
                          {meta.label}
                        </span>
                      </td>
                      <td style={{ padding: '0.7rem 0.9rem' }}>
                        <div style={{ display: 'flex', gap: 4, alignItems: 'center' }}>
                          {inv.status === 'draft' && (
                            <button onClick={() => sendInvoice(inv.id)} title="Send"
                              style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#60a5fa', padding: '3px 5px', borderRadius: 'var(--radius-xs)' }}>
                              <Send size={15} />
                            </button>
                          )}
                          <button onClick={() => downloadPDF(inv.id, inv.invoice_number)} title="Download PDF"
                            style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-tertiary)', padding: '3px 5px', borderRadius: 'var(--radius-xs)' }}>
                            <Download size={15} />
                          </button>
                          {inv.status === 'draft' && (
                            <button onClick={() => setConfirmDeleteId(inv.id)} title="Delete"
                              style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#f87171', padding: '3px 5px', borderRadius: 'var(--radius-xs)' }}>
                              <Trash2 size={15} />
                            </button>
                          )}
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          {/* Mobile Cards */}
          <div className="mobileOnly">
            {invoices.map(inv => {
              const isOverdue = inv.status !== 'paid' && inv.status !== 'cancelled' && new Date(inv.due_date) < new Date();
              const meta = STATUS_META[inv.status];
              return (
                <div key={inv.id} className={styles.card} style={{ marginBottom: 8, padding: '0.85rem 1rem' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 6 }}>
                    <div>
                      <div style={{ fontWeight: 700, color: 'var(--text-primary)', fontSize: '0.95rem' }}>{inv.client_name}</div>
                      <div style={{ fontFamily: 'monospace', fontSize: '0.78rem', color: 'var(--accent)' }}>{inv.invoice_number}</div>
                    </div>
                    <span style={{
                      display: 'inline-block', padding: '0.18rem 0.6rem', borderRadius: 'var(--radius-full)', fontSize: '0.73rem', fontWeight: 600,
                      background: meta.color + '22', color: meta.color,
                    }}>
                      {meta.label}
                    </span>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <div>
                      <div style={{ fontSize: '1.15rem', fontWeight: 700, color: 'var(--text-primary)' }}>
                        {fmt(inv.total_amount ?? 0, inv.currency)}
                      </div>
                      <div style={{ fontSize: '0.78rem', color: isOverdue ? '#f87171' : 'var(--text-tertiary)', fontWeight: isOverdue ? 600 : 400 }}>
                        Due {new Date(inv.due_date).toLocaleDateString('en-GB')}
                        {isOverdue && ' · Overdue'}
                      </div>
                    </div>
                    <div style={{ display: 'flex', gap: 4 }}>
                      {inv.status === 'draft' && (
                        <button onClick={() => sendInvoice(inv.id)}
                          style={{ display: 'flex', alignItems: 'center', gap: 4, padding: '0.3rem 0.6rem', borderRadius: 'var(--radius-sm)', border: '1px solid rgba(96,165,250,0.4)', background: 'rgba(96,165,250,0.1)', color: '#60a5fa', cursor: 'pointer', fontSize: '0.78rem', fontWeight: 500 }}>
                          <Send size={13} /> Send
                        </button>
                      )}
                      <button onClick={() => downloadPDF(inv.id, inv.invoice_number)}
                        style={{ display: 'flex', alignItems: 'center', gap: 4, padding: '0.3rem 0.6rem', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border)', background: 'none', color: 'var(--text-secondary)', cursor: 'pointer', fontSize: '0.78rem' }}>
                        <Download size={13} /> PDF
                      </button>
                      {inv.status === 'draft' && (
                        <button onClick={() => setConfirmDeleteId(inv.id)}
                          style={{ display: 'flex', alignItems: 'center', padding: '0.3rem 0.5rem', borderRadius: 'var(--radius-sm)', border: '1px solid rgba(239,68,68,0.3)', background: 'none', color: '#f87171', cursor: 'pointer' }}>
                          <Trash2 size={13} />
                        </button>
                      )}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>

          {/* Pagination */}
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '1rem', gap: 8 }}>
            <span style={{ fontSize: '0.82rem', color: 'var(--text-tertiary)' }}>
              Page {page + 1} · {invoices.length} results
            </span>
            <div style={{ display: 'flex', gap: 6 }}>
              <button
                onClick={() => setPage(p => Math.max(0, p - 1))}
                disabled={page === 0}
                style={{ display: 'flex', alignItems: 'center', gap: 4, padding: '0.35rem 0.75rem', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border)', background: 'var(--bg-card)', color: page === 0 ? 'var(--text-tertiary)' : 'var(--text-primary)', cursor: page === 0 ? 'not-allowed' : 'pointer', fontSize: '0.82rem' }}>
                <ChevronLeft size={14} /> Prev
              </button>
              <button
                onClick={() => setPage(p => p + 1)}
                disabled={!hasMore}
                style={{ display: 'flex', alignItems: 'center', gap: 4, padding: '0.35rem 0.75rem', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border)', background: 'var(--bg-card)', color: !hasMore ? 'var(--text-tertiary)' : 'var(--text-primary)', cursor: !hasMore ? 'not-allowed' : 'pointer', fontSize: '0.82rem' }}>
                Next <ChevronRight size={14} />
              </button>
            </div>
          </div>
        </>
      )}

      {/* Delete Confirm Modal */}
      {confirmDeleteId && (
        <div style={{
          position: 'fixed', inset: 0, background: 'var(--bg-overlay)', zIndex: 'var(--z-modal)',
          display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '1rem',
        }}>
          <div className={styles.card} style={{ maxWidth: 360, width: '100%', padding: '1.5rem', textAlign: 'center' }}>
            <Trash2 size={32} style={{ color: '#f87171', marginBottom: 12 }} />
            <h3 style={{ margin: '0 0 0.5rem', color: 'var(--text-primary)' }}>Delete Invoice?</h3>
            <p style={{ color: 'var(--text-secondary)', fontSize: '0.88rem', margin: '0 0 1.25rem' }}>
              This action cannot be undone.
            </p>
            <div style={{ display: 'flex', gap: 8, justifyContent: 'center' }}>
              <button onClick={confirmDelete} className={styles.btn} style={{ background: '#ef4444' }}>
                Delete
              </button>
              <button onClick={() => setConfirmDeleteId(null)}
                style={{ padding: '0.5rem 1rem', borderRadius: 'var(--radius-md)', border: '1px solid var(--border)', background: 'none', color: 'var(--text-secondary)', cursor: 'pointer' }}>
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}

      <style>{`
        @media (max-width: 767px) {
          .desktopOnly { display: none !important; }
          .mobileOnly  { display: block !important; }
        }
        @media (min-width: 768px) {
          .desktopOnly { display: block !important; }
          .mobileOnly  { display: none !important; }
        }
        .invoiceLineHeader { display: grid; }
        @media (max-width: 480px) {
          .invoiceLineHeader { display: none; }
        }
      `}</style>
    </div>
  );
}
