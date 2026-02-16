import { useCallback, useEffect, useState, type FormEvent } from 'react';
import { useRouter } from 'next/router';
import { useTranslation } from '../hooks/useTranslation';
import styles from '../styles/Home.module.css';

const ANALYTICS_SERVICE_URL = process.env.NEXT_PUBLIC_ANALYTICS_SERVICE_URL || 'http://localhost:8011';
const AGENT_SERVICE_URL = process.env.NEXT_PUBLIC_AGENT_SERVICE_URL || 'http://localhost:8000/api/agent';
const PARTNER_REGISTRY_URL = process.env.NEXT_PUBLIC_PARTNER_REGISTRY_URL || 'http://localhost:8009';
const COPILOT_SESSION_STORAGE_KEY = 'copilotSessionId';
const COPILOT_MESSAGE_STORAGE_KEY = 'copilotLastMessage';

type DashboardPageProps = {
  token: string;
};

type AdviceResponse = {
  details: string;
  headline: string;
};

type ForecastPoint = {
  balance: number;
  date: string;
};

type TaxEstimateResult = {
  end_date: string;
  estimated_class4_nic_due: number;
  estimated_income_tax_due: number;
  estimated_effective_tax_rate: number;
  estimated_tax_due: number;
  mtd_obligation?: {
    final_declaration_required: boolean;
    next_deadline?: string | null;
    notes: string[];
    policy_code: string;
    qualifying_income_estimate: number;
    quarterly_updates: Array<{
      due_date: string;
      quarter: string;
      status: 'due_now' | 'overdue' | 'upcoming';
    }>;
    reporting_cadence: 'annual_only' | 'quarterly_updates_plus_final_declaration';
    reporting_required: boolean;
    tax_year_end: string;
    tax_year_start: string;
    threshold?: number | null;
  };
  personal_allowance_used: number;
  start_date: string;
  taxable_amount_after_allowance: number;
  taxable_profit: number;
  total_expenses: number;
  total_income: number;
};

type SeedReadinessResponse = {
  active_invoice_count: number;
  conversion_rate_percent: number;
  current_month_mrr_gbp: number;
  generated_at: string;
  leads_last_90d: number;
  mrr_growth_percent: number;
  monthly_mrr_series: Array<{ month: string; mrr_gbp: number }>;
  paid_invoice_rate_percent: number;
  period_months: number;
  pmf_band?: 'early' | 'emerging' | 'pmf_confirmed';
  qualification_rate_percent: number;
  qualified_last_90d: number;
  readiness_band: 'early' | 'progressing' | 'investable';
  readiness_score_percent: number;
  retained_users_30d?: number;
  retained_users_90d?: number;
  rolling_3_month_avg_mrr_gbp: number;
};

type PMFMonthlyCohortPoint = {
  activation_rate_percent: number;
  cohort_month: string;
  new_users: number;
  retention_rate_30d_percent: number;
  retention_rate_60d_percent: number;
  retention_rate_90d_percent: number;
};

type PMFEvidenceResponse = {
  activated_users: number;
  activation_rate_percent: number;
  activation_window_days: number;
  as_of_date: string;
  cohort_months: number;
  eligible_users_30d: number;
  eligible_users_60d: number;
  eligible_users_90d: number;
  generated_at: string;
  monthly_cohorts: PMFMonthlyCohortPoint[];
  note?: string;
  notes: string[];
  pmf_band: 'early' | 'emerging' | 'pmf_confirmed';
  retained_users_30d: number;
  retained_users_60d: number;
  retained_users_90d: number;
  retention_rate_30d_percent: number;
  retention_rate_60d_percent: number;
  retention_rate_90d_percent: number;
  total_new_users: number;
};

type PMFGateStatusResponse = {
  activation_passed: boolean;
  activation_rate_percent: number;
  gate_name: 'seed_pmf_gate_v1';
  gate_passed: boolean;
  generated_at: string;
  nps_passed: boolean;
  next_actions: string[];
  overall_nps_score: number;
  required_activation_rate_percent: number;
  required_overall_nps_score: number;
  required_retention_rate_90d_percent: number;
  retention_passed: boolean;
  retention_rate_90d_percent: number;
  sample_size_passed: boolean;
  summary: string;
};

type UnitEconomicsResponse = {
  as_of_date: string;
  average_cac_gbp?: number | null;
  churn_gate_passed: boolean;
  current_month_mrr_gbp: number;
  estimated_ltv_gbp?: number | null;
  generated_at: string;
  ltv_cac_gate_passed: boolean;
  ltv_cac_ratio?: number | null;
  monthly_churn_rate_percent: number;
  monthly_expansion_rate_percent: number;
  mrr_gate_passed: boolean;
  mrr_stability_band: 'stable' | 'variable' | 'volatile';
  mrr_stability_percent: number;
  next_actions: string[];
  period_months: number;
  required_max_monthly_churn_percent: number;
  required_min_ltv_cac_ratio: number;
  required_mrr_gbp: number;
  rolling_3_month_avg_mrr_gbp: number;
  seed_gate_passed: boolean;
};

type SelfEmployedInvoiceStatus = 'draft' | 'issued' | 'paid' | 'overdue' | 'void';

type SelfEmployedInvoiceLine = {
  description: string;
  id: string;
  line_total_gbp: number;
  quantity: number;
  unit_price_gbp: number;
};

type SelfEmployedInvoiceSummary = {
  created_at: string;
  currency: string;
  customer_name: string;
  due_date: string;
  id: string;
  invoice_number: string;
  issue_date: string;
  payment_link_url?: string | null;
  status: SelfEmployedInvoiceStatus;
  total_amount_gbp: number;
};

type SelfEmployedInvoiceListResponse = {
  items: SelfEmployedInvoiceSummary[];
  total: number;
};

type SelfEmployedBrandProfileResponse = {
  accent_color?: string | null;
  business_name: string;
  logo_url?: string | null;
  message: string;
  payment_terms_note?: string | null;
  updated_at: string;
};

type SelfEmployedRecurringCadence = 'weekly' | 'monthly' | 'quarterly';

type SelfEmployedRecurringPlanSummary = {
  active: boolean;
  cadence: SelfEmployedRecurringCadence;
  created_at: string;
  customer_name: string;
  id: string;
  last_generated_invoice_id?: string | null;
  next_issue_date: string;
  updated_at: string;
};

type SelfEmployedRecurringPlanListResponse = {
  items: SelfEmployedRecurringPlanSummary[];
  total: number;
};

type SelfEmployedReminderChannelReadiness = {
  can_dispatch: boolean;
  channel: 'email' | 'sms';
  checks: string[];
  configured: boolean;
  enabled: boolean;
  provider: string;
  warnings: string[];
};

type SelfEmployedReminderDeliveryReadinessResponse = {
  email: SelfEmployedReminderChannelReadiness;
  generated_at: string;
  note: string;
  overall_ready: boolean;
  sms: SelfEmployedReminderChannelReadiness;
};

type SelfEmployedReminderSmokeCheckChannelResult = {
  channel: 'email' | 'sms';
  configured: boolean;
  delivery_status: 'sent' | 'failed' | 'skipped';
  detail: string;
  enabled: boolean;
  network_check_performed: boolean;
  provider: string;
};

type SelfEmployedReminderSmokeCheckResponse = {
  generated_at: string;
  passed: boolean;
  perform_network_check: boolean;
  requested_channel: 'email' | 'sms' | 'both';
  results: SelfEmployedReminderSmokeCheckChannelResult[];
};

type NPSMonthlyTrendPoint = {
  detractors_count: number;
  month: string;
  nps_score: number;
  passives_count: number;
  promoters_count: number;
  responses_count: number;
};

type NPSTrendResponse = {
  detractors_count: number;
  generated_at: string;
  monthly_trend: NPSMonthlyTrendPoint[];
  note: string;
  overall_nps_score: number;
  passives_count: number;
  period_months: number;
  promoters_count: number;
  total_responses: number;
};

type CopilotEvidence = {
  record_ids: string[];
  source_endpoint: string;
  source_service: string;
  summary: string;
};

type CopilotSuggestedAction = {
  action_id: string;
  action_payload?: Record<string, unknown> | null;
  description: string;
  label: string;
  requires_confirmation: boolean;
};

type CopilotChatResponse = {
  answer: string;
  confidence: number;
  confidence_band: 'low' | 'medium' | 'high';
  evidence: CopilotEvidence[];
  intent: string;
  intent_reason: string;
  session_id: string;
  suggested_actions: CopilotSuggestedAction[];
};

