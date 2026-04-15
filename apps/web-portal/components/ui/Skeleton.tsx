import { CSSProperties } from 'react';

interface SkeletonProps {
  width?: string | number;
  height?: string | number;
  borderRadius?: string;
  style?: CSSProperties;
}

interface SkeletonGroupProps {
  rows?: number;
  gap?: string;
}

const SHIMMER = `
  @keyframes shimmer {
    0% { background-position: -200% center; }
    100% { background-position: 200% center; }
  }
`;

export function Skeleton({ width = '100%', height = '1rem', borderRadius = '0.375rem', style }: SkeletonProps) {
  return (
    <>
      <style>{SHIMMER}</style>
      <div
        aria-hidden="true"
        style={{
          width,
          height,
          borderRadius,
          background: 'linear-gradient(90deg, rgba(148,163,184,0.08) 25%, rgba(148,163,184,0.15) 50%, rgba(148,163,184,0.08) 75%)',
          backgroundSize: '200% 100%',
          animation: 'shimmer 1.4s ease-in-out infinite',
          ...style,
        }}
      />
    </>
  );
}

export function SkeletonText({ rows = 3, gap = '0.6rem' }: SkeletonGroupProps) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap }}>
      {Array.from({ length: rows }).map((_, i) => (
        <Skeleton key={i} width={i === rows - 1 ? '65%' : '100%'} height="0.875rem" />
      ))}
    </div>
  );
}

export function SkeletonCard() {
  return (
    <div style={{
      background: 'var(--bg-surface, #1e293b)',
      border: '1px solid var(--border, rgba(148,163,184,0.1))',
      borderRadius: '0.75rem',
      padding: '1.25rem',
      display: 'flex',
      flexDirection: 'column',
      gap: '0.75rem',
    }}>
      <Skeleton height="0.875rem" width="40%" />
      <Skeleton height="2rem" width="60%" />
      <Skeleton height="0.75rem" width="50%" />
    </div>
  );
}

export default Skeleton;
