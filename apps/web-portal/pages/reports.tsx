import { useEffect, useMemo, useState } from 'react';
import { useTranslation } from '../hooks/useTranslation';
import styles from '../styles/Home.module.css';

const ANALYTICS_SERVICE_URL = process.env.NEXT_PUBLIC_ANALYTICS_SERVICE_URL || '/api/analytics';
const TAX_SERVICE_URL = process.env.NEXT_PUBLIC_TAX_ENGINE_URL || '/api/tax';

const AFFORDABILITY_TAX_YEAR = { start: '2025-04-06', end: '2026-04-05' } as const;

type ReportsPageProps = {
  token: string;
};

type MortgageTypeSummary = {
  code: string;
  description: string;
  label: string;
};

type LenderProfileSummary = {
  code: string;
  description: string;
  label: string;
};

type MortgageDocumentItem = {
  code: string;
  reason: string;
  title: string;
};

type MortgageChecklistResponse = {
  conditional_documents: MortgageDocumentItem[];
  employment_profile: string;
  jurisdiction: string;
  lender_profile: string;
  lender_profile_label: string;
  lender_notes: string[];
  mortgage_description: string;
  mortgage_label: string;
  mortgage_type: string;
  next_steps: string[];
  required_documents: MortgageDocumentItem[];
};

type MortgageEvidenceQualityIssue = {
  check_type: 'staleness' | 'name_mismatch' | 'period_mismatch' | 'unreadable_ocr';
  document_code?: string | null;
  document_filename: string;
  message: string;
  severity: 'critical' | 'warning' | 'info';
  suggested_action: string;
};

type MortgageEvidenceQualitySummary = {
  critical_count: number;
  has_blockers: boolean;
  info_count: number;
  total_issues: number;
  warning_count: number;
};

type MortgageSubmissionGate = {
  advisor_review_confirmed: boolean;
  advisor_review_required: boolean;
  broker_submission_allowed: boolean;
  broker_submission_blockers: string[];
  compliance_disclaimer: string;
};

type MortgageRefreshReminderSummary = {
  due_now_count: number;
  has_due_now: boolean;
  next_due_date?: string | null;
  total_reminders: number;
  upcoming_count: number;
};

type MortgageRefreshReminder = {
  cadence_days: number;
  document_code: string;
  document_filename: string;
  due_date: string;
  message: string;
  reminder_type: 'statement_refresh' | 'id_validity_check';
  status: 'due_now' | 'upcoming';
  suggested_action: string;
  title: string;
};

type MortgageReadinessResponse = MortgageChecklistResponse & {
  detected_document_codes: string[];
  evidence_quality_issues: MortgageEvidenceQualityIssue[];
  evidence_quality_summary: MortgageEvidenceQualitySummary;
  matched_required_documents: MortgageDocumentItem[];
  missing_conditional_documents: MortgageDocumentItem[];
  missing_required_documents: MortgageDocumentItem[];
  next_actions: string[];
  overall_completion_percent: number;
  readiness_status: 'not_ready' | 'almost_ready' | 'ready_for_broker_review';
  readiness_summary: string;
  refresh_reminder_summary: MortgageRefreshReminderSummary;
  refresh_reminders: MortgageRefreshReminder[];
  required_completion_percent: number;
  submission_gate: MortgageSubmissionGate;
  uploaded_document_count: number;
};

type MortgageReadinessMatrixItem = {
  missing_required_count: number;
  mortgage_label: string;
  mortgage_type: string;
  overall_completion_percent: number;
  readiness_status: 'not_ready' | 'almost_ready' | 'ready_for_broker_review';
  required_completion_percent: number;
};

type MortgageReadinessMatrixResponse = {
  almost_ready_count: number;
  average_overall_completion_percent: number;
  average_required_completion_percent: number;
  include_adverse_credit_pack: boolean;
  items: MortgageReadinessMatrixItem[];
  lender_profile: string;
  lender_profile_label: string;
  not_ready_count: number;
  overall_status: 'not_ready' | 'almost_ready' | 'ready_for_broker_review';
  ready_for_broker_review_count: number;
  total_mortgage_types: number;
  uploaded_document_count: number;
};

type MortgageDocumentEvidenceItem = {
  code: string;
  match_status: 'matched' | 'missing';
  matched_filenames: string[];
  reason: string;
  title: string;
};

type MortgagePackIndexResponse = MortgageReadinessResponse & {
  conditional_document_evidence: MortgageDocumentEvidenceItem[];
  generated_at: string;
  required_document_evidence: MortgageDocumentEvidenceItem[];
};

