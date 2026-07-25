/**
 * PositionDetail — one trade's whole story (/position/:signalId).
 *
 * Every event was already stored (the append-only ledger) and the audit trail already had an
 * endpoint — but there was nowhere to SEE a single trade. This is that view, and it answers the
 * question a discipline product exists to answer: "what was I told to do, and what did I actually do?"
 *
 * Three layers, deliberately in this order:
 *   1. THE PLAN — from the IMMUTABLE frozen snapshot, not today's recompute. This is the card as it
 *      was when you acted on it, so the page can never retroactively re-write history in the model's
 *      favour. If the snapshot predates the Stage-2 floor it simply isn't shown (never faked).
 *   2. WHERE YOU ARE — remaining qty, average cost, realized P&L and realized R from your own fills.
 *   3. THE JOURNEY — every event in order, with the R captured at each sell and which tranche it
 *      belonged to. Corrections appear as superseded rows rather than vanishing, because the ledger
 *      is append-only and the audit trail is the point.
 */
import React, { useMemo } from 'react';
import { useParams, Link } from 'react-router-dom';
import { useExecutionPosition, useSignalSnapshot } from '@/hooks/queries/useExecution';
import { EmptyState } from '@/components/shared/EmptyState';
import { DISCLAIMER } from '@/lib/signalCopy';
import '@/styles/position-detail.css';

const num = (n, d = 2) =>
  n == null || Number.isNaN(Number(n)) ? '—'
    : Number(n).toLocaleString('en-IN', { minimumFractionDigits: d, maximumFractionDigits: d });
const money = (n) => (n == null ? '—' : `₹${Math.round(Number(n)).toLocaleString('en-IN')}`);
const signedMoney = (n) =>
  n == null ? '—' : `${Number(n) >= 0 ? '+' : '−'}₹${Math.abs(Math.round(Number(n))).toLocaleString('en-IN')}`;

const TRANCHE_LABEL = {
  target: '+2R target', pattern: 'Blow-off / exhaustion', runner: 'Runner · 44w SMA', manual: 'Manual',
};

const fmtDate = (iso) => {
  if (!iso) return '—';
  try {
    return new Date(iso).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' });
  } catch { return String(iso).slice(0, 10); }
};