type CopilotExecutionResponse = {
  confirmation_reason?: string | null;
  downstream_status_code?: number | null;
  executed: boolean;
  message: string;
  valid_confirmation: boolean;
};

type CopilotAuditEvent = {
  action_id?: string | null;
  event_type: string;
  timestamp: string;
};

function TaxCalculator({ token }: { token: string }) {
  const [result, setResult] = useState<TaxEstimateResult | null>(null);
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [startDate, setStartDate] = useState('2023-01-01');
  const [endDate, setEndDate] = useState('2023-12-31');

  const handleCalculate = async (event: FormEvent) => {
    event.preventDefault();
    setError('');
    setResult(null);
    setIsLoading(true);
    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_TAX_ENGINE_URL || 'http://localhost:8007'}/calculate`, {
        body: JSON.stringify({ end_date: endDate, jurisdiction: 'UK', start_date: startDate }),
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        method: 'POST',
      });
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.detail || 'Failed to calculate tax');
      }
      setResult(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unexpected error');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className={styles.subContainer}>
      <h2>Tax Estimator (UK)</h2>
      <form onSubmit={handleCalculate}>
        <div className={styles.dateInputs}>
          <input className={styles.input} onChange={(event) => setStartDate(event.target.value)} type="date" value={startDate} />
          <input className={styles.input} onChange={(event) => setEndDate(event.target.value)} type="date" value={endDate} />
        </div>
        <button className={styles.button} disabled={isLoading} type="submit">
          {isLoading ? 'Calculating...' : 'Calculate Tax'}
        </button>
      </form>
      {error && <p className={styles.error}>{error}</p>}
      {result && (
        <div className={styles.resultsContainer}>
          <h3>
            Estimated Tax for {result.start_date} to {result.end_date}
          </h3>
          <div className={styles.resultItem}>
            <span>Total Income:</span> <span className={styles.positive}>£{result.total_income.toFixed(2)}</span>
          </div>
          <div className={styles.resultItem}>
            <span>Deductible Expenses:</span> <span className={styles.negative}>£{result.total_expenses.toFixed(2)}</span>
          </div>
          <div className={styles.resultItemMain}>
            <span>Estimated Tax Due:</span> <span>£{result.estimated_tax_due.toFixed(2)}</span>
          </div>
          <div className={styles.resultItem}>
            <span>Income Tax (estimate):</span> <span>£{result.estimated_income_tax_due.toFixed(2)}</span>
          </div>
          <div className={styles.resultItem}>
            <span>Class 4 NIC (estimate):</span> <span>£{result.estimated_class4_nic_due.toFixed(2)}</span>
          </div>
          {result.mtd_obligation && (
            <div className={styles.copilotWhyBlock} style={{ marginTop: '10px' }}>
              <p>
                <strong>MTD ITSA policy:</strong> {result.mtd_obligation.policy_code} (
                {result.mtd_obligation.tax_year_start} to {result.mtd_obligation.tax_year_end})
              </p>
              <p>
                <strong>Quarterly updates required:</strong>{' '}
                {result.mtd_obligation.reporting_required ? 'Yes' : 'No'}{' '}
                {typeof result.mtd_obligation.threshold === 'number'
                  ? `(threshold £${result.mtd_obligation.threshold.toFixed(0)}, estimated income £${result.mtd_obligation.qualifying_income_estimate.toFixed(2)})`
                  : ''}
              </p>
              {result.mtd_obligation.reporting_required && result.mtd_obligation.next_deadline && (
                <p>
                  <strong>Next quarterly deadline:</strong> {result.mtd_obligation.next_deadline}
                </p>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function CashFlowPreview({ token }: { token: string }) {
  const [data, setData] = useState<ForecastPoint[]>([]);
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const fetchForecast = async () => {
      setIsLoading(true);
      try {
        const response = await fetch(`${ANALYTICS_SERVICE_URL}/forecast/cash-flow`, {
          body: JSON.stringify({ days_to_forecast: 14 }),
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${token}`,
          },
          method: 'POST',
        });
        if (!response.ok) {
          throw new Error('Failed to fetch cash flow forecast');
        }
        const result = await response.json();
        setData(result.forecast || []);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Unexpected error');
      } finally {
        setIsLoading(false);
      }
    };
    fetchForecast();
  }, [token]);

  const maxAbsBalance = data.reduce((max, point) => Math.max(max, Math.abs(point.balance)), 0) || 1;

  return (
    <div className={styles.subContainer}>
      <h2>Cash Flow Forecast (Next 14 Days)</h2>
      {error && <p className={styles.error}>{error}</p>}
      {isLoading && (
        <div className={styles.skeletonTable}>
          {Array.from({ length: 4 }).map((_, index) => (
            <div className={styles.skeletonRow} key={index}>
              <div className={styles.skeletonCell} />
              <div className={styles.skeletonCell} />
              <div className={styles.skeletonCell} />
            </div>
          ))}
        </div>
      )}
      {!error && !isLoading && data.length === 0 && <p className={styles.emptyState}>No forecast data available yet.</p>}
      {data.length > 0 && (
        <>
          <table className={styles.table}>
            <thead>
              <tr>
                <th>Date</th>
                <th>Projected Balance</th>
                <th>Trend</th>
              </tr>
            </thead>
            <tbody>
              {data.map((point) => {
                const normalizedWidth = Math.max(8, Math.round((Math.abs(point.balance) / maxAbsBalance) * 100));
                return (
                  <tr key={point.date}>
                    <td>{point.date}</td>
                    <td className={point.balance >= 0 ? styles.positive : styles.negative}>£{point.balance.toFixed(2)}</td>
                    <td className={styles.tableTrendCell}>
                      <div className={styles.trendTrack}>
                        <span
                          className={`${styles.trendFill} ${point.balance >= 0 ? styles.trendPositive : styles.trendNegative}`}
                          style={{ width: `${normalizedWidth}%` }}
                        />
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
          <p className={styles.tableCaption}>Spark bars show relative daily balance movement within the current forecast window.</p>
        </>
      )}
    </div>
  );
}

function ActionCenter({ token }: { token: string }) {
  const [advice, setAdvice] = useState<AdviceResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const router = useRouter();

  useEffect(() => {
    const fetchAdvice = async () => {
      setIsLoading(true);
      try {
        const response = await fetch(`${process.env.NEXT_PUBLIC_ADVICE_SERVICE_URL || 'http://localhost:8008'}/generate`, {
          body: JSON.stringify({ topic: 'income_protection' }),
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${token}`,
          },
          method: 'POST',
        });
        if (!response.ok) {
          return;
        }
        setAdvice(await response.json());
      } catch (err) {
        console.error(err);
      } finally {
        setIsLoading(false);
      }
    };
    fetchAdvice();
  }, [token]);

  if (isLoading) {
    return (
      <div className={`${styles.subContainer} ${styles.actionableAdviceCard}`}>
        <div>
          <div className={`${styles.skeletonLine} ${styles.skeletonLineShort}`} />
          <div className={`${styles.skeletonLine} ${styles.skeletonLineLong}`} />
          <div className={`${styles.skeletonLine} ${styles.skeletonLineMedium}`} />
        </div>
        <div>
          <div className={`${styles.skeletonLine} ${styles.skeletonLineMedium}`} />
          <div className={`${styles.skeletonLine} ${styles.skeletonLineLong}`} />
        </div>
      </div>
    );
  }

  if (!advice) {
    return null;
  }

  return (
    <div className={`${styles.subContainer} ${styles.actionableAdviceCard}`}>
      <div className={styles.adviceTextContent}>
        <h3>{advice.headline}</h3>
        <p>{advice.details}</p>
      </div>
      <div className={styles.advicePartnerList}>
        <h4>What&apos;s Next?</h4>
        <p>Explore our marketplace of trusted partners for insurance, accounting, and more.</p>
        <button className={styles.button} onClick={() => router.push('/marketplace')} type="button">
          Explore Partner Services
        </button>
      </div>
    </div>
  );
}

function SelfEmployedInvoicingPanel({ token }: { token: string }) {
  const [invoices, setInvoices] = useState<SelfEmployedInvoiceSummary[]>([]);
  const [recurringPlans, setRecurringPlans] = useState<SelfEmployedRecurringPlanSummary[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');
  const [customerName, setCustomerName] = useState('');
  const [customerEmail, setCustomerEmail] = useState('');
  const [customerPhone, setCustomerPhone] = useState('');
  const [lineDescription, setLineDescription] = useState('Professional services');
  const [quantity, setQuantity] = useState(1);
  const [unitPrice, setUnitPrice] = useState(100);
  const [taxRate, setTaxRate] = useState(0);
  const [recurringCadence, setRecurringCadence] = useState<SelfEmployedRecurringCadence>('monthly');
  const [brandBusinessName, setBrandBusinessName] = useState('');
  const [brandLogoUrl, setBrandLogoUrl] = useState('');
  const [brandAccentColor, setBrandAccentColor] = useState('#2244AA');
  const [brandPaymentTerms, setBrandPaymentTerms] = useState('Payment due within 14 days.');
  const [createState, setCreateState] = useState<{ error?: string; isLoading: boolean; message?: string }>({
    isLoading: false,
  });
  const [updatingInvoiceId, setUpdatingInvoiceId] = useState<string | null>(null);
  const [automationState, setAutomationState] = useState<{ error?: string; isLoading: boolean; message?: string }>({
    isLoading: false,
  });
  const [readiness, setReadiness] = useState<SelfEmployedReminderDeliveryReadinessResponse | null>(null);
  const [readinessState, setReadinessState] = useState<{ error?: string; isLoading: boolean }>({
    isLoading: false,
  });
  const [smokeChannel, setSmokeChannel] = useState<'email' | 'sms' | 'both'>('both');
  const [smokeEmail, setSmokeEmail] = useState('');
  const [smokePhone, setSmokePhone] = useState('');
  const [performSmokeNetworkCheck, setPerformSmokeNetworkCheck] = useState(false);
  const [smokeState, setSmokeState] = useState<{
    error?: string;
    isLoading: boolean;
    message?: string;
    result?: SelfEmployedReminderSmokeCheckResponse;
  }>({
    isLoading: false,
  });

  const loadInvoices = useCallback(async () => {
    setIsLoading(true);
    setError('');
    try {
      const [invoicesResponse, recurringResponse, brandResponse] = await Promise.all([
        fetch(`${PARTNER_REGISTRY_URL}/self-employed/invoices?limit=20&offset=0`, {
          headers: { Authorization: `Bearer ${token}` },
        }),
        fetch(`${PARTNER_REGISTRY_URL}/self-employed/invoicing/recurring-plans?limit=20&offset=0`, {
          headers: { Authorization: `Bearer ${token}` },
        }),
        fetch(`${PARTNER_REGISTRY_URL}/self-employed/invoicing/brand`, {
          headers: { Authorization: `Bearer ${token}` },
        }),
      ]);

      const invoicesPayload = (await invoicesResponse.json()) as SelfEmployedInvoiceListResponse | { detail?: string };
      if (!invoicesResponse.ok) {
        throw new Error((invoicesPayload as { detail?: string }).detail || 'Failed to load invoices');
      }
      setInvoices((invoicesPayload as SelfEmployedInvoiceListResponse).items || []);

      const recurringPayload = (await recurringResponse.json()) as SelfEmployedRecurringPlanListResponse | { detail?: string };
      if (!recurringResponse.ok) {
        throw new Error((recurringPayload as { detail?: string }).detail || 'Failed to load recurring plans');
      }
      setRecurringPlans((recurringPayload as SelfEmployedRecurringPlanListResponse).items || []);

      if (brandResponse.ok) {
        const brandPayload = (await brandResponse.json()) as SelfEmployedBrandProfileResponse;
        setBrandBusinessName(brandPayload.business_name || '');
        setBrandLogoUrl(brandPayload.logo_url || '');
        setBrandAccentColor(brandPayload.accent_color || '#2244AA');
        setBrandPaymentTerms(brandPayload.payment_terms_note || 'Payment due within 14 days.');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load invoices');
    } finally {
      setIsLoading(false);
    }
  }, [token]);

  useEffect(() => {
    void loadInvoices();
  }, [loadInvoices]);

  const createInvoice = async (event: FormEvent) => {
    event.preventDefault();
    setCreateState({ isLoading: true });
    try {
      const response = await fetch(`${PARTNER_REGISTRY_URL}/self-employed/invoices`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          customer_name: customerName.trim(),
          customer_email: customerEmail.trim() || undefined,
          customer_phone: customerPhone.trim() || undefined,
          tax_rate_percent: taxRate,
          brand_business_name: brandBusinessName.trim() || undefined,
          brand_logo_url: brandLogoUrl.trim() || undefined,
          brand_accent_color: brandAccentColor.trim() || undefined,
          lines: [
            {
              description: lineDescription.trim(),
              quantity,
              unit_price_gbp: unitPrice,
            },
          ],
        }),
      });
      const payload = (await response.json()) as { detail?: string };
      if (!response.ok) {
        throw new Error(payload.detail || 'Failed to create invoice');
      }
      setCreateState({ isLoading: false, message: 'Invoice created successfully.' });
      setCustomerName('');
      setCustomerEmail('');
      setCustomerPhone('');
      setLineDescription('Professional services');
      setQuantity(1);
      setUnitPrice(100);
      setTaxRate(0);
      void loadInvoices();
    } catch (err) {
      setCreateState({
        isLoading: false,
        error: err instanceof Error ? err.message : 'Invoice creation failed',
      });
    }
  };

  const saveBrandProfile = async () => {
    setAutomationState({ isLoading: true });
    try {
      const response = await fetch(`${PARTNER_REGISTRY_URL}/self-employed/invoicing/brand`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          business_name: brandBusinessName.trim(),
          logo_url: brandLogoUrl.trim() || undefined,
          accent_color: brandAccentColor.trim() || undefined,
          payment_terms_note: brandPaymentTerms.trim() || undefined,
        }),
      });
      const payload = (await response.json()) as { detail?: string; message?: string };
      if (!response.ok) {
        throw new Error(payload.detail || 'Failed to save brand profile');
      }
      setAutomationState({
        isLoading: false,
        message: payload.message || 'Brand profile saved.',
      });
    } catch (err) {
      setAutomationState({
        isLoading: false,
        error: err instanceof Error ? err.message : 'Failed to save brand profile',
      });
    }
  };

  const createRecurringPlan = async () => {
    setAutomationState({ isLoading: true });
    try {
      const response = await fetch(`${PARTNER_REGISTRY_URL}/self-employed/invoicing/recurring-plans`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          customer_name: customerName.trim(),
          customer_email: customerEmail.trim() || undefined,
          customer_phone: customerPhone.trim() || undefined,
          tax_rate_percent: taxRate,
          cadence: recurringCadence,
          lines: [
            {
              description: lineDescription.trim(),
              quantity,
              unit_price_gbp: unitPrice,
            },
          ],
        }),
      });
      const payload = (await response.json()) as { detail?: string };
      if (!response.ok) {
        throw new Error(payload.detail || 'Failed to create recurring plan');
      }
      setAutomationState({ isLoading: false, message: 'Recurring plan created.' });
      void loadInvoices();
    } catch (err) {
      setAutomationState({
        isLoading: false,
        error: err instanceof Error ? err.message : 'Failed to create recurring plan',
      });
    }
  };

  const runDueRecurringPlans = async () => {
    setAutomationState({ isLoading: true });
    try {
      const response = await fetch(`${PARTNER_REGISTRY_URL}/self-employed/invoicing/recurring-plans/run-due`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
      });
      const payload = (await response.json()) as { detail?: string; generated_count?: number };
      if (!response.ok) {
        throw new Error(payload.detail || 'Failed to run recurring plans');
      }
      setAutomationState({
        isLoading: false,
        message: `Recurring automation done. Generated: ${payload.generated_count ?? 0}`,
      });
      void loadInvoices();
    } catch (err) {
      setAutomationState({
        isLoading: false,
        error: err instanceof Error ? err.message : 'Failed to run recurring plans',
      });
    }
  };

  const runReminderNotifications = async () => {
    setAutomationState({ isLoading: true });
    try {
      const response = await fetch(`${PARTNER_REGISTRY_URL}/self-employed/invoicing/reminders/run?due_in_days=14`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
      });
      const payload = (await response.json()) as { detail?: string; reminders_sent_count?: number };
      if (!response.ok) {
        throw new Error(payload.detail || 'Failed to run reminders');
      }
      setAutomationState({
        isLoading: false,
        message: `Reminder notifications sent: ${payload.reminders_sent_count ?? 0}`,
      });
      void loadInvoices();
    } catch (err) {
      setAutomationState({
        isLoading: false,
        error: err instanceof Error ? err.message : 'Failed to run reminders',
      });
    }
  };

  const checkReminderReadiness = async (): Promise<SelfEmployedReminderDeliveryReadinessResponse | null> => {
    setReadinessState({ isLoading: true });
    try {
      const response = await fetch(`${PARTNER_REGISTRY_URL}/self-employed/invoicing/reminders/readiness`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      const payload = (await response.json()) as SelfEmployedReminderDeliveryReadinessResponse | { detail?: string };
      if (!response.ok) {
        throw new Error((payload as { detail?: string }).detail || 'Failed to fetch delivery readiness');
      }
      const snapshot = payload as SelfEmployedReminderDeliveryReadinessResponse;
      setReadiness(snapshot);
      setReadinessState({ isLoading: false });
      return snapshot;
    } catch (err) {
      setReadinessState({
        isLoading: false,
        error: err instanceof Error ? err.message : 'Failed to fetch delivery readiness',
      });
      return null;
    }
  };

  const runReminderSmokeCheckRequest = async ({
    channel,
    performNetworkCheck,
    testRecipientEmail,
    testRecipientPhone,
    successMessagePrefix,
  }: {
    channel: 'email' | 'sms' | 'both';
    performNetworkCheck: boolean;
    successMessagePrefix: string;
    testRecipientEmail?: string;
    testRecipientPhone?: string;
  }): Promise<SelfEmployedReminderSmokeCheckResponse | null> => {
    setSmokeState({ isLoading: true });
    try {
      const response = await fetch(`${PARTNER_REGISTRY_URL}/self-employed/invoicing/reminders/smoke-check`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          channel,
          perform_network_check: performNetworkCheck,
          test_recipient_email: testRecipientEmail,
          test_recipient_phone: testRecipientPhone,
        }),
      });
      const payload = (await response.json()) as SelfEmployedReminderSmokeCheckResponse | { detail?: string };
      if (!response.ok) {
        throw new Error((payload as { detail?: string }).detail || 'Failed to run reminder smoke-check');
      }
      const smokePayload = payload as SelfEmployedReminderSmokeCheckResponse;
      setSmokeState({
        isLoading: false,
        message: smokePayload.passed ? `${successMessagePrefix} passed.` : `${successMessagePrefix} completed with issues.`,
        result: smokePayload,
      });
      return smokePayload;
    } catch (err) {
      setSmokeState({
        isLoading: false,
        error: err instanceof Error ? err.message : 'Failed to run reminder smoke-check',
      });
      return null;
    }
  };

  const runReminderSmokeCheck = async () => {
    await runReminderSmokeCheckRequest({
      channel: smokeChannel,
      performNetworkCheck: performSmokeNetworkCheck,
      testRecipientEmail: smokeEmail.trim() || undefined,
      testRecipientPhone: smokePhone.trim() || undefined,
      successMessagePrefix: 'Smoke-check',
    });
  };

  const runConfigOnlyPreset = async () => {
    setSmokeChannel('both');
    setPerformSmokeNetworkCheck(false);
    await checkReminderReadiness();
    await runReminderSmokeCheckRequest({
      channel: 'both',
      performNetworkCheck: false,
      testRecipientEmail: smokeEmail.trim() || customerEmail.trim() || undefined,
      testRecipientPhone: smokePhone.trim() || customerPhone.trim() || undefined,
      successMessagePrefix: 'Config-only preset',
    });
  };

  const runFullSandboxPreset = async () => {
    const readinessSnapshot = await checkReminderReadiness();
    const fallbackEmail = smokeEmail.trim() || customerEmail.trim();
    const fallbackPhone = smokePhone.trim() || customerPhone.trim();
    const emailRequired = readinessSnapshot?.email.can_dispatch ?? false;
    const smsRequired = readinessSnapshot?.sms.can_dispatch ?? false;

    if (emailRequired && !fallbackEmail) {
      setSmokeState({
        isLoading: false,
        error: 'Full sandbox preset requires test email because email channel is ready.',
      });
      return;
    }
    if (smsRequired && !fallbackPhone) {
      setSmokeState({
        isLoading: false,
        error: 'Full sandbox preset requires test phone because SMS channel is ready.',
      });
      return;
    }

    setSmokeChannel('both');
    setPerformSmokeNetworkCheck(true);
    if (fallbackEmail) {
      setSmokeEmail(fallbackEmail);
    }
    if (fallbackPhone) {
      setSmokePhone(fallbackPhone);
    }
    await runReminderSmokeCheckRequest({
      channel: 'both',
      performNetworkCheck: true,
      testRecipientEmail: fallbackEmail || undefined,
      testRecipientPhone: fallbackPhone || undefined,
      successMessagePrefix: 'Full sandbox preset',
    });
  };

  const updateStatus = async (invoiceId: string, status: SelfEmployedInvoiceStatus) => {
    setUpdatingInvoiceId(invoiceId);
    try {
      const response = await fetch(`${PARTNER_REGISTRY_URL}/self-employed/invoices/${invoiceId}/status`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ status }),
      });
      const payload = (await response.json()) as { detail?: string };
      if (!response.ok) {
        throw new Error(payload.detail || 'Failed to update invoice status');
      }
      void loadInvoices();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Status update failed');
    } finally {
      setUpdatingInvoiceId(null);
    }
  };

  const downloadInvoice = async (invoiceId: string, format: 'pdf' | 'csv') => {
    try {
      const response = await fetch(`${PARTNER_REGISTRY_URL}/self-employed/invoices/${invoiceId}/${format}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!response.ok) {
        throw new Error('Failed to download invoice');
      }
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const anchor = document.createElement('a');
      anchor.href = url;
      anchor.download = `self_employed_invoice.${format}`;
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Download failed');
    }
  };

  const requiresSmokeEmail = performSmokeNetworkCheck && (smokeChannel === 'email' || smokeChannel === 'both');
  const requiresSmokePhone = performSmokeNetworkCheck && (smokeChannel === 'sms' || smokeChannel === 'both');
  const smokeCheckInputInvalid =
    (requiresSmokeEmail && !smokeEmail.trim()) || (requiresSmokePhone && !smokePhone.trim());

  return (
    <section className={styles.subContainer}>
      <h2>Client Invoicing (Self-Employed)</h2>
      <p>Create invoices for your clients, manage recurring billing, run reminders, and export PDF/CSV.</p>
      <div className={styles.copilotWhyBlock} style={{ marginBottom: '12px' }}>
        <p>
          <strong>Brand profile:</strong> used in generated invoices and exports.
        </p>
        <div className={styles.dateInputs}>
          <input
            className={styles.input}
            onChange={(event) => setBrandBusinessName(event.target.value)}
            placeholder="Business name for invoice template"
            type="text"
            value={brandBusinessName}
          />
          <input
            className={styles.input}
            onChange={(event) => setBrandLogoUrl(event.target.value)}
            placeholder="Logo URL (optional)"
            type="url"
            value={brandLogoUrl}
          />
          <input
            className={styles.input}
            onChange={(event) => setBrandAccentColor(event.target.value)}
            placeholder="#2244AA"
            type="text"
            value={brandAccentColor}
          />
        </div>
        <div className={styles.dateInputs}>
          <input
            className={styles.input}
            onChange={(event) => setBrandPaymentTerms(event.target.value)}
            placeholder="Payment terms note"
            type="text"
            value={brandPaymentTerms}
          />
          <button
            className={styles.tableActionButton}
            disabled={automationState.isLoading || !brandBusinessName.trim()}
            onClick={saveBrandProfile}
            type="button"
          >
            Save brand profile
          </button>
        </div>
      </div>
      <form onSubmit={createInvoice}>
        <div className={styles.dateInputs}>
          <input
            className={styles.input}
            onChange={(event) => setCustomerName(event.target.value)}
            placeholder="Customer name"
            required
            type="text"
            value={customerName}
          />
          <input
            className={styles.input}
            onChange={(event) => setCustomerEmail(event.target.value)}
            placeholder="Customer email (optional)"
            type="email"
            value={customerEmail}
          />
          <input
            className={styles.input}
            onChange={(event) => setCustomerPhone(event.target.value)}
            placeholder="Customer phone (for SMS reminders, optional)"
            type="tel"
            value={customerPhone}
          />
        </div>
        <div className={styles.dateInputs}>
          <input
            className={styles.input}
            onChange={(event) => setLineDescription(event.target.value)}
            placeholder="Line description"
            required
            type="text"
            value={lineDescription}
          />
          <input
            className={styles.input}
            min={0.01}
            onChange={(event) => setQuantity(Number(event.target.value))}
            step={0.01}
            type="number"
            value={quantity}
          />
          <input
            className={styles.input}
            min={0}
            onChange={(event) => setUnitPrice(Number(event.target.value))}
            step={0.01}
            type="number"
            value={unitPrice}
          />
          <input
            className={styles.input}
            max={100}
            min={0}
            onChange={(event) => setTaxRate(Number(event.target.value))}
            step={0.1}
            type="number"
            value={taxRate}
          />
          <select
            className={styles.input}
            onChange={(event) => setRecurringCadence(event.target.value as SelfEmployedRecurringCadence)}
            value={recurringCadence}
          >
            <option value="weekly">Weekly recurring</option>
            <option value="monthly">Monthly recurring</option>
            <option value="quarterly">Quarterly recurring</option>
          </select>
        </div>
        <div className={styles.npsScoreRow}>
          <button className={styles.button} disabled={createState.isLoading} type="submit">
            {createState.isLoading ? 'Creating invoice...' : 'Create client invoice'}
          </button>
          <button
            className={styles.tableActionButton}
            disabled={automationState.isLoading || !customerName.trim() || !lineDescription.trim()}
            onClick={createRecurringPlan}
            type="button"
          >
            Save recurring plan
          </button>
          <button
            className={styles.tableActionButton}
            disabled={automationState.isLoading}
            onClick={runDueRecurringPlans}
            type="button"
          >
            Run recurring now
          </button>
          <button
            className={styles.tableActionButton}
            disabled={automationState.isLoading}
            onClick={runReminderNotifications}
            type="button"
          >
            Send reminders
          </button>
        </div>
      </form>
      {createState.message && <p className={styles.message}>{createState.message}</p>}
      {createState.error && <p className={styles.error}>{createState.error}</p>}
      {automationState.message && <p className={styles.message}>{automationState.message}</p>}
      {automationState.error && <p className={styles.error}>{automationState.error}</p>}
      <div className={styles.copilotWhyBlock} style={{ marginBottom: '14px' }}>
        <p>
          <strong>Reminder delivery operations:</strong> run readiness and smoke-check without leaving dashboard.
        </p>
        <div className={styles.npsScoreRow}>
          <button className={styles.tableActionButton} disabled={readinessState.isLoading} onClick={checkReminderReadiness} type="button">
            {readinessState.isLoading ? 'Checking readiness...' : 'Check readiness'}
          </button>
          <button
            className={styles.tableActionButton}
            disabled={smokeState.isLoading || readinessState.isLoading}
            onClick={runConfigOnlyPreset}
            type="button"
          >
            Preset: Config-only check
          </button>
          <button
            className={styles.tableActionButton}
            disabled={smokeState.isLoading || readinessState.isLoading}
            onClick={runFullSandboxPreset}
            type="button"
          >
            Preset: Full sandbox send
          </button>
          <select
            className={styles.input}
            onChange={(event) => setSmokeChannel(event.target.value as 'email' | 'sms' | 'both')}
            value={smokeChannel}
          >
            <option value="both">Smoke-check: both channels</option>
            <option value="email">Smoke-check: email only</option>
            <option value="sms">Smoke-check: SMS only</option>
          </select>
          <label style={{ alignItems: 'center', display: 'flex', gap: '6px' }}>
            <input
              checked={performSmokeNetworkCheck}
              onChange={(event) => setPerformSmokeNetworkCheck(event.target.checked)}
              type="checkbox"
            />
            Perform network check
          </label>
          <button
            className={styles.tableActionButton}
            disabled={smokeState.isLoading || smokeCheckInputInvalid}
            onClick={runReminderSmokeCheck}
            type="button"
          >
            {smokeState.isLoading ? 'Running smoke-check...' : 'Run smoke-check'}
          </button>
        </div>
        <div className={styles.dateInputs} style={{ marginTop: '10px' }}>
          <input
            className={styles.input}
            onChange={(event) => setSmokeEmail(event.target.value)}
            placeholder="Test recipient email (or leave empty to use customer email)"
            type="email"
            value={smokeEmail}
          />
          <input
            className={styles.input}
            onChange={(event) => setSmokePhone(event.target.value)}
            placeholder="Test recipient phone (or leave empty to use customer phone)"
            type="tel"
            value={smokePhone}
          />
        </div>
        {readinessState.error && <p className={styles.error}>{readinessState.error}</p>}
        {readiness && (
          <div style={{ marginTop: '10px' }}>
            <p>
              <strong>Readiness:</strong> {readiness.overall_ready ? 'ready' : 'not ready'} - {readiness.note}
            </p>
            <ul className={styles.partnerList}>
              {[readiness.email, readiness.sms].map((channel) => (
                <li key={channel.channel}>
                  {channel.channel.toUpperCase()} ({channel.provider}): enabled={String(channel.enabled)}, configured=
                  {String(channel.configured)}, can_dispatch={String(channel.can_dispatch)}
                  {channel.warnings.length ? `, warnings: ${channel.warnings.join(' | ')}` : ''}
                </li>
              ))}
            </ul>
          </div>
        )}
        {smokeState.message && <p className={styles.message}>{smokeState.message}</p>}
        {smokeState.error && <p className={styles.error}>{smokeState.error}</p>}
        {smokeState.result && (
          <ul className={styles.partnerList} style={{ marginTop: '8px' }}>
            {smokeState.result.results.map((result, index) => (
              <li key={`${result.channel}-${index}`}>
                {result.channel.toUpperCase()} ({result.provider}) - {result.delivery_status}: {result.detail}
              </li>
            ))}
          </ul>
        )}
      </div>
      {error && <p className={styles.error}>{error}</p>}
      {recurringPlans.length > 0 && (
        <div className={styles.copilotWhyBlock} style={{ marginBottom: '14px' }}>
          <p>
            <strong>Recurring plans:</strong> {recurringPlans.length}
          </p>
          <ul className={styles.partnerList}>
            {recurringPlans.map((plan) => (
              <li key={plan.id}>
                {plan.customer_name} - {plan.cadence}, next issue {plan.next_issue_date}, {plan.active ? 'active' : 'paused'}
              </li>
            ))}
          </ul>
        </div>
      )}
      {isLoading ? (
        <p>Loading invoices...</p>
      ) : invoices.length === 0 ? (
        <p className={styles.emptyState}>No client invoices yet.</p>
      ) : (
        <table className={styles.table}>
          <thead>
            <tr>
              <th>Invoice</th>
              <th>Customer</th>
              <th>Status</th>
              <th>Total</th>
              <th>Due date</th>
              <th>Payment</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {invoices.map((invoice) => (
              <tr key={invoice.id}>
                <td>{invoice.invoice_number}</td>
                <td>{invoice.customer_name}</td>
                <td>{invoice.status}</td>
                <td>£{invoice.total_amount_gbp.toFixed(2)}</td>
                <td>{invoice.due_date}</td>
                <td>
                  {invoice.payment_link_url ? (
                    <a href={invoice.payment_link_url} rel="noreferrer" target="_blank">
                      Pay link
                    </a>
                  ) : (
                    '—'
                  )}
                </td>
                <td>
                  <div className={styles.npsScoreRow}>
                    {invoice.status === 'draft' && (
                      <button
                        className={styles.tableActionButton}
                        disabled={updatingInvoiceId === invoice.id}
                        onClick={() => updateStatus(invoice.id, 'issued')}
                        type="button"
                      >
                        Issue
                      </button>
                    )}
                    {(invoice.status === 'issued' || invoice.status === 'overdue') && (
                      <button
                        className={styles.tableActionButton}
                        disabled={updatingInvoiceId === invoice.id}
                        onClick={() => updateStatus(invoice.id, 'paid')}
                        type="button"
                      >
                        Mark paid
                      </button>
                    )}
                    <button className={styles.tableActionButton} onClick={() => downloadInvoice(invoice.id, 'pdf')} type="button">
                      PDF
                    </button>
                    <button className={styles.tableActionButton} onClick={() => downloadInvoice(invoice.id, 'csv')} type="button">
                      CSV
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  );
}

function PMFSignalsPanel({ token }: { token: string }) {
  const [seedSnapshot, setSeedSnapshot] = useState<SeedReadinessResponse | null>(null);
  const [pmfEvidence, setPmfEvidence] = useState<PMFEvidenceResponse | null>(null);
  const [pmfGate, setPmfGate] = useState<PMFGateStatusResponse | null>(null);
  const [unitEconomics, setUnitEconomics] = useState<UnitEconomicsResponse | null>(null);
  const [npsTrend, setNpsTrend] = useState<NPSTrendResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [loadError, setLoadError] = useState('');
  const [restrictionMessage, setRestrictionMessage] = useState('');
  const [npsScore, setNpsScore] = useState(10);
  const [npsFeedback, setNpsFeedback] = useState('');
  const [npsSubmitState, setNpsSubmitState] = useState<{ error?: string; isLoading: boolean; message?: string }>({
    isLoading: false,
  });
  const [snapshotExportState, setSnapshotExportState] = useState<{ error?: string; isLoading: boolean; message?: string }>({
    isLoading: false,
  });

  const loadSignals = useCallback(async () => {
    setIsLoading(true);
    setLoadError('');
    setRestrictionMessage('');
    try {
      const [seedResponse, pmfResponse, pmfGateResponse, unitEconomicsResponse, npsResponse] = await Promise.all([
        fetch(`${PARTNER_REGISTRY_URL}/investor/seed-readiness?period_months=6`, {
          headers: { Authorization: `Bearer ${token}` },
        }),
        fetch(`${PARTNER_REGISTRY_URL}/investor/pmf-evidence?cohort_months=6&activation_window_days=30`, {
          headers: { Authorization: `Bearer ${token}` },
        }),
        fetch(`${PARTNER_REGISTRY_URL}/investor/pmf-gate?cohort_months=6&activation_window_days=30&nps_period_months=6`, {
          headers: { Authorization: `Bearer ${token}` },
        }),
        fetch(`${PARTNER_REGISTRY_URL}/investor/unit-economics?period_months=6`, {
          headers: { Authorization: `Bearer ${token}` },
        }),
        fetch(`${PARTNER_REGISTRY_URL}/investor/nps/trend?period_months=6`, {
          headers: { Authorization: `Bearer ${token}` },
        }),
      ]);

      const parseJsonSafely = async (response: Response): Promise<Record<string, unknown>> => {
        try {
          const payload = (await response.json()) as Record<string, unknown>;
          return payload;
        } catch {
          return {};
        }
      };

      const [seedPayload, pmfPayload, pmfGatePayload, unitEconomicsPayload, npsPayload] = await Promise.all([
        parseJsonSafely(seedResponse),
        parseJsonSafely(pmfResponse),
        parseJsonSafely(pmfGateResponse),
        parseJsonSafely(unitEconomicsResponse),
        parseJsonSafely(npsResponse),
      ]);

      const anyRestricted = [seedResponse, pmfResponse, pmfGateResponse, unitEconomicsResponse, npsResponse].some(
        (response) => response.status === 403
      );
      if (anyRestricted) {
        setRestrictionMessage('Investor metrics require billing/admin permissions. NPS submission remains available.');
      }

      if (seedResponse.ok) {
        setSeedSnapshot(seedPayload as unknown as SeedReadinessResponse);
      } else {
        setSeedSnapshot(null);
      }
      if (pmfResponse.ok) {
        setPmfEvidence(pmfPayload as unknown as PMFEvidenceResponse);
      } else {
        setPmfEvidence(null);
      }
      if (pmfGateResponse.ok) {
        setPmfGate(pmfGatePayload as unknown as PMFGateStatusResponse);
      } else {
        setPmfGate(null);
      }
      if (unitEconomicsResponse.ok) {
        setUnitEconomics(unitEconomicsPayload as unknown as UnitEconomicsResponse);
      } else {
        setUnitEconomics(null);
      }
      if (npsResponse.ok) {
        setNpsTrend(npsPayload as unknown as NPSTrendResponse);
      } else {
        setNpsTrend(null);
      }

      const criticalFailures = [seedResponse, pmfResponse, pmfGateResponse, unitEconomicsResponse, npsResponse].filter(
        (response) => !response.ok && response.status !== 403
      );
      if (criticalFailures.length > 0) {
        setLoadError('Some investor metrics could not be loaded right now. Retry in a moment.');
      }
    } catch (err) {
      setLoadError(err instanceof Error ? err.message : 'Unexpected PMF metrics error');
    } finally {
      setIsLoading(false);
    }
  }, [token]);

  useEffect(() => {
    void loadSignals();
  }, [loadSignals]);

  const submitNPS = async (event: FormEvent) => {
    event.preventDefault();
    setNpsSubmitState({ isLoading: true });
    try {
      const response = await fetch(`${PARTNER_REGISTRY_URL}/investor/nps/responses`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          score: npsScore,
          feedback: npsFeedback.trim() || undefined,
          context_tag: 'dashboard',
        }),
      });
      const payload = (await response.json()) as { detail?: string; message?: string };
      if (!response.ok) {
        throw new Error(payload.detail || 'Failed to submit NPS feedback');
      }
      setNpsSubmitState({
        isLoading: false,
        message: payload.message || 'NPS feedback submitted successfully.',
      });
      setNpsFeedback('');
      void loadSignals();
    } catch (err) {
      setNpsSubmitState({
        isLoading: false,
        error: err instanceof Error ? err.message : 'NPS submission failed',
      });
    }
  };

  const exportInvestorSnapshot = async () => {
    setSnapshotExportState({ isLoading: true });
    try {
      const response = await fetch(`${PARTNER_REGISTRY_URL}/investor/snapshot/export?format=csv`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!response.ok) {
        const payload = (await response.json()) as { detail?: string };
        throw new Error(payload.detail || 'Failed to export investor snapshot');
      }
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const anchor = document.createElement('a');
      anchor.href = url;
      anchor.download = 'investor_snapshot.csv';
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
      window.URL.revokeObjectURL(url);
      setSnapshotExportState({
        isLoading: false,
        message: 'Investor snapshot exported successfully.',
      });
    } catch (err) {
      setSnapshotExportState({
        isLoading: false,
        error: err instanceof Error ? err.message : 'Snapshot export failed',
      });
    }
  };

  return (
    <section className={styles.subContainer}>
      <h2>PMF & Growth Signals</h2>
      <p>Activation, retention cohorts, MRR momentum, and NPS trend in one panel.</p>
      <button
        className={styles.tableActionButton}
        disabled={snapshotExportState.isLoading}
        onClick={exportInvestorSnapshot}
        type="button"
      >
        {snapshotExportState.isLoading ? 'Exporting snapshot...' : 'Export investor snapshot (CSV)'}
      </button>
      {snapshotExportState.message && <p className={styles.message}>{snapshotExportState.message}</p>}
      {snapshotExportState.error && <p className={styles.error}>{snapshotExportState.error}</p>}
      {loadError && <p className={styles.error}>{loadError}</p>}
      {restrictionMessage && <p className={styles.message}>{restrictionMessage}</p>}
      {isLoading && <p>Loading PMF and growth metrics...</p>}

      {!isLoading && (seedSnapshot || pmfEvidence || pmfGate || unitEconomics || npsTrend) && (
        <div className={styles.metricsGrid}>
          {seedSnapshot && (
            <>
              <article className={styles.metricCard}>
                <h4>Seed readiness</h4>
                <p>
                  {seedSnapshot.readiness_score_percent.toFixed(1)}% ({seedSnapshot.readiness_band})
                </p>
              </article>
              <article className={styles.metricCard}>
                <h4>MRR growth (MoM)</h4>
                <p>{seedSnapshot.mrr_growth_percent.toFixed(1)}%</p>
              </article>
              <article className={styles.metricCard}>
                <h4>Paid invoice rate</h4>
                <p>{seedSnapshot.paid_invoice_rate_percent.toFixed(1)}%</p>
              </article>
            </>
          )}
          {pmfEvidence && (
            <>
              <article className={styles.metricCard}>
                <h4>Activation</h4>
                <p>
                  {pmfEvidence.activation_rate_percent.toFixed(1)}% ({pmfEvidence.activated_users}/{pmfEvidence.total_new_users})
                </p>
              </article>
              <article className={styles.metricCard}>
                <h4>Retention 30d</h4>
                <p>{pmfEvidence.retention_rate_30d_percent.toFixed(1)}%</p>
              </article>
              <article className={styles.metricCard}>
                <h4>Retention 90d</h4>
                <p>{pmfEvidence.retention_rate_90d_percent.toFixed(1)}%</p>
              </article>
            </>
          )}
          {pmfGate && (
            <article className={styles.metricCard}>
              <h4>PMF gate</h4>
              <p>{pmfGate.gate_passed ? 'PASSED' : 'NOT YET'}</p>
            </article>
          )}
          {unitEconomics && (
            <>
              <article className={styles.metricCard}>
                <h4>Seed financial gate</h4>
                <p>{unitEconomics.seed_gate_passed ? 'PASSED' : 'NOT YET'}</p>
              </article>
              <article className={styles.metricCard}>
                <h4>Monthly churn</h4>
                <p>
                  {unitEconomics.monthly_churn_rate_percent.toFixed(1)}% (target &lt;{' '}
                  {unitEconomics.required_max_monthly_churn_percent.toFixed(1)}%)
                </p>
              </article>
              <article className={styles.metricCard}>
                <h4>LTV/CAC</h4>
                <p>
                  {unitEconomics.ltv_cac_ratio !== null && unitEconomics.ltv_cac_ratio !== undefined
                    ? unitEconomics.ltv_cac_ratio.toFixed(2)
                    : 'n/a'}{' '}
                  (target ≥ {unitEconomics.required_min_ltv_cac_ratio.toFixed(1)})
                </p>
              </article>
            </>
          )}
          {npsTrend && (
            <article className={styles.metricCard}>
              <h4>Overall NPS</h4>
              <p>{npsTrend.overall_nps_score.toFixed(1)}</p>
            </article>
          )}
        </div>
      )}

      {pmfGate && (
        <div className={styles.copilotWhyBlock} style={{ marginTop: '10px' }}>
          <p>
            <strong>Gate status:</strong> {pmfGate.summary}
          </p>
          <p>
            <strong>Criteria:</strong> Activation {pmfGate.activation_rate_percent.toFixed(1)}% / required{' '}
            {pmfGate.required_activation_rate_percent.toFixed(1)}%; Retention 90d{' '}
            {pmfGate.retention_rate_90d_percent.toFixed(1)}% / required {pmfGate.required_retention_rate_90d_percent.toFixed(1)}%;
            NPS {pmfGate.overall_nps_score.toFixed(1)} / required {pmfGate.required_overall_nps_score.toFixed(1)}.
          </p>
          {!pmfGate.gate_passed && pmfGate.next_actions.length > 0 && (
            <ul className={styles.copilotEvidenceList}>
              {pmfGate.next_actions.map((item) => (
                <li key={item}>
                  <p>{item}</p>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}

      {unitEconomics && (
        <div className={styles.copilotWhyBlock} style={{ marginTop: '10px' }}>
          <p>
            <strong>Unit economics:</strong> current MRR £{unitEconomics.current_month_mrr_gbp.toFixed(2)} vs target £
            {unitEconomics.required_mrr_gbp.toFixed(2)}; monthly churn {unitEconomics.monthly_churn_rate_percent.toFixed(1)}%; stability{' '}
            {unitEconomics.mrr_stability_percent.toFixed(1)}% ({unitEconomics.mrr_stability_band}).
          </p>
          {!unitEconomics.seed_gate_passed && unitEconomics.next_actions.length > 0 && (
            <ul className={styles.copilotEvidenceList}>
              {unitEconomics.next_actions.map((item) => (
                <li key={item}>
                  <p>{item}</p>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}

      {pmfEvidence && (
        <>
          <h3 className={styles.sectionTitle}>Monthly activation/retention cohorts</h3>
          <table className={styles.table}>
            <thead>
              <tr>
                <th>Cohort</th>
                <th>New users</th>
                <th>Activation %</th>
                <th>Retention 30d %</th>
                <th>Retention 60d %</th>
                <th>Retention 90d %</th>
              </tr>
            </thead>
            <tbody>
              {pmfEvidence.monthly_cohorts.map((row) => (
                <tr key={row.cohort_month}>
                  <td>{row.cohort_month}</td>
                  <td>{row.new_users}</td>
                  <td>{row.activation_rate_percent.toFixed(1)}</td>
                  <td>{row.retention_rate_30d_percent.toFixed(1)}</td>
                  <td>{row.retention_rate_60d_percent.toFixed(1)}</td>
                  <td>{row.retention_rate_90d_percent.toFixed(1)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </>
      )}

      {npsTrend && (
        <>
          <h3 className={styles.sectionTitle}>Monthly NPS trend</h3>
          <table className={styles.table}>
            <thead>
              <tr>
                <th>Month</th>
                <th>Responses</th>
                <th>Promoters</th>
                <th>Passives</th>
                <th>Detractors</th>
                <th>NPS</th>
              </tr>
            </thead>
            <tbody>
              {npsTrend.monthly_trend.map((row) => (
                <tr key={row.month}>
                  <td>{row.month}</td>
                  <td>{row.responses_count}</td>
                  <td>{row.promoters_count}</td>
                  <td>{row.passives_count}</td>
                  <td>{row.detractors_count}</td>
                  <td>{row.nps_score.toFixed(1)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </>
      )}

      <h3 className={styles.sectionTitle}>Share NPS feedback</h3>
      <form className={styles.copilotComposer} onSubmit={submitNPS}>
        <div className={styles.npsScoreRow}>
          <label htmlFor="nps-score">Score (0-10)</label>
          <input
            className={styles.input}
            id="nps-score"
            max={10}
            min={0}
            onChange={(event) => setNpsScore(Math.max(0, Math.min(10, Number(event.target.value) || 0)))}
            type="number"
            value={npsScore}
          />
        </div>
        <textarea
          className={`${styles.input} ${styles.copilotTextarea}`}
          onChange={(event) => setNpsFeedback(event.target.value)}
          placeholder="Optional: what should we improve next?"
          value={npsFeedback}
        />
        <button className={styles.button} disabled={npsSubmitState.isLoading} type="submit">
          {npsSubmitState.isLoading ? 'Submitting...' : 'Submit NPS'}
        </button>
      </form>
      {npsSubmitState.message && <p className={styles.message}>{npsSubmitState.message}</p>}
      {npsSubmitState.error && <p className={styles.error}>{npsSubmitState.error}</p>}
    </section>
  );
}

function AICopilotPanel({ token }: { token: string }) {
  const router = useRouter();
  const [message, setMessage] = useState('Give me a readiness snapshot and next action.');
  const [response, setResponse] = useState<CopilotChatResponse | null>(null);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [whyOpenForActionKey, setWhyOpenForActionKey] = useState<string | null>(null);
  const [actionState, setActionState] = useState<Record<string, { error?: string; isLoading: boolean; message?: string }>>({});
  const [auditEvents, setAuditEvents] = useState<CopilotAuditEvent[]>([]);

  const quickPrompts = [
    'Give me a readiness snapshot and next action.',
    'Show OCR queue risk and what to fix first.',
    'Help reconcile unmatched receipt drafts.',
    'Prepare tax submission safely for HMRC.',
  ];

  useEffect(() => {
    if (typeof window === 'undefined') {
      return;
    }
    const storedSessionId = window.localStorage.getItem(COPILOT_SESSION_STORAGE_KEY);
    const storedMessage = window.localStorage.getItem(COPILOT_MESSAGE_STORAGE_KEY);
    if (storedSessionId) {
      setSessionId(storedSessionId);
    }
    if (storedMessage) {
      setMessage(storedMessage);
    }
  }, []);

  useEffect(() => {
    if (typeof window === 'undefined') {
      return;
    }
    if (sessionId) {
      window.localStorage.setItem(COPILOT_SESSION_STORAGE_KEY, sessionId);
    }
    window.localStorage.setItem(COPILOT_MESSAGE_STORAGE_KEY, message);
  }, [sessionId, message]);

  const loadAuditEvents = async () => {
    try {
      const response = await fetch(`${AGENT_SERVICE_URL}/audit/events?limit=6`, {
        method: 'GET',
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });
      if (!response.ok) {
        return;
      }
      const payload = (await response.json()) as { items?: CopilotAuditEvent[] };
      setAuditEvents(Array.isArray(payload.items) ? payload.items : []);
    } catch {
      // Non-blocking telemetry panel load.
    }
  };

  const buildActionKey = (action: CopilotSuggestedAction, index: number) => `${action.action_id}:${index}`;
  const getEvidenceForAction = (action: CopilotSuggestedAction) => {
    if (!response) {
      return [];
    }
    if (action.action_id.startsWith('documents.') || action.action_id.includes('ocr')) {
      return response.evidence.filter((item) => item.source_service === 'documents-service');
    }
    if (action.action_id.startsWith('transactions.') || action.action_id.includes('reconcile')) {
      return response.evidence.filter((item) => item.source_service === 'transactions-service');
    }
    if (action.action_id.startsWith('tax.')) {
      return response.evidence.filter((item) => item.source_service === 'tax-engine');
    }
    return response.evidence;
  };

  const handleAskCopilot = async (event: FormEvent) => {
    event.preventDefault();
    const trimmed = message.trim();
    if (!trimmed) {
      setError('Enter a request for AI Copilot.');
      return;
    }
    setError('');
    setIsLoading(true);
    try {
      const body: { message: string; session_id?: string } = { message: trimmed };
      if (sessionId) {
        body.session_id = sessionId;
      }
      const apiResponse = await fetch(`${AGENT_SERVICE_URL}/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(body),
      });
      const payload = (await apiResponse.json()) as CopilotChatResponse | { detail?: string };
      if (!apiResponse.ok) {
        throw new Error((payload as { detail?: string }).detail || 'Failed to fetch AI Copilot response');
      }
      const chatPayload = payload as CopilotChatResponse;
      setResponse(chatPayload);
      setSessionId(chatPayload.session_id);
      setWhyOpenForActionKey(null);
      void loadAuditEvents();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unexpected Copilot error');
    } finally {
      setIsLoading(false);
    }
  };

  const handleConfirmAction = async (action: CopilotSuggestedAction, index: number) => {
    if (!response) {
      return;
    }
    const actionPayload = action.action_payload && typeof action.action_payload === 'object' ? action.action_payload : {};
    const actionKey = buildActionKey(action, index);
    setActionState((current) => ({
      ...current,
      [actionKey]: { isLoading: true },
    }));
    try {
      const confirmationRequest = await fetch(`${AGENT_SERVICE_URL}/actions/request-confirmation`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          session_id: response.session_id,
          action_id: action.action_id,
          action_payload: actionPayload,
        }),
      });
      const confirmationPayload = (await confirmationRequest.json()) as {
        confirmation_token?: string;
        detail?: string;
      };
      if (!confirmationRequest.ok || !confirmationPayload.confirmation_token) {
        throw new Error(confirmationPayload.detail || 'Failed to request confirmation token');
      }

      const executeRequest = await fetch(`${AGENT_SERVICE_URL}/actions/execute`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          session_id: response.session_id,
          action_id: action.action_id,
          confirmation_token: confirmationPayload.confirmation_token,
          action_payload: actionPayload,
        }),
      });
      const executePayload = (await executeRequest.json()) as CopilotExecutionResponse;
      if (!executeRequest.ok) {
        throw new Error(executePayload.message || 'Execution failed');
      }
      if (!executePayload.executed) {
        throw new Error(executePayload.confirmation_reason || executePayload.message || 'Action was not executed');
      }
      const successMessage = executePayload.downstream_status_code
        ? `Done (${executePayload.downstream_status_code}): ${executePayload.message}`
        : executePayload.message;
      setActionState((current) => ({
        ...current,
        [actionKey]: { isLoading: false, message: successMessage },
      }));
      void loadAuditEvents();
    } catch (err) {
      setActionState((current) => ({
        ...current,
        [actionKey]: { isLoading: false, error: err instanceof Error ? err.message : 'Action failed' },
      }));
    }
  };

  return (
    <section className={`${styles.subContainer} ${styles.copilotPanel}`}>
      <h2>AI Copilot</h2>
      <p>Ask for OCR, reconciliation, and tax readiness guidance with evidence-backed suggestions.</p>
      <form className={styles.copilotComposer} onSubmit={handleAskCopilot}>
        <textarea
          className={`${styles.input} ${styles.copilotTextarea}`}
          onChange={(event) => setMessage(event.target.value)}
          value={message}
          placeholder="Example: Help me close OCR queue and submit tax safely."
        />
        <button className={styles.button} disabled={isLoading} type="submit">
          {isLoading ? 'Thinking...' : 'Ask Copilot'}
        </button>
      </form>
      <div className={styles.copilotQuickPrompts}>
        {quickPrompts.map((prompt) => (
          <button
            className={styles.presetButton}
            key={prompt}
            onClick={() => setMessage(prompt)}
            type="button"
          >
            {prompt}
          </button>
        ))}
      </div>
      {error && (
        <div className={styles.copilotFallback}>
          <p className={styles.error}>{error}</p>
          <p>Copilot is temporarily unavailable. Continue with manual control paths:</p>
          <div className={styles.copilotFallbackActions}>
            <button className={styles.tableActionButton} onClick={() => router.push('/documents')} type="button">
              Open OCR review queue
            </button>
            <button className={styles.tableActionButton} onClick={() => router.push('/transactions')} type="button">
              Open reconciliation screen
            </button>
            <button className={styles.tableActionButton} onClick={() => router.push('/submission')} type="button">
              Open submission flow
            </button>
          </div>
        </div>
      )}

      {response && (
        <div className={styles.copilotResults}>
          <div className={styles.copilotMeta}>
            <span>Intent: {response.intent}</span>
            <span>Confidence: {response.confidence.toFixed(2)}</span>
            <span>Band: {response.confidence_band}</span>
            <span>Session: {response.session_id}</span>
          </div>
          <p className={styles.copilotIntentReason}>Why this intent: {response.intent_reason}</p>
          <div className={styles.copilotAnswer}>{response.answer}</div>

          <h3 className={styles.sectionTitle}>Evidence</h3>
          <ul className={styles.copilotEvidenceList}>
            {response.evidence.map((item, index) => (
              <li key={`${item.source_service}-${item.source_endpoint}-${index}`}>
                <strong>{item.source_service}</strong> <code>{item.source_endpoint}</code>
                <p>{item.summary}</p>
              </li>
            ))}
          </ul>

          <h3 className={styles.sectionTitle}>Suggested actions</h3>
          <div className={styles.copilotActionGrid}>
            {response.suggested_actions.map((action, index) => {
              const actionKey = buildActionKey(action, index);
              const currentState = actionState[actionKey];
              const hasPayload = Boolean(action.action_payload);
              const isWhyOpen = whyOpenForActionKey === actionKey;
              const actionEvidence = getEvidenceForAction(action);
              return (
                <article className={styles.copilotActionCard} key={actionKey}>
                  <div className={styles.copilotActionHeader}>
                    <strong>{action.label}</strong>
                    <span className={styles.reviewBadge}>
                      {action.requires_confirmation ? 'Confirmation required' : 'Manual'}
                    </span>
                  </div>
                  <p>{action.description}</p>
                  {hasPayload && (
                    <pre className={styles.copilotPayloadPreview}>{JSON.stringify(action.action_payload, null, 2)}</pre>
                  )}
                  <button
                    className={styles.tableActionButton}
                    onClick={() => setWhyOpenForActionKey(isWhyOpen ? null : actionKey)}
                    type="button"
                  >
                    {isWhyOpen ? 'Hide why this suggestion' : 'Why this suggestion?'}
                  </button>
                  {isWhyOpen && (
                    <div className={styles.copilotWhyBlock}>
                      <p>Confidence: {response.confidence.toFixed(2)}</p>
                      {actionEvidence.length === 0 ? (
                        <p>No direct evidence mapping was found; this recommendation is based on overall readiness context.</p>
                      ) : (
                        <ul>
                          {actionEvidence.slice(0, 3).map((item, evidenceIndex) => (
                            <li key={`${actionKey}-evidence-${evidenceIndex}`}>
                              <strong>{item.source_service}</strong>: {item.summary}
                            </li>
                          ))}
                        </ul>
                      )}
                    </div>
                  )}
                  {action.requires_confirmation && (
                    <button
                      className={styles.tableActionButton}
                      disabled={currentState?.isLoading}
                      onClick={() => handleConfirmAction(action, index)}
                      type="button"
                    >
                      {currentState?.isLoading ? 'Confirming...' : 'Confirm'}
                    </button>
                  )}
                  {currentState?.message && <p className={styles.message}>{currentState.message}</p>}
                  {currentState?.error && <p className={styles.error}>{currentState.error}</p>}
                </article>
              );
            })}
          </div>
          {auditEvents.length > 0 && (
            <>
              <h3 className={styles.sectionTitle}>Recent Copilot activity</h3>
              <ul className={styles.copilotEvidenceList}>
                {auditEvents.map((event, index) => (
                  <li key={`${event.event_type}-${event.timestamp}-${index}`}>
                    <strong>{event.event_type}</strong>
                    {event.action_id ? <span> ({event.action_id})</span> : null}
                    <p>{new Date(event.timestamp).toLocaleString()}</p>
                  </li>
                ))}
              </ul>
            </>
          )}
        </div>
      )}
    </section>
  );
}

export default function DashboardPage({ token }: DashboardPageProps) {
  const { t } = useTranslation();

  return (
    <div className={styles.dashboard}>
      <h1>{t('dashboard.title')}</h1>
      <p>{t('dashboard.description')}</p>
      <AICopilotPanel token={token} />
      <PMFSignalsPanel token={token} />
      <SelfEmployedInvoicingPanel token={token} />
      <ActionCenter token={token} />
      <CashFlowPreview token={token} />
      <TaxCalculator token={token} />
    </div>
  );
}
