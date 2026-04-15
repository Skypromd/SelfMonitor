import { ReactNode, useMemo, useState } from 'react';
import EmptyState from './EmptyState';
import Skeleton from './Skeleton';

export interface Column<T> {
  key: string;
  header: string;
  render?: (row: T) => ReactNode;
  sortable?: boolean;
  mobileHide?: boolean;
  width?: string;
}

interface DataTableProps<T> {
  columns: Column<T>[];
  data: T[];
  keyField: keyof T;
  loading?: boolean;
  searchable?: boolean;
  searchPlaceholder?: string;
  pageSize?: number;
  emptyTitle?: string;
  emptyDescription?: string;
  onRowClick?: (row: T) => void;
}

function getVal<T>(row: T, key: string): string {
  const v = (row as Record<string, unknown>)[key];
  return v == null ? '' : String(v);
}

export function DataTable<T>({
  columns, data, keyField, loading, searchable, searchPlaceholder = 'Search…',
  pageSize = 20, emptyTitle = 'No results', emptyDescription, onRowClick,
}: DataTableProps<T>) {
  const [search, setSearch] = useState('');
  const [sortKey, setSortKey] = useState<string | null>(null);
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('asc');
  const [page, setPage] = useState(1);

  const filtered = useMemo(() => {
    if (!search.trim()) return data;
    const q = search.toLowerCase();
    return data.filter((row) =>
      columns.some((col) => getVal(row, col.key).toLowerCase().includes(q))
    );
  }, [data, search, columns]);

  const sorted = useMemo(() => {
    if (!sortKey) return filtered;
    return [...filtered].sort((a, b) => {
      const av = getVal(a, sortKey);
      const bv = getVal(b, sortKey);
      const cmp = av.localeCompare(bv, undefined, { numeric: true });
      return sortDir === 'asc' ? cmp : -cmp;
    });
  }, [filtered, sortKey, sortDir]);

  const totalPages = Math.max(1, Math.ceil(sorted.length / pageSize));
  const pageData = sorted.slice((page - 1) * pageSize, page * pageSize);

  const handleSort = (key: string) => {
    if (sortKey === key) setSortDir((d) => d === 'asc' ? 'desc' : 'asc');
    else { setSortKey(key); setSortDir('asc'); }
    setPage(1);
  };

  if (loading) {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
        {Array.from({ length: 5 }).map((_, i) => <Skeleton key={i} height="2.5rem" />)}
      </div>
    );
  }

  return (
    <div>
      {searchable && (
        <div style={{ marginBottom: '0.75rem' }}>
          <input
            value={search}
            onChange={(e) => { setSearch(e.target.value); setPage(1); }}
            placeholder={searchPlaceholder}
            style={{
              width: '100%', maxWidth: '320px',
              height: '2.25rem', padding: '0 0.75rem',
              background: 'var(--bg-input, rgba(15,23,42,0.6))',
              border: '1px solid var(--border, rgba(148,163,184,0.2))',
              borderRadius: '0.5rem',
              color: 'var(--text-primary, #f1f5f9)',
              fontSize: '0.85rem', outline: 'none',
              boxSizing: 'border-box',
            }}
          />
        </div>
      )}

      {/* Desktop table */}
      <div className="dt-table-wrap" style={{ overflowX: 'auto' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.875rem' }}>
          <thead>
            <tr style={{ borderBottom: '1px solid var(--border, rgba(148,163,184,0.12))' }}>
              {columns.map((col) => (
                <th
                  key={col.key}
                  onClick={col.sortable ? () => handleSort(col.key) : undefined}
                  style={{
                    padding: '0.6rem 0.875rem',
                    textAlign: 'left',
                    fontSize: '0.72rem',
                    fontWeight: 700,
                    color: 'var(--text-secondary, #94a3b8)',
                    textTransform: 'uppercase',
                    letterSpacing: '0.06em',
                    cursor: col.sortable ? 'pointer' : 'default',
                    userSelect: 'none',
                    whiteSpace: 'nowrap',
                    width: col.width,
                  }}
                >
                  {col.header}
                  {col.sortable && sortKey === col.key && (sortDir === 'asc' ? ' ↑' : ' ↓')}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {pageData.length === 0 ? (
              <tr>
                <td colSpan={columns.length}>
                  <EmptyState title={emptyTitle} description={emptyDescription} />
                </td>
              </tr>
            ) : (
              pageData.map((row) => (
                <tr
                  key={String(row[keyField])}
                  onClick={onRowClick ? () => onRowClick(row) : undefined}
                  style={{
                    borderBottom: '1px solid var(--border, rgba(148,163,184,0.06))',
                    cursor: onRowClick ? 'pointer' : 'default',
                    transition: 'background 0.1s',
                  }}
                  onMouseEnter={(e) => { if (onRowClick) (e.currentTarget as HTMLTableRowElement).style.background = 'rgba(148,163,184,0.04)'; }}
                  onMouseLeave={(e) => { (e.currentTarget as HTMLTableRowElement).style.background = 'transparent'; }}
                >
                  {columns.map((col) => (
                    <td
                      key={col.key}
                      style={{
                        padding: '0.65rem 0.875rem',
                        color: 'var(--text-primary, #f1f5f9)',
                        verticalAlign: 'middle',
                      }}
                    >
                      {col.render ? col.render(row) : getVal(row, col.key)}
                    </td>
                  ))}
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Mobile cards */}
      <div className="dt-cards" style={{ display: 'none', flexDirection: 'column', gap: '0.6rem' }}>
        {pageData.map((row) => (
          <div
            key={String(row[keyField])}
            onClick={onRowClick ? () => onRowClick(row) : undefined}
            style={{
              background: 'var(--bg-surface, #1e293b)',
              border: '1px solid var(--border, rgba(148,163,184,0.12))',
              borderRadius: '0.625rem',
              padding: '0.875rem 1rem',
              cursor: onRowClick ? 'pointer' : 'default',
            }}
          >
            {columns.filter((c) => !c.mobileHide).map((col) => (
              <div key={col.key} style={{ display: 'flex', justifyContent: 'space-between', gap: '0.5rem', marginBottom: '0.4rem' }}>
                <span style={{ fontSize: '0.72rem', color: 'var(--text-secondary, #94a3b8)', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.05em', flexShrink: 0 }}>{col.header}</span>
                <span style={{ fontSize: '0.85rem', color: 'var(--text-primary, #f1f5f9)', textAlign: 'right' }}>
                  {col.render ? col.render(row) : getVal(row, col.key)}
                </span>
              </div>
            ))}
          </div>
        ))}
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginTop: '0.875rem', gap: '0.5rem' }}>
          <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary, #94a3b8)' }}>
            {(page - 1) * pageSize + 1}–{Math.min(page * pageSize, sorted.length)} of {sorted.length}
          </span>
          <div style={{ display: 'flex', gap: '0.4rem' }}>
            <button
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page === 1}
              style={{ padding: '0.3rem 0.65rem', background: 'rgba(148,163,184,0.1)', border: '1px solid rgba(148,163,184,0.15)', borderRadius: '0.375rem', color: 'var(--text-primary, #f1f5f9)', cursor: page === 1 ? 'not-allowed' : 'pointer', opacity: page === 1 ? 0.4 : 1, fontSize: '0.82rem' }}
            >
              ←
            </button>
            <span style={{ padding: '0.3rem 0.65rem', fontSize: '0.82rem', color: 'var(--text-primary, #f1f5f9)' }}>
              {page} / {totalPages}
            </span>
            <button
              onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
              disabled={page === totalPages}
              style={{ padding: '0.3rem 0.65rem', background: 'rgba(148,163,184,0.1)', border: '1px solid rgba(148,163,184,0.15)', borderRadius: '0.375rem', color: 'var(--text-primary, #f1f5f9)', cursor: page === totalPages ? 'not-allowed' : 'pointer', opacity: page === totalPages ? 0.4 : 1, fontSize: '0.82rem' }}
            >
              →
            </button>
          </div>
        </div>
      )}

      <style>{`
        @media(max-width:640px){
          .dt-table-wrap{display:none}
          .dt-cards{display:flex!important}
        }
      `}</style>
    </div>
  );
}

export default DataTable;
