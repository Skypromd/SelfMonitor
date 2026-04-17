import Link from 'next/link';
import { Badge } from './ui/Badge';

export type CisCreditsBreakdown = {
  verified_gbp: number;
  unverified_self_attested_gbp: number;
  labels: string[];
  hmrc_submit_extra_confirm_required: boolean;
  legacy_cis_field_routed_to_unverified?: boolean;
  legacy_cis_field_ignored_use_split_inputs?: boolean;
};

export function CisComplianceBanner({
  breakdown,
}: {
  breakdown: CisCreditsBreakdown | undefined | null;
}) {
  if (!breakdown || (breakdown.verified_gbp <= 0 && breakdown.unverified_self_attested_gbp <= 0)) {
    return null;
  }
  const unverified = breakdown.unverified_self_attested_gbp > 0.01;
  return (
    <div
      style={{
        background: unverified ? 'rgba(251,191,36,0.08)' : 'rgba(52,211,153,0.08)',
        border: `1px solid ${unverified ? 'rgba(251,191,36,0.35)' : 'rgba(52,211,153,0.25)'}`,
        borderRadius: 12,
        padding: '14px 18px',
        marginBottom: 16,
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap', marginBottom: 8 }}>
        <span style={{ fontWeight: 700, color: 'var(--text-primary)', fontSize: '0.92rem' }}>
          CIS tax credits (Construction Industry Scheme)
        </span>
        {unverified && (
          <Badge variant="unverified" style={{ textTransform: 'uppercase', letterSpacing: '0.04em' }}>
            UNVERIFIED
          </Badge>
        )}
        {!unverified && <Badge variant="success">Verified</Badge>}
      </div>
      <div style={{ fontSize: '0.86rem', color: 'var(--text-secondary)', lineHeight: 1.55 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', maxWidth: 420, gap: 12 }}>
          <span>CIS withheld (verified)</span>
          <strong style={{ color: 'var(--text-primary)' }}>
            £{breakdown.verified_gbp.toLocaleString('en-GB', { minimumFractionDigits: 2 })}
          </strong>
        </div>
        <div style={{ display: 'flex', justifyContent: 'space-between', maxWidth: 420, gap: 12 }}>
          <span>CIS withheld (unverified self-attested)</span>
          <strong style={{ color: 'var(--text-primary)' }}>
            £{breakdown.unverified_self_attested_gbp.toLocaleString('en-GB', { minimumFractionDigits: 2 })}
          </strong>
        </div>
        {unverified && (
          <p style={{ margin: '10px 0 0' }}>
            No CIS Statement uploaded for the unverified portion. Figures are self-attested. HMRC may request
            evidence.{' '}
            <Link href="/documents" style={{ color: 'var(--accent)' }}>
              Upload statement to verify
            </Link>
          </p>
        )}
        {breakdown.hmrc_submit_extra_confirm_required && (
          <p style={{ margin: '8px 0 0', color: 'var(--warning, #fbbf24)' }}>
            Additional confirmation is required before submitting to HMRC if unverified CIS amounts are included.
          </p>
        )}
        {breakdown.legacy_cis_field_ignored_use_split_inputs && (
          <p style={{ margin: '8px 0 0', fontSize: '0.8rem', opacity: 0.9 }}>
            Legacy single CIS field was ignored — use verified vs self-attested split fields.
          </p>
        )}
      </div>
    </div>
  );
}
