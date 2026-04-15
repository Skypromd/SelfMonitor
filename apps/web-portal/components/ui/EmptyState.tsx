import { ReactNode } from 'react';
import Button from './Button';

interface EmptyStateProps {
  illustration?: ReactNode;
  title: string;
  description?: string;
  ctaLabel?: string;
  onCta?: () => void;
  ctaHref?: string;
}

const DEFAULT_ILLUSTRATION = (
  <svg width="64" height="64" viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
    <circle cx="32" cy="32" r="30" stroke="rgba(148,163,184,0.2)" strokeWidth="2" />
    <path d="M22 26h20M22 32h14M22 38h8" stroke="rgba(148,163,184,0.35)" strokeWidth="2" strokeLinecap="round" />
    <circle cx="44" cy="44" r="8" fill="rgba(20,184,166,0.1)" stroke="rgba(20,184,166,0.3)" strokeWidth="1.5" />
    <path d="M41 44h6M44 41v6" stroke="#14b8a6" strokeWidth="1.5" strokeLinecap="round" />
  </svg>
);

export function EmptyState({ illustration, title, description, ctaLabel, onCta, ctaHref }: EmptyStateProps) {
  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      textAlign: 'center',
      padding: '3rem 1.5rem',
      gap: '1rem',
    }}>
      <div style={{ opacity: 0.8 }}>{illustration ?? DEFAULT_ILLUSTRATION}</div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.35rem' }}>
        <p style={{ fontWeight: 700, fontSize: '1.05rem', color: 'var(--text-primary, #f1f5f9)', margin: 0 }}>{title}</p>
        {description && (
          <p style={{ fontSize: '0.875rem', color: 'var(--text-secondary, #94a3b8)', margin: 0, maxWidth: '360px' }}>{description}</p>
        )}
      </div>
      {ctaLabel && (
        ctaHref ? (
          <a href={ctaHref} style={{ textDecoration: 'none' }}>
            <Button variant="primary" size="md">{ctaLabel}</Button>
          </a>
        ) : (
          <Button variant="primary" size="md" onClick={onCta}>{ctaLabel}</Button>
        )
      )}
    </div>
  );
}

export default EmptyState;
