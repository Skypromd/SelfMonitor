import { ButtonHTMLAttributes, forwardRef, ReactNode } from 'react';

type Variant = 'primary' | 'secondary' | 'danger' | 'ghost';
type Size = 'sm' | 'md' | 'lg';

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  size?: Size;
  loading?: boolean;
  leftIcon?: ReactNode;
  rightIcon?: ReactNode;
}

const BASE: React.CSSProperties = {
  display: 'inline-flex',
  alignItems: 'center',
  justifyContent: 'center',
  gap: '0.4rem',
  fontWeight: 600,
  borderRadius: '0.5rem',
  border: '1px solid transparent',
  cursor: 'pointer',
  transition: 'background 0.15s, opacity 0.15s, border-color 0.15s',
  whiteSpace: 'nowrap',
  outline: 'none',
  userSelect: 'none',
};

const VARIANT_STYLES: Record<Variant, React.CSSProperties> = {
  primary: {
    background: 'var(--accent, #14b8a6)',
    color: '#fff',
    borderColor: 'var(--accent, #14b8a6)',
  },
  secondary: {
    background: 'rgba(148,163,184,0.12)',
    color: 'var(--text-primary, #f1f5f9)',
    borderColor: 'rgba(148,163,184,0.25)',
  },
  danger: {
    background: 'rgba(239,68,68,0.12)',
    color: '#f87171',
    borderColor: 'rgba(239,68,68,0.3)',
  },
  ghost: {
    background: 'transparent',
    color: 'var(--text-secondary, #94a3b8)',
    borderColor: 'transparent',
  },
};

const SIZE_STYLES: Record<Size, React.CSSProperties> = {
  sm: { padding: '0.3rem 0.7rem', fontSize: '0.8rem', height: '2rem' },
  md: { padding: '0.5rem 1rem', fontSize: '0.875rem', height: '2.5rem' },
  lg: { padding: '0.65rem 1.4rem', fontSize: '1rem', height: '3rem' },
};

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ variant = 'primary', size = 'md', loading, leftIcon, rightIcon, children, disabled, style, ...rest }, ref) => {
    const isDisabled = disabled || loading;
    return (
      <button
        ref={ref}
        {...rest}
        disabled={isDisabled}
        style={{
          ...BASE,
          ...VARIANT_STYLES[variant],
          ...SIZE_STYLES[size],
          opacity: isDisabled ? 0.55 : 1,
          cursor: isDisabled ? 'not-allowed' : 'pointer',
          ...style,
        }}
      >
        {loading ? <span style={{ width: '1em', height: '1em', border: '2px solid currentColor', borderTopColor: 'transparent', borderRadius: '50%', display: 'inline-block', animation: 'spin 0.6s linear infinite' }} /> : leftIcon}
        {children}
        {!loading && rightIcon}
        <style>{`@keyframes spin{to{transform:rotate(360deg)}}`}</style>
      </button>
    );
  }
);

Button.displayName = 'Button';
export default Button;
