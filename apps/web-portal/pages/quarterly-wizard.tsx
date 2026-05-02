/**
 * 7-Minute Quarterly Wizard
 * Guides the user through 6 steps to get HMRC-ready in under 7 minutes.
 * Progress is persisted to localStorage so the user can resume later.
 */

import Link from 'next/link';
import { useRouter } from 'next/router';
import { useEffect, useState } from 'react';
import styles from '../styles/Home.module.css';

const BANKING_SERVICE_URL = (process.env.NEXT_PUBLIC_BANKING_SERVICE_URL || '/api/banking').replace(/\/$/, '');
const TXN_SERVICE_URL = (process.env.NEXT_PUBLIC_TRANSACTIONS_SERVICE_URL || '/api/transactions').replace(/\/$/, '');
const TAX_SERVICE_URL = (process.env.NEXT_PUBLIC_TAX_ENGINE_URL || '/api/tax').replace(/\/$/, '');
const INTEGRATIONS_API = (process.env.NEXT_PUBLIC_INTEGRATIONS_SERVICE_URL || '/api/integrations').replace(/\/$/, '');

const STORAGE_KEY = 'quarterly-wizard-progress';

type StepId = 'sync' | 'inbox' | 'receipts_cis' | 'preview' | 'confirm' | 'submit';

interface WizardStep {
  id: StepId;
  title: string;
  subtitle: string;
  estimatedMinutes: number;
  icon: string;
  actionLabel: string;
  actionHref?: string;
}

const STEPS: WizardStep[] = [
  {
    id: 'sync',
    title: 'Sync Your Bank',
    subtitle: 'Import the latest transactions from your connected bank account.',
    estimatedMinutes: 1,
    icon: '🏦',
    actionLabel: 'Go to Bank Connections →',
    actionHref: '/connect-bank',
  },
  {
    id: 'inbox',
    title: 'Fix Inbox Blockers',
    subtitle: 'Categorise uncategorised transactions and clear Inbox Zero blockers.',
    estimatedMinutes: 2,
    icon: '📥',
    actionLabel: 'Open Transaction Inbox →',
    actionHref: '/transactions?filter=uncategorised',
  },
  {
    id: 'receipts_cis',
    title: 'Review Receipts & CIS',
    subtitle: 'Match missing receipts and verify CIS income from your contractors.',
    estimatedMinutes: 2,
    icon: '🧾',
    actionLabel: 'Review No-Receipt Transactions →',
    actionHref: '/transactions?filter=no_receipt',
  },
  {
    id: 'preview',
    title: 'Preview Quarterly Update',
    subtitle: 'See your tax figures for the quarter and check your tax reserve.',
    estimatedMinutes: 1,
    icon: '📊',
    actionLabel: 'Open Tax Preparation →',
    actionHref: '/tax-preparation',
  },
  {
    id: 'confirm',
    title: 'Confirm',
    subtitle: 'Review the final preview and tick the "true and complete" acknowledgement.',
    estimatedMinutes: 1,
    icon: '✅',
    actionLabel: 'Go to Export / Download →',
    actionHref: '/submission',
  },
  {
    id: 'submit',
    title: 'Submit or Save Guided Package',
    subtitle: 'Submit directly to HMRC or save your guided evidence pack for your accountant.',
    estimatedMinutes: 1,
    icon: '🚀',
    actionLabel: 'Submit to HMRC →',
    actionHref: '/submission',
  },
];

type Props = { token: string };

interface StepBlockers {
  sync: string[];
  inbox: string[];
  receipts_cis: string[];
  preview: string[];
  confirm: string[];
  submit: string[];
}

function loadProgress(): Set<StepId> {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return new Set();
    const arr = JSON.parse(raw) as StepId[];
    return new Set(arr);
  } catch {
    return new Set();
  }
}

function saveProgress(completed: Set<StepId>) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify([...completed]));
  } catch { /* ignore */ }
}

