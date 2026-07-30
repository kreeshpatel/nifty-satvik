/**
 * PaperRefRecord — the "Paper (ref)" modelled record on the Portfolio page.
 *
 * Renders the bhanushali weekly-swing paper book from /api/portfolio/paper-ref: a summary
 * strip, the NAV series, open positions, and closed trades — all read server-side from the
 * canonical cron-published artifacts, so there is no parallel computation to drift.
 *
 * Why this exists alongside the page's existing Paper mode: the positions half was already
 * live (it reads results/paper_portfolio_weekly.json), but the equity curve pointed at
 * results/paper_ledger_history.csv — the old momentum paper broker's ledger, whose producer
 * was removed with the momentum book. That file is absent from the repo, so the curve was
 * rendering an empty series that merely looked live. This reads the live NAV instead.
 *
 * Honesty rules baked in, not optional:
 *   - labelled modelled fills / reference book / not live holdings / not advice;
 *   - the data-freshness stamp is shown prominently, not buried;
 *   - zero closed trades renders an explicit empty state — never a fabricated row.
 *
 * House design system only: pv3-* classes, tabular-nums on every figure, no new dependency
 * (the sparkline is an inline SVG polyline, the same approach DashboardV3 uses).
 */
import React, { useMemo } from 'react';
import { usePaperRef } from '@/hooks/queries/usePaperRef';

const fmtN = (n) =>
  n == null || Number.isNaN(n) ? '—' : Number(n).toLocaleString('en-IN', { maximumFractionDigits: 2 });
const fmtL = (n) => {
  if (n == null || Number.isNaN(n)) return '—';
  const v = Number(n);
  return Math.abs(v) >= 1e5 ? `₹${(v / 1e5).toFixed(2)}L` : `₹${fmtN(v)}`;
};
const fmtPct = (n) => (n == null || Number.isNaN(n) ? '—' : `${Number(n) >= 0 ? '+' : ''}${Number(n).toFixed(2)}%`);
const fmtR = (n) => (n == null || Number.isNaN(n) ? '—' : `${Number(n) >= 0 ? '+' : ''}${Number(n).toFixed(2)}R`);
const tone = (n) => (n == null ? '' : Number(n) >= 0 ? 'num-bull' : 'num-bear');

/** Inline SVG NAV sparkline — no charting dependency (same approach as DashboardV3). */
function NavSpark({ points }) {
  const d = useMemo(() => {
    if (!points || points.length < 2) return null;
    const vals = points.map((p) => p.value);
    const lo = Math.min(...vals);
    const hi = Math.max(...vals);
    const span = hi - lo || 1;
    const W = 260;
    const H = 44;
    return points
      .map((p, i) => {
        const x = (i / (points.length - 1)) * W;
        const y = H - ((p.value - lo) / span) * (H - 4) - 2;
        return `${i === 0 ? 'M' : 'L'}${x.toFixed(1)},${y.toFixed(1)}`;
      })
      .join(' ');
  }, [points]);

  if (!d) return <div className="pv3-t-ui-footnote">NAV series accumulates daily.</div>;
  const up = points[points.length - 1].value >= points[0].value;
  return (
    <svg viewBox="0 0 260 44" width="100%" height="44" preserveAspectRatio="none"
         role="img" aria-label="Paper book NAV series">
      <path d={d} fill="none" strokeWidth="1.6" vectorEffect="non-scaling-stroke"
            stroke={up ? 'var(--bull)' : 'var(--bear)'} />
    </svg>
  );
}


const STATUS_LABEL = {
  filled: 'Filled', pending: 'Pending', lapsed: 'Lapsed', skipped: 'Skipped', unknown: 'Unknown',
};