type MortgageAffordabilityResponse = {
  additional_property_surcharge_applied: boolean;
  annual_interest_rate_pct: number;
  baseline_income_multiple: number;
  credit_band: string;
  deposit_pct_computed: number | null;
  disclaimer: string;
  employed_planning_multiple: number;
  employment: string;
  first_time_buyer: boolean;
  lender_scenarios: Array<{
    id: string;
    illustrative_fit_reasons: string[];
    illustrative_fit_score: number;
    income_multiple: number;
    label: string;
    max_loan_from_income_gbp: number;
    min_accounts_years: number;
    min_deposit_pct: number;
    notes: string;
    segment: string;
  }>;
  loan_amount_for_payment_gbp: number | null;
  ltv_pct: number | null;
  max_loan_from_income_gbp: number;
  max_loan_from_income_gbp_self_employed_range: [number, number] | null;
  monthly_payment_gbp: number;
  monthly_payment_if_rates_up_3pp_gbp: number;
  self_employed_planning_multiple_range: [number, number];
  stamp_duty_england_gbp: number | null;
  stress_rate_add_pct_points: number;
  stressed_annual_interest_rate_pct: number;
  term_years: number;
  years_trading: number | null;
};

const EMPLOYMENT_PROFILE_OPTIONS = [
  { label: 'Self-employed sole trader', value: 'sole_trader' },
  { label: 'Limited company director', value: 'limited_company_director' },
  { label: 'Contractor / day-rate worker', value: 'contractor' },
  { label: 'PAYE employed', value: 'employed' },
  { label: 'Mixed income profile', value: 'mixed' },
] as const;