export default function QuarterlyWizardPage({ token }: Props) {
  const router = useRouter();
  const [completedSteps, setCompletedSteps] = useState<Set<StepId>>(new Set());
  const [activeStep, setActiveStep] = useState<StepId>('sync');
  const [blockers, setBlockers] = useState<StepBlockers>({
    sync: [], inbox: [], receipts_cis: [], preview: [], confirm: [], submit: [],
  });
  const [blockersLoading, setBlockersLoading] = useState(true);
  const [submitRef, setSubmitRef] = useState<string | null>(null);
  const [celebrating, setCelebrating] = useState(false);

  // Load saved progress from localStorage
  useEffect(() => {
    const saved = loadProgress();
    setCompletedSteps(saved);
    // Set active step to the first incomplete one
    const first = STEPS.find((s) => !saved.has(s.id));
    if (first) setActiveStep(first.id);
    else setActiveStep('submit');
  }, []);

  // Fetch real-time blockers for each step
  useEffect(() => {
    let cancelled = false;
    const headers = { Authorization: `Bearer ${token}` };

    void (async () => {
      setBlockersLoading(true);
      try {
        const [syncRes, uncatRes, noReceiptRes, cisRes] = await Promise.allSettled([
          fetch(`${BANKING_SERVICE_URL}/connections/sync-quota`, { headers }),
          fetch(`${TXN_SERVICE_URL}/transactions?limit=1&filter=uncategorised`, { headers }),
          fetch(`${TXN_SERVICE_URL}/transactions?limit=1&filter=no_receipt`, { headers }),
          fetch(`${TXN_SERVICE_URL}/cis/tasks?status=open&limit=1`, { headers }),
        ]);

        if (cancelled) return;

        const newBlockers: StepBlockers = { sync: [], inbox: [], receipts_cis: [], preview: [], confirm: [], submit: [] };

        if (syncRes.status === 'fulfilled' && syncRes.value.ok) {
          const d = await syncRes.value.json() as { remaining?: number; daily_limit?: number };
          if (typeof d.remaining === 'number' && d.remaining === 0) {
            newBlockers.sync.push('Daily sync limit reached — try again tomorrow (UTC).');
          }
        } else {
          newBlockers.sync.push('Bank not connected — connect to import transactions.');
        }

        if (uncatRes.status === 'fulfilled' && uncatRes.value.ok) {
          const d = await uncatRes.value.json() as unknown[] | { items?: unknown[]; total?: number };
          const count = Array.isArray(d) ? d.length : (d.total ?? 0);
          if (count > 0) newBlockers.inbox.push(`${count}+ uncategorised transaction${count !== 1 ? 's' : ''} need review.`);
        }

        if (noReceiptRes.status === 'fulfilled' && noReceiptRes.value.ok) {
          const d = await noReceiptRes.value.json() as unknown[] | { items?: unknown[]; total?: number };
          const count = Array.isArray(d) ? d.length : (d.total ?? 0);
          if (count > 0) newBlockers.receipts_cis.push(`${count}+ transaction${count !== 1 ? 's' : ''} missing receipts.`);
        }

        if (cisRes.status === 'fulfilled' && cisRes.value.ok) {
          const d = await cisRes.value.json() as unknown[] | { items?: unknown[]; total?: number };
          const count = Array.isArray(d) ? d.length : (d.total ?? 0);
          if (count > 0) newBlockers.receipts_cis.push(`${count} open CIS review task${count !== 1 ? 's' : ''}.`);
        }

        setBlockers(newBlockers);
      } finally {
        if (!cancelled) setBlockersLoading(false);
      }
    })();

    return () => { cancelled = true; };
  }, [token]);

  const markComplete = (stepId: StepId) => {
    setCompletedSteps((prev) => {
      const next = new Set(prev);
      next.add(stepId);
      saveProgress(next);
      // Auto-advance to next step
      const idx = STEPS.findIndex((s) => s.id === stepId);
      if (idx < STEPS.length - 1) setActiveStep(STEPS[idx + 1].id);
      return next;
    });
  };

  const allDone = STEPS.every((s) => completedSteps.has(s.id));

  const handleFinish = () => {
    setCelebrating(true);
    setSubmitRef(`QW-${Date.now().toString(36).toUpperCase()}`);
  };

  const handleReset = () => {
    localStorage.removeItem(STORAGE_KEY);
    setCompletedSteps(new Set());
    setActiveStep('sync');
    setCelebrating(false);
    setSubmitRef(null);
  };

  const totalMinutes = STEPS.reduce((sum, s) => sum + s.estimatedMinutes, 0);
  const remainingMinutes = STEPS.filter((s) => !completedSteps.has(s.id)).reduce((sum, s) => sum + s.estimatedMinutes, 0);

  if (celebrating && submitRef) {
    return (
      <div className={styles.pageContainer}>
        <div style={{ maxWidth: 560, margin: '3rem auto', textAlign: 'center' }}>
          <div style={{ fontSize: '3.5rem', marginBottom: '1rem' }}>🎉</div>
          <h1 style={{ marginBottom: '0.5rem' }}>Quarter Complete!</h1>
          <p style={{ color: 'var(--lp-muted)', fontSize: '0.95rem', marginBottom: '1.5rem' }}>
            You have finished all 6 steps. Your guided package is ready.
          </p>
          <div style={{ padding: '1rem 1.5rem', background: 'rgba(13,148,136,0.1)', border: '1px solid rgba(13,148,136,0.3)', borderRadius: 12, marginBottom: '1.5rem' }}>
            <div style={{ fontSize: '0.78rem', color: 'var(--lp-muted)', marginBottom: 4 }}>Reference</div>
            <div style={{ fontFamily: 'monospace', fontWeight: 700, fontSize: '1.1rem', color: 'var(--lp-accent-teal)' }}>{submitRef}</div>
          </div>
          <div style={{ display: 'flex', gap: '0.75rem', justifyContent: 'center', flexWrap: 'wrap' }}>
            <Link href="/submission" style={{ padding: '0.65rem 1.4rem', borderRadius: 10, background: 'var(--lp-accent-teal)', color: '#fff', fontWeight: 700, fontSize: '0.9rem', textDecoration: 'none' }}>
              Submit to HMRC →
            </Link>
            <button type="button" onClick={handleReset}
              style={{ padding: '0.65rem 1.4rem', borderRadius: 10, border: '1px solid var(--lp-border)', background: 'transparent', color: 'var(--lp-muted)', fontWeight: 600, fontSize: '0.9rem', cursor: 'pointer' }}>
              Start next quarter
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className={styles.pageContainer}>
      <div style={{ maxWidth: 720, margin: '0 auto' }}>
        {/* Header */}
        <div style={{ marginBottom: '1.5rem' }}>
          <h1 style={{ margin: 0, fontSize: '1.5rem' }}>⚡ 7-Minute Quarterly Wizard</h1>
          <p style={{ color: 'var(--lp-muted)', margin: '0.35rem 0 0', fontSize: '0.9rem' }}>
            {allDone
              ? 'All steps complete — you\'re HMRC-ready!'
              : `~${remainingMinutes} min remaining of ~${totalMinutes} min total`}
          </p>
        </div>

        {/* Progress bar */}
        <div style={{ height: 6, background: 'var(--lp-border)', borderRadius: 99, marginBottom: '1.5rem', overflow: 'hidden' }}>
          <div style={{
            height: '100%',
            width: `${(completedSteps.size / STEPS.length) * 100}%`,
            background: 'var(--lp-accent-teal)',
            borderRadius: 99,
            transition: 'width 0.35s ease',
          }} />
        </div>

        {/* Steps */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
          {STEPS.map((step, idx) => {
            const isCompleted = completedSteps.has(step.id);
            const isActive = activeStep === step.id;
            const stepBlockers = blockers[step.id];
            const hasBlockers = stepBlockers.length > 0;

            return (
              <div
                key={step.id}
                style={{
                  border: `1px solid ${isActive ? 'var(--lp-accent-teal)' : isCompleted ? 'rgba(16,185,129,0.35)' : 'var(--lp-border)'}`,
                  borderRadius: 14,
                  background: isActive
                    ? 'rgba(13,148,136,0.05)'
                    : isCompleted
                    ? 'rgba(16,185,129,0.04)'
                    : 'var(--lp-bg-elevated)',
                  overflow: 'hidden',
                  transition: 'border-color 0.2s',
                }}
              >
                {/* Step header — always visible */}
                <button
                  type="button"
                  onClick={() => setActiveStep(step.id)}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '0.85rem',
                    width: '100%',
                    padding: '0.9rem 1.1rem',
                    background: 'transparent',
                    border: 'none',
                    cursor: 'pointer',
                    textAlign: 'left',
                  }}
                >
                  {/* Step number / checkmark */}
                  <div style={{
                    width: 32, height: 32, flexShrink: 0, borderRadius: '50%',
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    fontSize: '0.82rem', fontWeight: 700,
                    background: isCompleted ? 'rgba(16,185,129,0.15)' : isActive ? 'rgba(13,148,136,0.12)' : 'rgba(100,116,139,0.1)',
                    color: isCompleted ? '#10b981' : isActive ? 'var(--lp-accent-teal)' : 'var(--lp-muted)',
                    border: `1px solid ${isCompleted ? 'rgba(16,185,129,0.4)' : isActive ? 'rgba(13,148,136,0.4)' : 'var(--lp-border)'}`,
                  }}>
                    {isCompleted ? '✓' : idx + 1}
                  </div>

                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap' }}>
                      <span style={{ fontSize: '0.95rem', fontWeight: 600, color: isCompleted ? 'var(--lp-muted)' : 'var(--text-primary)' }}>
                        {step.icon} {step.title}
                      </span>
                      <span style={{ fontSize: '0.72rem', color: 'var(--lp-muted)', background: 'rgba(100,116,139,0.1)', border: '1px solid var(--lp-border)', borderRadius: 999, padding: '1px 8px' }}>
                        ~{step.estimatedMinutes} min
                      </span>
                      {!blockersLoading && hasBlockers && !isCompleted && (
                        <span style={{ fontSize: '0.72rem', color: '#f59e0b', background: 'rgba(245,158,11,0.1)', border: '1px solid rgba(245,158,11,0.3)', borderRadius: 999, padding: '1px 8px' }}>
                          {stepBlockers.length} blocker{stepBlockers.length !== 1 ? 's' : ''}
                        </span>
                      )}
                    </div>
                    <p style={{ margin: '0.2rem 0 0', fontSize: '0.82rem', color: 'var(--lp-muted)', lineHeight: 1.45 }}>
                      {step.subtitle}
                    </p>
                  </div>
                </button>

                {/* Expanded panel — only for active step */}
                {isActive && (
                  <div style={{ padding: '0 1.1rem 1.1rem', borderTop: '1px solid var(--lp-border)' }}>
                    {/* Blockers */}
                    {!blockersLoading && hasBlockers && !isCompleted && (
                      <div style={{ margin: '0.85rem 0 0.75rem', padding: '0.65rem 0.85rem', background: 'rgba(245,158,11,0.07)', border: '1px solid rgba(245,158,11,0.3)', borderRadius: 10 }}>
                        <div style={{ fontSize: '0.78rem', fontWeight: 700, color: '#f59e0b', marginBottom: 4 }}>Blockers to fix</div>
                        <ul style={{ margin: 0, paddingLeft: '1.1rem' }}>
                          {stepBlockers.map((b, i) => (
                            <li key={i} style={{ fontSize: '0.82rem', color: 'var(--lp-muted)', marginBottom: 2 }}>{b}</li>
                          ))}
                        </ul>
                      </div>
                    )}

                    {/* Action link */}
                    <div style={{ display: 'flex', gap: '0.65rem', marginTop: '0.85rem', flexWrap: 'wrap', alignItems: 'center' }}>
                      {step.actionHref && (
                        <Link
                          href={step.actionHref}
                          style={{
                            padding: '0.45rem 1rem',
                            borderRadius: 8,
                            background: 'var(--lp-accent-teal)',
                            color: '#fff',
                            fontWeight: 600,
                            fontSize: '0.85rem',
                            textDecoration: 'none',
                          }}
                        >
                          {step.actionLabel}
                        </Link>
                      )}

                      {!isCompleted ? (
                        <button
                          type="button"
                          onClick={() => markComplete(step.id)}
                          style={{
                            padding: '0.45rem 1rem',
                            borderRadius: 8,
                            border: '1px solid rgba(16,185,129,0.45)',
                            background: 'rgba(16,185,129,0.1)',
                            color: '#10b981',
                            fontWeight: 600,
                            fontSize: '0.85rem',
                            cursor: 'pointer',
                          }}
                        >
                          Mark as done ✓
                        </button>
                      ) : (
                        <button
                          type="button"
                          onClick={() => {
                            setCompletedSteps((prev) => {
                              const next = new Set(prev);
                              next.delete(step.id);
                              saveProgress(next);
                              return next;
                            });
                          }}
                          style={{
                            padding: '0.45rem 1rem',
                            borderRadius: 8,
                            border: '1px solid var(--lp-border)',
                            background: 'transparent',
                            color: 'var(--lp-muted)',
                            fontWeight: 500,
                            fontSize: '0.82rem',
                            cursor: 'pointer',
                          }}
                        >
                          Undo
                        </button>
                      )}
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>

        {/* Bottom actions */}
        <div style={{ marginTop: '1.5rem', display: 'flex', gap: '0.75rem', flexWrap: 'wrap', alignItems: 'center' }}>
          {allDone && (
            <button
              type="button"
              onClick={handleFinish}
              style={{
                padding: '0.7rem 1.5rem',
                borderRadius: 10,
                border: 'none',
                background: 'var(--lp-accent-teal)',
                color: '#fff',
                fontWeight: 700,
                fontSize: '1rem',
                cursor: 'pointer',
              }}
            >
              🎉 Finish — get receipt reference
            </button>
          )}
          <button
            type="button"
            onClick={handleReset}
            style={{
              padding: '0.5rem 1rem',
              borderRadius: 8,
              border: '1px solid var(--lp-border)',
              background: 'transparent',
              color: 'var(--lp-muted)',
              fontWeight: 500,
              fontSize: '0.82rem',
              cursor: 'pointer',
            }}
          >
            Reset progress
          </button>
          <span style={{ fontSize: '0.78rem', color: 'var(--lp-muted)', marginLeft: 'auto' }}>
            Progress saved locally — you can resume at any time.
          </span>
        </div>
      </div>
    </div>
  );
}