export default function PositionDetail() {
  const { signalId } = useParams();
  const posQuery = useExecutionPosition(signalId);
  const snapQuery = useSignalSnapshot(signalId);

  const pos = posQuery.data ?? null;
  const snap = snapQuery.data ?? null;          // may legitimately 404 (pre-floor signals)
  const events = useMemo(() => pos?.events ?? [], [pos]);

  // R for a sell = (price − entry) / (entry − stop), using the FROZEN plan's risk. Without a
  // snapshot we can't know the original risk, so we show nothing rather than guess.
  const riskPerShare = snap && snap.entry != null && snap.stop != null && snap.entry > snap.stop
    ? Number(snap.entry) - Number(snap.stop) : null;
  const rAt = (price) =>
    riskPerShare && snap?.entry != null ? (Number(price) - Number(snap.entry)) / riskPerShare : null;

  // Which planned tranches has the user actually booked?
  const tranches = snap?.exit_plan?.tranches ?? [];
  const bookedTranches = new Set(
    events.filter((e) => e.side === 'SELL' && !e.superseded && e.tranche).map((e) => e.tranche));

  if (posQuery.isLoading) {
    return <div className="pd-page"><div className="pd-card pd-muted">Loading this position…</div></div>;
  }
  if (posQuery.isError || !pos) {
    return (
      <div className="pd-page">
        <EmptyState
          title="No record for this position"
          body="You haven’t recorded any fills against this signal yet. Record a buy from This week or Research and its story will build here."
        />
        <div className="pd-foot"><Link className="pd-link" to="/portfolio">← Back to portfolio</Link></div>
      </div>
    );
  }

  const closed = pos.status === 'CLOSED';

  return (
    <div className="pd-page">
      <header className="pd-head">
        <div>
          <div className="pd-kicker">POSITION · YOUR RECORD</div>
          <h1 className="pd-title">
            {pos.ticker}
            <span className={`pd-status ${closed ? 'pd-status-closed' : 'pd-status-open'}`}>
              {closed ? 'Closed' : 'Open'}
            </span>
          </h1>
          <div className="pd-sub">
            Signal {signalId} · every fill you reported, in order. Corrections are kept, never overwritten.
          </div>
        </div>
      </header>

      {/* ── WHERE YOU ARE ── */}
      <section className="pd-kpis">
        <div className="pd-kpi">
          <span className="pd-kpi-k">{closed ? 'Bought' : 'Holding'}</span>
          <span className="pd-kpi-v tnum">{closed ? pos.total_bought_qty : pos.remaining_qty} sh</span>
        </div>
        <div className="pd-kpi">
          <span className="pd-kpi-k">Average cost</span>
          <span className="pd-kpi-v tnum">{num(pos.avg_buy_price)}</span>
        </div>
        <div className="pd-kpi">
          <span className="pd-kpi-k">Realized P&amp;L</span>
          <span className={`pd-kpi-v tnum ${pos.realized_pnl > 0 ? 'num-bull' : pos.realized_pnl < 0 ? 'num-bear' : ''}`}>
            {pos.total_sold_qty ? signedMoney(pos.realized_pnl) : '—'}
          </span>
        </div>
        <div className="pd-kpi">
          <span className="pd-kpi-k">Realized R</span>
          <span className={`pd-kpi-v tnum ${pos.realized_r > 0 ? 'num-bull' : pos.realized_r < 0 ? 'num-bear' : ''}`}>
            {pos.realized_r != null ? `${pos.realized_r > 0 ? '+' : ''}${pos.realized_r}R` : '—'}
          </span>
        </div>
      </section>

      {/* ── THE PLAN (frozen) ── */}
      {snap ? (
        <section className="pd-section">
          <div className="pd-section-h">
            <h2>The plan you were given</h2>
            <span className="pd-section-sub">Frozen when first published — unchanged by later recomputes</span>
          </div>
          <div className="pd-plan">
            <div className="pd-plan-levels">
              <div><span className="pd-k">Entry</span><span className="tnum">{num(snap.entry)}</span></div>
              <div><span className="pd-k">Stop</span><span className="tnum num-bear">{num(snap.stop)}</span></div>
              <div><span className="pd-k">Target</span><span className="tnum num-bull">{num(snap.target)}</span></div>
              {riskPerShare && (
                <div><span className="pd-k">1R</span><span className="tnum">{num(riskPerShare)}</span></div>
              )}
            </div>
            {tranches.length > 0 && (
              <ol className="pd-tranches">
                {tranches.map((t, i) => {
                  const done = bookedTranches.has(t.type);
                  return (
                    <li key={i} className={`pd-tranche${done ? ' is-done' : ''}`}>
                      <span className="pd-tranche-mark">{done ? '✓' : i + 1}</span>
                      <span className="pd-tranche-body">
                        <b>{t.pct}%</b> · {TRANCHE_LABEL[t.type] || t.type}
                        {t.level != null && <> at <span className="tnum">{num(t.level)}</span></>}
                        {t.arm != null && <> (armed above +{t.arm}R)</>}
                        <span className="pd-tranche-state">{done ? 'booked' : 'pending'}</span>
                      </span>
                    </li>
                  );
                })}
              </ol>
            )}
          </div>
        </section>
      ) : (
        <section className="pd-section">
          <div className="pd-note">
            No frozen plan stored for this signal — it predates the snapshot floor. Your fills below are
            still the full record; only the original card can’t be shown.
          </div>
        </section>
      )}

      {/* ── THE JOURNEY ── */}
      <section className="pd-section">
        <div className="pd-section-h">
          <h2>Your journey <span className="pd-count">{events.filter((e) => !e.superseded).length}</span></h2>
          <span className="pd-section-sub">Every fill you reported, oldest first</span>
        </div>
        <ol className="pd-timeline">
          {events.map((e) => {
            const isBuy = e.side === 'BUY';
            const r = !isBuy ? rAt(e.price) : null;
            return (
              <li key={e.id} className={`pd-event${e.superseded ? ' is-superseded' : ''}`}>
                <span className={`pd-event-dot ${isBuy ? 'num-info' : 'num-bull'}`} />
                <div className="pd-event-body">
                  <div className="pd-event-top">
                    <b className={isBuy ? 'num-info' : 'num-bull'}>{isBuy ? 'Bought' : 'Sold'}</b>
                    <span className="tnum">{e.qty} sh @ {num(e.price)}</span>
                    <span className="pd-event-val tnum">{money(e.qty * e.price)}</span>
                    {e.superseded && <span className="pd-badge">superseded by a correction</span>}
                    {e.corrects_event_id && <span className="pd-badge pd-badge-fix">correction</span>}
                  </div>
                  <div className="pd-event-meta">
                    {fmtDate(e.executed_at || e.created_at)}
                    {!isBuy && e.tranche && <> · {TRANCHE_LABEL[e.tranche] || e.tranche}</>}
                    {r != null && (
                      <> · <span className={r >= 0 ? 'num-bull' : 'num-bear'}>
                        {r >= 0 ? '+' : ''}{r.toFixed(2)}R
                      </span></>
                    )}
                    {e.note && <> · <span className="pd-note-inline">{e.note}</span></>}
                  </div>
                </div>
              </li>
            );
          })}
        </ol>
        {!closed && (
          <div className="pd-open-note">
            Still open — {pos.remaining_qty} sh riding. The runner exits on a weekly close below the
            44-week SMA; nothing to do until the model flags it.
          </div>
        )}
      </section>

      <footer className="pd-foot">
        <Link className="pd-link" to="/portfolio">← Back to portfolio</Link>
        <Link className="pd-link" to="/this-week">This week →</Link>
        <div className="pd-disclaimer">{DISCLAIMER}</div>
      </footer>
    </div>
  );
}
