import { HTMLAttributes, ReactNode } from 'react';

interface CardProps extends HTMLAttributes<HTMLDivElement> {
  header?: ReactNode;
  footer?: ReactNode;
  hoverable?: boolean;
  padding?: 'none' | 'sm' | 'md' | 'lg';
}

const PADDING_MAP = { none: '0', sm: '0.75rem', md: '1.25rem', lg: '1.75rem' };

export function Card({ header, footer, hoverable, padding = 'md', children, style, className, ...rest }: CardProps) {
  return (
    <div
      className={className}
      {...rest}
      style={{
        background: 'var(--bg-surface, #1e293b)',
        border: '1px solid var(--border, rgba(148,163,184,0.12))',
        borderRadius: '0.75rem',
        overflow: 'hidden',
        transition: hoverable ? 'box-shadow 0.2s, transform 0.2s' : undefined,
        ...style,
      }}
      onMouseEnter={hoverable ? (e) => { (e.currentTarget as HTMLDivElement).style.boxShadow = '0 8px 30px rgba(0,0,0,0.25)'; (e.currentTarget as HTMLDivElement).style.transform = 'translateY(-1px)'; } : undefined}
      onMouseLeave={hoverable ? (e) => { (e.currentTarget as HTMLDivElement).style.boxShadow = 'none'; (e.currentTarget as HTMLDivElement).style.transform = 'none'; } : undefined}
    >
      {header && (
        <div style={{
          padding: PADDING_MAP[padding],
          paddingBottom: '0.75rem',
          borderBottom: '1px solid var(--border, rgba(148,163,184,0.1))',
          fontWeight: 600,
          color: 'var(--text-primary, #f1f5f9)',
        }}>
          {header}
        </div>
      )}
      <div style={{ padding: PADDING_MAP[padding] }}>{children}</div>
      {footer && (
        <div style={{
          padding: PADDING_MAP[padding],
          paddingTop: '0.75rem',
          borderTop: '1px solid var(--border, rgba(148,163,184,0.1))',
          color: 'var(--text-secondary, #94a3b8)',
          fontSize: '0.875rem',
        }}>
          {footer}
        </div>
      )}
    </div>
  );
}

export default Card;