/** Every card the scanner issued and what became of it — the discipline, not just the outcomes. */
function Recommendations({ rows, retention, isLoading }) {
  const [showPrior, setShowPrior] = React.useState(false);
  const weeks = React.useMemo(
    () => Array.from(new Set((rows || []).map((r) => r.week).filter(Boolean))).sort().reverse(),
    [rows],
  );
  const current = weeks[0] || null;
  const thisWeek = (rows || []).filter((r) => r.week === current);
  const prior = (rows || []).filter((r) => r.week !== current);

  const Row = ({ r }) => (
    <React.Fragment>
      <div className="pv3-td">
        <div className="pv3-td-name-sym">{r.ticker}</div>
        <div className="pv3-td-name-full tabular-nums">{r.week}{r.grade ? ` · ${r.grade}` : ''}</div>
      </div>
      <div className="pv3-td pv3-td-r tabular-nums">
        {r.entry_low != null && r.entry_high != null ? `${fmtN(r.entry_low)}–${fmtN(r.entry_high)}` : fmtN(r.entry)}
      </div>
      <div className="pv3-td pv3-td-r tabular-nums" style={{ color: 'var(--bear)' }}>{fmtN(r.stop)}</div>
      <div className="pv3-td pv3-td-r tabular-nums" style={{ color: 'var(--bull)' }}>{fmtN(r.target)}</div>
      <div className="pv3-td pv3-td-r tabular-nums">
        {r.rr_at_zone_low != null ? `${r.rr_at_zone_low.toFixed(2)}` : '—'}
      </div>
      <div className={`pv3-td pv3-td-r tabular-nums ${r.late_in_zone ? 'num-bear' : ''}`}>
        {r.rr_at_price != null ? (
          <>
            {r.rr_at_price.toFixed(2)}
            {r.late_in_zone && <span className="pv3-badge pv3-badge-skipped" style={{ marginLeft: 6 }}>Late</span>}
          </>
        ) : '—'}
        {r.position_in_zone != null && (
          <div className="pv3-td-name-full tabular-nums">{r.position_in_zone.toFixed(0)}% into zone</div>
        )}
      </div>
      <div className="pv3-td pv3-td-r tabular-nums">{r.buy_window_until || '—'}</div>
      <div className="pv3-td pv3-td-r">
        <span className={`pv3-badge pv3-badge-${r.status}`}>{STATUS_LABEL[r.status] || r.status}</span>
      </div>
      {r.status_reason && (
        <div className="pv3-rec-why" style={{ gridColumn: '1 / -1' }}>{r.status_reason}</div>
      )}
    </React.Fragment>
  );

  return (
    <>
      <div className="pv3-card-head" style={{ marginTop: 16 }}>
        <div>
          <div className="pv3-t-ui-headline">Recommendations</div>
          <div className="pv3-t-ui-footnote">
            Every card issued and its outcome · printed zone/stop/target are verbatim; R:R now is live context, not a reprint
          </div>
        </div>
        <span className="pv3-t-ui-footnote tabular-nums">{(rows || []).length} cards</span>
      </div>

      <div className="pv3-paper-table pv3-rec-table" role="table" aria-label="Issued recommendations">
        <div className="pv3-th">Symbol</div>
        <div className="pv3-th pv3-th-r">Buy zone</div>
        <div className="pv3-th pv3-th-r">Stop</div>
        <div className="pv3-th pv3-th-r">Target</div>
        <div className="pv3-th pv3-th-r">R:R zone-low</div>
        <div className="pv3-th pv3-th-r">R:R now</div>
        <div className="pv3-th pv3-th-r">Window</div>
        <div className="pv3-th pv3-th-r">Status</div>
        {isLoading ? (
          <div className="pv3-td" style={{ gridColumn: '1 / -1' }}>Loading…</div>
        ) : thisWeek.length === 0 ? (
          <div className="pv3-closed-empty" style={{ gridColumn: '1 / -1' }}>No cards issued this week.</div>
        ) : thisWeek.map((r) => <Row key={`${r.ticker}-${r.week}`} r={r} />)}
      </div>

      {prior.length > 0 && (
        <>
          <button className="pv3-rec-toggle" onClick={() => setShowPrior((v) => !v)} aria-expanded={showPrior}>
            {showPrior ? 'Hide' : 'Show'} prior weeks ({prior.length})
          </button>
          {showPrior && (
            <div className="pv3-paper-scroll">
              <div className="pv3-paper-table pv3-rec-table" role="table" aria-label="Prior week recommendations">
                <div className="pv3-th">Symbol</div>
                <div className="pv3-th pv3-th-r">Buy zone</div>
                <div className="pv3-th pv3-th-r">Stop</div>
                <div className="pv3-th pv3-th-r">Target</div>
                <div className="pv3-th pv3-th-r">R:R zone-low</div>
                <div className="pv3-th pv3-th-r">R:R now</div>
                <div className="pv3-th pv3-th-r">Window</div>
                <div className="pv3-th pv3-th-r">Status</div>
                {prior.map((r) => <Row key={`${r.ticker}-${r.week}`} r={r} />)}
              </div>
            </div>
          )}
        </>
      )}

      {retention && retention.archive_present === false && (
        <div className="pv3-t-ui-footnote" style={{ marginTop: 8 }}>{retention.note}</div>
      )}
    </>
  );
}

