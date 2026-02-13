import { useEffect, useState, type FormEvent } from 'react';
import { useTranslation } from '../hooks/useTranslation';
import styles from '../styles/Home.module.css';

const AUTH_SERVICE_BASE_URL = process.env.NEXT_PUBLIC_AUTH_SERVICE_URL || 'http://localhost:8000';
const PARTNER_REGISTRY_URL = process.env.NEXT_PUBLIC_PARTNER_REGISTRY_URL || 'http://localhost:8009';

type AdminPageProps = {
  token: string;
};

type PartnerOption = {
  id: string;
  name: string;
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

export default function AdminPage({ token }: AdminPageProps) {
  const [emailToDeactivate, setEmailToDeactivate] = useState('');
  const [deactivateError, setDeactivateError] = useState('');
  const [deactivateMessage, setDeactivateMessage] = useState('');
  const [leadId, setLeadId] = useState('');
  const [leadStatus, setLeadStatus] = useState<'qualified' | 'rejected' | 'converted'>('qualified');
  const [leadStatusError, setLeadStatusError] = useState('');
  const [leadStatusMessage, setLeadStatusMessage] = useState('');
  const [billingError, setBillingError] = useState('');
  const [billingMessage, setBillingMessage] = useState('');
  const [isBillingLoading, setIsBillingLoading] = useState(false);
  const [report, setReport] = useState<BillingReportResponse | null>(null);
  const [partners, setPartners] = useState<PartnerOption[]>([]);
  const [selectedPartnerId, setSelectedPartnerId] = useState('');
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const [includeQualified, setIncludeQualified] = useState(true);
  const [includeConverted, setIncludeConverted] = useState(true);
  const { t } = useTranslation();

  useEffect(() => {
    const loadPartners = async () => {
      try {
        const response = await fetch(`${PARTNER_REGISTRY_URL}/partners`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (!response.ok) {
          return;
        }
        setPartners(await response.json());
      } catch (err) {
        console.error(err);
      }
    };

    loadPartners();
  }, [token]);

  const selectedStatuses = () => {
    const statuses: string[] = [];
    if (includeQualified) {
      statuses.push('qualified');
    }
    if (includeConverted) {
      statuses.push('converted');
    }
    return statuses;
  };

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
    selectedStatuses().forEach((statusValue) => params.append('statuses', statusValue));
    return params.toString();
  };

  const loadBillingReport = async () => {
    const statuses = selectedStatuses();
    if (!statuses.length) {
      setBillingError('Select at least one billable status.');
      return;
    }

    setBillingError('');
    setBillingMessage('');
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
      setBillingMessage('Billing report updated.');
    } catch (err) {
      setBillingError(err instanceof Error ? err.message : 'Unexpected error');
    } finally {
      setIsBillingLoading(false);
    }
  };

  const downloadBillingCsv = async () => {
    const statuses = selectedStatuses();
    if (!statuses.length) {
      setBillingError('Select at least one billable status.');
      return;
    }

    setBillingError('');
    setBillingMessage('');
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
      setBillingMessage('Billing CSV downloaded.');
    } catch (err) {
      setBillingError(err instanceof Error ? err.message : 'Unexpected error');
    }
  };

  const handleDeactivate = async (event: FormEvent) => {
    event.preventDefault();
    setDeactivateError('');
    setDeactivateMessage('');

    try {
      const response = await fetch(`${AUTH_SERVICE_BASE_URL}/users/${emailToDeactivate}/deactivate`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
      });
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.detail || 'Failed to deactivate user');
      }

      setDeactivateMessage(`User ${data.email} has been deactivated.`);
      setEmailToDeactivate('');
    } catch (err) {
      setDeactivateError(err instanceof Error ? err.message : 'Unexpected error');
    }
  };

  const handleLeadStatusUpdate = async (event: FormEvent) => {
    event.preventDefault();
    setLeadStatusError('');
    setLeadStatusMessage('');

    if (!leadId) {
      setLeadStatusError('Lead ID is required.');
      return;
    }

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
      setLeadStatusMessage(`Lead ${payload.lead_id} updated to status '${payload.status}'.`);
    } catch (err) {
      setLeadStatusError(err instanceof Error ? err.message : 'Unexpected error');
    }
  };

  return (
    <div className={styles.dashboard}>
      <h1>{t('nav.admin')}</h1>
      <p>{t('admin.description')}</p>
      <div className={styles.subContainer}>
        <h2>{t('admin.form_title')}</h2>
        <form onSubmit={handleDeactivate}>
          <input
            className={styles.input}
            onChange={(event) => setEmailToDeactivate(event.target.value)}
            placeholder="user.email@example.com"
            type="email"
            value={emailToDeactivate}
          />
          <button className={styles.button} type="submit">
            {t('admin.deactivate_button')}
          </button>
        </form>
        {deactivateMessage && <p className={styles.message}>{deactivateMessage}</p>}
        {deactivateError && <p className={styles.error}>{deactivateError}</p>}
      </div>

      <div className={styles.subContainer}>
        <h2>Lead Lifecycle Management</h2>
        <p>Set lead status for billing reconciliation.</p>
        <form onSubmit={handleLeadStatusUpdate}>
          <input
            className={styles.input}
            onChange={(event) => setLeadId(event.target.value)}
            placeholder="Lead UUID"
            type="text"
            value={leadId}
          />
          <select className={styles.categorySelect} onChange={(event) => setLeadStatus(event.target.value as 'qualified' | 'rejected' | 'converted')} value={leadStatus}>
            <option value="qualified">qualified</option>
            <option value="rejected">rejected</option>
            <option value="converted">converted</option>
          </select>
          <div style={{ marginTop: '0.75rem' }}>
            <button className={styles.button} type="submit">
              Update Lead Status
            </button>
          </div>
        </form>
        {leadStatusMessage && <p className={styles.message}>{leadStatusMessage}</p>}
        {leadStatusError && <p className={styles.error}>{leadStatusError}</p>}
      </div>

      <div className={styles.subContainer}>
        <h2>Billing Report</h2>
        <p>Review billable volume and monetary totals by partner.</p>
        <div className={styles.fileInputContainer}>
          <input className={styles.input} onChange={(event) => setStartDate(event.target.value)} type="date" value={startDate} />
          <input className={styles.input} onChange={(event) => setEndDate(event.target.value)} type="date" value={endDate} />
        </div>
        <div className={styles.fileInputContainer}>
          <select className={styles.categorySelect} onChange={(event) => setSelectedPartnerId(event.target.value)} value={selectedPartnerId}>
            <option value="">All partners</option>
            {partners.map((partner) => (
              <option key={partner.id} value={partner.id}>
                {partner.name}
              </option>
            ))}
          </select>
          <label>
            <input checked={includeQualified} onChange={(event) => setIncludeQualified(event.target.checked)} type="checkbox" /> qualified
          </label>
          <label>
            <input checked={includeConverted} onChange={(event) => setIncludeConverted(event.target.checked)} type="checkbox" /> converted
          </label>
          <button className={styles.button} disabled={isBillingLoading} onClick={loadBillingReport} type="button">
            {isBillingLoading ? 'Loading...' : 'Load Billing'}
          </button>
          <button className={`${styles.button} ${styles.secondaryButton}`} onClick={downloadBillingCsv} type="button">
            Download CSV
          </button>
        </div>

        {billingMessage && <p className={styles.message}>{billingMessage}</p>}
        {billingError && <p className={styles.error}>{billingError}</p>}

        {report && (
          <>
            <div className={styles.resultsContainer}>
              <div className={styles.resultItem}><span>Currency:</span><span>{report.currency}</span></div>
              <div className={styles.resultItem}><span>Total leads:</span><span>{report.total_leads}</span></div>
              <div className={styles.resultItem}><span>Qualified leads:</span><span>{report.qualified_leads}</span></div>
              <div className={styles.resultItem}><span>Converted leads:</span><span>{report.converted_leads}</span></div>
              <div className={styles.resultItemMain}><span>Total amount:</span><span>{report.total_amount_gbp.toFixed(2)} {report.currency}</span></div>
            </div>

            <table className={styles.table}>
              <thead>
                <tr>
                  <th>Partner</th>
                  <th>Qualified</th>
                  <th>Converted</th>
                  <th>Rates (GBP)</th>
                  <th>Amount (GBP)</th>
                </tr>
              </thead>
              <tbody>
                {report.by_partner.map((item) => (
                  <tr key={item.partner_id}>
                    <td>{item.partner_name}</td>
                    <td>{item.qualified_leads}</td>
                    <td>{item.converted_leads}</td>
                    <td>{item.qualified_lead_fee_gbp.toFixed(2)} / {item.converted_lead_fee_gbp.toFixed(2)}</td>
                    <td className={styles.positive}>{item.amount_gbp.toFixed(2)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </>
        )}
      </div>
    </div>
  );
}
