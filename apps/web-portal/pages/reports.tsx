import Link from 'next/link';
import { useEffect, useMemo, useState } from 'react';
import { useTranslation } from '../hooks/useTranslation';
import { formatApiError } from '../lib/apiError';
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
  credit_band_effective: string;
  property_type: string;
  ccj_in_past_6y: boolean;
  planner_notes: string[];
  deposit_pct_computed: number | null;
  disclaimer: string;
  illustrative_lenders_as_of: string;
  illustrative_lenders_pack_version: number;
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

type MortgageProgressStep = {
  detail: string;
  done: boolean;
  id: string;
  progress_ratio: number | null;
  status: 'completed' | 'current' | 'upcoming';
  title: string;
};

type MortgageProgressResponse = {
  current_step_id: string | null;
  disclaimer: string;
  estimated_months_to_deposit_goal: number | null;
  estimated_timeline_note: string | null;
  signals: Record<string, unknown>;
  steps: MortgageProgressStep[];
};

type MortgageMoneyPreviewMonthRow = {
  expenditure_gbp: number;
  income_gbp: number;
  month: string;
  net_gbp: number;
};

type MortgageMoneyPreviewTaxYearRow = {
  expenditure_gbp: number;
  income_gbp: number;
  net_profit_gbp: number;
  period_end: string | null;
  period_start: string | null;
  tax_year: string;
};

type MortgageMoneyPreviewResponse = {
  disclaimer: string;
  monthly_income_and_expenditure: MortgageMoneyPreviewMonthRow[];
  months_requested: number;
  tax_year_summaries: MortgageMoneyPreviewTaxYearRow[];
  window_end: string;
  window_start: string;
};

