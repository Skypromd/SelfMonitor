import { HTMLAttributes } from 'react';

type BadgeVariant =
  | 'active' | 'inactive' | 'trialing' | 'cancelled' | 'pending'
  | 'success' | 'error' | 'warning' | 'info'
  | 'final' | 'draft' | 'high' | 'medium' | 'low'
  | 'unverified'
  | 'default';

interface BadgeProps extends HTMLAttributes<HTMLSpanElement> {
  variant?: BadgeVariant;
  size?: 'sm' | 'md';
}

const VARIANT_STYLES: Record<BadgeVariant, { bg: string; color: string }> = {
  active:    { bg: 'rgba(52,211,153,0.12)',  color: '#34d399' },
  success:   { bg: 'rgba(52,211,153,0.12)',  color: '#34d399' },
  final:     { bg: 'rgba(52,211,153,0.12)',  color: '#34d399' },
  low:       { bg: 'rgba(52,211,153,0.12)',  color: '#34d399' },
  inactive:  { bg: 'rgba(148,163,184,0.12)', color: '#94a3b8' },
  cancelled: { bg: 'rgba(148,163,184,0.12)', color: '#94a3b8' },
  default:   { bg: 'rgba(148,163,184,0.12)', color: '#94a3b8' },
  trialing:  { bg: 'rgba(251,191,36,0.12)',  color: '#fbbf24' },
  pending:   { bg: 'rgba(251,191,36,0.12)',  color: '#fbbf24' },
  warning:   { bg: 'rgba(251,191,36,0.12)',  color: '#fbbf24' },
  draft:     { bg: 'rgba(251,191,36,0.12)',  color: '#fbbf24' },
  medium:    { bg: 'rgba(251,191,36,0.12)',  color: '#fbbf24' },
  error:     { bg: 'rgba(248,113,113,0.12)', color: '#f87171' },
  high:      { bg: 'rgba(248,113,113,0.12)', color: '#f87171' },
  info:      { bg: 'rgba(99,102,241,0.12)',  color: '#818cf8' },
  unverified: { bg: 'rgba(251,191,36,0.18)', color: '#fbbf24' },
};

export function Badge({ variant = 'default', size = 'sm', children, style, ...rest }: BadgeProps) {
  const vs = VARIANT_STYLES[variant] ?? VARIANT_STYLES.default;
  return (
    <span
      {...rest}
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        padding: size === 'sm' ? '0.15rem 0.55rem' : '0.25rem 0.75rem',
        borderRadius: '999px',
        fontSize: size === 'sm' ? '0.72rem' : '0.82rem',
        fontWeight: 600,
        textTransform: 'capitalize',
        letterSpacing: '0.02em',
        background: vs.bg,
        color: vs.color,
        border: `1px solid ${vs.color}30`,
        ...style,
      }}
    >
      {children}
    </span>
  );
}

export default Badge;