export default function PaperRefRecord() {
  const { data, isLoading, isError } = usePaperRef();

  const s = data?.summary || {};
  const positions = data?.positions || [];
  const closed = data?.closed || [];
  const nav = data?.nav || [];

  const asOf = useMemo(() => {
    if (!data?.as_of) return null;
    const dt = new Date(data.as_of);
    return Number.isNaN(dt.getTime()) ? String(data.as_of) : dt.toLocaleString('en-IN', {
      dateStyle: 'medium', timeStyle: 'short',
    });
  }, [data]);

  if (isError) {
    return (
      <div className="pv3-card">
        <div className="pv3-card-head">
          <div>
            <div className="pv3-t-ui-headline">Paper (ref) · modelled record</div>
            <div className="pv3-t-ui-footnote">Record unavailable right now.</div>
          </div>
        </div>
      </div>
    );
  }

  if (!isLoading && data && data.available === false) {
    return (
      <div className="pv3-card">
        <div className="pv3-card-head">
          <div>
            <div className="pv3-t-ui-headline">Paper (ref) · modelled record</div>
            <div className="pv3-t-ui-footnote">
              {data.note || 'Not available for this account.'}
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="pv3-card">
      <div className="pv3-card-head">
        <div>
          <div className="pv3-t-ui-headline">Paper (ref) · modelled record</div>
          <div className="pv3-t-ui-footnote">
            Modelled fills on a paper reference book · not live holdings · not advice
          </div>
        </div>
        <span className="pv3-t-ui-footnote tabular-nums">
          {isLoading ? 'loading…' : asOf ? `as of ${asOf}` : 'freshness unknown'}
        </span>
      </div>

      {/* Summary strip */}
      <div className="pv3-stat-strip">
        {[
          ['NAV', fmtL(s.total_value)],
          ['Since inception', fmtPct(s.since_inception_pct), tone(s.since_inception_pct)],
          ['From peak', fmtPct(s.drawdown_from_peak_pct), tone(s.drawdown_from_peak_pct)],
          ['Open', `${s.n_positions ?? 0}`],
          ['Closed', `${s.total_trades ?? 0}`],
          ['Cash', fmtL(s.cash)],
        ].map(([label, value, cls]) => (
          <div className="pv3-stat" key={label}>
            <div className="pv3-t-ui-micro">{label}</div>
            <div className={`pv3-t-num-small tabular-nums ${cls || ''}`}>{isLoading ? '—' : value}</div>
          </div>
        ))}
      </div>

      {/* NAV sparkline */}
      <div style={{ marginTop: 12 }}>
        <div className="pv3-t-ui-micro">NAV{nav.length ? ` · ${nav.length} points since ${nav[0].date}` : ''}</div>
        <NavSpark points={nav} />
      </div>

      <Recommendations
        rows={data?.recommendations}
        retention={data?.retention}
        isLoading={isLoading}
      />

      {/* Open positions */}
      <div className="pv3-card-head" style={{ marginTop: 16 }}>
        <div className="pv3-t-ui-headline">Open positions</div>
      </div>
      <div className="pv3-paper-table" role="table" aria-label="Paper book open positions">
        <div className="pv3-th">Symbol</div>
        <div className="pv3-th pv3-th-r">Entry</div>
        <div className="pv3-th pv3-th-r">Stop</div>
        <div className="pv3-th pv3-th-r">Mark</div>
        <div className="pv3-th pv3-th-r">Unreal.</div>
        <div className="pv3-th pv3-th-r">R</div>
        <div className="pv3-th pv3-th-r">Days</div>
        {isLoading ? (
          <div className="pv3-td" style={{ gridColumn: '1 / -1' }}>Loading…</div>
        ) : positions.length === 0 ? (
          <div className="pv3-closed-empty" style={{ gridColumn: '1 / -1' }}>No open positions.</div>
        ) : positions.map((p) => (
          <React.Fragment key={p.ticker}>
            <div className="pv3-td">
              <div className="pv3-td-name-sym">{p.ticker}</div>
              <div className="pv3-td-name-full tabular-nums">{p.entry_date}</div>
            </div>
            <div className="pv3-td pv3-td-r tabular-nums">{fmtN(p.entry_price)}</div>
            <div className="pv3-td pv3-td-r tabular-nums" style={{ color: 'var(--bear)' }}>{fmtN(p.stop)}</div>
            <div className="pv3-td pv3-td-r tabular-nums">{fmtN(p.current_price)}</div>
            <div className={`pv3-td pv3-td-r tabular-nums ${tone(p.unrealised_pnl)}`}>
              {fmtPct(p.unrealised_pnl_pct)}
            </div>
            <div className={`pv3-td pv3-td-r tabular-nums ${tone(p.unrealised_r)}`}>{fmtR(p.unrealised_r)}</div>
            <div className="pv3-td pv3-td-r tabular-nums">{p.days_held}d</div>
          </React.Fragment>
        ))}
      </div>

      {/* Closed trades */}
      <div className="pv3-card-head" style={{ marginTop: 16 }}>
        <div className="pv3-t-ui-headline">Closed trades</div>
        <span className="pv3-t-ui-footnote tabular-nums">{closed.length} recorded</span>
      </div>
      <div className="pv3-paper-scroll">
        <div className="pv3-paper-table pv3-paper-table-closed" role="table" aria-label="Paper book closed trades">
          <div className="pv3-th">Symbol</div>
          <div className="pv3-th pv3-th-r">Entry</div>
          <div className="pv3-th pv3-th-r">Exit</div>
          <div className="pv3-th pv3-th-r">Reason</div>
          <div className="pv3-th pv3-th-r">R</div>
          {isLoading ? (
            <div className="pv3-td" style={{ gridColumn: '1 / -1' }}>Loading…</div>
          ) : closed.length === 0 ? (
            <div className="pv3-closed-empty" style={{ gridColumn: '1 / -1' }}>
              No closed trades yet — the book has not exited a position since inception
              {s.inception_date ? ` (${s.inception_date})` : ''}.
            </div>
          ) : closed.map((t, i) => (
            <React.Fragment key={`${t.ticker}-${t.exit_date}-${i}`}>
              <div className="pv3-td">
                <div className="pv3-td-name-sym">{t.ticker}</div>
                <div className="pv3-td-name-full tabular-nums">{t.entry_date}</div>
              </div>
              <div className="pv3-td pv3-td-r tabular-nums">{fmtN(t.entry_price)}</div>
              <div className="pv3-td pv3-td-r tabular-nums">{fmtN(t.exit_price)}</div>
              <div className="pv3-td pv3-td-r">{t.exit_reason || '—'}</div>
              <div className={`pv3-td pv3-td-r tabular-nums ${tone(t.realised_r)}`}>{fmtR(t.realised_r)}</div>
            </React.Fragment>
          ))}
        </div>
      </div>

      <div className="pv3-t-ui-footnote" style={{ marginTop: 12 }}>
        Modelled fills at modelled prices on a reference book. Not live holdings, not a
        recommendation, and not investment advice. Past modelled performance does not indicate
        future results.
      </div>
    </div>
  );
}