export default function ReportsPage({ token }: ReportsPageProps) {
  const [isLoading, setIsLoading] = useState(false);
  const [isLoadingChecklist, setIsLoadingChecklist] = useState(false);
  const [isAssessingReadiness, setIsAssessingReadiness] = useState(false);
  const [isBuildingMatrix, setIsBuildingMatrix] = useState(false);
  const [isExportingPackJson, setIsExportingPackJson] = useState(false);
  const [isExportingPackPdf, setIsExportingPackPdf] = useState(false);
  const [isLoadingMortgageTypes, setIsLoadingMortgageTypes] = useState(true);
  const [isLoadingLenderProfiles, setIsLoadingLenderProfiles] = useState(true);
  const [mortgageTypes, setMortgageTypes] = useState<MortgageTypeSummary[]>([]);
  const [lenderProfiles, setLenderProfiles] = useState<LenderProfileSummary[]>([]);
  const [selectedMortgageType, setSelectedMortgageType] = useState('');
  const [selectedLenderProfile, setSelectedLenderProfile] = useState('');
  const [employmentProfile, setEmploymentProfile] = useState<(typeof EMPLOYMENT_PROFILE_OPTIONS)[number]['value']>(
    'sole_trader'
  );
  const [includeAdverseCreditPack, setIncludeAdverseCreditPack] = useState(false);
  const [advisorReviewConfirmed, setAdvisorReviewConfirmed] = useState(false);
  const [checklist, setChecklist] = useState<MortgageChecklistResponse | null>(null);
  const [readiness, setReadiness] = useState<MortgageReadinessResponse | null>(null);
  const [readinessMatrix, setReadinessMatrix] = useState<MortgageReadinessMatrixResponse | null>(null);
  const [error, setError] = useState('');
  const [checklistError, setChecklistError] = useState('');
  const [readinessError, setReadinessError] = useState('');
  const [matrixError, setMatrixError] = useState('');
  const [affordIncome, setAffordIncome] = useState('');
  const [affordProperty, setAffordProperty] = useState('');
  const [affordDeposit, setAffordDeposit] = useState('');
  const [affordRate, setAffordRate] = useState('5');
  const [affordTerm, setAffordTerm] = useState('30');
  const [affordEmployment, setAffordEmployment] = useState<'employed' | 'self_employed'>('self_employed');
  const [affordFtb, setAffordFtb] = useState(false);
  const [affordAdditional, setAffordAdditional] = useState(false);
  const [affordCredit, setAffordCredit] = useState<'clean' | 'minor' | 'adverse'>('clean');
  const [affordYearsTrading, setAffordYearsTrading] = useState('');
  const [affordResult, setAffordResult] = useState<MortgageAffordabilityResponse | null>(null);
  const [affordLoading, setAffordLoading] = useState(false);
  const [affordError, setAffordError] = useState('');
  const { formatNumber, t } = useTranslation();

  useEffect(() => {
    const loadSelectors = async () => {
      setIsLoadingMortgageTypes(true);
      setIsLoadingLenderProfiles(true);
      try {
        const headers = { Authorization: `Bearer ${token}` };
        const [mortgageTypesResponse, lenderProfilesResponse] = await Promise.all([
          fetch(`${ANALYTICS_SERVICE_URL}/mortgage/types`, { headers }),
          fetch(`${ANALYTICS_SERVICE_URL}/mortgage/lender-profiles`, { headers }),
        ]);
        if (!mortgageTypesResponse.ok) {
          throw new Error('Failed to load mortgage types');
        }
        if (!lenderProfilesResponse.ok) {
          throw new Error('Failed to load lender profiles');
        }
        const mortgageTypesPayload = (await mortgageTypesResponse.json()) as MortgageTypeSummary[];
        const lenderProfilesPayload = (await lenderProfilesResponse.json()) as LenderProfileSummary[];
        setMortgageTypes(mortgageTypesPayload);
        setLenderProfiles(lenderProfilesPayload);
        if (mortgageTypesPayload.length > 0) {
          setSelectedMortgageType(mortgageTypesPayload[0].code);
        }
        if (lenderProfilesPayload.length > 0) {
          setSelectedLenderProfile(lenderProfilesPayload[0].code);
        }
      } catch (err) {
        setChecklistError(err instanceof Error ? err.message : 'Unexpected error');
      } finally {
        setIsLoadingMortgageTypes(false);
        setIsLoadingLenderProfiles(false);
      }
    };
    loadSelectors();
  }, [token]);

  const fillIncomeFromTax = async () => {
    setAffordError('');
    try {
      const res = await fetch(`${TAX_SERVICE_URL}/calculate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({
          start_date: AFFORDABILITY_TAX_YEAR.start,
          end_date: AFFORDABILITY_TAX_YEAR.end,
          jurisdiction: 'UK',
        }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error((err as { detail?: string }).detail ?? 'Tax calculation failed');
      }
      const data = (await res.json()) as { taxable_profit?: number; total_income?: number };
      const inc = data.taxable_profit ?? data.total_income;
      if (inc == null || Number.isNaN(Number(inc))) {
        throw new Error('No taxable profit or total income in tax response');
      }
      setAffordIncome(String(Math.max(0, Math.round(Number(inc) * 100) / 100)));
    } catch (e) {
      setAffordError(e instanceof Error ? e.message : 'Could not load income');
    }
  };

  const runAffordability = async () => {
    setAffordError('');
    setAffordResult(null);
    const income = parseFloat(affordIncome.replace(/,/g, ''));
    if (!income || income <= 0) {
      setAffordError('Enter a positive annual income (or use “Fill from tax estimate”).');
      return;
    }
    const priceRaw = affordProperty.trim() ? parseFloat(affordProperty.replace(/,/g, '')) : NaN;
    const depRaw = affordDeposit.trim() ? parseFloat(affordDeposit.replace(/,/g, '')) : NaN;
    const rate = parseFloat(affordRate) || 5;
    const term = parseInt(affordTerm, 10) || 30;
    const ytRaw = affordYearsTrading.trim() ? parseInt(affordYearsTrading, 10) : NaN;
    const yearsTrading = !Number.isNaN(ytRaw) && ytRaw >= 0 ? ytRaw : null;
    setAffordLoading(true);
    try {
      const res = await fetch(`${ANALYTICS_SERVICE_URL}/mortgage/affordability`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({
          annual_income_gbp: income,
          employment: affordEmployment,
          property_price_gbp: !Number.isNaN(priceRaw) && priceRaw > 0 ? priceRaw : null,
          deposit_gbp: !Number.isNaN(depRaw) && depRaw >= 0 ? depRaw : null,
          annual_interest_rate_pct: rate,
          term_years: term,
          first_time_buyer: affordFtb,
          additional_property: affordAdditional,
          credit_band: affordCredit,
          years_trading: yearsTrading,
        }),
      });
      const payload = (await res.json()) as MortgageAffordabilityResponse | { detail?: string };
      if (!res.ok) {
        throw new Error('detail' in payload && payload.detail ? String(payload.detail) : 'Affordability request failed');
      }
      setAffordResult(payload as MortgageAffordabilityResponse);
    } catch (e) {
      setAffordError(e instanceof Error ? e.message : 'Unexpected error');
    } finally {
      setAffordLoading(false);
    }
  };

  const handleGenerateReport = async () => {
    setIsLoading(true);
    setError('');

    try {
      const response = await fetch(`${ANALYTICS_SERVICE_URL}/reports/mortgage-readiness`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!response.ok) {
        throw new Error('Failed to generate report');
      }

      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const anchor = document.createElement('a');
      anchor.href = url;
      anchor.download = `mortgage-readiness-report-${new Date().toISOString().split('T')[0]}.pdf`;
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unexpected error');
    } finally {
      setIsLoading(false);
    }
  };

  const selectedMortgageTypeDescription = useMemo(
    () => mortgageTypes.find((item) => item.code === selectedMortgageType)?.description ?? '',
    [mortgageTypes, selectedMortgageType]
  );
  const selectedLenderProfileDescription = useMemo(
    () => lenderProfiles.find((item) => item.code === selectedLenderProfile)?.description ?? '',
    [lenderProfiles, selectedLenderProfile]
  );

  const handleGenerateChecklist = async () => {
    setChecklistError('');
    setReadinessError('');
    setChecklist(null);
    setReadiness(null);
    if (!selectedMortgageType) {
      setChecklistError('Please select a mortgage type first.');
      return;
    }
    if (!selectedLenderProfile) {
      setChecklistError('Please select a lender profile first.');
      return;
    }

    setIsLoadingChecklist(true);
    try {
      const response = await fetch(`${ANALYTICS_SERVICE_URL}/mortgage/checklist`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          mortgage_type: selectedMortgageType,
          lender_profile: selectedLenderProfile,
          employment_profile: employmentProfile,
          include_adverse_credit_pack: includeAdverseCreditPack,
          advisor_review_confirmed: advisorReviewConfirmed,
        }),
      });
      const payload = (await response.json()) as MortgageChecklistResponse | { detail?: string };
      if (!response.ok) {
        throw new Error('detail' in payload && payload.detail ? payload.detail : 'Failed to generate checklist');
      }
      setChecklist(payload as MortgageChecklistResponse);
    } catch (err) {
      setChecklistError(err instanceof Error ? err.message : 'Unexpected error');
    } finally {
      setIsLoadingChecklist(false);
    }
  };

  const handleAssessReadiness = async () => {
    setReadinessError('');
    setReadiness(null);
    if (!selectedMortgageType) {
      setReadinessError('Please select a mortgage type first.');
      return;
    }
    if (!selectedLenderProfile) {
      setReadinessError('Please select a lender profile first.');
      return;
    }
    setIsAssessingReadiness(true);
    try {
      const response = await fetch(`${ANALYTICS_SERVICE_URL}/mortgage/readiness`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          mortgage_type: selectedMortgageType,
          lender_profile: selectedLenderProfile,
          employment_profile: employmentProfile,
          include_adverse_credit_pack: includeAdverseCreditPack,
        }),
      });
      const payload = (await response.json()) as MortgageReadinessResponse | { detail?: string };
      if (!response.ok) {
        throw new Error('detail' in payload && payload.detail ? payload.detail : 'Failed to assess readiness');
      }
      setReadiness(payload as MortgageReadinessResponse);
    } catch (err) {
      setReadinessError(err instanceof Error ? err.message : 'Unexpected error');
    } finally {
      setIsAssessingReadiness(false);
    }
  };

  const handleBuildMatrix = async () => {
    setMatrixError('');
    setReadinessMatrix(null);
    if (!selectedLenderProfile) {
      setMatrixError('Please select a lender profile first.');
      return;
    }
    setIsBuildingMatrix(true);
    try {
      const response = await fetch(`${ANALYTICS_SERVICE_URL}/mortgage/readiness-matrix`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          employment_profile: employmentProfile,
          lender_profile: selectedLenderProfile,
          include_adverse_credit_pack: includeAdverseCreditPack,
        }),
      });
      const payload = (await response.json()) as MortgageReadinessMatrixResponse | { detail?: string };
      if (!response.ok) {
        throw new Error('detail' in payload && payload.detail ? payload.detail : 'Failed to build readiness matrix');
      }
      setReadinessMatrix(payload as MortgageReadinessMatrixResponse);
    } catch (err) {
      setMatrixError(err instanceof Error ? err.message : 'Unexpected error');
    } finally {
      setIsBuildingMatrix(false);
    }
  };

  const buildMortgagePayload = () => ({
    mortgage_type: selectedMortgageType,
    lender_profile: selectedLenderProfile,
    employment_profile: employmentProfile,
    include_adverse_credit_pack: includeAdverseCreditPack,
    advisor_review_confirmed: advisorReviewConfirmed,
  });

  const handleExportPackIndexJson = async () => {
    setMatrixError('');
    if (!selectedMortgageType || !selectedLenderProfile) {
      setMatrixError('Select mortgage and lender profile first.');
      return;
    }
    setIsExportingPackJson(true);
    try {
      const response = await fetch(`${ANALYTICS_SERVICE_URL}/mortgage/pack-index`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(buildMortgagePayload()),
      });
      const payload = (await response.json()) as MortgagePackIndexResponse | { detail?: string };
      if (!response.ok) {
        throw new Error('detail' in payload && payload.detail ? payload.detail : 'Failed to export pack manifest');
      }
      const jsonBlob = new Blob([JSON.stringify(payload, null, 2)], { type: 'application/json' });
      const url = window.URL.createObjectURL(jsonBlob);
      const anchor = document.createElement('a');
      anchor.href = url;
      anchor.download = `mortgage-pack-index-${selectedMortgageType}-${new Date().toISOString().slice(0, 10)}.json`;
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      setMatrixError(err instanceof Error ? err.message : 'Unexpected error');
    } finally {
      setIsExportingPackJson(false);
    }
  };

  const handleExportPackIndexPdf = async () => {
    setMatrixError('');
    if (!selectedMortgageType || !selectedLenderProfile) {
      setMatrixError('Select mortgage and lender profile first.');
      return;
    }
    setIsExportingPackPdf(true);
    try {
      const response = await fetch(`${ANALYTICS_SERVICE_URL}/mortgage/pack-index.pdf`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(buildMortgagePayload()),
      });
      if (!response.ok) {
        const payload = (await response.json()) as { detail?: string };
        throw new Error(payload.detail || 'Failed to export pack PDF');
      }
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const anchor = document.createElement('a');
      anchor.href = url;
      anchor.download = `mortgage-pack-index-${selectedMortgageType}-${new Date().toISOString().slice(0, 10)}.pdf`;
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      setMatrixError(err instanceof Error ? err.message : 'Unexpected error');
    } finally {
      setIsExportingPackPdf(false);
    }
  };

  return (
    <div className={styles.pageContainer}>
      <h1>{t('nav.reports')}</h1>
      <p>{t('reports.description')}</p>
      <div className={styles.subContainer}>
        <h2>{t('reports.mortgage_title')}</h2>
        <p>{t('reports.mortgage_description')}</p>
        <button className={styles.button} disabled={isLoading} onClick={handleGenerateReport}>
          {isLoading ? t('reports.generating_button') : t('reports.generate_button')}
        </button>
        {error && <p className={styles.error}>{error}</p>}
      </div>

      <div className={styles.subContainer}>
        <h2>Mortgage affordability (illustrative)</h2>
        <p className={styles.tableCaption}>
          Planning tool only — not a mortgage offer or regulated advice. England SDLT is simplified; confirm with gov.uk.
        </p>
        <div className={styles.adminFiltersGrid}>
          <label className={styles.filterField}>
            <span>Annual income (£)</span>
            <input
              className={styles.categorySelect}
              type="text"
              inputMode="decimal"
              value={affordIncome}
              onChange={(e) => setAffordIncome(e.target.value)}
              placeholder="e.g. 52000"
            />
          </label>
          <label className={styles.filterField}>
            <span>Employment (for multiple)</span>
            <select
              className={styles.categorySelect}
              value={affordEmployment}
              onChange={(e) => setAffordEmployment(e.target.value as 'employed' | 'self_employed')}
            >
              <option value="self_employed">Self-employed (planning ~3–4×)</option>
              <option value="employed">Employed (planning ~4.5×)</option>
            </select>
          </label>
          <label className={styles.filterField}>
            <span>Property price (£, optional)</span>
            <input
              className={styles.categorySelect}
              type="text"
              inputMode="decimal"
              value={affordProperty}
              onChange={(e) => setAffordProperty(e.target.value)}
              placeholder="For LTV / SDLT / loan size"
            />
          </label>
          <label className={styles.filterField}>
            <span>Deposit (£, optional)</span>
            <input
              className={styles.categorySelect}
              type="text"
              inputMode="decimal"
              value={affordDeposit}
              onChange={(e) => setAffordDeposit(e.target.value)}
            />
          </label>
          <label className={styles.filterField}>
            <span>Interest rate % (nominal)</span>
            <input
              className={styles.categorySelect}
              type="text"
              inputMode="decimal"
              value={affordRate}
              onChange={(e) => setAffordRate(e.target.value)}
            />
          </label>
          <label className={styles.filterField}>
            <span>Term (years)</span>
            <input
              className={styles.categorySelect}
              type="text"
              inputMode="numeric"
              value={affordTerm}
              onChange={(e) => setAffordTerm(e.target.value)}
            />
          </label>
          <label className={styles.filterField}>
            <span>Credit (illustrative fit)</span>
            <select
              className={styles.categorySelect}
              value={affordCredit}
              onChange={(e) => setAffordCredit(e.target.value as 'clean' | 'minor' | 'adverse')}
            >
              <option value="clean">Clean</option>
              <option value="minor">Minor issues</option>
              <option value="adverse">Adverse / complex</option>
            </select>
          </label>
          <label className={styles.filterField}>
            <span>Years trading (optional)</span>
            <input
              className={styles.categorySelect}
              type="text"
              inputMode="numeric"
              value={affordYearsTrading}
              onChange={(e) => setAffordYearsTrading(e.target.value)}
              placeholder="e.g. 2"
            />
          </label>
          <label className={styles.filterField}>
            <span>SDLT / buyer</span>
            <label className={styles.checkboxPill}>
              <input checked={affordFtb} onChange={(e) => setAffordFtb(e.target.checked)} type="checkbox" />
              First-time buyer (England relief up to £625k)
            </label>
            <label className={styles.checkboxPill} style={{ marginTop: 8 }}>
              <input checked={affordAdditional} onChange={(e) => setAffordAdditional(e.target.checked)} type="checkbox" />
              Additional property (+3% illustrative surcharge)
            </label>
          </label>
        </div>
        <div className={styles.adminActionsRow}>
          <button className={styles.button} type="button" onClick={() => void fillIncomeFromTax()}>
            Fill income from tax estimate (2025/26)
          </button>
          <button className={styles.button} type="button" disabled={affordLoading} onClick={() => void runAffordability()}>
            {affordLoading ? 'Calculating…' : 'Calculate'}
          </button>
        </div>
        {affordError && <p className={styles.error}>{affordError}</p>}
        {affordResult && (
          <div className={styles.resultsContainer} style={{ marginTop: 16 }}>
            <p style={{ fontSize: '0.85rem', color: 'var(--lp-text-muted)' }}>{affordResult.disclaimer}</p>
            <ul style={{ fontSize: '0.9rem', lineHeight: 1.6 }}>
              <li>
                Max loan (baseline multiple {affordResult.baseline_income_multiple}×):{' '}
                <strong>£{formatNumber(affordResult.max_loan_from_income_gbp)}</strong>
              </li>
              {affordResult.max_loan_from_income_gbp_self_employed_range && (
                <li>
                  Self-employed range (illustrative): £{formatNumber(affordResult.max_loan_from_income_gbp_self_employed_range[0])} – £
                  {formatNumber(affordResult.max_loan_from_income_gbp_self_employed_range[1])} on same income
                </li>
              )}
              {affordResult.loan_amount_for_payment_gbp != null && (
                <li>
                  Loan used for payment calc: £{formatNumber(affordResult.loan_amount_for_payment_gbp)}
                  {affordResult.ltv_pct != null ? ` (LTV ${affordResult.ltv_pct}%)` : ''}
                </li>
              )}
              <li>
                Monthly payment: <strong>£{formatNumber(affordResult.monthly_payment_gbp)}</strong> at{' '}
                {affordResult.annual_interest_rate_pct}% over {affordResult.term_years} years
              </li>
              <li>
                If rate +{affordResult.stress_rate_add_pct_points}pp: <strong>£{formatNumber(affordResult.monthly_payment_if_rates_up_3pp_gbp)}</strong>/month
              </li>
              {affordResult.stamp_duty_england_gbp != null && (
                <li>Stamp duty (England, illustrative): £{formatNumber(affordResult.stamp_duty_england_gbp)}</li>
              )}
            </ul>
            <h4>Lender scenarios (sorted by illustrative fit — not approval %)</h4>
            <div style={{ overflowX: 'auto' }}>
              <table className={styles.table}>
                <thead>
                  <tr>
                    <th>Fit</th>
                    <th>Lender</th>
                    <th>Segment</th>
                    <th>× income</th>
                    <th>Max loan</th>
                    <th>Why</th>
                  </tr>
                </thead>
                <tbody>
                  {affordResult.lender_scenarios.map((row) => (
                    <tr key={row.id}>
                      <td>{row.illustrative_fit_score}</td>
                      <td>{row.label}</td>
                      <td style={{ fontSize: '0.82rem' }}>{row.segment}</td>
                      <td>{row.income_multiple}</td>
                      <td>£{formatNumber(row.max_loan_from_income_gbp)}</td>
                      <td style={{ fontSize: '0.8rem' }}>
                        {row.notes}
                        {row.illustrative_fit_reasons?.length ? (
                          <div style={{ marginTop: 4, color: 'var(--lp-text-muted)' }}>
                            {row.illustrative_fit_reasons.join(' ')}
                          </div>
                        ) : null}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>

      <div className={styles.subContainer}>
        <h2>Mortgage document checklist (England)</h2>
        <p>
          Select mortgage type and income profile to prepare the full document pack expected by lenders in England.
        </p>
        {isLoadingMortgageTypes || isLoadingLenderProfiles ? (
          <p>Loading mortgage types...</p>
        ) : (
          <>
            <div className={styles.adminFiltersGrid}>
              <label className={styles.filterField}>
                <span>Mortgage type</span>
                <select
                  className={styles.categorySelect}
                  onChange={(event) => setSelectedMortgageType(event.target.value)}
                  value={selectedMortgageType}
                >
                  {mortgageTypes.map((mortgageType) => (
                    <option key={mortgageType.code} value={mortgageType.code}>
                      {mortgageType.label}
                    </option>
                  ))}
                </select>
              </label>
              <label className={styles.filterField}>
                <span>Income profile</span>
                <select
                  className={styles.categorySelect}
                  onChange={(event) =>
                    setEmploymentProfile(event.target.value as (typeof EMPLOYMENT_PROFILE_OPTIONS)[number]['value'])
                  }
                  value={employmentProfile}
                >
                  {EMPLOYMENT_PROFILE_OPTIONS.map((profile) => (
                    <option key={profile.value} value={profile.value}>
                      {profile.label}
                    </option>
                  ))}
                </select>
              </label>
              <label className={styles.filterField}>
                <span>Lender profile</span>
                <select
                  className={styles.categorySelect}
                  onChange={(event) => setSelectedLenderProfile(event.target.value)}
                  value={selectedLenderProfile}
                >
                  {lenderProfiles.map((profile) => (
                    <option key={profile.code} value={profile.code}>
                      {profile.label}
                    </option>
                  ))}
                </select>
              </label>
              <label className={styles.filterField}>
                <span>Risk add-ons</span>
                <label className={styles.checkboxPill}>
                  <input
                    checked={includeAdverseCreditPack}
                    onChange={(event) => setIncludeAdverseCreditPack(event.target.checked)}
                    type="checkbox"
                  />
                  Include adverse credit pack
                </label>
              </label>
              <label className={styles.filterField}>
                <span>Submission gate</span>
                <label className={styles.checkboxPill}>
                  <input
                    checked={advisorReviewConfirmed}
                    onChange={(event) => setAdvisorReviewConfirmed(event.target.checked)}
                    type="checkbox"
                  />
                  Advisor review confirmed
                </label>
              </label>
            </div>
            {selectedMortgageTypeDescription && <p className={styles.tableCaption}>{selectedMortgageTypeDescription}</p>}
            {selectedLenderProfileDescription && <p className={styles.tableCaption}>{selectedLenderProfileDescription}</p>}
            <div className={styles.adminActionsRow}>
              <button className={styles.button} disabled={isLoadingChecklist} onClick={handleGenerateChecklist} type="button">
                {isLoadingChecklist ? 'Building checklist...' : 'Generate checklist'}
              </button>
              <button
                className={styles.button}
                disabled={isAssessingReadiness}
                onClick={handleAssessReadiness}
                type="button"
              >
                {isAssessingReadiness ? 'Assessing readiness...' : 'Assess readiness from uploaded docs'}
              </button>
              <button className={styles.button} disabled={isBuildingMatrix} onClick={handleBuildMatrix} type="button">
                {isBuildingMatrix ? 'Building matrix...' : 'Build all-types matrix'}
              </button>
              <button
                className={styles.button}
                disabled={isExportingPackJson}
                onClick={handleExportPackIndexJson}
                type="button"
              >
                {isExportingPackJson ? 'Exporting JSON...' : 'Export pack index JSON'}
              </button>
              <button
                className={styles.button}
                disabled={isExportingPackPdf}
                onClick={handleExportPackIndexPdf}
                type="button"
              >
                {isExportingPackPdf ? 'Exporting PDF...' : 'Export pack index PDF'}
              </button>
            </div>
            {checklistError && <p className={styles.error}>{checklistError}</p>}
            {readinessError && <p className={styles.error}>{readinessError}</p>}
            {matrixError && <p className={styles.error}>{matrixError}</p>}
            {checklist && (
              <div className={styles.resultsContainer}>
                <h3>
                  {checklist.mortgage_label} ({checklist.jurisdiction})
                </h3>
                <p>{checklist.mortgage_description}</p>
                <p className={styles.tableCaption}>Lender profile: {checklist.lender_profile_label}</p>
                <h4>Required documents</h4>
                <ul>
                  {checklist.required_documents.map((item) => (
                    <li key={item.code}>
                      <strong>{item.title}</strong> — {item.reason}
                    </li>
                  ))}
                </ul>
                <h4>Conditional / lender-specific documents</h4>
                <ul>
                  {checklist.conditional_documents.map((item) => (
                    <li key={item.code}>
                      <strong>{item.title}</strong> — {item.reason}
                    </li>
                  ))}
                </ul>
                <h4>Lender notes</h4>
                <ul>
                  {checklist.lender_notes.map((note, index) => (
                    <li key={index}>{note}</li>
                  ))}
                </ul>
                <h4>Next steps</h4>
                <ul>
                  {checklist.next_steps.map((step, index) => (
                    <li key={index}>{step}</li>
                  ))}
                </ul>
              </div>
            )}
            {readiness && (
              <div className={styles.resultsContainer}>
                <h3>Mortgage pack readiness</h3>
                <p className={styles.tableCaption}>Lender profile: {readiness.lender_profile_label}</p>
                <div className={styles.resultItemMain}>
                  <span>Status</span>
                  <strong>{readiness.readiness_status.replace(/_/g, ' ')}</strong>
                </div>
                <div className={styles.resultItem}>
                  <span>Required completion</span>
                  <span>{formatNumber(readiness.required_completion_percent, { maximumFractionDigits: 1, minimumFractionDigits: 1 })}%</span>
                </div>
                <div className={styles.resultItem}>
                  <span>Overall completion</span>
                  <span>{formatNumber(readiness.overall_completion_percent, { maximumFractionDigits: 1, minimumFractionDigits: 1 })}%</span>
                </div>
                <div className={styles.resultItem}>
                  <span>Uploaded documents detected</span>
                  <span>{readiness.uploaded_document_count}</span>
                </div>
                <div className={styles.resultItem}>
                  <span>Evidence quality issues (critical / warning / info)</span>
                  <span>
                    {readiness.evidence_quality_summary.critical_count} / {readiness.evidence_quality_summary.warning_count} /{' '}
                    {readiness.evidence_quality_summary.info_count}
                  </span>
                </div>
                <p>{readiness.readiness_summary}</p>
                {readiness.evidence_quality_summary.has_blockers && (
                  <p className={styles.error}>
                    Critical evidence-quality blockers detected. Resolve these before broker submission.
                  </p>
                )}
                <h4>Compliance and submission gate</h4>
                <p>{readiness.submission_gate.compliance_disclaimer}</p>
                <div className={styles.resultItem}>
                  <span>Advisor review confirmed</span>
                  <span>{readiness.submission_gate.advisor_review_confirmed ? 'Yes' : 'No'}</span>
                </div>
                <div className={styles.resultItem}>
                  <span>Broker submission allowed</span>
                  <strong>{readiness.submission_gate.broker_submission_allowed ? 'Yes' : 'No'}</strong>
                </div>
                {!readiness.submission_gate.broker_submission_allowed && (
                  <>
                    <p className={styles.tableCaption}>Submission blockers:</p>
                    <ul>
                      {readiness.submission_gate.broker_submission_blockers.map((blocker, index) => (
                        <li key={`${blocker}-${index}`}>{blocker}</li>
                      ))}
                    </ul>
                  </>
                )}
                <h4>Evidence quality alerts</h4>
                {readiness.evidence_quality_issues.length === 0 ? (
                  <p className={styles.emptyState}>No evidence-quality issues detected.</p>
                ) : (
                  <ul>
                    {readiness.evidence_quality_issues.slice(0, 8).map((issue, index) => (
                      <li key={`${issue.document_filename}-${issue.check_type}-${index}`}>
                        <strong>{issue.severity.toUpperCase()}</strong> — {issue.document_filename}: {issue.message}{' '}
                        <em>({issue.suggested_action})</em>
                      </li>
                    ))}
                  </ul>
                )}
                <h4>Monthly refresh reminders (statements and ID)</h4>
                <div className={styles.resultItem}>
                  <span>Due now / Upcoming</span>
                  <span>
                    {readiness.refresh_reminder_summary.due_now_count} / {readiness.refresh_reminder_summary.upcoming_count}
                  </span>
                </div>
                {readiness.refresh_reminder_summary.next_due_date && (
                  <p className={styles.tableCaption}>Next reminder due: {readiness.refresh_reminder_summary.next_due_date}</p>
                )}
                {readiness.refresh_reminders.length === 0 ? (
                  <p className={styles.emptyState}>No monthly refresh reminders yet.</p>
                ) : (
                  <ul>
                    {readiness.refresh_reminders.slice(0, 8).map((reminder, index) => (
                      <li key={`${reminder.document_code}-${reminder.document_filename}-${index}`}>
                        <strong>{reminder.status === 'due_now' ? 'DUE NOW' : 'UPCOMING'}</strong> — {reminder.title}
                        {' '}({reminder.document_filename}, due {reminder.due_date}): {reminder.message}{' '}
                        <em>({reminder.suggested_action})</em>
                      </li>
                    ))}
                  </ul>
                )}
                <h4>Missing required documents</h4>
                {readiness.missing_required_documents.length === 0 ? (
                  <p className={styles.emptyState}>All required documents detected.</p>
                ) : (
                  <ul>
                    {readiness.missing_required_documents.map((item) => (
                      <li key={item.code}>
                        <strong>{item.title}</strong> — {item.reason}
                      </li>
                    ))}
                  </ul>
                )}
                <h4>Immediate actions</h4>
                <ul>
                  {readiness.next_actions.map((action, index) => (
                    <li key={index}>{action}</li>
                  ))}
                </ul>
              </div>
            )}
            {readinessMatrix && (
              <div className={styles.resultsContainer}>
                <h3>All mortgage types readiness matrix</h3>
                <div className={styles.resultItem}>
                  <span>Overall status</span>
                  <strong>{readinessMatrix.overall_status.replace(/_/g, ' ')}</strong>
                </div>
                <div className={styles.resultItem}>
                  <span>Average required completion</span>
                  <span>
                    {formatNumber(readinessMatrix.average_required_completion_percent, {
                      maximumFractionDigits: 1,
                      minimumFractionDigits: 1,
                    })}
                    %
                  </span>
                </div>
                <div className={styles.resultItem}>
                  <span>Ready / Almost / Not ready</span>
                  <span>
                    {readinessMatrix.ready_for_broker_review_count} / {readinessMatrix.almost_ready_count} /{' '}
                    {readinessMatrix.not_ready_count}
                  </span>
                </div>
                <div className={styles.tableResponsive}>
                  <table className={styles.table}>
                    <thead>
                      <tr>
                        <th>Mortgage type</th>
                        <th>Required %</th>
                        <th>Overall %</th>
                        <th>Status</th>
                        <th>Missing required</th>
                      </tr>
                    </thead>
                    <tbody>
                      {readinessMatrix.items.map((item) => (
                        <tr key={item.mortgage_type}>
                          <td>{item.mortgage_label}</td>
                          <td>{formatNumber(item.required_completion_percent, { maximumFractionDigits: 1, minimumFractionDigits: 1 })}%</td>
                          <td>{formatNumber(item.overall_completion_percent, { maximumFractionDigits: 1, minimumFractionDigits: 1 })}%</td>
                          <td>{item.readiness_status.replace(/_/g, ' ')}</td>
                          <td>{item.missing_required_count}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}

