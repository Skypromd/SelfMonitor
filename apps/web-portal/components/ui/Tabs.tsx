import { ReactNode, useRef } from 'react';

interface Tab {
  id: string;
  label: ReactNode;
  badge?: string | number;
}

interface TabsProps {
  tabs: Tab[];
  activeId: string;
  onChange: (id: string) => void;
  size?: 'sm' | 'md';
}

export function Tabs({ tabs, activeId, onChange, size = 'md' }: TabsProps) {
  const scrollRef = useRef<HTMLDivElement>(null);

  return (
    <div
      ref={scrollRef}
      role="tablist"
      style={{
        display: 'flex',
        gap: '0.2rem',
        overflowX: 'auto',
        scrollbarWidth: 'none',
        padding: '0.25rem',
        background: 'rgba(148,163,184,0.06)',
        borderRadius: '0.625rem',
        border: '1px solid var(--border, rgba(148,163,184,0.1))',
      }}
    >
      <style>{`.tabs-scroll::-webkit-scrollbar{display:none}`}</style>
      {tabs.map((tab) => {
        const isActive = tab.id === activeId;
        return (
          <button
            key={tab.id}
            role="tab"
            aria-selected={isActive}
            onClick={() => onChange(tab.id)}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '0.4rem',
              padding: size === 'sm' ? '0.3rem 0.65rem' : '0.45rem 0.9rem',
              fontSize: size === 'sm' ? '0.78rem' : '0.86rem',
              fontWeight: isActive ? 700 : 500,
              borderRadius: '0.45rem',
              border: 'none',
              cursor: 'pointer',
              whiteSpace: 'nowrap',
              transition: 'background 0.15s, color 0.15s',
              flexShrink: 0,
              background: isActive ? 'var(--bg-surface, #1e293b)' : 'transparent',
              color: isActive ? 'var(--accent, #14b8a6)' : 'var(--text-secondary, #94a3b8)',
              boxShadow: isActive ? '0 1px 4px rgba(0,0,0,0.2)' : 'none',
            }}
          >
            {tab.label}
            {tab.badge !== undefined && (
              <span style={{
                padding: '0 0.4rem',
                background: isActive ? 'var(--accent, #14b8a6)' : 'rgba(148,163,184,0.2)',
                color: isActive ? '#fff' : 'var(--text-secondary, #94a3b8)',
                borderRadius: '999px',
                fontSize: '0.7rem',
                fontWeight: 700,
                lineHeight: '1.4',
              }}>
                {tab.badge}
              </span>
            )}
          </button>
        );
      })}
    </div>
  );
}

export default Tabs;
