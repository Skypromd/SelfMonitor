import Link from 'next/link';

export type MtdDraftLatest = {
  draft_id: string | null;
  workflow_status: string | null;
  expires_at: string | null;
  quarter: string | null;
  report_hash: string | null;
};

export function mtdWorkflowLabel(status: string | null | undefined): string {
  switch (status) {
    case 'draft':
      return 'Draft prepared';
    case 'ready_for_accountant_review':
      return 'With accountant';
    case 'accountant_reviewed':
      return 'Accountant reviewed';
    case 'ready_for_user_confirm':
      return 'Ready for your confirmation';
    case 'submitted':
      return 'Submitted to HMRC';
    default:
      return status || '—';
  }
}

const submissionLinkTaxPrep = { fontWeight: 600 as const, color: 'var(--accent-teal, #0d9488)' };

export function MtdTaxPrepSubmissionCta() {
  return (
    <p style={{ margin: '12px 0 0', fontSize: '0.82rem', color: 'var(--text-secondary)' }}>
      For guided confirm and HMRC steps, open{' '}
      <Link href="/submission" style={submissionLinkTaxPrep}>
        Submission
      </Link>
      .
    </p>
  );
}

export function MtdTaxPrepDraftCaption() {
  return (
    <div style={{ fontSize: '0.82rem', color: 'var(--text-secondary)', marginBottom: 8 }}>
      Quarterly draft is saved here; nothing is sent to HMRC until you confirm in{' '}
      <Link href="/submission" style={submissionLinkTaxPrep}>
        Submission
      </Link>
      .
    </div>
  );
}

export function MtdDraftWorkflowStrip({
  reportingRequired,
  mtdDraft,
}: {
  reportingRequired: boolean;
  mtdDraft: MtdDraftLatest | null;
}) {
  if (!reportingRequired) return null;
  return (
    <div
      style={{
        marginTop: '0.75rem',
        padding: '0.75rem 1rem',
        borderRadius: 10,
        background: 'rgba(99,102,241,0.08)',
        border: '1px solid rgba(99,102,241,0.25)',
        fontSize: '0.82rem',
        lineHeight: 1.55,
        color: 'var(--lp-muted)',
      }}
    >
      <strong style={{ color: 'var(--lp-text, #0f172a)' }}>Quarterly MTD draft</strong>
      <div style={{ marginTop: '0.35rem' }}>
        {mtdDraft?.draft_id && mtdDraft.workflow_status ? (
          <>
            <span
              style={{
                display: 'inline-block',
                marginRight: 8,
                padding: '2px 10px',
                borderRadius: 999,
                background: '#6366f1',
                color: '#fff',
                fontSize: '0.72rem',
                fontWeight: 600,
              }}
            >
              {mtdWorkflowLabel(mtdDraft.workflow_status)}
            </span>
            {mtdDraft.quarter ? <span style={{ marginRight: 8 }}>Quarter {mtdDraft.quarter}</span> : null}
            Update workflow in{' '}
            <Link href="/tax-preparation" style={{ color: 'var(--lp-accent-teal)', fontWeight: 600 }}>
              Tax preparation
            </Link>
            . Quarterly HMRC steps use this draft when your filing requires it.
          </>
        ) : (
          <>
            No draft saved yet. Align figures and optional accountant review in{' '}
            <Link href="/tax-preparation" style={{ color: 'var(--lp-accent-teal)', fontWeight: 600 }}>
              Tax preparation
            </Link>
            .
          </>
        )}
      </div>
    </div>
  );
}
