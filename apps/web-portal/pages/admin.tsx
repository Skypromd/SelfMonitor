import { useEffect, useMemo, useState, type FormEvent } from 'react';
import { useTranslation } from '../hooks/useTranslation';
import styles from '../styles/Home.module.css';

const AUTH_SERVICE_BASE_URL = process.env.NEXT_PUBLIC_AUTH_SERVICE_URL || 'http://localhost:8000';
const PARTNER_REGISTRY_URL = process.env.NEXT_PUBLIC_PARTNER_REGISTRY_URL || 'http://localhost:8009';
const TOAST_DURATION_MS = 4200;

type AdminPageProps = {
  token: string;
};

type PeriodPreset = 'custom' | '7d' | '30d' | 'qtd';

type PartnerOption = {
  converted_lead_fee_gbp: number;
  id: string;
  name: string;
  qualified_lead_fee_gbp: number;
};

type BillingReportByPartner = {
  amount_gbp: number;
  converted_lead_fee_gbp: number;
  converted_leads: number;
  partner_id: string;
  partner_name: string;
  qualified_lead_fee_gbp: number;
  qualified_leads: number;
  unique_users: number;
};

type BillingReportResponse = {
  by_partner: BillingReportByPartner[];
  converted_leads: number;
  currency: string;
  period_end: string | null;
  period_start: string | null;
  qualified_leads: number;
  total_amount_gbp: number;
  total_leads: number;
  unique_users: number;
};

type LeadOpsItem = {
  created_at: string;
  id: string;
  partner_id: string;
  partner_name: string;
  status: 'initiated' | 'qualified' | 'rejected' | 'converted';
  updated_at: string;
  user_id: string;
};

type LeadOpsResponse = {
  items: LeadOpsItem[];
  total: number;
};

type InvoiceSummary = {
  created_at: string;
  currency: string;
  id: string;
  period_end: string | null;
  period_start: string | null;
  status: 'generated' | 'issued' | 'paid' | 'void';
  total_amount_gbp: number;
};

type InvoiceListResponse = {
  items: InvoiceSummary[];
  total: number;
};

type LeadLifecycleStatus = 'qualified' | 'rejected' | 'converted';

type ToastKind = 'success' | 'error' | 'info';

type ToastItem = {
  id: string;
  kind: ToastKind;
  message: string;
};

