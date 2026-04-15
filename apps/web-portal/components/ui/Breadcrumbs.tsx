import Link from 'next/link';

interface BreadcrumbItem {
  label: string;
  href?: string;
}

interface BreadcrumbsProps {
  items: BreadcrumbItem[];
  hideOnMobile?: boolean;
}

export function Breadcrumbs({ items, hideOnMobile = true }: BreadcrumbsProps) {
  return (
    <nav
      aria-label="Breadcrumb"
      style={{ display: hideOnMobile ? 'none' : 'flex' }}
      className="breadcrumbs-nav"
    >
      <ol style={{ display: 'flex', alignItems: 'center', gap: '0.25rem', listStyle: 'none', padding: 0, margin: 0 }}>
        {items.map((item, i) => {
          const isLast = i === items.length - 1;
          return (
            <li key={i} style={{ display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
              {i > 0 && (
                <span style={{ color: 'var(--text-tertiary, #64748b)', fontSize: '0.8rem', userSelect: 'none' }}>
                  /
                </span>
              )}
              {isLast || !item.href ? (
                <span style={{
                  fontSize: '0.82rem',
                  color: isLast ? 'var(--text-primary, #f1f5f9)' : 'var(--text-secondary, #94a3b8)',
                  fontWeight: isLast ? 600 : 400,
                }}>
                  {item.label}
                </span>
              ) : (
                <Link
                  href={item.href}
                  style={{
                    fontSize: '0.82rem',
                    color: 'var(--text-secondary, #94a3b8)',
                    textDecoration: 'none',
                    borderRadius: '0.25rem',
                    padding: '0.1rem 0.2rem',
                  }}
                >
                  {item.label}
                </Link>
              )}
            </li>
          );
        })}
      </ol>
      <style>{`
        @media(min-width:640px){.breadcrumbs-nav{display:flex!important}}
      `}</style>
    </nav>
  );
}

export default Breadcrumbs;
