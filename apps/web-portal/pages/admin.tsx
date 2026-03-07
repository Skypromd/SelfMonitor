import { useEffect, useMemo, useState, type FormEvent } from 'react';
import { useTranslation } from '../hooks/useTranslation';
import styles from '../styles/Home.module.css';

const AUTH_SERVICE_BASE_URL = process.env.NEXT_PUBLIC_AUTH_SERVICE_URL || 'http://localhost:8001';
const PARTNER_REGISTRY_URL = process.env.NEXT_PUBLIC_PARTNER_REGISTRY_URL || 'http://localhost:8016';
const BILLING_SERVICE_URL = process.env.NEXT_PUBLIC_BILLING_SERVICE_URL || 'http://localhost:8024';
const TOAST_DURATION_MS = 4200;

type AdminUser = { email: string; is_admin: boolean };

type BillingPlanStat = {
  plan: string;
  count: number;
  mrr: number;
  active: number;
  trialing: number;
  inactive: number;
};

type BillingAdminStats = {
  by_plan: BillingPlanStat[];
  total_mrr: number;
  total_arr: number;
  total_subscribers: number;
  total_active: number;
  total_trialing: number;
  recent_subscriptions: { email: string; plan: string; status: string; created_at: number; has_stripe: boolean }[];
};