function csvEscapeCell(value: string): string {
  if (/[",\r\n]/.test(value)) {
    return `"${value.replace(/"/g, '""')}"`;
  }
  return value;
}

function buildMoneyPreviewCsv(data: MortgageMoneyPreviewResponse): string {
  const lines: string[] = [];
  lines.push(csvEscapeCell('Disclaimer') + ',' + csvEscapeCell(data.disclaimer));
  lines.push(`window_start,${csvEscapeCell(data.window_start)}`);
  lines.push(`window_end,${csvEscapeCell(data.window_end)}`);
  lines.push('');
  lines.push('month,income_gbp,expenditure_gbp,net_gbp');
  for (const r of data.monthly_income_and_expenditure) {
    lines.push([r.month, r.income_gbp, r.expenditure_gbp, r.net_gbp].join(','));
  }
  lines.push('');
  lines.push('tax_year,period_start,period_end,income_gbp,expenditure_gbp,net_profit_gbp');
  for (const r of data.tax_year_summaries) {
    lines.push(
      [
        csvEscapeCell(r.tax_year),
        r.period_start ?? '',
        r.period_end ?? '',
        r.income_gbp,
        r.expenditure_gbp,
        r.net_profit_gbp,
      ].join(',')
    );
  }
  return lines.join('\r\n');
}

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
  const [isDownloadingBrokerZip, setIsDownloadingBrokerZip] = useState(false);
  const [brokerBundleNino, setBrokerBundleNino] = useState('');
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
  const [affordPropertyType, setAffordPropertyType] = useState<
    'standard_residential' | 'buy_to_let' | 'leasehold_flat'
  >('standard_residential');
  const [affordCcjPast6y, setAffordCcjPast6y] = useState(false);
  const [affordYearsTrading, setAffordYearsTrading] = useState('');
  const [affordResult, setAffordResult] = useState<MortgageAffordabilityResponse | null>(null);
  const [affordLoading, setAffordLoading] = useState(false);
  const [affordError, setAffordError] = useState('');
  const [progDepositSaved, setProgDepositSaved] = useState('');
  const [progDepositTarget, setProgDepositTarget] = useState('');
  const [progMonthlySave, setProgMonthlySave] = useState('');
  const [progCredit, setProgCredit] = useState<'unknown' | 'ok' | 'building'>('unknown');
  const [progDebts, setProgDebts] = useState<'unknown' | 'managing' | 'reduce_first'>('unknown');
  const [progTaxFiled, setProgTaxFiled] = useState<boolean | ''>('');
  const [progReadiness, setProgReadiness] = useState('');
  const [progYears, setProgYears] = useState('');
  const [progLoading, setProgLoading] = useState(false);
  const [progResult, setProgResult] = useState<MortgageProgressResponse | null>(null);
  const [progError, setProgError] = useState('');
  const [moneyPreviewMonths, setMoneyPreviewMonths] = useState(12);
  const [moneyPreviewTaxYears, setMoneyPreviewTaxYears] = useState(3);
  const [moneyPreviewLoading, setMoneyPreviewLoading] = useState(false);
  const [moneyPreviewError, setMoneyPreviewError] = useState('');
  const [moneyPreviewResult, setMoneyPreviewResult] = useState<MortgageMoneyPreviewResponse | null>(null);
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
        setChecklistError(formatApiError(err, 'load mortgage data'));
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
          property_type: affordPropertyType,
          ccj_in_past_6y: affordCcjPast6y,
        }),
      });
      const payload = (await res.json()) as MortgageAffordabilityResponse | { detail?: string };
      if (!res.ok) {
        throw new Error('detail' in payload && payload.detail ? String(payload.detail) : 'Affordability request failed');
      }
      setAffordResult(payload as MortgageAffordabilityResponse);
    } catch (e) {
      setAffordError(formatApiError(e, 'calculate affordability'));
    } finally {
      setAffordLoading(false);
    }
  };

  const loadMortgageProgress = async () => {
    setProgError('');
    setProgResult(null);
    const ds = progDepositSaved.trim() ? parseFloat(progDepositSaved.replace(/,/g, '')) : NaN;
    const dt = progDepositTarget.trim() ? parseFloat(progDepositTarget.replace(/,/g, '')) : NaN;
    const ms = progMonthlySave.trim() ? parseFloat(progMonthlySave.replace(/,/g, '')) : NaN;
    const rd = progReadiness.trim() ? parseInt(progReadiness, 10) : NaN;
    const yr = progYears.trim() ? parseFloat(progYears.replace(/,/g, '')) : NaN;
    setProgLoading(true);
    try {
      const res = await fetch(`${ANALYTICS_SERVICE_URL}/mortgage/progress-tracker`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({
          credit_focus: progCredit,
          deposit_saved_gbp: !Number.isNaN(ds) && ds >= 0 ? ds : null,
          deposit_target_gbp: !Number.isNaN(dt) && dt > 0 ? dt : null,
          monthly_savings_gbp: !Number.isNaN(ms) && ms > 0 ? ms : null,
          debts_priority: progDebts,
          tax_return_filed: progTaxFiled === '' ? null : progTaxFiled,
          self_employed_years_override: !Number.isNaN(yr) && yr >= 0 ? yr : null,
          mortgage_readiness_percent: !Number.isNaN(rd) && rd >= 0 ? rd : null,
          include_backend_signals: true,
        }),
      });
      const payload = (await res.json()) as MortgageProgressResponse | { detail?: string };
      if (!res.ok) {
        throw new Error('detail' in payload && payload.detail ? String(payload.detail) : 'Progress request failed');
      }
      setProgResult(payload as MortgageProgressResponse);
    } catch (e) {
      setProgError(e instanceof Error ? e.message : 'Unexpected error');
    } finally {
      setProgLoading(false);
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

  const handleDownloadBrokerBundleZip = async () => {
    setMatrixError('');
    if (!selectedMortgageType || !selectedLenderProfile) {
      setMatrixError('Select mortgage and lender profile first.');
      return;
    }
    setIsDownloadingBrokerZip(true);
    try {
      const months = Math.min(36, Math.max(1, Math.floor(Number(moneyPreviewMonths)) || 12));
      const taxYears = Math.min(6, Math.max(1, Math.floor(Number(moneyPreviewTaxYears)) || 3));
      const params = new URLSearchParams({
        months: String(months),
        tax_years: String(taxYears),
        statement_days: '180',
        include_bank_statement_csv: 'true',
      });
      const ninoCompact = brokerBundleNino.replace(/\s/g, '').toUpperCase();
      if (ninoCompact.length === 9) {
        params.set('include_hmrc_individual_calculation', 'true');
        params.set('hmrc_nino', ninoCompact);
      }
      const response = await fetch(
        `${ANALYTICS_SERVICE_URL}/mortgage/broker-bundle.zip?${params.toString()}`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify(buildMortgagePayload()),
        }
      );
      if (!response.ok) {
        const errBody = await response.json().catch(() => ({}));
        throw new Error(
          typeof (errBody as { detail?: string }).detail === 'string'
            ? (errBody as { detail: string }).detail
            : 'Failed to download broker bundle'
        );
      }
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const anchor = document.createElement('a');
      anchor.href = url;
      anchor.download = `broker-bundle-${selectedMortgageType}-${new Date().toISOString().slice(0, 10)}.zip`;
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      setMatrixError(err instanceof Error ? err.message : 'Unexpected error');
    } finally {
      setIsDownloadingBrokerZip(false);
    }
  };

  const handleLoadMoneyPreview = async () => {
    setMoneyPreviewError('');
    setMoneyPreviewLoading(true);
    try {
      const months = Math.min(36, Math.max(1, Math.floor(Number(moneyPreviewMonths)) || 12));
      const taxYears = Math.min(6, Math.max(1, Math.floor(Number(moneyPreviewTaxYears)) || 3));
      const params = new URLSearchParams({
        months: String(months),
        tax_years: String(taxYears),
      });
      const response = await fetch(`${ANALYTICS_SERVICE_URL}/mortgage/money-preview?${params.toString()}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      const payload = (await response.json()) as MortgageMoneyPreviewResponse | { detail?: string };
      if (!response.ok) {
        throw new Error('detail' in payload && payload.detail ? payload.detail : 'Failed to load money preview');
      }
      setMoneyPreviewResult(payload as MortgageMoneyPreviewResponse);
    } catch (err) {
      setMoneyPreviewResult(null);
      setMoneyPreviewError(err instanceof Error ? err.message : 'Unexpected error');
    } finally {
      setMoneyPreviewLoading(false);
    }
  };

  const handleDownloadMoneyPreviewJson = () => {
    if (!moneyPreviewResult) {
      return;
    }
    const jsonBlob = new Blob([JSON.stringify(moneyPreviewResult, null, 2)], { type: 'application/json' });
    const url = window.URL.createObjectURL(jsonBlob);
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = `mortgage-money-preview-${new Date().toISOString().slice(0, 10)}.json`;
    document.body.appendChild(anchor);
    anchor.click();
    anchor.remove();
    window.URL.revokeObjectURL(url);
  };

  const handleDownloadMoneyPreviewCsv = () => {
    if (!moneyPreviewResult) {
      return;
    }
    const csv = buildMoneyPreviewCsv(moneyPreviewResult);
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8' });
    const url = window.URL.createObjectURL(blob);
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = `mortgage-money-preview-${new Date().toISOString().slice(0, 10)}.csv`;
    document.body.appendChild(anchor);
    anchor.click();
    anchor.remove();
    window.URL.revokeObjectURL(url);
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
            <span>Property type (illustrative fit)</span>
            <select
              className={styles.categorySelect}
              value={affordPropertyType}
              onChange={(e) =>
                setAffordPropertyType(e.target.value as typeof affordPropertyType)
              }
            >
              <option value="standard_residential">House / standard residential</option>
              <option value="leasehold_flat">Leasehold flat</option>
              <option value="buy_to_let">Buy-to-let</option>
            </select>
          </label>
          <label className={styles.filterField}>
            <span>Credit file (self-reported)</span>
            <label className={styles.checkboxPill}>
              <input checked={affordCcjPast6y} onChange={(e) => setAffordCcjPast6y(e.target.checked)} type="checkbox" />
              CCJ in past 6 years (tilts illustrative fit when your credit selection is clean)
            </label>
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
            <p style={{ fontSize: '0.8rem', color: 'var(--lp-text-muted)', marginTop: '0.35rem' }}>
              Illustrative lender pack as of {affordResult.illustrative_lenders_as_of} (v{affordResult.illustrative_lenders_pack_version}).
            </p>
            {affordResult.credit_band_effective && affordResult.credit_band_effective !== affordResult.credit_band && (
              <p style={{ fontSize: '0.82rem', marginTop: 8 }}>
                Illustrative credit band used for lender ordering: <strong>{affordResult.credit_band_effective}</strong>{' '}
                (you selected {affordResult.credit_band}
                {affordResult.ccj_in_past_6y ? '; CCJ in past 6y' : ''}).
              </p>
            )}
            {Array.isArray(affordResult.planner_notes) && affordResult.planner_notes.length > 0 && (
              <ul style={{ fontSize: '0.82rem', marginTop: 8, color: 'var(--lp-text-muted)' }}>
                {affordResult.planner_notes.map((n, i) => (
                  <li key={i}>{n}</li>
                ))}
              </ul>
            )}
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
        <h2>Road to mortgage (tracker)</h2>
        <p className={styles.tableCaption}>
          Informational steps only — not a lender timeline. Backend can enrich months of bank data and document count when you refresh.
        </p>
        <p className={styles.tableCaption} style={{ marginTop: 0 }}>
          <Link href="/assistant?mode=mortgage">Open AI assistant in mortgage mode</Link> for UK self-employed context
          (informational, not regulated advice).
        </p>
        <div className={styles.adminFiltersGrid}>
          <label className={styles.filterField}>
            <span>Deposit saved (£)</span>
            <input
              className={styles.categorySelect}
              type="text"
              inputMode="decimal"
              value={progDepositSaved}
              onChange={(e) => setProgDepositSaved(e.target.value)}
            />
          </label>
          <label className={styles.filterField}>
            <span>Deposit target (£)</span>
            <input
              className={styles.categorySelect}
              type="text"
              inputMode="decimal"
              value={progDepositTarget}
              onChange={(e) => setProgDepositTarget(e.target.value)}
            />
          </label>
          <label className={styles.filterField}>
            <span>Monthly savings (£)</span>
            <input
              className={styles.categorySelect}
              type="text"
              inputMode="decimal"
              value={progMonthlySave}
              onChange={(e) => setProgMonthlySave(e.target.value)}
              placeholder="For ETA to deposit goal"
            />
          </label>
          <label className={styles.filterField}>
            <span>Credit (self-report)</span>
            <select
              className={styles.categorySelect}
              value={progCredit}
              onChange={(e) => setProgCredit(e.target.value as 'unknown' | 'ok' | 'building')}
            >
              <option value="unknown">Unknown</option>
              <option value="ok">On track</option>
              <option value="building">Actively building / repairing</option>
            </select>
          </label>
          <label className={styles.filterField}>
            <span>Debts</span>
            <select
              className={styles.categorySelect}
              value={progDebts}
              onChange={(e) => setProgDebts(e.target.value as 'unknown' | 'managing' | 'reduce_first')}
            >
              <option value="unknown">Unknown</option>
              <option value="managing">Managing</option>
              <option value="reduce_first">Reduce before mortgage</option>
            </select>
          </label>
          <label className={styles.filterField}>
            <span>Tax return filed?</span>
            <select
              className={styles.categorySelect}
              value={progTaxFiled === '' ? '' : progTaxFiled ? 'yes' : 'no'}
              onChange={(e) => {
                const v = e.target.value;
                setProgTaxFiled(v === '' ? '' : v === 'yes');
              }}
            >
              <option value="">Not specified</option>
              <option value="yes">Yes</option>
              <option value="no">No</option>
            </select>
          </label>
          <label className={styles.filterField}>
            <span>Years trading (override)</span>
            <input
              className={styles.categorySelect}
              type="text"
              inputMode="decimal"
              value={progYears}
              onChange={(e) => setProgYears(e.target.value)}
              placeholder="Optional if bank history loaded"
            />
          </label>
          <label className={styles.filterField}>
            <span>Pack readiness %</span>
            <input
              className={styles.categorySelect}
              type="text"
              inputMode="numeric"
              value={progReadiness}
              onChange={(e) => setProgReadiness(e.target.value)}
              placeholder="From Assess readiness below"
            />
          </label>
        </div>
        <div className={styles.adminActionsRow}>
          {readiness != null && (
            <button
              type="button"
              className={styles.button}
              onClick={() => setProgReadiness(String(readiness.overall_completion_percent))}
            >
              Use last readiness %
            </button>
          )}
          <button type="button" className={styles.button} disabled={progLoading} onClick={() => void loadMortgageProgress()}>
            {progLoading ? 'Loading…' : 'Refresh progress'}
          </button>
        </div>
        {progError && <p className={styles.error}>{progError}</p>}
        {progResult && (
          <div className={styles.resultsContainer} style={{ marginTop: 16 }}>
            <p style={{ fontSize: '0.85rem', color: 'var(--lp-text-muted)' }}>{progResult.disclaimer}</p>
            {progResult.estimated_timeline_note && (
              <p style={{ fontSize: '0.9rem', marginBottom: 12 }}>{progResult.estimated_timeline_note}</p>
            )}
            <p style={{ fontSize: '0.82rem', color: 'var(--lp-text-muted)' }}>
              Signals: bank history ~{String(progResult.signals.months_bank_history ?? '—')} months, docs{' '}
              {String(progResult.signals.document_count ?? '—')}, readiness {String(progResult.signals.mortgage_readiness_percent ?? '—')}
              %.
            </p>
            <ol style={{ margin: '12px 0 0 0', paddingLeft: 20, lineHeight: 1.65 }}>
              {progResult.steps.map((s) => (
                <li key={s.id} style={{ marginBottom: 10 }}>
                  <strong>
                    [{s.status}] {s.title}
                  </strong>
                  {s.progress_ratio != null ? (
                    <span style={{ marginLeft: 8, fontSize: '0.85rem' }}>
                      ({Math.round(s.progress_ratio * 100)}% of deposit goal)
                    </span>
                  ) : null}
                  <div style={{ fontSize: '0.88rem', color: 'var(--lp-text-muted)' }}>{s.detail}</div>
                </li>
              ))}
            </ol>
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
              <button
                className={styles.button}
                disabled={isDownloadingBrokerZip}
                onClick={handleDownloadBrokerBundleZip}
                type="button"
              >
                {isDownloadingBrokerZip ? 'Building ZIP...' : 'Download broker starter bundle (ZIP)'}
              </button>
            </div>
            <div className={styles.adminFiltersGrid} style={{ marginTop: 10 }}>
              <label className={styles.filterField}>
                <span>HMRC NINO (optional — adds Individual Calculation JSON to the ZIP)</span>
                <input
                  className={styles.categorySelect}
                  maxLength={14}
                  onChange={(e) => setBrokerBundleNino(e.target.value)}
                  placeholder="9 characters, e.g. QQ123456C"
                  type="text"
                  value={brokerBundleNino}
                />
              </label>
            </div>
            <p className={styles.tableCaption} style={{ marginTop: 6, marginBottom: 0 }}>
              Every broker ZIP includes <code>hmrc-official-tax-evidence-steps.txt</code> with steps to obtain official
              HMRC PDFs (not generated by MyNetTax). Quick links:{' '}
              <a href="https://www.gov.uk/personal-tax-account" rel="noopener noreferrer" target="_blank">
                Personal Tax Account
              </a>
              {' · '}
              <a href="https://www.gov.uk/sa302-tax-calculation" rel="noopener noreferrer" target="_blank">
                SA302 / tax calculation
              </a>
              . Upload saved PDFs on the <Link href="/documents">Documents</Link> page so they count toward your mortgage pack checklist.
            </p>
            <div style={{ marginTop: 20 }}>
              <h3 style={{ margin: '0 0 8px 0' }}>Linked bank money preview</h3>
              <p className={styles.tableCaption} style={{ marginBottom: 12 }}>
                Illustrative monthly income and expenditure plus UK tax-year rollups from linked bank transactions
                (analytics-service). Not statutory accounts or HMRC figures; confirm requirements with your broker.
              </p>
              <div className={styles.adminFiltersGrid}>
                <label className={styles.filterField}>
                  <span>Lookback months (1–36)</span>
                  <input
                    className={styles.categorySelect}
                    max={36}
                    min={1}
                    onChange={(e) => setMoneyPreviewMonths(Number(e.target.value))}
                    type="number"
                    value={moneyPreviewMonths}
                  />
                </label>
                <label className={styles.filterField}>
                  <span>Tax years (1–6)</span>
                  <input
                    className={styles.categorySelect}
                    max={6}
                    min={1}
                    onChange={(e) => setMoneyPreviewTaxYears(Number(e.target.value))}
                    type="number"
                    value={moneyPreviewTaxYears}
                  />
                </label>
              </div>
              <div className={styles.adminActionsRow}>
                <button className={styles.button} disabled={moneyPreviewLoading} onClick={handleLoadMoneyPreview} type="button">
                  {moneyPreviewLoading ? 'Loading preview...' : 'Load money preview'}
                </button>
                <button
                  className={styles.button}
                  disabled={!moneyPreviewResult}
                  onClick={handleDownloadMoneyPreviewJson}
                  type="button"
                >
                  Download preview JSON
                </button>
                <button
                  className={styles.button}
                  disabled={!moneyPreviewResult}
                  onClick={handleDownloadMoneyPreviewCsv}
                  type="button"
                >
                  Download preview CSV
                </button>
              </div>
              {moneyPreviewError && <p className={styles.error}>{moneyPreviewError}</p>}
              {moneyPreviewResult ? (
                <div className={styles.resultsContainer} style={{ marginTop: 16 }}>
                  <p className={styles.tableCaption}>{moneyPreviewResult.disclaimer}</p>
                  <p className={styles.tableCaption}>
                    Window {moneyPreviewResult.window_start} → {moneyPreviewResult.window_end} (months requested:{' '}
                    {moneyPreviewResult.months_requested})
                  </p>
                  <h4 style={{ marginTop: 16 }}>Monthly income and expenditure</h4>
                  {moneyPreviewResult.monthly_income_and_expenditure.length === 0 ? (
                    <p className={styles.tableCaption}>No transactions in this window.</p>
                  ) : (
                    <div className={styles.tableResponsive}>
                      <table className={styles.table}>
                        <thead>
                          <tr>
                            <th>Month</th>
                            <th>Income (GBP)</th>
                            <th>Expenditure (GBP)</th>
                            <th>Net (GBP)</th>
                          </tr>
                        </thead>
                        <tbody>
                          {moneyPreviewResult.monthly_income_and_expenditure.map((row) => (
                            <tr key={row.month}>
                              <td>{row.month}</td>
                              <td>{formatNumber(row.income_gbp, { maximumFractionDigits: 2, minimumFractionDigits: 2 })}</td>
                              <td>{formatNumber(row.expenditure_gbp, { maximumFractionDigits: 2, minimumFractionDigits: 2 })}</td>
                              <td>{formatNumber(row.net_gbp, { maximumFractionDigits: 2, minimumFractionDigits: 2 })}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                  <h4 style={{ marginTop: 16 }}>UK tax year summaries</h4>
                  {moneyPreviewResult.tax_year_summaries.length === 0 ? (
                    <p className={styles.tableCaption}>No tax-year aggregates yet.</p>
                  ) : (
                    <div className={styles.tableResponsive}>
                      <table className={styles.table}>
                        <thead>
                          <tr>
                            <th>Tax year</th>
                            <th>Period</th>
                            <th>Income (GBP)</th>
                            <th>Expenditure (GBP)</th>
                            <th>Net profit (GBP)</th>
                          </tr>
                        </thead>
                        <tbody>
                          {moneyPreviewResult.tax_year_summaries.map((row) => (
                            <tr key={row.tax_year}>
                              <td>{row.tax_year}</td>
                              <td>
                                {row.period_start && row.period_end
                                  ? `${row.period_start} → ${row.period_end}`
                                  : '—'}
                              </td>
                              <td>{formatNumber(row.income_gbp, { maximumFractionDigits: 2, minimumFractionDigits: 2 })}</td>
                              <td>{formatNumber(row.expenditure_gbp, { maximumFractionDigits: 2, minimumFractionDigits: 2 })}</td>
                              <td>{formatNumber(row.net_profit_gbp, { maximumFractionDigits: 2, minimumFractionDigits: 2 })}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                </div>
              ) : null}
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

