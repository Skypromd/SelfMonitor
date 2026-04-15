import { createContext, ReactNode, useCallback, useContext, useState } from 'react';

type ToastKind = 'success' | 'error' | 'warning' | 'info';

interface ToastItem {
  id: string;
  kind: ToastKind;
  message: string;
}

interface ToastContextValue {
  toast: (kind: ToastKind, message: string, durationMs?: number) => void;
}

const ToastContext = createContext<ToastContextValue>({ toast: () => {} });

const KIND_STYLES: Record<ToastKind, { bg: string; border: string; icon: string }> = {
  success: { bg: 'rgba(52,211,153,0.12)', border: 'rgba(52,211,153,0.3)',  icon: '✓' },
  error:   { bg: 'rgba(248,113,113,0.12)', border: 'rgba(248,113,113,0.3)', icon: '✕' },
  warning: { bg: 'rgba(251,191,36,0.12)', border: 'rgba(251,191,36,0.3)',  icon: '!' },
  info:    { bg: 'rgba(99,102,241,0.12)',  border: 'rgba(99,102,241,0.3)',  icon: 'i' },
};

const KIND_COLOR: Record<ToastKind, string> = {
  success: '#34d399', error: '#f87171', warning: '#fbbf24', info: '#818cf8',
};

export function ToastProvider({ children }: { children: ReactNode }) {
  const [items, setItems] = useState<ToastItem[]>([]);

  const toast = useCallback((kind: ToastKind, message: string, durationMs = 4200) => {
    const id = `${Date.now()}-${Math.random().toString(16).slice(2)}`;
    setItems((prev) => [...prev, { id, kind, message }]);
    setTimeout(() => setItems((prev) => prev.filter((i) => i.id !== id)), durationMs);
  }, []);

  const dismiss = (id: string) => setItems((prev) => prev.filter((i) => i.id !== id));

  return (
    <ToastContext.Provider value={{ toast }}>
      {children}
      <div style={{
        position: 'fixed', bottom: '1.5rem', right: '1.5rem', zIndex: 9999,
        display: 'flex', flexDirection: 'column', gap: '0.6rem', maxWidth: '380px',
      }}>
        {items.map((item) => {
          const s = KIND_STYLES[item.kind];
          return (
            <div
              key={item.id}
              role="status"
              style={{
                display: 'flex', alignItems: 'flex-start', gap: '0.6rem',
                padding: '0.75rem 1rem',
                background: s.bg,
                border: `1px solid ${s.border}`,
                borderRadius: '0.625rem',
                boxShadow: '0 4px 16px rgba(0,0,0,0.3)',
                animation: 'toastIn 0.2s ease',
              }}
            >
              <span style={{
                width: '1.25rem', height: '1.25rem', borderRadius: '50%',
                background: KIND_COLOR[item.kind] + '22',
                color: KIND_COLOR[item.kind],
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                fontSize: '0.75rem', fontWeight: 700, flexShrink: 0,
              }}>
                {s.icon}
              </span>
              <span style={{ flex: 1, fontSize: '0.875rem', color: 'var(--text-primary, #f1f5f9)', lineHeight: 1.45 }}>
                {item.message}
              </span>
              <button
                onClick={() => dismiss(item.id)}
                aria-label="Dismiss"
                style={{
                  background: 'none', border: 'none', cursor: 'pointer',
                  color: 'var(--text-secondary, #94a3b8)', fontSize: '1rem',
                  lineHeight: 1, padding: 0, flexShrink: 0,
                }}
              >
                ×
              </button>
            </div>
          );
        })}
      </div>
      <style>{`@keyframes toastIn{from{opacity:0;transform:translateX(1rem)}to{opacity:1;transform:none}}`}</style>
    </ToastContext.Provider>
  );
}

export function useToast() {
  return useContext(ToastContext);
}

export default ToastProvider;
