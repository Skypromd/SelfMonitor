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

type MortgageDocumentItem = {
  code: string;
  reason: string;
  title: string;
};

type MortgageChecklistResponse = {
  conditional_documents: MortgageDocumentItem[];
  employment_profile: string;
  jurisdiction: string;
  lender_notes: string[];
  mortgage_description: string;
  mortgage_label: string;
  mortgage_type: string;
  next_steps: string[];
  required_documents: MortgageDocumentItem[];
};

type MortgageReadinessResponse = MortgageChecklistResponse & {
  detected_document_codes: string[];
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
  const [isLoadingMortgageTypes, setIsLoadingMortgageTypes] = useState(true);
  const [mortgageTypes, setMortgageTypes] = useState<MortgageTypeSummary[]>([]);
  const [selectedMortgageType, setSelectedMortgageType] = useState('');
  const [employmentProfile, setEmploymentProfile] = useState<(typeof EMPLOYMENT_PROFILE_OPTIONS)[number]['value']>(
    'sole_trader'
  );
  const [includeAdverseCreditPack, setIncludeAdverseCreditPack] = useState(false);
  const [checklist, setChecklist] = useState<MortgageChecklistResponse | null>(null);
  const [readiness, setReadiness] = useState<MortgageReadinessResponse | null>(null);
  const [error, setError] = useState('');
  const [checklistError, setChecklistError] = useState('');
  const [readinessError, setReadinessError] = useState('');
  const { t } = useTranslation();

  useEffect(() => {
    const loadMortgageTypes = async () => {
      setIsLoadingMortgageTypes(true);
      try {
        const response = await fetch(`${ANALYTICS_SERVICE_URL}/mortgage/types`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (!response.ok) {
          throw new Error('Failed to load mortgage types');
        }
        const payload = (await response.json()) as MortgageTypeSummary[];
        setMortgageTypes(payload);
        if (payload.length > 0) {
          setSelectedMortgageType(payload[0].code);
        }
      } catch (err) {
        setChecklistError(err instanceof Error ? err.message : 'Unexpected error');
      } finally {
        setIsLoadingMortgageTypes(false);
      }
    };
    loadMortgageTypes();
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

  const handleGenerateChecklist = async () => {
    setChecklistError('');
    setReadinessError('');
    setChecklist(null);
    setReadiness(null);
    if (!selectedMortgageType) {
      setChecklistError('Please select a mortgage type first.');
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
        {isLoadingMortgageTypes ? (
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
            </div>
            {checklistError && <p className={styles.error}>{checklistError}</p>}
            {readinessError && <p className={styles.error}>{readinessError}</p>}
            {checklist && (
              <div className={styles.resultsContainer}>
                <h3>
                  {checklist.mortgage_label} ({checklist.jurisdiction})
                </h3>
                <p>{checklist.mortgage_description}</p>
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
                <p>{readiness.readiness_summary}</p>
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
          </>
        )}
      </div>
    </div>
  );
}
