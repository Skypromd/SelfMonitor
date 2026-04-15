import { ReactNode, useEffect } from 'react';

interface ModalProps {
  open: boolean;
  onClose: () => void;
  title?: string;
  children: ReactNode;
  footer?: ReactNode;
  size?: 'sm' | 'md' | 'lg';
}

const SIZE_WIDTH = { sm: '400px', md: '560px', lg: '720px' };

export function Modal({ open, onClose, title, children, footer, size = 'md' }: ModalProps) {
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose(); };
    document.addEventListener('keydown', onKey);
    document.body.style.overflow = 'hidden';
    return () => { document.removeEventListener('keydown', onKey); document.body.style.overflow = ''; };
  }, [open, onClose]);

  if (!open) return null;

  return (
    <div
      onClick={onClose}
      style={{
        position: 'fixed', inset: 0, zIndex: 1000,
        background: 'rgba(0,0,0,0.65)',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        padding: '1rem',
      }}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
        style={{
          background: 'var(--bg-surface, #1e293b)',
          border: '1px solid var(--border, rgba(148,163,184,0.15))',
          borderRadius: '0.875rem',
          width: '100%',
          maxWidth: SIZE_WIDTH[size],
          maxHeight: '90vh',
          overflow: 'auto',
          boxShadow: '0 20px 60px rgba(0,0,0,0.5)',
          /* mobile bottom sheet */
          ['@media(maxWidth:640px)' as string]: { alignSelf: 'flex-end', borderBottomLeftRadius: 0, borderBottomRightRadius: 0, maxHeight: '85vh' },
        }}
      >
        {title && (
          <div style={{
            display: 'flex', alignItems: 'center', justifyContent: 'space-between',
            padding: '1.25rem 1.5rem',
            borderBottom: '1px solid var(--border, rgba(148,163,184,0.12))',
          }}>
            <h3 style={{ margin: 0, fontSize: '1.05rem', fontWeight: 700, color: 'var(--text-primary, #f1f5f9)' }}>{title}</h3>
            <button
              onClick={onClose}
              aria-label="Close"
              style={{
                background: 'none', border: 'none', cursor: 'pointer',
                color: 'var(--text-secondary, #94a3b8)', fontSize: '1.4rem',
                lineHeight: 1, padding: '0.2rem 0.4rem', borderRadius: '0.375rem',
              }}
            >
              ×
            </button>
          </div>
        )}
        <div style={{ padding: '1.5rem' }}>{children}</div>
        {footer && (
          <div style={{
            padding: '1rem 1.5rem',
            borderTop: '1px solid var(--border, rgba(148,163,184,0.12))',
            display: 'flex', justifyContent: 'flex-end', gap: '0.75rem',
          }}>
            {footer}
          </div>
        )}
      </div>
    </div>
  );
}

export default Modal;
