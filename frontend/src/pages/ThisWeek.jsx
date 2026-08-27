/**
 * ThisWeek — the single "do this" surface (/this-week).
 *
 * WHY: the week's actions were spread across three places — the Research table (what to buy), the
 * Portfolio outstanding strip (what to sell), and the daily monitor flags (what just triggered). The
 * user had to synthesise their own to-do list from all three. This page answers one question:
 * "what do I actually do this week?" — and every line carries the action that records it.
 *
 * It ADDS no new judgement: buys come from the model's actionable Grade-A book (sized with the
 * user's own saved capital + risk tier), exits come from the server-derived reconciliation items
 * (model plan − your ledger), and holds are positions with nothing outstanding. Recording a fill
 * clears the line, because reconciliation is derived rather than stored.
 *
 * MISSED EXITS (the "I didn't get out at my stop" case). The book's stop is a weekly-close stop
 * executed at the next open, so a sell the model booked LEAVES the weekly envelope on the following
 * Saturday — and the position the user still holds went dark on the one page meant to instruct it.
 * The daily monitor now re-prices every booked exit (`missed_exits`), reconciliation raises one only
 * for a user whose ledger still shows the shares, and this section states the cost of waiting in the
 * numbers that make it act-on-able: what the record sold at, when, and where the price is now. It is
 * NOT new advice — the exit is the model's own, already taken; only the drift is computed here.
 *
 * CADENCE (the honest version): the book is decided at the Saturday close, but this is NOT a
 * "do nothing until Saturday" product — the +2R tranche is a resting intraweek limit and a stop can
 * breach midweek. So the header states the next scan AND that a midweek trigger is acted on at the
 * next open, matching the engine (weekly-close decision, next-open execution).
 */
