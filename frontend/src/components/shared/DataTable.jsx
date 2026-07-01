import React, { useMemo, useState, useRef, useEffect } from 'react';
import { ChevronUp, ChevronDown, ChevronsUpDown } from 'lucide-react';
import { cn } from '@/lib/utils';

/**
 * DataTable — the canonical retail-pro table.
 *
 * Design decisions:
 *   - Medium density: 12px row padding (not 8px Bloomberg, not 20px "airy")
 *   - Sticky header with ui-subhead typography
 *   - Sortable columns with inline chevron in text-3 (clear affordance)
 *   - Zebra stripes OFF (reads as noise once dense)
 *   - Row hover --surface-2, click navigates via onRowClick
 *   - Right-aligned numeric columns via `align: 'right'` on column spec
 *   - Keyboard nav: ↑/↓ traverses, Enter fires onRowClick
 *   - Windowing enabled beyond `virtualThreshold` rows (default 40)
 *
 * Column spec
 * -----------
 * {
 *   key:        unique string/id
 *   header:     string | ReactNode   column header label
 *   accessor:   fn(row) => value     data extractor (default: row[key])
 *   render:     fn(value, row, i) => ReactNode   custom cell renderer
 *   align:      'left' | 'right' | 'center'   default 'left', use 'right' for numbers
 *   sortable:   boolean              enables sort toggle
 *   width:      string               e.g. '120px', 'auto', '1fr'
 *   className:  string               optional per-cell className
 * }
 *
 * Props
 * -----
 * columns:    Column[]
 * rows:       any[]
 * getRowId:   fn(row, index) => string   default row.id ?? index
 * onRowClick: fn(row, index)             whole-row click handler
 * activeRowId: string                     highlights current selection
 * initialSort: { key, dir: 'asc'|'desc' } optional default sort
 * emptyState: ReactNode                   falls back to inline "No rows"
 * dense:      boolean                     tighter row padding (for dashboard previews)
 * virtualThreshold: number                default 40
 */
