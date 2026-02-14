import { useEffect, useMemo, useState } from 'react';
import { useTranslation } from '../hooks/useTranslation';
import styles from '../styles/Home.module.css';

const ANALYTICS_SERVICE_URL = process.env.NEXT_PUBLIC_ANALYTICS_SERVICE_URL || 'http://localhost:8011';

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
  required_completion_percent: number;
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
  const [checklist, setChecklist] = useState<MortgageChecklistResponse | null>(null);
  const [readiness, setReadiness] = useState<MortgageReadinessResponse | null>(null);
  const [readinessMatrix, setReadinessMatrix] = useState<MortgageReadinessMatrixResponse | null>(null);
  const [error, setError] = useState('');
  const [checklistError, setChecklistError] = useState('');
  const [readinessError, setReadinessError] = useState('');
  const [matrixError, setMatrixError] = useState('');
  const { t } = useTranslation();

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
    <div className={styles.dashboard}>
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
                  <span>{readiness.required_completion_percent.toFixed(1)}%</span>
                </div>
                <div className={styles.resultItem}>
                  <span>Overall completion</span>
                  <span>{readiness.overall_completion_percent.toFixed(1)}%</span>
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
                  <span>{readinessMatrix.average_required_completion_percent.toFixed(1)}%</span>
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
                          <td>{item.required_completion_percent.toFixed(1)}%</td>
                          <td>{item.overall_completion_percent.toFixed(1)}%</td>
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
