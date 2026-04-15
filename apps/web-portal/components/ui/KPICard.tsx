import { ReactNode } from 'react';

interface SparkPoint { value: number }

interface KPICardProps {
  label: string;
  value: ReactNode;
  sub?: string;
  trend?: 'up' | 'down' | 'flat';
  trendValue?: string;
  spark?: SparkPoint[];
  accent?: string;
  icon?: ReactNode;
}

function Sparkline({ points, color }: { points: SparkPoint[]; color: string }) {
  if (points.length < 2) return null;
  const w = 80;
  const h = 28;
  const max = Math.max(...points.map((p) => p.value), 1);
  const min = Math.min(...points.map((p) => p.value), 0);
  const range = max - min || 1;
  const step = w / (points.length - 1);
  const pts = points.map((p, i) => `${i * step},${h - ((p.value - min) / range) * h}`).join(' ');
  const area = `${pts} ${w},${h} 0,${h}`;
  return (
    <svg width={w} height={h} viewBox={`0 0 ${w} ${h}`} style={{ overflow: 'visible' }}>
      <polygon points={area} fill={color} opacity={0.15} />
      <polyline points={pts} fill="none" stroke={color} strokeWidth={1.5} strokeLinejoin="round" />
    </svg>
  );
}

const TREND_ICON: Record<string, string> = { up: '↑', down: '↓', flat: '→' };
const TREND_COLOR: Record<string, string> = { up: '#34d399', down: '#f87171', flat: '#94a3b8' };

export function KPICard({ label, value, sub, trend, trendValue, spark, accent = '#14b8a6', icon }: KPICardProps) {
  return (
    <div style={{
      background: 'var(--bg-surface, #1e293b)',
      border: '1px solid var(--border, rgba(148,163,184,0.12))',
      borderRadius: '0.75rem',
      padding: '1.1rem 1.25rem',
      display: 'flex',
      flexDirection: 'column',
      gap: '0.35rem',
      position: 'relative',
      overflow: 'hidden',
    }}>
      {/* Accent bar */}
      <div style={{ position: 'absolute', top: 0, left: 0, width: 3, height: '100%', background: accent, borderRadius: '4px 0 0 4px' }} />

      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <p style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-secondary, #94a3b8)', textTransform: 'uppercase', letterSpacing: '0.06em', margin: 0 }}>
          {label}
        </p>
        {icon && <span style={{ color: accent, fontSize: '1.1rem' }}>{icon}</span>}
      </div>

      <p style={{ fontSize: '1.65rem', fontWeight: 700, color: 'var(--text-primary, #f1f5f9)', margin: 0, lineHeight: 1.1 }}>
        {value}
      </p>

      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '0.5rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
          {trend && (
            <span style={{ fontSize: '0.78rem', fontWeight: 700, color: TREND_COLOR[trend] }}>
              {TREND_ICON[trend]} {trendValue}
            </span>
          )}
          {sub && !trend && (
            <span style={{ fontSize: '0.78rem', color: 'var(--text-tertiary, #64748b)' }}>{sub}</span>
          )}
        </div>
        {spark && <Sparkline points={spark} color={accent} />}
      </div>
      {sub && trend && (
        <span style={{ fontSize: '0.75rem', color: 'var(--text-tertiary, #64748b)' }}>{sub}</span>
      )}
    </div>
  );
}

export default KPICard;