export function DataTable({
  columns,
  rows,
  getRowId = (r, i) => r?.id ?? i,
  onRowClick,
  activeRowId,
  initialSort,
  emptyState,
  dense = false,
  virtualThreshold = 40,
  className,
}) {
  const [sort, setSort] = useState(initialSort ?? null);
  const containerRef = useRef(null);
  const [focusedIndex, setFocusedIndex] = useState(-1);

  const sortedRows = useMemo(() => {
    if (!sort) return rows;
    const col = columns.find((c) => c.key === sort.key);
    if (!col) return rows;
    const getVal = col.accessor ?? ((r) => r[col.key]);
    const sorted = [...rows].sort((a, b) => {
      const av = getVal(a);
      const bv = getVal(b);
      if (av == null && bv == null) return 0;
      if (av == null) return 1;
      if (bv == null) return -1;
      if (typeof av === 'number' && typeof bv === 'number') return av - bv;
      return String(av).localeCompare(String(bv));
    });
    return sort.dir === 'desc' ? sorted.reverse() : sorted;
  }, [rows, sort, columns]);

  // Virtualize when the dataset is large. We use a simple fixed-row-height
  // windowing approach: measure viewport scroll, render only visible rows
  // plus a small overscan. Keeps 1000-row datasets at 60fps without the
  // complexity of react-window.
  const rowHeight = dense ? 40 : 48;
  const [scrollTop, setScrollTop] = useState(0);
  const [viewportHeight, setViewportHeight] = useState(0);
  const shouldVirtualize = sortedRows.length > virtualThreshold;

  useEffect(() => {
    if (!shouldVirtualize) return;
    const el = containerRef.current;
    if (!el) return;
    const onScroll = () => setScrollTop(el.scrollTop);
    const onResize = () => setViewportHeight(el.clientHeight);
    onResize();
    el.addEventListener('scroll', onScroll, { passive: true });
    window.addEventListener('resize', onResize);
    return () => {
      el.removeEventListener('scroll', onScroll);
      window.removeEventListener('resize', onResize);
    };
  }, [shouldVirtualize]);

  let visibleRows = sortedRows;
  let topPad = 0;
  let bottomPad = 0;
  if (shouldVirtualize && viewportHeight > 0) {
    const overscan = 6;
    const startIdx = Math.max(0, Math.floor(scrollTop / rowHeight) - overscan);
    const endIdx = Math.min(
      sortedRows.length,
      Math.ceil((scrollTop + viewportHeight) / rowHeight) + overscan
    );
    visibleRows = sortedRows.slice(startIdx, endIdx);
    topPad = startIdx * rowHeight;
    bottomPad = (sortedRows.length - endIdx) * rowHeight;
  }

  function toggleSort(colKey) {
    const col = columns.find((c) => c.key === colKey);
    if (!col?.sortable) return;
    setSort((prev) => {
      if (prev?.key !== colKey) return { key: colKey, dir: 'asc' };
      if (prev.dir === 'asc') return { key: colKey, dir: 'desc' };
      return null;
    });
  }

  function handleKeyDown(e) {
    if (!onRowClick) return;
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setFocusedIndex((i) => Math.min(sortedRows.length - 1, (i < 0 ? -1 : i) + 1));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setFocusedIndex((i) => Math.max(0, (i < 0 ? 0 : i) - 1));
    } else if (e.key === 'Enter' && focusedIndex >= 0) {
      e.preventDefault();
      onRowClick(sortedRows[focusedIndex], focusedIndex);
    }
  }

  if (!rows || rows.length === 0) {
    return (
      <div
        className={cn('rounded-xl', className)}
        style={{
          background: 'var(--surface-1)',
          border: '1px solid var(--edge-1)',
          borderRadius: 'var(--r-card)',
        }}
      >
        {emptyState ?? (
          <div className="t-ui-body text-center" style={{ padding: 32, color: 'var(--text-3)' }}>
            No rows
          </div>
        )}
      </div>
    );
  }

  // Default `1fr` columns get a minmax(120px, 1fr) so they don't collapse
  // below readable width on phones. Explicit widths are passed through.
  // Combined with the outer overflow-x wrapper, a wide table now scrolls
  // horizontally on mobile instead of squeezing every cell to 40px.
  const gridCols = columns
    .map((c) => (c.width ? c.width : 'minmax(120px, 1fr)'))
    .join(' ');

  return (
    <div
      className={cn('relative mobile-table-scroll', className)}
      style={{
        background: 'var(--surface-1)',
        border: '1px solid var(--edge-1)',
        borderRadius: 'var(--r-card)',
        overflow: 'auto',
        boxShadow: 'var(--shadow-sm)',
        WebkitOverflowScrolling: 'touch',
      }}
    >
      {/* HEADER — sticky. Grid layout keeps header + body columns aligned without manual widths. */}
      <div
        role="row"
        className="grid items-center"
        style={{
          gridTemplateColumns: gridCols,
          padding: '10px 14px',
          borderBottom: '1px solid var(--edge-1)',
          background: 'var(--surface-1)',
          position: 'sticky',
          top: 0,
          zIndex: 1,
        }}
      >
        {columns.map((col) => {
          const isSorted = sort?.key === col.key;
          const Chevron = !col.sortable
            ? null
            : isSorted
              ? (sort.dir === 'asc' ? ChevronUp : ChevronDown)
              : ChevronsUpDown;
          return (
            <button
              key={col.key}
              type="button"
              onClick={() => toggleSort(col.key)}
              disabled={!col.sortable}
              className="t-ui-subhead inline-flex items-center"
              style={{
                justifyContent: col.align === 'right' ? 'flex-end' : col.align === 'center' ? 'center' : 'flex-start',
                color: isSorted ? 'var(--text-1)' : 'var(--text-2)',
                background: 'transparent',
                border: 'none',
                padding: 0,
                cursor: col.sortable ? 'pointer' : 'default',
                gap: 4,
                textAlign: col.align ?? 'left',
                width: '100%',
              }}
            >
              <span>{col.header}</span>
              {Chevron && (
                <Chevron
                  size={14}
                  strokeWidth={1.75}
                  style={{ color: isSorted ? 'var(--text-1)' : 'var(--text-4)' }}
                />
              )}
            </button>
          );
        })}
      </div>

      {/* BODY — virtualized when row count exceeds threshold. */}
      <div
        ref={containerRef}
        role="rowgroup"
        tabIndex={onRowClick ? 0 : undefined}
        onKeyDown={handleKeyDown}
        style={{
          maxHeight: shouldVirtualize ? '60vh' : 'none',
          overflow: shouldVirtualize ? 'auto' : 'visible',
          outline: 'none',
        }}
      >
        {topPad > 0 && <div style={{ height: topPad }} aria-hidden="true" />}
        {visibleRows.map((row, visibleIdx) => {
          const absoluteIdx = shouldVirtualize
            ? Math.floor(topPad / rowHeight) + visibleIdx
            : visibleIdx;
          const rowId = getRowId(row, absoluteIdx);
          const isActive = activeRowId != null && rowId === activeRowId;
          const isFocused = focusedIndex === absoluteIdx;
          return (
            <div
              key={rowId}
              role="row"
              onClick={() => onRowClick?.(row, absoluteIdx)}
              className="grid items-center"
              style={{
                gridTemplateColumns: gridCols,
                height: rowHeight,
                padding: '0 14px',
                borderBottom: absoluteIdx === sortedRows.length - 1 ? 'none' : '1px solid var(--edge-1)',
                cursor: onRowClick ? 'pointer' : 'default',
                background: isActive
                  ? 'var(--surface-2)'
                  : isFocused
                    ? 'var(--surface-2)'
                    : 'transparent',
                transition: 'background 0.12s ease',
              }}
              onMouseEnter={(e) => {
                if (!isActive && !isFocused) e.currentTarget.style.background = 'var(--surface-2)';
              }}
              onMouseLeave={(e) => {
                if (!isActive && !isFocused) e.currentTarget.style.background = 'transparent';
              }}
            >
              {columns.map((col) => {
                const getVal = col.accessor ?? ((r) => r[col.key]);
                const value = getVal(row);
                return (
                  <div
                    key={col.key}
                    role="cell"
                    className={cn('truncate', col.className)}
                    style={{
                      textAlign: col.align ?? 'left',
                      color: 'var(--text-1)',
                      fontSize: 13,
                      fontFamily: col.align === 'right' ? 'var(--font-mono)' : 'var(--font-sans)',
                      fontVariantNumeric: col.align === 'right' ? 'tabular-nums' : 'normal',
                    }}
                  >
                    {col.render ? col.render(value, row, absoluteIdx) : value}
                  </div>
                );
              })}
            </div>
          );
        })}
        {bottomPad > 0 && <div style={{ height: bottomPad }} aria-hidden="true" />}
      </div>
    </div>
  );
}

export default DataTable;
