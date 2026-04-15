import { forwardRef, InputHTMLAttributes, ReactNode } from 'react';

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
  hint?: string;
  leftAddon?: ReactNode;
  rightAddon?: ReactNode;
  inputSize?: 'sm' | 'md' | 'lg';
}

const SIZE_STYLES = {
  sm: { height: '2rem',   fontSize: '0.8rem',   padding: '0 0.65rem' },
  md: { height: '2.5rem', fontSize: '0.875rem', padding: '0 0.875rem' },
  lg: { height: '3rem',   fontSize: '1rem',     padding: '0 1rem' },
};

export const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ label, error, hint, leftAddon, rightAddon, inputSize = 'md', style, id, ...rest }, ref) => {
    const inputId = id ?? (label ? label.toLowerCase().replace(/\s+/g, '-') : undefined);
    const sz = SIZE_STYLES[inputSize];
    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.35rem' }}>
        {label && (
          <label htmlFor={inputId} style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-secondary, #94a3b8)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
            {label}
          </label>
        )}
        <div style={{ position: 'relative', display: 'flex', alignItems: 'center' }}>
          {leftAddon && (
            <span style={{ position: 'absolute', left: '0.75rem', color: 'var(--text-tertiary, #64748b)', fontSize: sz.fontSize, pointerEvents: 'none' }}>
              {leftAddon}
            </span>
          )}
          <input
            ref={ref}
            id={inputId}
            {...rest}
            style={{
              width: '100%',
              height: sz.height,
              padding: sz.padding,
              paddingLeft: leftAddon ? '2.25rem' : sz.padding,
              paddingRight: rightAddon ? '2.25rem' : sz.padding,
              fontSize: sz.fontSize,
              background: 'var(--bg-input, rgba(15,23,42,0.6))',
              border: `1px solid ${error ? 'rgba(248,113,113,0.5)' : 'var(--border, rgba(148,163,184,0.2))'}`,
              borderRadius: '0.5rem',
              color: 'var(--text-primary, #f1f5f9)',
              outline: 'none',
              transition: 'border-color 0.15s, box-shadow 0.15s',
              boxSizing: 'border-box',
              ...style,
            }}
            onFocus={(e) => {
              e.currentTarget.style.borderColor = error ? '#f87171' : 'var(--accent, #14b8a6)';
              e.currentTarget.style.boxShadow = `0 0 0 2px ${error ? 'rgba(248,113,113,0.2)' : 'rgba(20,184,166,0.2)'}`;
              rest.onFocus?.(e);
            }}
            onBlur={(e) => {
              e.currentTarget.style.borderColor = error ? 'rgba(248,113,113,0.5)' : 'var(--border, rgba(148,163,184,0.2))';
              e.currentTarget.style.boxShadow = 'none';
              rest.onBlur?.(e);
            }}
          />
          {rightAddon && (
            <span style={{ position: 'absolute', right: '0.75rem', color: 'var(--text-tertiary, #64748b)', fontSize: sz.fontSize }}>
              {rightAddon}
            </span>
          )}
        </div>
        {error && <p style={{ fontSize: '0.75rem', color: '#f87171', margin: 0 }}>{error}</p>}
        {hint && !error && <p style={{ fontSize: '0.75rem', color: 'var(--text-tertiary, #64748b)', margin: 0 }}>{hint}</p>}
      </div>
    );
  }
);

Input.displayName = 'Input';
export default Input;
