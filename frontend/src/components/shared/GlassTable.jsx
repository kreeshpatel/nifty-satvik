import React, { useState, useMemo } from 'react';
import { ChevronDown } from 'lucide-react';
import { GlassCard } from '@/components/shared/GlassCard';
import { cn } from '@/lib/utils';

/**
 * GlassTable — shared table primitive wrapped in a tier-1 glass card.
 *
 * Handles:
 *   - Header band (title + count pill + actions slot)
 *   - Sortable columns (opt-in per column)
 *   - Consistent row padding + hover tint
 *   - Optional row click navigation
 *   - Optional footer slot
 *   - Empty state
 *
 * columns:
 *   {
 *     key:           string                     — react key + fallback accessor
 *     label:         string                     — column header text
 *     align:         'left' | 'right' | 'center'  (default 'left')
 *     width:         string                     — e.g. '80px', '20%'
 *     render:        (row) => ReactNode
 *     sortable:      boolean                    — enable sort on this column
 *     sortAccessor:  (row) => comparable value  — defaults to row[key]
 *   }[]
 */
export function GlassTable({
  title,
  count,
  actions,
  columns,
  rows,
  rowKey,
  onRowClick,
  empty,
  footer,
  compact = false,
  className,
}) {
  const rowPad = compact ? 'py-3' : 'py-4';

  const [sortColumn, setSortColumn] = useState(null);
  const [sortDir, setSortDir] = useState(null); // 'asc' | 'desc' | null

  const handleHeaderClick = (col) => {
    if (!col.sortable) return;
    if (sortColumn !== col.key) {
      setSortColumn(col.key);
      setSortDir('asc');
      return;
    }
    // cycle: asc → desc → none
    setSortDir((d) => (d === 'asc' ? 'desc' : d === 'desc' ? null : 'asc'));
    if (sortDir === 'desc') setSortColumn(null);
  };

  const sortedRows = useMemo(() => {
    if (!sortColumn || !sortDir) return rows;
    const col = columns.find((c) => c.key === sortColumn);
    if (!col) return rows;
    const accessor = col.sortAccessor || ((row) => row[col.key]);
    const sorted = [...rows].sort((a, b) => {
      const av = accessor(a);
      const bv = accessor(b);
      if (av == null) return 1;
      if (bv == null) return -1;
      if (typeof av === 'number' && typeof bv === 'number') return av - bv;
      return String(av).localeCompare(String(bv));
    });
    return sortDir === 'desc' ? sorted.reverse() : sorted;
  }, [rows, columns, sortColumn, sortDir]);

  return (
    <GlassCard tier={1} className={cn('overflow-hidden', className)}>
      {(title || actions) && (
        <header className="flex items-center justify-between gap-3 px-6 pt-5 pb-4">
          <div className="flex items-center gap-2.5 min-w-0">
            {title && (
              <h2 className="section-heading">
                {title}
              </h2>
            )}
            {typeof count === 'number' && (
              <span
                className="text-[10px] font-mono tabular-nums px-1.5 py-0.5 rounded-full text-nq-text-muted"
                style={{
                  background: 'rgba(255, 255, 255, 0.05)',
                  border: '1px solid rgba(255, 255, 255, 0.06)',
                }}
              >
                {count}
              </span>
            )}
          </div>
          {actions && <div className="shrink-0">{actions}</div>}
        </header>
      )}

      <div className="overflow-x-auto scrollbar-thin">
        <table className="w-full">
          <thead className="sticky top-0 z-10" style={{ background: 'rgba(15, 23, 42, 0.75)', backdropFilter: 'blur(16px)' }}>
            <tr
              className="text-[10px] font-mono uppercase tracking-[0.14em]"
              style={{
                color: 'rgba(156, 163, 175, 0.75)',
                borderBottom: '1px solid rgba(255, 255, 255, 0.04)',
                borderTop: '1px solid rgba(255, 255, 255, 0.04)',
              }}
            >
              {columns.map((col) => {
                const isSorted = sortColumn === col.key && sortDir;
                const canSort = col.sortable;
                const onKey = canSort
                  ? (e) => {
                      if (e.key === 'Enter' || e.key === ' ') {
                        e.preventDefault();
                        handleHeaderClick(col);
                      }
                    }
                  : undefined;
                return (
                  <th
                    key={col.key}
                    aria-sort={
                      canSort
                        ? isSorted
                          ? sortDir === 'asc' ? 'ascending' : 'descending'
                          : 'none'
                        : undefined
                    }
                    scope="col"
                    className={cn(
                      'px-4 py-2.5 font-medium',
                      col.align === 'right' && 'text-right',
                      col.align === 'center' && 'text-center',
                      !col.align && 'text-left'
                    )}
                    style={col.width ? { width: col.width } : undefined}
                  >
                    {canSort ? (
                      <button
                        type="button"
                        onClick={() => handleHeaderClick(col)}
                        onKeyDown={onKey}
                        className={cn(
                          'inline-flex items-center gap-1.5 uppercase tracking-[0.14em] transition-colors',
                          'hover:text-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#22DD88]/70 focus-visible:ring-offset-2 focus-visible:ring-offset-[#0F172A] rounded-sm',
                          col.align === 'right' && 'justify-end',
                          col.align === 'center' && 'justify-center'
                        )}
                      >
                        {col.label}
                        <ChevronDown
                          className={cn(
                            'h-3 w-3 transition-all',
                            isSorted ? 'opacity-100 text-white' : 'opacity-25',
                            isSorted && sortDir === 'asc' && 'rotate-180'
                          )}
                          strokeWidth={2.4}
                          aria-hidden
                        />
                      </button>
                    ) : (
                      <span
                        className={cn(
                          'inline-flex items-center gap-1.5',
                          col.align === 'right' && 'justify-end',
                          col.align === 'center' && 'justify-center'
                        )}
                      >
                        {col.label}
                      </span>
                    )}
                  </th>
                );
              })}
            </tr>
          </thead>
          <tbody>
            {sortedRows.length === 0 && empty ? (
              <tr>
                <td colSpan={columns.length} className="px-4 py-10 text-center">
                  {empty}
                </td>
              </tr>
            ) : (
              sortedRows.map((row, idx) => {
                const activate = onRowClick ? () => onRowClick(row) : undefined;
                const onKey = activate
                  ? (e) => {
                      if (e.key === 'Enter' || e.key === ' ') {
                        e.preventDefault();
                        activate();
                      }
                    }
                  : undefined;
                return (
                  <tr
                    key={rowKey(row)}
                    onClick={activate}
                    onKeyDown={onKey}
                    tabIndex={activate ? 0 : undefined}
                    role={activate ? 'button' : undefined}
                    className={cn(
                      'group transition-colors duration-150 hover:bg-white/[0.025]',
                      activate &&
                        'cursor-pointer focus:outline-none focus-visible:bg-white/[0.04]'
                    )}
                    style={{
                      borderBottom:
                        idx < sortedRows.length - 1
                          ? '1px solid rgba(255, 255, 255, 0.03)'
                          : 'none',
                    }}
                  >
                    {columns.map((col) => (
                      <td
                        key={col.key}
                        className={cn(
                          'px-4',
                          rowPad,
                          col.align === 'right' && 'text-right',
                          col.align === 'center' && 'text-center'
                        )}
                      >
                        {col.render ? col.render(row) : row[col.key]}
                      </td>
                    ))}
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>

      {footer && <div className="px-6 pb-5 pt-4">{footer}</div>}
    </GlassCard>
  );
}