import React, { useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { toast } from 'sonner';
import { useSignals } from '@/hooks/queries/useSignals';
import { useReconciliation, useExecutionPositions, useRecordBuy } from '@/hooks/queries/useExecution';
import { useSizerConfig, useSizingPrefs } from '@/hooks/queries/useSizingPrefs';
import { useQuoteBatch } from '@/hooks/queries/useQuoteBatch';
import ExecutionCaptureModal from '@/components/shared/ExecutionCaptureModal';
import { EmptyState } from '@/components/shared/EmptyState';
import { DISCLAIMER } from '@/lib/signalCopy';
import { sizePortfolio, SIZER_STATUS } from '@/lib/sizing';
import '@/styles/this-week.css';

const IST_OFFSET_MIN = 330;
const fmtNum = (n) => (n == null ? '—' : Number(n).toLocaleString('en-IN', { maximumFractionDigits: 2 }));
const money0 = (n) => (n == null ? '—' : `₹${Math.round(Number(n)).toLocaleString('en-IN')}`);

/** Next Saturday 18:00 IST (the weekly scan), as {when, inWords}. */
function nextScan(now = new Date()) {
  const istNow = new Date(now.getTime() + (IST_OFFSET_MIN + now.getTimezoneOffset()) * 60000);
  const d = new Date(istNow);
  d.setHours(18, 0, 0, 0);
  const daysToSat = (6 - d.getDay() + 7) % 7;
  d.setDate(d.getDate() + daysToSat);
  if (d <= istNow) d.setDate(d.getDate() + 7);       // today's 18:00 already passed
  const hrs = Math.round((d - istNow) / 3600000);
  const inWords = hrs < 24 ? `in ${hrs} hour${hrs === 1 ? '' : 's'}`
    : `in ${Math.round(hrs / 24)} day${Math.round(hrs / 24) === 1 ? '' : 's'}`;
  return { when: d.toLocaleDateString('en-IN', { weekday: 'long' }), inWords };
}

const signalIdOf = (s) => {
  const t = String(s?.ticker || s?.sym || '').toUpperCase();
  return s?.signal_id || (t && s?.signal_date ? `${t}__${s.signal_date}` : null);
};

const SEV_TONE = { high: 'bear', action: 'bull', warn: 'warn', info: 'info' };
// Summary chip tone -> the same ladder the sections use, so the header and the body can
// never imply different priorities.
const SUM_TONE = { missed: 'ns-chip--alarm', due: 'ns-chip--warn',
                   buy: 'ns-chip--brand', hold: 'ns-chip--quiet' };

export default function ThisWeek() {
  const signalsQuery = useSignals({ model: 'bhanushali' });
  const reconQuery = useReconciliation();
  const execQuery = useExecutionPositions();
  const cfgQuery = useSizerConfig();
  const prefsQuery = useSizingPrefs();
  const recordBuy = useRecordBuy();

  const [capture, setCapture] = useState(null);
  const [bulkOpen, setBulkOpen] = useState(false);
  const [bulkBusy, setBulkBusy] = useState(false);

  const rawSignals = useMemo(() => signalsQuery.data?.signals ?? [], [signalsQuery.data]);
  const items = reconQuery.data?.items ?? [];
  const positions = useMemo(() => execQuery.data ?? [], [execQuery.data]);
  const openPositions = useMemo(
    () => positions.filter((p) => (Number(p.remaining_qty) || 0) > 0), [positions]);
  const heldIds = useMemo(() => new Set(openPositions.map((p) => p.signal_id)), [openPositions]);

  // ── BUY: the model's actionable book, minus what you already hold ──
  const buyCandidates = useMemo(() => rawSignals.filter((s) => {
    const a = (s.actionability || '').toUpperCase();
    const isBuy = a === 'BUY_OPEN' || a === 'ACTIONABLE_BUY';
    return isBuy && !s.bought_date && !heldIds.has(signalIdOf(s));
  }), [rawSignals, heldIds]);

  const quoteSyms = useMemo(
    () => [...new Set(buyCandidates.map((s) => (s.ticker || '').toUpperCase()).filter(Boolean))],
    [buyCandidates]);
  const quotes = useQuoteBatch(quoteSyms, { enabled: quoteSyms.length > 0 }).data ?? null;

  const capital = prefsQuery.data?.default_capital ?? null;
  const tier = prefsQuery.data?.risk_tier ?? 'medium';
  const tierPct = cfgQuery.data?.tiers?.[tier] ?? 0.02;
  const capPct = cfgQuery.data?.position_cap_pct ?? 0.20;

  // Sized with the user's OWN saved capital + tier — the same pure allocator the Research sizer uses,
  // so "take the book" here and "Calculate" there can never disagree.
  const sized = useMemo(() => {
    if (!capital || buyCandidates.length === 0) return null;
    return sizePortfolio({
      signals: buyCandidates.map((s) => ({
        signalId: signalIdOf(s), sym: (s.ticker || '').toUpperCase(), entry: s.entry, stop: s.stop,
        buyHigh: s.entry_high ?? s.entry, ltp: quotes?.[(s.ticker || '').toUpperCase()]?.last_price ?? s.current_price,
      })),
      heldSignalIds: [...heldIds], capital, tierPct, capPct,
    });
  }, [buyCandidates, capital, tierPct, capPct, heldIds, quotes]);

  const fundedRows = useMemo(
    () => (sized?.rows ?? []).filter((r) => r.status === SIZER_STATUS.FUNDED), [sized]);

  const exits = items.filter((i) => i.type === 'SELL_DUE' || i.type === 'STALE_HOLD');
  // Rendered in their OWN section rather than folded into "Exits due": an exit that is still due is
  // on-plan, and one you have already missed is not. Collapsing the two would let the urgent case
  // inherit the calm copy of the ordinary one.
  const missedExits = items.filter((i) => i.type === 'MISSED_EXIT');
  const actionable = [...exits, ...missedExits];
  const quietHolds = openPositions.filter((p) => !actionable.some((e) => e.signal_id === p.signal_id));

  // The page's own shape, stated before it is scrolled. Ordered the way the sections are — sells
  // before buys — so the summary and the body can never imply different priorities. Holds are
  // counted but toned down: they are the absence of work, not a fifth item on the list.
  const summary = [
    missedExits.length && { k: 'missed', n: missedExits.length, label: missedExits.length === 1 ? 'missed exit' : 'missed exits' },
    exits.length && { k: 'due', n: exits.length, label: exits.length === 1 ? 'exit due' : 'exits due' },
    buyCandidates.length && { k: 'buy', n: buyCandidates.length, label: buyCandidates.length === 1 ? 'buy open' : 'buys open' },
    quietHolds.length && { k: 'hold', n: quietHolds.length, label: 'holding' },
  ].filter(Boolean);

  const loading = signalsQuery.isLoading || reconQuery.isLoading || execQuery.isLoading;
  const nothingToDo = !loading && buyCandidates.length === 0 && actionable.length === 0;
  const scan = nextScan();

  const sigFor = (signalId) => {
    const s = rawSignals.find((x) => signalIdOf(x) === signalId);
    if (!s) return null;
    return {
      sym: (s.ticker || '').toUpperCase(), signalId, entry: s.entry, stop: s.stop, target: s.target,
      exitLevel: s.exit_plan?.tranches?.find((t) => t.type === 'runner')?.level ?? null,
      current_price: s.current_price,
    };
  };

  /** #3 — record the whole sized book in one action (edit exceptions afterwards). */
  const takeTheBook = async () => {
    setBulkBusy(true);
    let ok = 0;
    for (const r of fundedRows) {
      try {
        await recordBuy.mutateAsync({
          signal_id: r.signalId, ticker: r.sym, qty: r.qty, price: r.entry,
          risk_tier_at_buy: tier,
        });
        ok += 1;
      } catch { /* the hook toasts; keep going so one failure doesn't strand the rest */ }
    }
    setBulkBusy(false);
    setBulkOpen(false);
    toast.success(`Recorded ${ok} of ${fundedRows.length} buys`, {
      description: 'Edit any that filled at a different price from Portfolio → the position’s trail.',
    });
  };

  if (signalsQuery.error) {
    return <div className="ns-page"><EmptyState title="Couldn’t load this week" body="Try again shortly." /></div>;
  }

  return (
    <div className="ns-page">
      <header className="tw-head">
        <div>
          <div className="ns-kicker">THIS WEEK · WHAT TO DO</div>
          <h1 className="ns-title">This week</h1>
          <p className="ns-sub">
            Everything the model expects of you, in one place. Recording a fill clears its line.
          </p>
          {!loading && summary.length > 0 && (
            <div className="tw-summary">
              {summary.map((s2) => (
                <span className={`ns-chip ${SUM_TONE[s2.k]}`} key={s2.k}>
                  <b className="tnum">{s2.n}</b> {s2.label}
                </span>
              ))}
            </div>
          )}
        </div>
        <div className="tw-cadence">
          <div className="tw-cadence-row">Next scan · <b>{scan.when} 6:00 PM IST</b> <span>({scan.inWords})</span></div>
          {/* The honest cadence: NOT "do nothing until Saturday". */}
          <div className="tw-cadence-note">
            The book is decided at the Saturday close. If a stop or your +2R limit triggers midweek,
            act on the next market open — you don’t wait for the scan.
          </div>
        </div>
      </header>

      {loading && <div className="ns-card ns-prose">Loading this week’s actions…</div>}

      {nothingToDo && (
        <div className="ns-card tw-nothing">
          <div className="tw-nothing-title">Nothing to do this week.</div>
          <div className="ns-prose">
            No new buys cleared the gate and nothing you hold needs action. Sitting on your hands is
            what the backtest assumes you do between scans — idle is the strategy working.
          </div>
        </div>
      )}

      {/* ── MISSED EXITS FIRST: the model is already flat and you are not, so this is the
           only section where every day of delay has a running cost. Sells before buys
           throughout — acting late on an exit costs more than acting late on an entry. ── */}
      {missedExits.length > 0 && (
        <section className="ns-section">
          <div className="ns-section-h">
            <h2>Missed exits <span className="ns-count ns-count--alarm">{missedExits.length}</span></h2>
            <span className="ns-section-sub">
              The model has already sold these. Re-checked every day until you record the sell.
            </span>
          </div>
          {missedExits.map((it) => {
            const drift = Number(it.drift_pct);
            const hasDrift = Number.isFinite(drift);
            return (
              <div className="ns-row ns-row--alarm" key={`${it.signal_id}-missed`}>
                <div className="ns-row-l">
                  <span className="ns-dot num-bear" />
                  <div>
                    <div className="ns-sym">
                      {it.ticker}
                      <span className="ns-tag">sold {it.due_date}</span>
                    </div>
                    <div className="ns-meta">
                      The record sold at <b className="tnum">{fmtNum(it.due_price)}</b>
                      {it.cause ? <> — {it.cause}</> : null}.{' '}
                      Now <b className="tnum">{fmtNum(it.last_close)}</b>
                      {hasDrift && (
                        <>
                          {' '}(<span className={`tnum ${drift < 0 ? 'num-bear' : 'num-bull'}`}>
                            {drift > 0 ? '+' : ''}{drift.toFixed(1)}%
                          </span>{' '}vs the model's exit)
                        </>
                      )}
                      {it.r_at_exit != null && (
                        <> · booked <b className="tnum">{Number(it.r_at_exit).toFixed(2)}R</b></>
                      )}
                    </div>
                    <div className="ns-meta ns-meta--do">Sell the remainder at market at the next open.</div>
                  </div>
                </div>
                <div className="ns-row-r">
                  <span className="ns-num">{it.remaining_qty} held</span>
                  <button
                    type="button" className="ns-btn ns-btn--primary"
                    onClick={() => {
                      const sig = sigFor(it.signal_id) || {
                        // The card is GONE from the envelope once the model books the exit — which is
                        // exactly when this item exists — so fall back to the item's own numbers
                        // rather than sending the user off to another page to do the same thing.
                        sym: it.ticker, signalId: it.signal_id, current_price: it.last_close,
                        entry: it.entry, stop: it.stop,
                      };
                      setCapture({ mode: 'sell', sig, tranche: 'manual' });
                    }}
                  >
                    Record sell
                  </button>
                </div>
              </div>
            );
          })}
        </section>
      )}

      {/* ── EXITS DUE: on-plan sells, after the off-plan ones above ── */}
      {exits.length > 0 && (
        <section className="ns-section">
          <div className="ns-section-h">
            <h2>Exits due <span className="ns-count">{exits.length}</span></h2>
            <span className="ns-section-sub">From the model’s plan vs your recorded ledger</span>
          </div>
          {exits.map((it) => (
            <div className="ns-row" key={`${it.signal_id}-${it.type}`}>
              <div className="ns-row-l">
                <span className={`ns-dot num-${SEV_TONE[it.severity] || 'info'}`} />
                <div>
                  <div className="ns-sym">{it.ticker}</div>
                  <div className="ns-meta">{it.message}</div>
                </div>
              </div>
              <div className="ns-row-r">
                <span className="ns-num">{it.remaining_qty} held</span>
                <button
                  type="button" className="ns-btn ns-btn--primary"
                  onClick={() => {
                    const sig = sigFor(it.signal_id);
                    if (sig) setCapture({ mode: 'sell', sig, tranche: 'manual' });
                    else toast.error('That signal is no longer in the current book', {
                      description: 'Record the sell from Portfolio instead.' });
                  }}
                >
                  Record sell
                </button>
              </div>
            </div>
          ))}
        </section>
      )}

      {/* ── BUYS ── */}
      {buyCandidates.length > 0 && (
        <section className="ns-section">
          <div className="ns-section-h">
            <h2>Buys open <span className="ns-count">{buyCandidates.length}</span></h2>
            <span className="ns-section-sub">
              {capital
                ? `Sized to ${money0(capital)} · ${tier} · ${Math.round(tierPct * 100)}% risk per trade`
                : 'Set your capital on Research → Position sizer to see quantities'}
            </span>
          </div>

          {fundedRows.length > 1 && (
            <div className="tw-bulk">
              <button type="button" className="ns-btn ns-btn--primary ns-btn--lg"
                      onClick={() => setBulkOpen(true)}>
                Take this week’s book ({fundedRows.length})
              </button>
              <span className="tw-bulk-note">Taking the whole ranked book is what the record is built on.</span>
            </div>
          )}

          {buyCandidates.map((s) => {
            const id = signalIdOf(s);
            const sym = (s.ticker || '').toUpperCase();
            const row = (sized?.rows ?? []).find((r) => r.signalId === id);
            return (
              <div className="ns-row" key={id}>
                <div className="ns-row-l">
                  <span className="ns-dot num-info" />
                  <div>
                    <div className="ns-sym">{sym}</div>
                    <div className="ns-meta">
                      Buy {s.entry_low != null && s.entry_high != null
                        ? <>between <b className="tnum">{fmtNum(s.entry_low)}</b>–<b className="tnum">{fmtNum(s.entry_high)}</b></>
                        : <>near <b className="tnum">{fmtNum(s.entry)}</b></>}
                      {' '}· stop <b className="tnum">{fmtNum(s.stop)}</b>
                    </div>
                  </div>
                </div>
                <div className="ns-row-r">
                  <span className="ns-num">
                    {row?.status === SIZER_STATUS.FUNDED ? `${row.qty} sh · ${money0(row.cost)}`
                      : row?.status === SIZER_STATUS.OUT_OF_RANGE ? 'above buy range'
                      : row?.status === SIZER_STATUS.NOT_FUNDED ? 'no cash left'
                      : capital ? '—' : 'set capital'}
                  </span>
                  <button
                    type="button" className="ns-btn"
                    onClick={() => setCapture({
                      mode: 'buy', sizerQty: row?.qty ?? null,
                      sig: { sym, signalId: id, entry: s.entry, stop: s.stop, target: s.target },
                    })}
                  >
                    Record buy
                  </button>
                </div>
              </div>
            );
          })}
        </section>
      )}

      {/* ── HOLDING: explicit "no action" so silence is never ambiguous ── */}
      {quietHolds.length > 0 && (
        <section className="ns-section">
          <div className="ns-section-h">
            <h2>Holding <span className="ns-count">{quietHolds.length}</span></h2>
            <span className="ns-section-sub">Nothing due — the plan is to let these run</span>
          </div>
          {quietHolds.map((p) => (
            <div className="ns-row ns-row--quiet" key={p.signal_id}>
              <div className="ns-row-l">
                <span className="ns-dot num-muted" />
                <div>
                  <div className="ns-sym">{p.ticker}</div>
                  <div className="ns-meta">
                    {p.remaining_qty} sh · avg <span className="tnum">{fmtNum(p.avg_buy_price)}</span>
                  </div>
                </div>
              </div>
              <div className="ns-row-r"><span className="ns-num">no action</span></div>
            </div>
          ))}
        </section>
      )}

      <footer className="ns-foot">
        <Link to="/premove" className="ns-link">Full research book →</Link>
        <Link to="/portfolio" className="ns-link">Your portfolio →</Link>
        <div className="ns-disclaimer">{DISCLAIMER}</div>
      </footer>

      {/* Bulk confirm — shows exactly what will be recorded before it writes. */}
      {bulkOpen && (
        <div className="ns-modal-wrap" role="dialog" aria-modal="true" aria-label="Take this week's book">
          <div className="ns-modal">
            <div className="ns-modal-h">Take this week’s book</div>
            <div className="ns-modal-sub">
              Records a buy for each funded name at its entry price. Edit any that filled differently
              from Portfolio afterwards — corrections are kept as new events, never overwrites.
            </div>
            <div className="tw-modal-list">
              {fundedRows.map((r) => (
                <div className="tw-modal-row" key={r.signalId}>
                  <span className="ns-sym">{r.sym}</span>
                  <span className="tnum">{r.qty} sh @ {fmtNum(r.entry)}</span>
                  <span className="ns-num">{money0(r.cost)}</span>
                </div>
              ))}
            </div>
            <div className="tw-modal-actions">
              <button type="button" className="ns-btn" onClick={() => setBulkOpen(false)} disabled={bulkBusy}>
                Cancel
              </button>
              <button type="button" className="ns-btn ns-btn--primary" onClick={takeTheBook} disabled={bulkBusy}>
                {bulkBusy ? 'Recording…' : `Record ${fundedRows.length} buys`}
              </button>
            </div>
          </div>
        </div>
      )}

      <ExecutionCaptureModal
        open={!!capture} mode={capture?.mode} sig={capture?.sig}
        sizerQty={capture?.sizerQty} tranche={capture?.tranche}
        onClose={() => setCapture(null)}
      />
    </div>
  );
}
