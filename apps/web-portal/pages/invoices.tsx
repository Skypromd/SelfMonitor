import { Download, FilePlus, FileText, Plus, Send, Trash2 } from 'lucide-react';
import { useCallback, useEffect, useState } from 'react';
import styles from '../styles/Home.module.css';

const INVOICE_SERVICE_URL =
  process.env.NEXT_PUBLIC_INVOICE_SERVICE_URL || 'http://localhost:8000/api/invoices';

type InvoiceStatus = 'draft' | 'sent' | 'paid' | 'overdue' | 'cancelled' | 'partially_paid';

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

const STATUS_COLOURS: Record<InvoiceStatus, string> = {
  draft: '#94a3b8',
  sent: '#60a5fa',
  paid: '#34d399',
  overdue: '#f87171',
  cancelled: '#6b7280',
  partially_paid: '#fbbf24',
};

type InvoicesPageProps = { token: string };

export default function InvoicesPage({ token }: InvoicesPageProps) {
  const [invoices, setInvoices] = useState<Invoice[]>([]);
  const [summary, setSummary] = useState<ReportSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [showForm, setShowForm] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [formMsg, setFormMsg] = useState('');
  const [statusFilter, setStatusFilter] = useState<InvoiceStatus | 'all'>('all');

  // New invoice form state
  const [clientName, setClientName] = useState('');
  const [clientEmail, setClientEmail] = useState('');
  const [dueDate, setDueDate] = useState('');
  const [currency, setCurrency] = useState('GBP');
  const [notes, setNotes] = useState('');
  const [lineItems, setLineItems] = useState<LineItem[]>([
    { description: '', quantity: 1, unit_price: 0, vat_rate: 20 },
  ]);

  const headers = { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' };

  const fetchInvoices = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const params = statusFilter !== 'all' ? `?status=${statusFilter}` : '';
      const [invRes, sumRes] = await Promise.all([
        fetch(`${INVOICE_SERVICE_URL}/invoices${params}`, { headers }),
        fetch(`${INVOICE_SERVICE_URL}/reports/summary`, { headers }),
      ]);
      if (invRes.ok) setInvoices(await invRes.json());
      if (sumRes.ok) setSummary(await sumRes.json());
    } catch {
      setError('Unable to reach the invoice service.');
    } finally {
      setLoading(false);
    }
  }, [token, statusFilter]);

  useEffect(() => { fetchInvoices(); }, [fetchInvoices]);

  const updateLineItem = (i: number, field: keyof LineItem, value: string | number) => {
    setLineItems((prev) => prev.map((li, idx) => (idx === i ? { ...li, [field]: value } : li)));
  };
  const addLine = () =>
    setLineItems((prev) => [...prev, { description: '', quantity: 1, unit_price: 0, vat_rate: 20 }]);
  const removeLine = (i: number) =>
    setLineItems((prev) => prev.filter((_, idx) => idx !== i));

  const lineTotal = (li: LineItem) =>
    li.quantity * li.unit_price * (1 + li.vat_rate / 100);
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
        line_items: lineItems.map((li) => ({
          description: li.description,
          quantity: String(li.quantity),
          unit_price: String(li.unit_price),
          vat_rate: String(li.vat_rate),
        })),
      };
      const res = await fetch(`${INVOICE_SERVICE_URL}/invoices`, {
        method: 'POST',
        headers,
        body: JSON.stringify(body),
      });
      if (res.ok) {
        setFormMsg('Invoice created!');
        setShowForm(false);
        setClientName(''); setClientEmail(''); setDueDate(''); setNotes('');
        setLineItems([{ description: '', quantity: 1, unit_price: 0, vat_rate: 20 }]);
        fetchInvoices();
      } else {
        const d = await res.json();
        setFormMsg(`Error: ${d.detail || res.statusText}`);
      }
    } catch {
      setFormMsg('Network error — service may not be running.');
    } finally {
      setSubmitting(false);
    }
  };

  const sendInvoice = async (id: string) => {
    try {
      await fetch(`${INVOICE_SERVICE_URL}/invoices/${id}/send`, { method: 'POST', headers });
      fetchInvoices();
    } catch { /* ignore */ }
  };

  const deleteInvoice = async (id: string) => {
    if (!confirm('Delete this invoice?')) return;
    try {
      await fetch(`${INVOICE_SERVICE_URL}/invoices/${id}`, { method: 'DELETE', headers });
      fetchInvoices();
    } catch { /* ignore */ }
  };

  const downloadPDF = async (id: string, num: string) => {
    try {
      const res = await fetch(`${INVOICE_SERVICE_URL}/invoices/${id}/pdf/download`, { headers });
      if (res.ok) {
        const blob = await res.blob();
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url; a.download = `invoice-${num}.pdf`; a.click();
        URL.revokeObjectURL(url);
      }
    } catch { /* ignore */ }
  };

  const fmt = (v: number, c = 'GBP') =>
    new Intl.NumberFormat('en-GB', { style: 'currency', currency: c }).format(v);

  return (
    <div className={styles.container}>
      <div className={styles.header}>
        <h1 className={styles.title}>Invoices</h1>
        <button className={styles.btn} onClick={() => setShowForm(!showForm)}>
          <Plus size={16} style={{ marginRight: 6 }} /> New Invoice
        </button>
      </div>

      {/* Summary Cards */}
      {summary && (
        <div className={styles.grid} style={{ marginBottom: '1.5rem' }}>
          {[
            { label: 'Total Revenue', value: fmt(summary.total_revenue), icon: <FileText size={20} /> },
            { label: 'VAT Collected', value: fmt(summary.total_vat), icon: <FilePlus size={20} /> },
            { label: 'Paid', value: summary.paid_count, icon: <Download size={20} /> },
            { label: 'Overdue', value: summary.overdue_count, icon: <Send size={20} />, warn: summary.overdue_count > 0 },
          ].map((c) => (
            <div key={c.label} className={styles.card} style={c.warn ? { borderColor: '#f87171' } : {}}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8, color: 'var(--lp-text-muted)' }}>
                {c.icon} <span style={{ fontSize: '0.85rem' }}>{c.label}</span>
              </div>
              <div style={{ fontSize: '1.5rem', fontWeight: 700, color: c.warn ? '#f87171' : 'var(--lp-text)' }}>{c.value}</div>
            </div>
          ))}
        </div>
      )}

      {/* Filter */}
      <div style={{ display: 'flex', gap: 8, marginBottom: '1.25rem', flexWrap: 'wrap' }}>
        {(['all', 'draft', 'sent', 'paid', 'overdue', 'partially_paid', 'cancelled'] as const).map((s) => (
          <button
            key={s}
            onClick={() => setStatusFilter(s)}
            style={{
              padding: '0.35rem 0.85rem', borderRadius: 20, border: 'none', cursor: 'pointer', fontSize: '0.8rem',
              background: statusFilter === s ? 'var(--lp-accent-teal)' : 'var(--lp-bg-card)',
              color: statusFilter === s ? '#fff' : 'var(--lp-text)',
            }}
          >
            {s === 'all' ? 'All' : s.charAt(0).toUpperCase() + s.slice(1).replace('_', ' ')}
          </button>
        ))}
      </div>

      {/* New Invoice Form */}
      {showForm && (
        <div className={styles.card} style={{ marginBottom: '1.5rem' }}>
          <h3 style={{ marginBottom: '1rem', color: 'var(--lp-text)' }}>New Invoice</h3>
          <form onSubmit={handleCreate}>
            <div className={styles.grid} style={{ marginBottom: '1rem' }}>
              <div>
                <label className={styles.label}>Client Name *</label>
                <input className={styles.input} value={clientName}
                  onChange={(e) => setClientName(e.target.value)} required />
              </div>
              <div>
                <label className={styles.label}>Client Email</label>
                <input type="email" className={styles.input} value={clientEmail}
                  onChange={(e) => setClientEmail(e.target.value)} />
              </div>
              <div>
                <label className={styles.label}>Due Date *</label>
                <input type="date" className={styles.input} value={dueDate}
                  onChange={(e) => setDueDate(e.target.value)} required />
              </div>
              <div>
                <label className={styles.label}>Currency</label>
                <select className={styles.input} value={currency} onChange={(e) => setCurrency(e.target.value)}>
                  {['GBP', 'EUR', 'USD', 'PLN', 'RON', 'UAH'].map((c) => (
                    <option key={c} value={c}>{c}</option>
                  ))}
                </select>
              </div>
            </div>

            {/* Line Items */}
            <div style={{ marginBottom: '1rem' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                <label className={styles.label} style={{ margin: 0 }}>Line Items</label>
                <button type="button" onClick={addLine} style={{ fontSize: '0.8rem', background: 'none', border: '1px solid var(--lp-border)', borderRadius: 6, padding: '0.25rem 0.6rem', color: 'var(--lp-accent-teal)', cursor: 'pointer' }}>
                  + Add Line
                </button>
              </div>
              {lineItems.map((li, i) => (
                <div key={i} style={{ display: 'grid', gridTemplateColumns: '2fr 1fr 1fr 1fr auto', gap: 8, marginBottom: 8, alignItems: 'center' }}>
                  <input className={styles.input} placeholder="Description" value={li.description}
                    onChange={(e) => updateLineItem(i, 'description', e.target.value)} required />
                  <input type="number" className={styles.input} placeholder="Qty" value={li.quantity} min={0} step={0.01}
                    onChange={(e) => updateLineItem(i, 'quantity', parseFloat(e.target.value) || 0)} />
                  <input type="number" className={styles.input} placeholder="Unit Price" value={li.unit_price} min={0} step={0.01}
                    onChange={(e) => updateLineItem(i, 'unit_price', parseFloat(e.target.value) || 0)} />
                  <input type="number" className={styles.input} placeholder="VAT%" value={li.vat_rate} min={0} max={100}
                    onChange={(e) => updateLineItem(i, 'vat_rate', parseFloat(e.target.value) || 0)} />
                  <button type="button" onClick={() => removeLine(i)}
                    style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#f87171', display: lineItems.length > 1 ? 'block' : 'none' }}>
                    <Trash2 size={16} />
                  </button>
                </div>
              ))}
              <div style={{ textAlign: 'right', color: 'var(--lp-text)', fontWeight: 600 }}>
                Total: {fmt(grandTotal, currency)}
              </div>
            </div>

            <div style={{ marginBottom: '1rem' }}>
              <label className={styles.label}>Notes</label>
              <textarea className={styles.input} value={notes} onChange={(e) => setNotes(e.target.value)}
                rows={3} style={{ resize: 'vertical' }} />
            </div>

            {formMsg && (
              <p style={{ color: formMsg.startsWith('Error') ? '#f87171' : '#34d399', marginBottom: 8 }}>{formMsg}</p>
            )}

            <div style={{ display: 'flex', gap: 8 }}>
              <button type="submit" className={styles.btn} disabled={submitting}>
                {submitting ? 'Creating…' : 'Create Invoice'}
              </button>
              <button type="button" onClick={() => setShowForm(false)}
                style={{ padding: '0.5rem 1rem', borderRadius: 8, border: '1px solid var(--lp-border)', background: 'none', color: 'var(--lp-text)', cursor: 'pointer' }}>
                Cancel
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Invoice List */}
      {loading ? (
        <p style={{ color: 'var(--lp-text-muted)' }}>Loading invoices…</p>
      ) : error ? (
        <p className={styles.error}>{error}</p>
      ) : invoices.length === 0 ? (
        <div className={styles.card} style={{ textAlign: 'center', padding: '2rem' }}>
          <FileText size={40} style={{ color: 'var(--lp-text-muted)', marginBottom: 12 }} />
          <p style={{ color: 'var(--lp-text-muted)' }}>No invoices yet. Create your first invoice above.</p>
        </div>
      ) : (
        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.9rem' }}>
            <thead>
              <tr style={{ borderBottom: '1px solid var(--lp-border)', color: 'var(--lp-text-muted)', textAlign: 'left' }}>
                {['Invoice #', 'Client', 'Issue Date', 'Due Date', 'Amount', 'Status', 'Actions'].map((h) => (
                  <th key={h} style={{ padding: '0.6rem 1rem', fontWeight: 500 }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {invoices.map((inv) => (
                <tr key={inv.id} style={{ borderBottom: '1px solid var(--lp-border)' }}>
                  <td style={{ padding: '0.7rem 1rem', color: 'var(--lp-accent-teal)', fontWeight: 600 }}>
                    {inv.invoice_number}
                  </td>
                  <td style={{ padding: '0.7rem 1rem' }}>
                    <div style={{ fontWeight: 500 }}>{inv.client_name}</div>
                    {inv.client_email && <div style={{ fontSize: '0.8rem', color: 'var(--lp-text-muted)' }}>{inv.client_email}</div>}
                  </td>
                  <td style={{ padding: '0.7rem 1rem', color: 'var(--lp-text-muted)' }}>
                    {new Date(inv.issue_date).toLocaleDateString('en-GB')}
                  </td>
                  <td style={{ padding: '0.7rem 1rem', color: new Date(inv.due_date) < new Date() && inv.status !== 'paid' ? '#f87171' : 'var(--lp-text-muted)' }}>
                    {new Date(inv.due_date).toLocaleDateString('en-GB')}
                  </td>
                  <td style={{ padding: '0.7rem 1rem', fontWeight: 600 }}>
                    {fmt(inv.total_amount ?? 0, inv.currency)}
                  </td>
                  <td style={{ padding: '0.7rem 1rem' }}>
                    <span style={{
                      display: 'inline-block', padding: '0.2rem 0.6rem', borderRadius: 12, fontSize: '0.75rem', fontWeight: 600,
                      background: STATUS_COLOURS[inv.status] + '22', color: STATUS_COLOURS[inv.status],
                    }}>
                      {inv.status.replace('_', ' ')}
                    </span>
                  </td>
                  <td style={{ padding: '0.7rem 1rem' }}>
                    <div style={{ display: 'flex', gap: 6 }}>
                      {(inv.status === 'draft') && (
                        <button onClick={() => sendInvoice(inv.id)} title="Send Invoice"
                          style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#60a5fa' }}>
                          <Send size={16} />
                        </button>
                      )}
                      <button onClick={() => downloadPDF(inv.id, inv.invoice_number)} title="Download PDF"
                        style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--lp-text-muted)' }}>
                        <Download size={16} />
                      </button>
                      {inv.status === 'draft' && (
                        <button onClick={() => deleteInvoice(inv.id)} title="Delete"
                          style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#f87171' }}>
                          <Trash2 size={16} />
                        </button>
                      )}
                    </div>
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