type AdminPageProps = {
  token: string;
  user?: AdminUser;
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
  due_date: string;
  id: string;
  invoice_number: string;
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

type AdminTab = 'overview' | 'subscriptions' | 'users' | 'billing' | 'leadops' | 'invoices' | 'ai-agent' | 'health' | 'support';

const TAB_LABELS: Record<AdminTab, string> = {
  overview: '📊 Overview',
  subscriptions: '💳 Subscriptions',
  users: '👥 Users',
  billing: '🤝 Partner Billing',
  leadops: '🔄 Lead Ops',
  invoices: '🧾 Invoices',
  'ai-agent': '🤖 AI Agent',
  health: '🟢 System Health',
  support: '💬 Support Tickets',
};

const MOCK_TICKETS = [
  { id: 'SM-10421', user: 'alice@example.com',    subject: 'Bank connection failing since update', category: 'Technical', priority: 'high',   status: 'open',     created: '2026-03-05 09:14', rating: null },
  { id: 'SM-10420', user: 'bob@startup.io',        subject: 'How do I export to Xero?',            category: 'Billing',   priority: 'low',    status: 'resolved', created: '2026-03-04 14:30', rating: 5    },
  { id: 'SM-10419', user: 'charlie@freelance.co',  subject: 'HMRC submission gave error 1046',      category: 'Technical', priority: 'high',   status: 'open',     created: '2026-03-04 11:05', rating: null },
  { id: 'SM-10418', user: 'diana@consultco.com',   subject: 'Request: dark mode for mobile app',   category: 'Feature',   priority: 'low',    status: 'resolved', created: '2026-03-03 16:50', rating: 4    },
  { id: 'SM-10417', user: 'evan@photography.me',   subject: 'Charged twice this month',             category: 'Billing',   priority: 'medium', status: 'open',     created: '2026-03-03 10:22', rating: null },
  { id: 'SM-10416', user: 'fiona@designstudio.uk', subject: 'Can\'t update VAT number in profile',  category: 'Account',   priority: 'medium', status: 'resolved', created: '2026-03-02 09:00', rating: 5    },
];

const MOCK_FEEDBACK = [
  { date: '2026-03-05', rating: 5, comment: 'Love the new dashboard! MRR tracking is exactly what I needed.', user: 'diana@consultco.com' },
  { date: '2026-03-04', rating: 4, comment: 'Bank sync is a bit slow sometimes but overall great product.',   user: 'evan@photography.me' },
  { date: '2026-03-03', rating: 5, comment: 'The AI assistant saved me hours on my tax return.',             user: 'alice@example.com' },
  { date: '2026-03-02', rating: 3, comment: 'Would love a bulk transaction editor.',                          user: 'greg@tradie.co.uk' },
  { date: '2026-03-01', rating: 5, comment: 'Best self-employed finance app I have used. Worth every penny.', user: 'helen@shopowner.com' },
];

const MOCK_PLAN_STATS = [
  { plan: 'Starter',  price: 9,  count: 187, mrr: 1683, color: '#14b8a6' },
  { plan: 'Growth',   price: 12, count: 124, mrr: 1488, color: '#6366f1' },
  { plan: 'Pro',      price: 15, count: 78,  mrr: 1170, color: '#f59e0b' },
  { plan: 'Business', price: 25, count: 23,  mrr: 575,  color: '#ec4899' },
];

const MOCK_MRR_HISTORY = [
  { month: 'Apr', mrr: 3100 }, { month: 'May', mrr: 3350 }, { month: 'Jun', mrr: 3600 },
  { month: 'Jul', mrr: 3820 }, { month: 'Aug', mrr: 4050 }, { month: 'Sep', mrr: 4200 },
  { month: 'Oct', mrr: 4380 }, { month: 'Nov', mrr: 4510 }, { month: 'Dec', mrr: 4650 },
  { month: 'Jan', mrr: 4720 }, { month: 'Feb', mrr: 4810 }, { month: 'Mar', mrr: 4890 },
];

const MOCK_USERS = [
  { id: '1', email: 'alice@example.com',      plan: 'Pro',      status: 'active',    joined: '2025-08-12', nextBill: '2026-04-12', revenue: 180 },
  { id: '2', email: 'bob@startup.io',          plan: 'Starter',  status: 'trialing',  joined: '2026-02-20', nextBill: '2026-03-06', revenue: 0   },
  { id: '3', email: 'charlie@freelance.co.uk', plan: 'Growth',   status: 'active',    joined: '2025-11-05', nextBill: '2026-04-05', revenue: 48  },
  { id: '4', email: 'diana@consultco.com',     plan: 'Business', status: 'active',    joined: '2025-07-01', nextBill: '2026-04-01', revenue: 225 },
  { id: '5', email: 'evan@photography.me',     plan: 'Starter',  status: 'active',    joined: '2025-09-30', nextBill: '2026-04-30', revenue: 54  },
  { id: '6', email: 'fiona@designstudio.uk',   plan: 'Pro',      status: 'active',    joined: '2025-10-15', nextBill: '2026-04-15', revenue: 150 },
  { id: '7', email: 'greg@tradie.co.uk',       plan: 'Starter',  status: 'cancelled', joined: '2025-06-10', nextBill: '—',          revenue: 27  },
  { id: '8', email: 'helen@shopowner.com',     plan: 'Growth',   status: 'trialing',  joined: '2026-03-01', nextBill: '2026-03-15', revenue: 0   },
];

const SYSTEM_SERVICES = [
  { name: 'Auth Service',     port: 8001, path: '/health' },
  { name: 'Analytics',        port: 8009, path: '/health' },
  { name: 'Localization',     port: 8012, path: '/health' },
  { name: 'User Profile',     port: 8005, path: '/health' },
  { name: 'Advice / AI',      port: 8010, path: '/health' },
  { name: 'Documents',        port: 8006, path: '/health' },
  { name: 'Partner Registry', port: 8016, path: '/health' },
  { name: 'Transactions',     port: 8003, path: '/health' },
];

const AI_AGENT_PERMISSIONS = [
  { id: 'read_users',        label: 'Read user list & profiles',         available: true,  defaultOn: true  },
  { id: 'read_reports',      label: 'Read KPIs & billing reports',       available: true,  defaultOn: true  },
  { id: 'manage_subs',       label: 'Upgrade / downgrade subscriptions', available: false, defaultOn: false },
  { id: 'send_emails',       label: 'Send transactional emails',         available: false, defaultOn: false },
  { id: 'deactivate_users',  label: 'Deactivate risky accounts',         available: false, defaultOn: false },
  { id: 'update_pricing',    label: 'Update partner pricing',            available: false, defaultOn: false },
  { id: 'generate_invoices', label: 'Auto-generate & issue invoices',    available: false, defaultOn: false },
  { id: 'update_leads',      label: 'Progress lead lifecycle',           available: false, defaultOn: false },
  { id: 'deploy_changes',    label: 'Deploy frontend/backend updates',   available: false, defaultOn: false },
];

export default function AdminPage({ token, user }: AdminPageProps) {
  // ── Double-check: server guard is in _app.tsx, but defensive check here too ──
  if (user && user.is_admin === false) {
    return (
      <div style={{
        display: 'flex', flexDirection: 'column', alignItems: 'center',
        justifyContent: 'center', minHeight: '60vh', gap: '1rem', color: '#94a3b8',
      }}>
        <div style={{ fontSize: '3rem' }}>🔒</div>
        <h1 style={{ color: '#f87171', fontSize: '1.5rem' }}>Access Denied</h1>
        <p>Admin privileges required to view this page.</p>
      </div>
    );
  }

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
  const [invoiceExportLoadingKey, setInvoiceExportLoadingKey] = useState<string | null>(null);
  const [selectedPartnerModal, setSelectedPartnerModal] = useState<BillingReportByPartner | null>(null);
  const [toasts, setToasts] = useState<ToastItem[]>([]);
  const [activeTab, setActiveTab] = useState<AdminTab>('overview');
  const [userSearch, setUserSearch] = useState('');
  const [userPlanFilter, setUserPlanFilter] = useState('all');
  const [agentEnabled, setAgentEnabled] = useState(false);
  const [agentPerms, setAgentPerms] = useState<Record<string, boolean>>(
    Object.fromEntries(AI_AGENT_PERMISSIONS.map((p) => [p.id, p.defaultOn])),
  );
  const [serviceStatuses, setServiceStatuses] = useState<Record<string, 'checking' | 'online' | 'offline'>>({});
  const [billingAdminStats, setBillingAdminStats] = useState<BillingAdminStats | null>(null);
  const [isBillingStatsLoading, setIsBillingStatsLoading] = useState(false);
  const { t } = useTranslation();

  const pushToast = (kind: ToastKind, message: string) => {
    const id = `${Date.now()}-${Math.random().toString(16).slice(2)}`;
    setToasts((current) => [...current, { id, kind, message }]);
    window.setTimeout(() => {
      setToasts((current) => current.filter((item) => item.id !== id));
    }, TOAST_DURATION_MS);
  };

  // ── Fetch real billing/subscription stats ────────────────────────────────────
  useEffect(() => {
    if (!token) return;
    const loadBillingStats = async () => {
      setIsBillingStatsLoading(true);
      try {
        const res = await fetch(`${BILLING_SERVICE_URL}/admin/stats`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (res.ok) setBillingAdminStats(await res.json());
      } catch {
        // non-fatal — falls back to mock data
      } finally {
        setIsBillingStatsLoading(false);
      }
    };
    void loadBillingStats();
  }, [token]);

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
      pushToast('success', `Invoice ${payload.invoice_number || payload.id} generated.`);
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

  const downloadInvoiceArtifact = async (invoice: InvoiceSummary, target: 'pdf' | 'xero' | 'quickbooks') => {
    const actionKey = `${invoice.id}:${target}`;
    setInvoiceExportLoadingKey(actionKey);
    try {
      const endpoint =
        target === 'pdf'
          ? `${PARTNER_REGISTRY_URL}/billing/invoices/${invoice.id}/pdf`
          : `${PARTNER_REGISTRY_URL}/billing/invoices/${invoice.id}/accounting.csv?target=${target}`;

      const response = await fetch(endpoint, {
        headers: { Authorization: `Bearer ${token}` },
      });

      if (!response.ok) {
        let detail = 'Failed to download invoice artifact';
        try {
          const payload = await response.json();
          if (payload?.detail) {
            detail = payload.detail as string;
          }
        } catch {
          // Keep fallback detail when non-JSON error payload.
        }
        throw new Error(detail);
      }

      const blob = await response.blob();
      const disposition = response.headers.get('content-disposition');
      const matched = disposition?.match(/filename="?([^"]+)"?/i);
      const fallbackName =
        target === 'pdf' ? `${invoice.invoice_number}.pdf` : `${invoice.invoice_number}_${target}.csv`;
      const filename = matched?.[1] || fallbackName;

      const url = window.URL.createObjectURL(blob);
      const anchor = document.createElement('a');
      anchor.href = url;
      anchor.download = filename;
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
      window.URL.revokeObjectURL(url);
      pushToast('success', `${invoice.invoice_number} ${target.toUpperCase()} downloaded.`);
    } catch (err) {
      pushToast('error', err instanceof Error ? err.message : 'Unexpected error downloading invoice artifact.');
    } finally {
      setInvoiceExportLoadingKey((current) => (current === actionKey ? null : current));
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

  // ── Computed values ──────────────────────────────────────────────────────────
  const TOTAL_MRR = MOCK_PLAN_STATS.reduce((sum, p) => sum + p.mrr, 0);
  const TOTAL_PAYING = MOCK_PLAN_STATS.reduce((sum, p) => sum + p.count, 0);
  const MRR_MAX = Math.max(...MOCK_MRR_HISTORY.map((m) => m.mrr));
  const PLAN_MAX = Math.max(...MOCK_PLAN_STATS.map((p) => p.count));

  const filteredUsers = MOCK_USERS.filter((u) => {
    const matchSearch = !userSearch || u.email.toLowerCase().includes(userSearch.toLowerCase());
    const matchPlan = userPlanFilter === 'all' || u.plan.toLowerCase() === userPlanFilter.toLowerCase();
    return matchSearch && matchPlan;
  });

  const checkAllServices = async () => {
    const initial: Record<string, 'checking' | 'online' | 'offline'> = {};
    SYSTEM_SERVICES.forEach((s) => { initial[s.name] = 'checking'; });
    setServiceStatuses(initial);
    await Promise.all(
      SYSTEM_SERVICES.map(async (service) => {
        try {
          const ctrl = new AbortController();
          const timer = window.setTimeout(() => ctrl.abort(), 3500);
          const resp = await fetch(`http://localhost:${service.port}${service.path}`, { signal: ctrl.signal });
          window.clearTimeout(timer);
          setServiceStatuses((prev) => ({ ...prev, [service.name]: resp.ok ? 'online' : 'offline' }));
        } catch {
          setServiceStatuses((prev) => ({ ...prev, [service.name]: 'offline' }));
        }
      }),
    );
  };

  const statusColor = (s: string) =>
    s === 'online' ? '#34d399' : s === 'checking' ? '#f59e0b' : '#f87171';
  const statusDot = (s: string) =>
    s === 'online' ? '🟢' : s === 'checking' ? '🟡' : '🔴';

  return (
    <div className={styles.dashboard}>
      <div className={styles.pageHeader}>
        <p className={styles.pageEyebrow}>Operations Console</p>
        <h1 className={styles.pageTitle}>{t('nav.admin')}</h1>
        <p className={styles.pageLead}>Full visibility and control over your SelfMonitor business — revenue, users, partners, and AI automation.</p>
      </div>

      {/* ── Tab Navigation ──────────────────────────────────────────────── */}
      <div className={styles.adminTabBar}>
        {(Object.keys(TAB_LABELS) as AdminTab[]).map((tab) => (
          <button
            key={tab}
            className={`${styles.adminTab} ${activeTab === tab ? styles.adminTabActive : ''}`}
            onClick={() => setActiveTab(tab)}
            type="button"
          >
            {TAB_LABELS[tab]}
          </button>
        ))}
      </div>

      {/* ══════════════════════════════════════════════════════════════════
          OVERVIEW TAB
      ══════════════════════════════════════════════════════════════════ */}
      {activeTab === 'overview' && (
        <>
          {/* KPI Grid */}
          <div className={styles.kpiGrid}>
            <div className={styles.kpiCard}>
              <p className={styles.kpiLabel}>Monthly Recurring Revenue</p>
              <p className={styles.kpiValue}>£{TOTAL_MRR.toLocaleString()}</p>
              <p className={styles.kpiSub}>+2.1% vs last month</p>
            </div>
            <div className={styles.kpiCard}>
              <p className={styles.kpiLabel}>Annual Run Rate</p>
              <p className={styles.kpiValue}>£{(TOTAL_MRR * 12).toLocaleString()}</p>
              <p className={styles.kpiSub}>Based on current MRR</p>
            </div>
            <div className={styles.kpiCard}>
              <p className={styles.kpiLabel}>Paying Users</p>
              <p className={styles.kpiValue}>{TOTAL_PAYING}</p>
              <p className={styles.kpiSub}>67 on free trial</p>
            </div>
            <div className={styles.kpiCard}>
              <p className={styles.kpiLabel}>ARPU</p>
              <p className={styles.kpiValue}>£{(TOTAL_MRR / TOTAL_PAYING).toFixed(2)}</p>
              <p className={styles.kpiSub}>Avg revenue per user</p>
            </div>
            <div className={styles.kpiCard}>
              <p className={styles.kpiLabel}>Churn Rate</p>
              <p className={styles.kpiValue}>2.3%</p>
              <p className={styles.kpiSub}>Monthly — target &lt;2%</p>
            </div>
            <div className={styles.kpiCard}>
              <p className={styles.kpiLabel}>Trial Conversion</p>
              <p className={styles.kpiValue}>38.4%</p>
              <p className={styles.kpiSub}>Trials → paid</p>
            </div>
          </div>

          {/* MRR 12-month bar chart */}
          <div className={styles.subContainer}>
            <div className={styles.sectionHeader}>
              <h2 className={styles.sectionTitle}>MRR Growth — Last 12 Months</h2>
              <p className={styles.sectionSubtitle}>Monthly Recurring Revenue trend. £{TOTAL_MRR.toLocaleString()} current MRR.</p>
            </div>
            <div className={styles.mrrBarChart}>
              {MOCK_MRR_HISTORY.map((item) => {
                const pct = (item.mrr / MRR_MAX) * 100;
                return (
                  <div key={item.month} className={styles.mrrBarCol}>
                    <span className={styles.mrrBarVal}>£{(item.mrr / 1000).toFixed(1)}k</span>
                    <div className={styles.mrrBarTrack}>
                      <div className={styles.mrrBarFill} style={{ height: `${pct}%` }} />
                    </div>
                    <span className={styles.mrrBarMonth}>{item.month}</span>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Plan distribution */}
          <div className={styles.subContainer}>
            <div className={styles.sectionHeader}>
              <h2 className={styles.sectionTitle}>User Distribution by Plan</h2>
              <p className={styles.sectionSubtitle}>{TOTAL_PAYING} paying subscribers across 4 tiers.</p>
            </div>
            <div className={styles.planDistGrid}>
              {MOCK_PLAN_STATS.map((p) => (
                <div key={p.plan} className={styles.planDistCard} style={{ borderColor: p.color }}>
                  <div className={styles.planDistHeader}>
                    <span className={styles.planDistName}>{p.plan}</span>
                    <span className={styles.planDistPrice} style={{ color: p.color }}>£{p.price}/mo</span>
                  </div>
                  <p className={styles.planDistCount}>{p.count} users</p>
                  <p className={styles.planDistMrr}>£{p.mrr.toLocaleString()} MRR</p>
                  <div className={styles.planDistBar}>
                    <div
                      className={styles.planDistBarFill}
                      style={{ width: `${(p.count / PLAN_MAX) * 100}%`, background: p.color }}
                    />
                  </div>
                  <p className={styles.planDistShare}>{((p.count / TOTAL_PAYING) * 100).toFixed(1)}% of customers</p>
                </div>
              ))}
            </div>
          </div>

          {/* Recent signups */}
          <div className={styles.subContainer}>
            <div className={styles.sectionHeader}>
              <h2 className={styles.sectionTitle}>Recent Signups</h2>
              <p className={styles.sectionSubtitle}>Last 5 registered users.</p>
            </div>
            <div className={styles.tableResponsive}>
              <table className={styles.table}>
                <thead>
                  <tr>
                    <th>Email</th>
                    <th>Plan</th>
                    <th>Status</th>
                    <th>Joined</th>
                    <th>Revenue (£)</th>
                  </tr>
                </thead>
                <tbody>
                  {MOCK_USERS.slice(0, 5).map((u) => (
                    <tr key={u.id}>
                      <td>{u.email}</td>
                      <td><span className={styles.planBadge}>{u.plan}</span></td>
                      <td>
                        <span style={{
                          color: u.status === 'active' ? '#34d399' : u.status === 'trialing' ? '#f59e0b' : '#f87171',
                          fontWeight: 600, textTransform: 'capitalize',
                        }}>{u.status}</span>
                      </td>
                      <td>{u.joined}</td>
                      <td className={u.revenue > 0 ? styles.positive : ''}>{u.revenue > 0 ? u.revenue : '—'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}

      {/* ══════════════════════════════════════════════════════════════════
          SUBSCRIPTIONS TAB
      ══════════════════════════════════════════════════════════════════ */}
      {activeTab === 'subscriptions' && (() => {
        // Use real data from billing-service if available, else fall back to mock
        const planColors: Record<string, string> = {
          starter: '#14b8a6', growth: '#6366f1', pro: '#f59e0b', business: '#ec4899', free: '#64748b',
        };
        const planPrices: Record<string, number> = {
          free: 0, starter: 9, growth: 12, pro: 15, business: 25,
        };
        const activePlans = billingAdminStats?.by_plan ?? MOCK_PLAN_STATS.map(p => ({
          plan: p.plan.toLowerCase(), count: p.count, mrr: p.mrr,
          active: p.count, trialing: 0, inactive: 0,
        }));
        const liveTotal_MRR = billingAdminStats?.total_mrr ?? TOTAL_MRR;
        const liveTotal_ARR = billingAdminStats?.total_arr ?? TOTAL_MRR * 12;
        const liveTotalSubscribers = billingAdminStats?.total_subscribers ?? TOTAL_PAYING;
        const liveActive = billingAdminStats?.total_active ?? TOTAL_PAYING;
        const liveTrialing = billingAdminStats?.total_trialing ?? 0;
        const isLive = billingAdminStats !== null;
        const recentSubs = billingAdminStats?.recent_subscriptions ?? [];

        return (
          <>
            {/* Live data badge */}
            <div style={{
              display: 'inline-flex', alignItems: 'center', gap: '0.5rem',
              padding: '0.3rem 0.75rem', borderRadius: 20,
              background: isLive ? 'rgba(52,211,153,0.1)' : 'rgba(251,191,36,0.1)',
              border: `1px solid ${isLive ? 'rgba(52,211,153,0.3)' : 'rgba(251,191,36,0.3)'}`,
              color: isLive ? '#34d399' : '#fbbf24',
              fontSize: '0.75rem', marginBottom: '1.25rem',
            }}>
              {isBillingStatsLoading ? '⏳ Loading live data…'
                : isLive ? '🟢 Live data — Stripe billing-service'
                : '🟡 Mock data — billing-service unavailable'}
            </div>

            {/* Plan KPI cards */}
            <div className={styles.kpiGrid}>
              {activePlans.map((p) => {
                const color = planColors[p.plan.toLowerCase()] ?? '#94a3b8';
                const price = planPrices[p.plan.toLowerCase()] ?? 0;
                return (
                  <div key={p.plan} className={styles.kpiCard} style={{ borderLeft: `3px solid ${color}` }}>
                    <p className={styles.kpiLabel}>{p.plan.charAt(0).toUpperCase() + p.plan.slice(1)} Plan</p>
                    <p className={styles.kpiValue} style={{ color }}>{p.count} users</p>
                    <p className={styles.kpiSub}>
                      £{p.mrr.toLocaleString()} / mo
                      {isLive && ` · ${p.active} active, ${p.trialing} trial`}
                      {!isLive && ` · £${price}/user`}
                    </p>
                  </div>
                );
              })}
              <div className={styles.kpiCard}>
                <p className={styles.kpiLabel}>Total MRR</p>
                <p className={styles.kpiValue}>£{liveTotal_MRR.toLocaleString()}</p>
                <p className={styles.kpiSub}>{isLive ? `${liveActive} active · ${liveTrialing} trialing` : 'All plans combined'}</p>
              </div>
              <div className={styles.kpiCard}>
                <p className={styles.kpiLabel}>Total ARR</p>
                <p className={styles.kpiValue}>£{Math.round(liveTotal_ARR).toLocaleString()}</p>
                <p className={styles.kpiSub}>{liveTotalSubscribers} total subscribers</p>
              </div>
            </div>

            {/* Plan breakdown table */}
            <div className={styles.subContainer}>
              <div className={styles.sectionHeader}>
                <h2 className={styles.sectionTitle}>Plan Breakdown</h2>
                <p className={styles.sectionSubtitle}>Revenue contribution per subscription tier.</p>
              </div>
              <div className={styles.tableResponsive}>
                <table className={styles.table}>
                  <thead>
                    <tr>
                      <th>Plan</th>
                      <th>Price/mo</th>
                      <th>Subscribers</th>
                      {isLive && <th>Active</th>}
                      {isLive && <th>Trialing</th>}
                      <th>MRR (£)</th>
                      <th>ARR (£)</th>
                      <th>% of MRR</th>
                      <th>Revenue Bar</th>
                    </tr>
                  </thead>
                  <tbody>
                    {activePlans.map((p) => {
                      const color = planColors[p.plan.toLowerCase()] ?? '#94a3b8';
                      const price = planPrices[p.plan.toLowerCase()] ?? 0;
                      const pct = liveTotal_MRR > 0 ? ((p.mrr / liveTotal_MRR) * 100).toFixed(1) : '0.0';
                      return (
                        <tr key={p.plan}>
                          <td><span className={styles.planBadge} style={{ background: color + '22', color }}>{p.plan.charAt(0).toUpperCase() + p.plan.slice(1)}</span></td>
                          <td>£{price}</td>
                          <td>{p.count}</td>
                          {isLive && <td><span style={{ color: '#34d399' }}>{p.active}</span></td>}
                          {isLive && <td><span style={{ color: '#fbbf24' }}>{p.trialing}</span></td>}
                          <td className={styles.positive}>£{p.mrr.toLocaleString()}</td>
                          <td className={styles.positive}>£{Math.round(p.mrr * 12).toLocaleString()}</td>
                          <td>{pct}%</td>
                          <td style={{ minWidth: 120 }}>
                            <div className={styles.barTrack}>
                              <span className={styles.barFill} style={{ width: `${Number(pct)}%`, background: color }} />
                            </div>
                          </td>
                        </tr>
                      );
                    })}
                    <tr style={{ fontWeight: 700, borderTop: '1px solid rgba(148,163,184,0.2)' }}>
                      <td>TOTAL</td><td>—</td><td>{liveTotalSubscribers}</td>
                      {isLive && <td><span style={{ color: '#34d399' }}>{liveActive}</span></td>}
                      {isLive && <td><span style={{ color: '#fbbf24' }}>{liveTrialing}</span></td>}
                      <td className={styles.positive}>£{liveTotal_MRR.toLocaleString()}</td>
                      <td className={styles.positive}>£{Math.round(liveTotal_ARR).toLocaleString()}</td>
                      <td>100%</td><td />
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>

            {/* Recent subscriptions (live only) */}
            {isLive && recentSubs.length > 0 && (
              <div className={styles.subContainer}>
                <div className={styles.sectionHeader}>
                  <h2 className={styles.sectionTitle}>Recent Subscriptions</h2>
                  <p className={styles.sectionSubtitle}>Latest 20 sign-ups from Stripe.</p>
                </div>
                <div className={styles.tableResponsive}>
                  <table className={styles.table}>
                    <thead>
                      <tr><th>Email</th><th>Plan</th><th>Status</th><th>Stripe</th><th>Date</th></tr>
                    </thead>
                    <tbody>
                      {recentSubs.map((s, i) => (
                        <tr key={i}>
                          <td>{s.email}</td>
                          <td><span className={styles.planBadge} style={{ background: (planColors[s.plan] ?? '#64748b') + '22', color: planColors[s.plan] ?? '#64748b' }}>{s.plan}</span></td>
                          <td><span style={{ color: s.status === 'active' ? '#34d399' : s.status === 'trialing' ? '#fbbf24' : '#94a3b8' }}>{s.status}</span></td>
                          <td>{s.has_stripe ? '✓' : '—'}</td>
                          <td style={{ color: '#64748b', fontSize: '0.8rem' }}>{new Date(s.created_at * 1000).toLocaleDateString('en-GB')}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

          {/* Upgrade funnel */}
          <div className={styles.subContainer}>
            <div className={styles.sectionHeader}>
              <h2 className={styles.sectionTitle}>Subscription Upgrade Funnel</h2>
              <p className={styles.sectionSubtitle}>How users move through plan tiers.</p>
            </div>
            <div className={styles.funnelContainer}>
              {[
                { label: 'Free Trial',  count: 67,  pct: 100 },
                { label: 'Starter',     count: 187, pct: 85  },
                { label: 'Growth',      count: 124, pct: 56  },
                { label: 'Pro',         count: 78,  pct: 35  },
                { label: 'Business',    count: 23,  pct: 10  },
              ].map((step) => (
                <div key={step.label} className={styles.funnelStep}>
                  <div className={styles.funnelBar} style={{ width: `${step.pct}%` }}>
                    <span className={styles.funnelLabel}>{step.label}</span>
                    <span className={styles.funnelCount}>{step.count}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* MRR trend */}
          <div className={styles.subContainer}>
            <div className={styles.sectionHeader}>
              <h2 className={styles.sectionTitle}>MRR History</h2>
              <p className={styles.sectionSubtitle}>12-month growth trajectory.</p>
            </div>
            <div className={styles.mrrBarChart}>
              {MOCK_MRR_HISTORY.map((item) => {
                const pct = (item.mrr / MRR_MAX) * 100;
                return (
                  <div key={item.month} className={styles.mrrBarCol}>
                    <span className={styles.mrrBarVal}>£{(item.mrr / 1000).toFixed(1)}k</span>
                    <div className={styles.mrrBarTrack}>
                      <div className={styles.mrrBarFill} style={{ height: `${pct}%` }} />
                    </div>
                    <span className={styles.mrrBarMonth}>{item.month}</span>
                  </div>
                );
              })}
            </div>
          </div>
        </>
        );
      })()}

      {/* ══════════════════════════════════════════════════════════════════
          USERS TAB
      ══════════════════════════════════════════════════════════════════ */}
      {activeTab === 'users' && (
        <>
          {/* Filters */}
          <div className={styles.subContainer}>
            <div className={styles.sectionHeader}>
              <h2 className={styles.sectionTitle}>User Management</h2>
              <p className={styles.sectionSubtitle}>Search, filter, and manage all {MOCK_USERS.length} registered users. (Demo data — connect Auth API for live records.)</p>
            </div>
            <div className={styles.adminFiltersGrid}>
              <label className={styles.filterField}>
                <span>Search email</span>
                <input
                  className={styles.input}
                  onChange={(e) => setUserSearch(e.target.value)}
                  placeholder="user@example.com"
                  type="text"
                  value={userSearch}
                />
              </label>
              <label className={styles.filterField}>
                <span>Filter by plan</span>
                <select
                  className={styles.categorySelect}
                  onChange={(e) => setUserPlanFilter(e.target.value)}
                  value={userPlanFilter}
                >
                  <option value="all">All plans</option>
                  <option value="starter">Starter</option>
                  <option value="growth">Growth</option>
                  <option value="pro">Pro</option>
                  <option value="business">Business</option>
                </select>
              </label>
            </div>

            <p className={styles.tableCaption}>Showing {filteredUsers.length} of {MOCK_USERS.length} users</p>
            <div className={styles.tableResponsive}>
              <table className={styles.table}>
                <thead>
                  <tr>
                    <th>Email</th>
                    <th>Plan</th>
                    <th>Status</th>
                    <th>Joined</th>
                    <th>Next Bill</th>
                    <th>Revenue (£)</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredUsers.length === 0 && (
                    <tr>
                      <td colSpan={7}><p className={styles.emptyState}>No users match the current filter.</p></td>
                    </tr>
                  )}
                  {filteredUsers.map((u) => (
                    <tr key={u.id}>
                      <td>{u.email}</td>
                      <td><span className={styles.planBadge}>{u.plan}</span></td>
                      <td>
                        <span style={{
                          color: u.status === 'active' ? '#34d399' : u.status === 'trialing' ? '#f59e0b' : '#f87171',
                          fontWeight: 600, textTransform: 'capitalize',
                        }}>{u.status}</span>
                      </td>
                      <td>{u.joined}</td>
                      <td>{u.nextBill}</td>
                      <td className={u.revenue > 0 ? styles.positive : ''}>{u.revenue > 0 ? `£${u.revenue}` : '—'}</td>
                      <td>
                        <button
                          className={styles.tableActionButton}
                          onClick={() => pushToast('info', `User ${u.email} details — connect live API to action.`)}
                          type="button"
                        >
                          Manage
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Deactivate user */}
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
        </>
      )}

      {/* ══════════════════════════════════════════════════════════════════
          PARTNER BILLING TAB
      ══════════════════════════════════════════════════════════════════ */}
      {activeTab === 'billing' && (
        <>
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
    </>
  )}

      {/* ══ LEAD OPS TAB ═══════════════════════════════════════════════════ */}
      {activeTab === 'leadops' && (
        <>
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
    </>
  )}

      {/* ══════════════════════════════════════════════════════════════════
          INVOICES TAB
      ══════════════════════════════════════════════════════════════════ */}
      {activeTab === 'invoices' && (
        <>
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
                <th>Invoice #</th>
                <th>Due date</th>
                <th>Status</th>
                <th>Total</th>
                <th>Exports</th>
                <th>Update</th>
              </tr>
            </thead>
            <tbody>
              {invoiceRows.length === 0 && (
                <tr>
                  <td colSpan={7}>
                    <p className={styles.emptyState}>No invoices generated yet.</p>
                  </td>
                </tr>
              )}
              {invoiceRows.map((invoice) => (
                <tr key={invoice.id}>
                  <td>{new Date(invoice.created_at).toLocaleString()}</td>
                  <td>{invoice.invoice_number}</td>
                  <td>{new Date(invoice.due_date).toLocaleDateString()}</td>
                  <td>{invoice.status}</td>
                  <td className={styles.positive}>{currency(invoice.total_amount_gbp, invoice.currency)}</td>
                  <td>
                    <div className={styles.invoiceExportGroup}>
                      <button
                        className={styles.tableActionButton}
                        disabled={invoiceExportLoadingKey === `${invoice.id}:pdf`}
                        onClick={() => downloadInvoiceArtifact(invoice, 'pdf')}
                        type="button"
                      >
                        {invoiceExportLoadingKey === `${invoice.id}:pdf` ? '...' : 'PDF'}
                      </button>
                      <button
                        className={styles.tableActionButton}
                        disabled={invoiceExportLoadingKey === `${invoice.id}:xero`}
                        onClick={() => downloadInvoiceArtifact(invoice, 'xero')}
                        type="button"
                      >
                        {invoiceExportLoadingKey === `${invoice.id}:xero` ? '...' : 'Xero'}
                      </button>
                      <button
                        className={styles.tableActionButton}
                        disabled={invoiceExportLoadingKey === `${invoice.id}:quickbooks`}
                        onClick={() => downloadInvoiceArtifact(invoice, 'quickbooks')}
                        type="button"
                      >
                        {invoiceExportLoadingKey === `${invoice.id}:quickbooks` ? '...' : 'QuickBooks'}
                      </button>
                    </div>
                  </td>
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
    </>
  )}

      {/* ══ AI AGENT TAB ════════════════════════════════════════════════════ */}
      {activeTab === 'ai-agent' && (
        <>
          <div className={styles.subContainer}>
            <div className={styles.sectionHeader}>
              <h2 className={styles.sectionTitle}>🤖 AI Agent Control Panel</h2>
              <p className={styles.sectionSubtitle}>
                Delegate repetitive admin tasks to your AI agent. Enable permissions one by one as you gain confidence.
                The agent will log every action it takes — you stay in full control.
              </p>
            </div>
            <div className={styles.agentStatusRow}>
              <div className={styles.agentStatusLabel}>
                <span style={{ fontSize: '1.5rem' }}>{agentEnabled ? '🟢' : '🔴'}</span>
                <div>
                  <strong style={{ color: '#f1f5f9', fontSize: '1.1rem' }}>
                    AI Agent {agentEnabled ? 'ENABLED' : 'DISABLED'}
                  </strong>
                  <p style={{ color: '#94a3b8', fontSize: '0.85rem', margin: 0 }}>
                    {agentEnabled
                      ? 'Agent is active and monitoring. It will act only within permitted scopes.'
                      : 'Agent is paused. No automated actions will be taken.'}
                  </p>
                </div>
              </div>
              <button
                className={agentEnabled ? styles.button : `${styles.button} ${styles.secondaryButton}`}
                onClick={() => setAgentEnabled((v) => !v)}
                style={{ background: agentEnabled ? '#14b8a6' : undefined }}
                type="button"
              >
                {agentEnabled ? 'Disable Agent' : 'Enable Agent'}
              </button>
            </div>
          </div>

          <div className={styles.subContainer}>
            <div className={styles.sectionHeader}>
              <h2 className={styles.sectionTitle}>Permission Matrix</h2>
              <p className={styles.sectionSubtitle}>Grant or revoke capabilities. Actions marked 🚧 are planned — not yet live.</p>
            </div>
            <div className={styles.permMatrix}>
              {AI_AGENT_PERMISSIONS.map((perm) => (
                <div key={perm.id} className={styles.permRow}>
                  <label className={styles.permToggle}>
                    <input
                      type="checkbox"
                      checked={perm.available ? agentPerms[perm.id] : false}
                      disabled={!perm.available}
                      onChange={(e) =>
                        setAgentPerms((prev) => ({ ...prev, [perm.id]: e.target.checked }))
                      }
                    />
                    <span className={styles.permLabel}>
                      {perm.available ? '✅' : '🚧'} {perm.label}
                    </span>
                  </label>
                  {!perm.available && (
                    <span className={styles.permComingSoon}>Coming Soon</span>
                  )}
                </div>
              ))}
            </div>
          </div>

          <div className={styles.subContainer}>
            <div className={styles.sectionHeader}>
              <h2 className={styles.sectionTitle}>Scheduled Automations</h2>
              <p className={styles.sectionSubtitle}>Recurring tasks the agent will execute on your behalf when enabled.</p>
            </div>
            <div className={styles.tableResponsive}>
              <table className={styles.table}>
                <thead>
                  <tr><th>Task</th><th>Schedule</th><th>Last Run</th><th>Next Run</th><th>Status</th></tr>
                </thead>
                <tbody>
                  {[
                    { task: 'Generate weekly billing report',  schedule: 'Every Monday 09:00',  last: 'Mar 3, 2026',  next: 'Mar 10, 2026',  status: 'active' },
                    { task: 'Trial expiry reminder emails',    schedule: 'Daily 10:00',          last: 'Mar 5, 2026',  next: 'Mar 6, 2026',   status: 'active' },
                    { task: 'Churn risk user identification',  schedule: 'Every Sunday 08:00',   last: 'Mar 2, 2026',  next: 'Mar 9, 2026',   status: 'planned' },
                    { task: 'Auto-invoice generation',         schedule: 'Month end',            last: 'Feb 28, 2026', next: 'Mar 31, 2026',  status: 'planned' },
                    { task: 'Suspicious login detection + deactivate', schedule: 'Hourly',        last: '—',           next: '—',             status: 'planned' },
                  ].map((row) => (
                    <tr key={row.task}>
                      <td>{row.task}</td>
                      <td>{row.schedule}</td>
                      <td>{row.last}</td>
                      <td>{row.next}</td>
                      <td>
                        <span style={{
                          color: row.status === 'active' ? '#34d399' : '#f59e0b',
                          textTransform: 'capitalize', fontWeight: 600,
                        }}>{row.status}</span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          <div className={styles.subContainer}>
            <div className={styles.sectionHeader}>
              <h2 className={styles.sectionTitle}>Agent Activity Log</h2>
              <p className={styles.sectionSubtitle}>Every action the AI agent takes is recorded here for audit.</p>
            </div>
            <div className={styles.tableResponsive}>
              <table className={styles.table}>
                <thead>
                  <tr><th>Timestamp</th><th>Action</th><th>Target</th><th>Result</th></tr>
                </thead>
                <tbody>
                  {agentEnabled ? (
                    <tr><td colSpan={4}><p className={styles.emptyState}>Agent active — no actions taken yet in this session.</p></td></tr>
                  ) : (
                    <tr><td colSpan={4}><p className={styles.emptyState}>Agent is disabled. Enable agent to start recording actions.</p></td></tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}

      {/* ══ SYSTEM HEALTH TAB ═══════════════════════════════════════════════ */}
      {activeTab === 'health' && (
        <>
          <div className={styles.subContainer}>
            <div className={styles.sectionHeader}>
              <h2 className={styles.sectionTitle}>Service Health Monitor</h2>
              <p className={styles.sectionSubtitle}>
                Live health checks for all {SYSTEM_SERVICES.length} microservices. Click the button to ping all endpoints.
              </p>
            </div>
            <div className={styles.adminActionsRow}>
              <button className={styles.button} onClick={checkAllServices} type="button">
                🔍 Ping All Services
              </button>
            </div>
            <div className={styles.healthGrid}>
              {SYSTEM_SERVICES.map((svc) => {
                const s = serviceStatuses[svc.name] || 'unknown';
                return (
                  <div key={svc.name} className={styles.healthCard}>
                    <div className={styles.healthCardTop}>
                      <span className={styles.healthDot}>{s === 'online' ? '🟢' : s === 'checking' ? '🟡' : s === 'offline' ? '🔴' : '⚪'}</span>
                      <strong className={styles.healthName}>{svc.name}</strong>
                    </div>
                    <p className={styles.healthPort}>Port {svc.port}</p>
                    <p className={styles.healthStatus} style={{ color: statusColor(s) }}>
                      {s === 'online' ? 'Online' : s === 'checking' ? 'Checking...' : s === 'offline' ? 'Offline' : 'Not checked'}
                    </p>
                  </div>
                );
              })}
            </div>
          </div>

          <div className={styles.subContainer}>
            <div className={styles.sectionHeader}>
              <h2 className={styles.sectionTitle}>Uptime & SLA</h2>
              <p className={styles.sectionSubtitle}>30-day rolling uptime metrics per service tier.</p>
            </div>
            <div className={styles.tableResponsive}>
              <table className={styles.table}>
                <thead>
                  <tr><th>Service</th><th>Uptime 30d</th><th>Avg Response</th><th>Incidents</th><th>SLA Target</th></tr>
                </thead>
                <tbody>
                  {[
                    { name: 'Auth Service',    uptime: '99.94%', avgMs: '42ms',  incidents: 0, sla: '99.9%' },
                    { name: 'Analytics',       uptime: '99.81%', avgMs: '180ms', incidents: 1, sla: '99.5%' },
                    { name: 'Localization',    uptime: '100%',   avgMs: '12ms',  incidents: 0, sla: '99.9%' },
                    { name: 'User Profile',    uptime: '99.88%', avgMs: '65ms',  incidents: 1, sla: '99.9%' },
                    { name: 'Advice / AI',     uptime: '99.72%', avgMs: '320ms', incidents: 2, sla: '99.5%' },
                    { name: 'Documents',       uptime: '99.91%', avgMs: '95ms',  incidents: 0, sla: '99.5%' },
                    { name: 'Partner Registry',uptime: '99.96%', avgMs: '38ms',  incidents: 0, sla: '99.9%' },
                    { name: 'Transactions',    uptime: '99.85%', avgMs: '78ms',  incidents: 1, sla: '99.9%' },
                  ].map((row) => (
                    <tr key={row.name}>
                      <td>{row.name}</td>
                      <td className={styles.positive}>{row.uptime}</td>
                      <td>{row.avgMs}</td>
                      <td style={{ color: row.incidents > 0 ? '#f87171' : '#34d399' }}>{row.incidents}</td>
                      <td>{row.sla}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}

      {activeTab === 'support' && (
        <>
          {/* KPI strip */}
          <div className={styles.kpiGrid}>
            <div className={styles.kpiCard}>
              <p className={styles.kpiLabel}>Total Tickets</p>
              <p className={styles.kpiValue}>{MOCK_TICKETS.length}</p>
              <p className={styles.kpiSub}>All time (demo)</p>
            </div>
            <div className={styles.kpiCard}>
              <p className={styles.kpiLabel}>Open</p>
              <p className={styles.kpiValue} style={{ color: '#f87171' }}>
                {MOCK_TICKETS.filter(t => t.status === 'open').length}
              </p>
              <p className={styles.kpiSub}>Need response</p>
            </div>
            <div className={styles.kpiCard}>
              <p className={styles.kpiLabel}>Resolved Today</p>
              <p className={styles.kpiValue} style={{ color: '#34d399' }}>3</p>
              <p className={styles.kpiSub}>March 5, 2026</p>
            </div>
            <div className={styles.kpiCard}>
              <p className={styles.kpiLabel}>Avg Rating</p>
              <p className={styles.kpiValue} style={{ color: '#f59e0b' }}>
                {(MOCK_FEEDBACK.reduce((s, f) => s + f.rating, 0) / MOCK_FEEDBACK.length).toFixed(1)} ⭐
              </p>
              <p className={styles.kpiSub}>Last 30 days</p>
            </div>
          </div>

          {/* Tickets table */}
          <div className={styles.subContainer}>
            <div className={styles.subHeader}>
              <h3 className={styles.subTitle}>Support Tickets</h3>
              <a
                href="http://localhost:3001"
                target="_blank"
                rel="noopener noreferrer"
                className={styles.actionBtn}
                style={{ textDecoration: 'none' }}
              >
                Open AI Support Portal ↗
              </a>
            </div>
            <table className={styles.dataTable}>
              <thead>
                <tr>
                  <th>ID</th>
                  <th>User</th>
                  <th>Subject</th>
                  <th>Category</th>
                  <th>Priority</th>
                  <th>Status</th>
                  <th>Created</th>
                </tr>
              </thead>
              <tbody>
                {MOCK_TICKETS.map(t => (
                  <tr key={t.id}>
                    <td><code style={{ fontSize: '.8rem' }}>{t.id}</code></td>
                    <td style={{ fontSize: '.85rem' }}>{t.user}</td>
                    <td style={{ maxWidth: 220, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{t.subject}</td>
                    <td>{t.category}</td>
                    <td>
                      <span style={{
                        padding: '.2rem .55rem',
                        borderRadius: 20,
                        fontSize: '.78rem',
                        fontWeight: 600,
                        background: t.priority === 'high' ? '#7f1d1d' : t.priority === 'medium' ? '#78350f' : '#14532d',
                        color:      t.priority === 'high' ? '#f87171' : t.priority === 'medium' ? '#fbbf24' : '#34d399',
                      }}>
                        {t.priority}
                      </span>
                    </td>
                    <td>
                      <span style={{
                        padding: '.2rem .55rem',
                        borderRadius: 20,
                        fontSize: '.78rem',
                        fontWeight: 600,
                        background: t.status === 'open' ? '#1e3a5f' : '#14532d',
                        color:      t.status === 'open' ? '#93c5fd' : '#34d399',
                      }}>
                        {t.status}
                      </span>
                    </td>
                    <td style={{ fontSize: '.82rem', color: 'var(--text-muted)' }}>{t.created}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Feedback table */}
          <div className={styles.subContainer} style={{ marginTop: '1.5rem' }}>
            <div className={styles.subHeader}>
              <h3 className={styles.subTitle}>Customer Feedback</h3>
            </div>
            <table className={styles.dataTable}>
              <thead>
                <tr>
                  <th>Date</th>
                  <th>User</th>
                  <th>Rating</th>
                  <th>Comment</th>
                </tr>
              </thead>
              <tbody>
                {MOCK_FEEDBACK.map((f, i) => (
                  <tr key={i}>
                    <td style={{ fontSize: '.82rem', color: 'var(--text-muted)' }}>{f.date}</td>
                    <td style={{ fontSize: '.85rem' }}>{f.user}</td>
                    <td>
                      {'⭐'.repeat(f.rating)}
                    </td>
                    <td style={{ fontSize: '.85rem' }}>{f.comment}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}

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