const currency = (value: number, code: string) => `${value.toFixed(2)} ${code}`;
const toIsoDate = (value: Date) => {
  const year = value.getFullYear();
  const month = String(value.getMonth() + 1).padStart(2, '0');
  const day = String(value.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
};

export default function AdminPage({ token }: AdminPageProps) {
  const [emailToDeactivate, setEmailToDeactivate] = useState('');
  const [leadId, setLeadId] = useState('');
  const [leadStatus, setLeadStatus] = useState<LeadLifecycleStatus>('qualified');
  const [isUserActionLoading, setIsUserActionLoading] = useState(false);
  const [isLeadActionLoading, setIsLeadActionLoading] = useState(false);
  const [isBillingLoading, setIsBillingLoading] = useState(false);
  const [report, setReport] = useState<BillingReportResponse | null>(null);
  const [partners, setPartners] = useState<PartnerOption[]>([]);
  const [selectedPartnerId, setSelectedPartnerId] = useState('');
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const [activePreset, setActivePreset] = useState<PeriodPreset>('30d');
  const [includeQualified, setIncludeQualified] = useState(true);
  const [includeConverted, setIncludeConverted] = useState(true);
  const [pricingPartnerId, setPricingPartnerId] = useState('');
  const [qualifiedPricing, setQualifiedPricing] = useState('');
  const [convertedPricing, setConvertedPricing] = useState('');
  const [isPricingLoading, setIsPricingLoading] = useState(false);
  const [leadOpsStatusFilter, setLeadOpsStatusFilter] = useState<'all' | 'initiated' | 'qualified' | 'rejected' | 'converted'>('all');
  const [leadOpsUserFilter, setLeadOpsUserFilter] = useState('');
  const [leadOpsRows, setLeadOpsRows] = useState<LeadOpsItem[]>([]);
  const [leadOpsTotal, setLeadOpsTotal] = useState(0);
  const [isLeadOpsLoading, setIsLeadOpsLoading] = useState(false);
  const [invoiceRows, setInvoiceRows] = useState<InvoiceSummary[]>([]);
  const [invoiceStatusDrafts, setInvoiceStatusDrafts] = useState<Record<string, InvoiceSummary['status']>>({});
  const [isInvoiceListLoading, setIsInvoiceListLoading] = useState(false);
  const [isInvoiceGenerateLoading, setIsInvoiceGenerateLoading] = useState(false);
  const [isInvoiceStatusLoading, setIsInvoiceStatusLoading] = useState<string | null>(null);
  const [selectedPartnerModal, setSelectedPartnerModal] = useState<BillingReportByPartner | null>(null);
  const [toasts, setToasts] = useState<ToastItem[]>([]);
  const { t } = useTranslation();

  const pushToast = (kind: ToastKind, message: string) => {
    const id = `${Date.now()}-${Math.random().toString(16).slice(2)}`;
    setToasts((current) => [...current, { id, kind, message }]);
    window.setTimeout(() => {
      setToasts((current) => current.filter((item) => item.id !== id));
    }, TOAST_DURATION_MS);
  };

  const dismissToast = (id: string) => {
    setToasts((current) => current.filter((item) => item.id !== id));
  };

  useEffect(() => {
    const loadPartners = async () => {
      try {
        const response = await fetch(`${PARTNER_REGISTRY_URL}/partners`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (!response.ok) {
          throw new Error('Failed to load partners for billing filters.');
        }
        setPartners(await response.json());
      } catch (err) {
        pushToast('error', err instanceof Error ? err.message : 'Unexpected error loading partners.');
      }
    };

    loadPartners();
  }, [token]);

  useEffect(() => {
    if (!pricingPartnerId && partners.length > 0) {
      const firstPartner = partners[0];
      setPricingPartnerId(firstPartner.id);
      setQualifiedPricing(firstPartner.qualified_lead_fee_gbp.toString());
      setConvertedPricing(firstPartner.converted_lead_fee_gbp.toString());
      return;
    }

    const selected = partners.find((partner) => partner.id === pricingPartnerId);
    if (selected) {
      setQualifiedPricing(selected.qualified_lead_fee_gbp.toString());
      setConvertedPricing(selected.converted_lead_fee_gbp.toString());
    }
  }, [partners, pricingPartnerId]);

  const selectedStatuses = useMemo(() => {
    const statuses: string[] = [];
    if (includeQualified) {
      statuses.push('qualified');
    }
    if (includeConverted) {
      statuses.push('converted');
    }
    return statuses;
  }, [includeConverted, includeQualified]);

  const billingRowsSorted = useMemo(() => {
    if (!report) {
      return [];
    }
    return [...report.by_partner].sort((a, b) => b.amount_gbp - a.amount_gbp);
  }, [report]);

  const maxPartnerAmount = useMemo(() => {
    if (!billingRowsSorted.length) {
      return 1;
    }
    return Math.max(...billingRowsSorted.map((item) => item.amount_gbp), 1);
  }, [billingRowsSorted]);

  const chartPoints = useMemo(() => {
    if (!billingRowsSorted.length) {
      return '';
    }
    if (billingRowsSorted.length === 1) {
      return `0,75 100,75`;
    }
    const step = 100 / (billingRowsSorted.length - 1);
    return billingRowsSorted
      .map((item, index) => {
        const x = index * step;
        const normalized = item.amount_gbp / maxPartnerAmount;
        const y = 90 - normalized * 70;
        return `${x},${y}`;
      })
      .join(' ');
  }, [billingRowsSorted, maxPartnerAmount]);

  const applyPreset = (preset: PeriodPreset) => {
    if (preset === 'custom') {
      setActivePreset('custom');
      return;
    }

    const today = new Date();
    const endValue = toIsoDate(today);
    let start = new Date(today);

    if (preset === '7d') {
      start.setDate(today.getDate() - 6);
    } else if (preset === '30d') {
      start.setDate(today.getDate() - 29);
    } else {
      const quarterStartMonth = Math.floor(today.getMonth() / 3) * 3;
      start = new Date(today.getFullYear(), quarterStartMonth, 1);
    }

    setStartDate(toIsoDate(start));
    setEndDate(endValue);
    setActivePreset(preset);
  };

  useEffect(() => {
    if (!startDate && !endDate && activePreset === '30d') {
      applyPreset('30d');
    }
  }, [activePreset, endDate, startDate]);

  useEffect(() => {
    if (!selectedPartnerModal) {
      return;
    }

    const onEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        setSelectedPartnerModal(null);
      }
    };

    document.body.style.overflow = 'hidden';
    window.addEventListener('keydown', onEscape);
    return () => {
      document.body.style.overflow = '';
      window.removeEventListener('keydown', onEscape);
    };
  }, [selectedPartnerModal]);

  const buildBillingQuery = () => {
    const params = new URLSearchParams();
    if (selectedPartnerId) {
      params.set('partner_id', selectedPartnerId);
    }
    if (startDate) {
      params.set('start_date', startDate);
    }
    if (endDate) {
      params.set('end_date', endDate);
    }
    selectedStatuses.forEach((statusValue) => params.append('statuses', statusValue));
    return params.toString();
  };

  const loadLeadOps = async () => {
    setIsLeadOpsLoading(true);
    try {
      const params = new URLSearchParams();
      if (selectedPartnerId) {
        params.set('partner_id', selectedPartnerId);
      }
      if (leadOpsStatusFilter !== 'all') {
        params.set('status', leadOpsStatusFilter);
      }
      if (leadOpsUserFilter) {
        params.set('user_id', leadOpsUserFilter);
      }
      params.set('limit', '25');
      params.set('offset', '0');

      const response = await fetch(`${PARTNER_REGISTRY_URL}/leads?${params.toString()}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      const payload: LeadOpsResponse | { detail?: string } = await response.json();
      if (!response.ok) {
        throw new Error((payload as { detail?: string }).detail || 'Failed to load leads');
      }
      const data = payload as LeadOpsResponse;
      setLeadOpsRows(data.items);
      setLeadOpsTotal(data.total);
      pushToast('success', 'Lead feed updated.');
    } catch (err) {
      pushToast('error', err instanceof Error ? err.message : 'Unexpected error loading lead feed.');
    } finally {
      setIsLeadOpsLoading(false);
    }
  };

  const refreshInvoiceList = async () => {
    setIsInvoiceListLoading(true);
    try {
      const response = await fetch(`${PARTNER_REGISTRY_URL}/billing/invoices?limit=20&offset=0`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      const payload: InvoiceListResponse | { detail?: string } = await response.json();
      if (!response.ok) {
        throw new Error((payload as { detail?: string }).detail || 'Failed to load invoices');
      }
      const data = payload as InvoiceListResponse;
      setInvoiceRows(data.items);
      setInvoiceStatusDrafts(
        data.items.reduce<Record<string, InvoiceSummary['status']>>((accumulator, item) => {
          accumulator[item.id] = item.status;
          return accumulator;
        }, {}),
      );
    } catch (err) {
      pushToast('error', err instanceof Error ? err.message : 'Unexpected error loading invoices.');
    } finally {
      setIsInvoiceListLoading(false);
    }
  };

  const generateInvoiceSnapshot = async () => {
    if (!selectedStatuses.length) {
      pushToast('error', 'Select at least one billable status.');
      return;
    }

    setIsInvoiceGenerateLoading(true);
    try {
      const body: {
        end_date?: string;
        partner_id?: string;
        start_date?: string;
        statuses: string[];
      } = { statuses: selectedStatuses };
      if (selectedPartnerId) {
        body.partner_id = selectedPartnerId;
      }
      if (startDate) {
        body.start_date = startDate;
      }
      if (endDate) {
        body.end_date = endDate;
      }

      const response = await fetch(`${PARTNER_REGISTRY_URL}/billing/invoices/generate`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(body),
      });
      const payload = await response.json();
      if (!response.ok) {
        throw new Error(payload.detail || 'Failed to generate invoice');
      }
      pushToast('success', `Invoice ${payload.id} generated.`);
      await refreshInvoiceList();
    } catch (err) {
      pushToast('error', err instanceof Error ? err.message : 'Unexpected error generating invoice.');
    } finally {
      setIsInvoiceGenerateLoading(false);
    }
  };

  const updateInvoiceStatus = async (invoiceId: string) => {
    const nextStatus = invoiceStatusDrafts[invoiceId];
    if (!nextStatus) {
      return;
    }

    setIsInvoiceStatusLoading(invoiceId);
    try {
      const response = await fetch(`${PARTNER_REGISTRY_URL}/billing/invoices/${invoiceId}/status`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ status: nextStatus }),
      });
      const payload = await response.json();
      if (!response.ok) {
        throw new Error(payload.detail || 'Failed to update invoice status');
      }
      pushToast('success', `Invoice ${invoiceId} updated to ${payload.status}.`);
      await refreshInvoiceList();
    } catch (err) {
      pushToast('error', err instanceof Error ? err.message : 'Unexpected error updating invoice status.');
    } finally {
      setIsInvoiceStatusLoading(null);
    }
  };

  const handlePricingUpdate = async (event: FormEvent) => {
    event.preventDefault();
    if (!pricingPartnerId) {
      pushToast('error', 'Select a partner first.');
      return;
    }

    const qualifiedValue = Number(qualifiedPricing);
    const convertedValue = Number(convertedPricing);
    if (!Number.isFinite(qualifiedValue) || qualifiedValue < 0 || !Number.isFinite(convertedValue) || convertedValue < 0) {
      pushToast('error', 'Pricing values must be non-negative numbers.');
      return;
    }

    setIsPricingLoading(true);
    try {
      const response = await fetch(`${PARTNER_REGISTRY_URL}/partners/${pricingPartnerId}/pricing`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          qualified_lead_fee_gbp: qualifiedValue,
          converted_lead_fee_gbp: convertedValue,
        }),
      });
      const payload = await response.json();
      if (!response.ok) {
        throw new Error(payload.detail || 'Failed to update partner pricing');
      }

      setPartners((current) =>
        current.map((partner) =>
          partner.id === pricingPartnerId
            ? {
                ...partner,
                qualified_lead_fee_gbp: payload.qualified_lead_fee_gbp,
                converted_lead_fee_gbp: payload.converted_lead_fee_gbp,
              }
            : partner,
        ),
      );
      pushToast('success', `Pricing updated for ${payload.name}.`);
    } catch (err) {
      pushToast('error', err instanceof Error ? err.message : 'Unexpected error updating pricing.');
    } finally {
      setIsPricingLoading(false);
    }
  };

  const loadBillingReport = async () => {
    if (!selectedStatuses.length) {
      pushToast('error', 'Select at least one billable status.');
      return;
    }

    setIsBillingLoading(true);
    try {
      const query = buildBillingQuery();
      const response = await fetch(`${PARTNER_REGISTRY_URL}/leads/billing${query ? `?${query}` : ''}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      const payload = await response.json();
      if (!response.ok) {
        throw new Error(payload.detail || 'Failed to load billing report');
      }
      setReport(payload);
      pushToast('success', 'Billing report refreshed.');
    } catch (err) {
      pushToast('error', err instanceof Error ? err.message : 'Unexpected error loading billing report.');
    } finally {
      setIsBillingLoading(false);
    }
  };

  const downloadBillingCsv = async () => {
    if (!selectedStatuses.length) {
      pushToast('error', 'Select at least one billable status.');
      return;
    }

    try {
      const query = buildBillingQuery();
      const response = await fetch(`${PARTNER_REGISTRY_URL}/leads/billing.csv${query ? `?${query}` : ''}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!response.ok) {
        const payload = await response.json();
        throw new Error(payload.detail || 'Failed to download billing CSV');
      }
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const anchor = document.createElement('a');
      anchor.href = url;
      anchor.download = `lead-billing-${new Date().toISOString().split('T')[0]}.csv`;
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
      window.URL.revokeObjectURL(url);
      pushToast('success', 'Billing CSV downloaded.');
    } catch (err) {
      pushToast('error', err instanceof Error ? err.message : 'Unexpected error downloading billing CSV.');
    }
  };

  const handleDeactivate = async (event: FormEvent) => {
    event.preventDefault();
    setIsUserActionLoading(true);

    try {
      const response = await fetch(`${AUTH_SERVICE_BASE_URL}/users/${emailToDeactivate}/deactivate`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
      });
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.detail || 'Failed to deactivate user');
      }

      setEmailToDeactivate('');
      pushToast('success', `User ${data.email} has been deactivated.`);
    } catch (err) {
      pushToast('error', err instanceof Error ? err.message : 'Unexpected error deactivating user.');
    } finally {
      setIsUserActionLoading(false);
    }
  };

  const handleLeadStatusUpdate = async (event: FormEvent) => {
    event.preventDefault();
    if (!leadId) {
      pushToast('error', 'Lead ID is required.');
      return;
    }

    setIsLeadActionLoading(true);
    try {
      const response = await fetch(`${PARTNER_REGISTRY_URL}/leads/${leadId}/status`, {
        body: JSON.stringify({ status: leadStatus }),
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        method: 'PATCH',
      });
      const payload = await response.json();
      if (!response.ok) {
        throw new Error(payload.detail || 'Failed to update lead status');
      }
      pushToast('success', `Lead ${payload.lead_id} updated to '${payload.status}'.`);
    } catch (err) {
      pushToast('error', err instanceof Error ? err.message : 'Unexpected error updating lead status.');
    } finally {
      setIsLeadActionLoading(false);
    }
  };

  useEffect(() => {
    void refreshInvoiceList();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token]);

  return (
    <div className={styles.dashboard}>
      <div className={styles.pageHeader}>
        <p className={styles.pageEyebrow}>Operations Console</p>
        <h1 className={styles.pageTitle}>{t('nav.admin')}</h1>
        <p className={styles.pageLead}>{t('admin.description')} Manage billing operations and lead lifecycle from one dashboard.</p>
      </div>

      <div className={styles.subContainer}>
        <div className={styles.sectionHeader}>
          <h2 className={styles.sectionTitle}>{t('admin.form_title')}</h2>
          <p className={styles.sectionSubtitle}>Restrict risky accounts before they affect workflows.</p>
        </div>
        <form onSubmit={handleDeactivate}>
          <input
            className={styles.input}
            onChange={(event) => setEmailToDeactivate(event.target.value)}
            placeholder="user.email@example.com"
            type="email"
            value={emailToDeactivate}
          />
          <button className={styles.button} disabled={isUserActionLoading} type="submit">
            {isUserActionLoading ? 'Processing...' : t('admin.deactivate_button')}
          </button>
        </form>
      </div>

      <div className={styles.subContainer}>
        <div className={styles.sectionHeader}>
          <h2 className={styles.sectionTitle}>Partner Pricing Controls</h2>
          <p className={styles.sectionSubtitle}>Update partner fee cards used by billing and invoice generation.</p>
        </div>
        <form className={styles.adminStatusForm} onSubmit={handlePricingUpdate}>
          <select
            className={styles.categorySelect}
            onChange={(event) => setPricingPartnerId(event.target.value)}
            value={pricingPartnerId}
          >
            <option value="" disabled>
              Select partner
            </option>
            {partners.map((partner) => (
              <option key={partner.id} value={partner.id}>
                {partner.name}
              </option>
            ))}
          </select>
          <input
            className={styles.input}
            onChange={(event) => setQualifiedPricing(event.target.value)}
            placeholder="Qualified fee GBP"
            type="number"
            min="0"
            step="0.01"
            value={qualifiedPricing}
          />
          <input
            className={styles.input}
            onChange={(event) => setConvertedPricing(event.target.value)}
            placeholder="Converted fee GBP"
            type="number"
            min="0"
            step="0.01"
            value={convertedPricing}
          />
          <button className={styles.button} disabled={isPricingLoading} type="submit">
            {isPricingLoading ? 'Saving...' : 'Save Pricing'}
          </button>
        </form>
      </div>

      <div className={styles.subContainer}>
        <div className={styles.sectionHeader}>
          <h2 className={styles.sectionTitle}>Lead Lifecycle Management</h2>
          <p className={styles.sectionSubtitle}>Apply lifecycle transitions used by billing.</p>
        </div>
        <form className={styles.adminStatusForm} onSubmit={handleLeadStatusUpdate}>
          <input
            className={styles.input}
            onChange={(event) => setLeadId(event.target.value)}
            placeholder="Lead UUID"
            type="text"
            value={leadId}
          />
          <select
            className={styles.categorySelect}
            onChange={(event) => setLeadStatus(event.target.value as LeadLifecycleStatus)}
            value={leadStatus}
          >
            <option value="qualified">qualified</option>
            <option value="rejected">rejected</option>
            <option value="converted">converted</option>
          </select>
          <button className={styles.button} disabled={isLeadActionLoading} type="submit">
            {isLeadActionLoading ? 'Updating...' : 'Update Lead Status'}
          </button>
        </form>
      </div>

      <div className={styles.subContainer}>
        <div className={styles.sectionHeader}>
          <h2 className={styles.sectionTitle}>Operational Lead Feed</h2>
          <p className={styles.sectionSubtitle}>Search and review recent lead events before status/invoice actions.</p>
        </div>
        <div className={styles.adminFiltersGrid}>
          <label className={styles.filterField}>
            <span>Status</span>
            <select
              className={styles.categorySelect}
              onChange={(event) =>
                setLeadOpsStatusFilter(event.target.value as 'all' | 'initiated' | 'qualified' | 'rejected' | 'converted')
              }
              value={leadOpsStatusFilter}
            >
              <option value="all">all</option>
              <option value="initiated">initiated</option>
              <option value="qualified">qualified</option>
              <option value="rejected">rejected</option>
              <option value="converted">converted</option>
            </select>
          </label>
          <label className={styles.filterField}>
            <span>User ID</span>
            <input
              className={styles.input}
              onChange={(event) => setLeadOpsUserFilter(event.target.value)}
              placeholder="user@example.com"
              type="text"
              value={leadOpsUserFilter}
            />
          </label>
          <div className={styles.filterField}>
            <span>Actions</span>
            <button className={styles.button} disabled={isLeadOpsLoading} onClick={loadLeadOps} type="button">
              {isLeadOpsLoading ? 'Loading...' : 'Load Leads'}
            </button>
          </div>
        </div>
        <p className={styles.tableCaption}>Total matching leads: {leadOpsTotal}</p>
        <div className={styles.tableResponsive}>
          <table className={styles.table}>
            <thead>
              <tr>
                <th>Created</th>
                <th>User</th>
                <th>Partner</th>
                <th>Status</th>
                <th>Lead ID</th>
              </tr>
            </thead>
            <tbody>
              {leadOpsRows.length === 0 && (
                <tr>
                  <td colSpan={5}>
                    <p className={styles.emptyState}>No leads loaded yet.</p>
                  </td>
                </tr>
              )}
              {leadOpsRows.map((row) => (
                <tr key={row.id}>
                  <td>{new Date(row.created_at).toLocaleString()}</td>
                  <td>{row.user_id}</td>
                  <td>{row.partner_name}</td>
                  <td>{row.status}</td>
                  <td>{row.id}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <div className={styles.subContainer}>
        <div className={styles.sectionHeader}>
          <h2 className={styles.sectionTitle}>Billing Report</h2>
          <p className={styles.sectionSubtitle}>Filter billable statuses and export finance-ready CSV snapshots.</p>
        </div>

        <div className={styles.billingControlPanel}>
          <div className={styles.presetRow}>
            <button
              className={`${styles.presetButton} ${activePreset === '7d' ? styles.presetButtonActive : ''}`}
              onClick={() => applyPreset('7d')}
              type="button"
            >
              7D
            </button>
            <button
              className={`${styles.presetButton} ${activePreset === '30d' ? styles.presetButtonActive : ''}`}
              onClick={() => applyPreset('30d')}
              type="button"
            >
              30D
            </button>
            <button
              className={`${styles.presetButton} ${activePreset === 'qtd' ? styles.presetButtonActive : ''}`}
              onClick={() => applyPreset('qtd')}
              type="button"
            >
              QTD
            </button>
            <button
              className={`${styles.presetButton} ${activePreset === 'custom' ? styles.presetButtonActive : ''}`}
              onClick={() => setActivePreset('custom')}
              type="button"
            >
              CUSTOM
            </button>
          </div>

          <div className={styles.adminFiltersGrid}>
            <label className={styles.filterField}>
              <span>Start date</span>
              <input
                className={styles.input}
                onChange={(event) => {
                  setStartDate(event.target.value);
                  setActivePreset('custom');
                }}
                type="date"
                value={startDate}
              />
            </label>
            <label className={styles.filterField}>
              <span>End date</span>
              <input
                className={styles.input}
                onChange={(event) => {
                  setEndDate(event.target.value);
                  setActivePreset('custom');
                }}
                type="date"
                value={endDate}
              />
            </label>
            <label className={styles.filterField}>
              <span>Partner</span>
              <select className={styles.categorySelect} onChange={(event) => setSelectedPartnerId(event.target.value)} value={selectedPartnerId}>
                <option value="">All partners</option>
                {partners.map((partner) => (
                  <option key={partner.id} value={partner.id}>
                    {partner.name}
                  </option>
                ))}
              </select>
            </label>
          </div>

          <div className={styles.statusPillsRow}>
            <label className={styles.checkboxPill}>
              <input checked={includeQualified} onChange={(event) => setIncludeQualified(event.target.checked)} type="checkbox" />
              <span>qualified</span>
            </label>
            <label className={styles.checkboxPill}>
              <input checked={includeConverted} onChange={(event) => setIncludeConverted(event.target.checked)} type="checkbox" />
              <span>converted</span>
            </label>
          </div>

          <div className={styles.adminActionsRow}>
            <button className={styles.button} disabled={isBillingLoading} onClick={loadBillingReport} type="button">
              {isBillingLoading ? 'Loading...' : 'Load Billing'}
            </button>
            <button className={`${styles.button} ${styles.secondaryButton}`} onClick={downloadBillingCsv} type="button">
              Download CSV
            </button>
          </div>
        </div>

        {report && (
          <>
            <div className={styles.kpiGrid}>
              <div className={styles.kpiCard}>
                <p className={styles.kpiLabel}>Total revenue</p>
                <p className={styles.kpiValue}>{currency(report.total_amount_gbp, report.currency)}</p>
              </div>
              <div className={styles.kpiCard}>
                <p className={styles.kpiLabel}>Qualified leads</p>
                <p className={styles.kpiValue}>{report.qualified_leads}</p>
              </div>
              <div className={styles.kpiCard}>
                <p className={styles.kpiLabel}>Converted leads</p>
                <p className={styles.kpiValue}>{report.converted_leads}</p>
              </div>
              <div className={styles.kpiCard}>
                <p className={styles.kpiLabel}>Unique users</p>
                <p className={styles.kpiValue}>{report.unique_users}</p>
              </div>
            </div>

            <div className={styles.billingVisualGrid}>
              <div className={styles.chartCard}>
                <h3 className={styles.chartTitle}>Revenue trend by partner</h3>
                <p className={styles.chartSubtitle}>Sorted by contribution amount in current filter window.</p>
                <svg className={styles.lineChart} preserveAspectRatio="none" viewBox="0 0 100 100">
                  <polyline className={styles.lineChartPath} points={chartPoints || '0,75 100,75'} />
                </svg>
              </div>

              <div className={styles.barChartCard}>
                {!billingRowsSorted.length && <p className={styles.emptyState}>No partner rows for selected filters.</p>}
                {billingRowsSorted.map((item) => (
                  <div className={styles.barRow} key={item.partner_id}>
                    <span className={styles.barLabel}>{item.partner_name}</span>
                    <div className={styles.barTrack}>
                      <span className={styles.barFill} style={{ width: `${Math.max(7, (item.amount_gbp / maxPartnerAmount) * 100)}%` }} />
                    </div>
                    <span className={styles.barValue}>{currency(item.amount_gbp, report.currency)}</span>
                  </div>
                ))}
              </div>
            </div>

            <div className={styles.tableResponsive}>
              <table className={styles.table}>
                <thead>
                  <tr>
                    <th>Partner</th>
                    <th>Qualified</th>
                    <th>Converted</th>
                    <th>Rates (GBP)</th>
                    <th>Amount (GBP)</th>
                    <th>Action</th>
                  </tr>
                </thead>
                <tbody>
                  {billingRowsSorted.map((item) => (
                    <tr key={item.partner_id}>
                      <td>{item.partner_name}</td>
                      <td>{item.qualified_leads}</td>
                      <td>{item.converted_leads}</td>
                      <td>
                        {item.qualified_lead_fee_gbp.toFixed(2)} / {item.converted_lead_fee_gbp.toFixed(2)}
                      </td>
                      <td className={styles.positive}>{item.amount_gbp.toFixed(2)}</td>
                      <td>
                        <button className={styles.tableActionButton} onClick={() => setSelectedPartnerModal(item)} type="button">
                          Details
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </>
        )}
      </div>

      <div className={styles.subContainer}>
        <div className={styles.sectionHeader}>
          <h2 className={styles.sectionTitle}>Invoice Operations</h2>
          <p className={styles.sectionSubtitle}>Generate immutable invoice snapshots and progress them through lifecycle.</p>
        </div>
        <div className={styles.adminActionsRow}>
          <button className={styles.button} disabled={isInvoiceGenerateLoading} onClick={generateInvoiceSnapshot} type="button">
            {isInvoiceGenerateLoading ? 'Generating...' : 'Generate Invoice Snapshot'}
          </button>
          <button className={`${styles.button} ${styles.secondaryButton}`} disabled={isInvoiceListLoading} onClick={refreshInvoiceList} type="button">
            {isInvoiceListLoading ? 'Refreshing...' : 'Refresh Invoice Queue'}
          </button>
        </div>
        <div className={styles.tableResponsive}>
          <table className={styles.table}>
            <thead>
              <tr>
                <th>Created</th>
                <th>Invoice ID</th>
                <th>Status</th>
                <th>Total</th>
                <th>Update</th>
              </tr>
            </thead>
            <tbody>
              {invoiceRows.length === 0 && (
                <tr>
                  <td colSpan={5}>
                    <p className={styles.emptyState}>No invoices generated yet.</p>
                  </td>
                </tr>
              )}
              {invoiceRows.map((invoice) => (
                <tr key={invoice.id}>
                  <td>{new Date(invoice.created_at).toLocaleString()}</td>
                  <td>{invoice.id}</td>
                  <td>{invoice.status}</td>
                  <td className={styles.positive}>{currency(invoice.total_amount_gbp, invoice.currency)}</td>
                  <td>
                    <div className={styles.invoiceActionGroup}>
                      <select
                        className={styles.categorySelect}
                        onChange={(event) =>
                          setInvoiceStatusDrafts((current) => ({
                            ...current,
                            [invoice.id]: event.target.value as InvoiceSummary['status'],
                          }))
                        }
                        value={invoiceStatusDrafts[invoice.id] || invoice.status}
                      >
                        <option value="generated">generated</option>
                        <option value="issued">issued</option>
                        <option value="paid">paid</option>
                        <option value="void">void</option>
                      </select>
                      <button
                        className={styles.tableActionButton}
                        disabled={isInvoiceStatusLoading === invoice.id}
                        onClick={() => updateInvoiceStatus(invoice.id)}
                        type="button"
                      >
                        {isInvoiceStatusLoading === invoice.id ? 'Saving...' : 'Apply'}
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {selectedPartnerModal && report && (
        <div className={styles.modalBackdrop} onClick={() => setSelectedPartnerModal(null)} role="presentation">
          <div className={styles.modalCard} onClick={(event) => event.stopPropagation()} role="dialog" aria-modal="true">
            <div className={styles.modalHeader}>
              <h3 className={styles.modalTitle}>{selectedPartnerModal.partner_name}</h3>
              <button aria-label="Close partner details" className={styles.toastClose} onClick={() => setSelectedPartnerModal(null)} type="button">
                ×
              </button>
            </div>
            <p className={styles.sectionSubtitle}>Partner billing drill-down for selected filters.</p>
            <div className={styles.modalGrid}>
              <div className={styles.modalMetric}>
                <span className={styles.modalLabel}>Qualified leads</span>
                <strong className={styles.modalValue}>{selectedPartnerModal.qualified_leads}</strong>
              </div>
              <div className={styles.modalMetric}>
                <span className={styles.modalLabel}>Converted leads</span>
                <strong className={styles.modalValue}>{selectedPartnerModal.converted_leads}</strong>
              </div>
              <div className={styles.modalMetric}>
                <span className={styles.modalLabel}>Unique users</span>
                <strong className={styles.modalValue}>{selectedPartnerModal.unique_users}</strong>
              </div>
              <div className={styles.modalMetric}>
                <span className={styles.modalLabel}>Revenue contribution</span>
                <strong className={styles.modalValue}>{currency(selectedPartnerModal.amount_gbp, report.currency)}</strong>
              </div>
              <div className={styles.modalMetric}>
                <span className={styles.modalLabel}>Conversion rate</span>
                <strong className={styles.modalValue}>
                  {selectedPartnerModal.qualified_leads
                    ? `${((selectedPartnerModal.converted_leads / selectedPartnerModal.qualified_leads) * 100).toFixed(1)}%`
                    : '0.0%'}
                </strong>
              </div>
              <div className={styles.modalMetric}>
                <span className={styles.modalLabel}>Avg revenue / user</span>
                <strong className={styles.modalValue}>
                  {selectedPartnerModal.unique_users
                    ? currency(selectedPartnerModal.amount_gbp / selectedPartnerModal.unique_users, report.currency)
                    : currency(0, report.currency)}
                </strong>
              </div>
            </div>
          </div>
        </div>
      )}

      <div className={styles.toastViewport}>
        {toasts.map((toast) => (
          <div
            className={`${styles.toastItem} ${
              toast.kind === 'success' ? styles.toastSuccess : toast.kind === 'error' ? styles.toastError : styles.toastInfo
            }`}
            key={toast.id}
            role="status"
          >
            <span>{toast.message}</span>
            <button aria-label="Dismiss notification" className={styles.toastClose} onClick={() => dismissToast(toast.id)} type="button">
              ×
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}
