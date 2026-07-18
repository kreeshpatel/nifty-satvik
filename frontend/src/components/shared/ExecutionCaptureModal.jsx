/**
 * ExecutionCaptureModal — the self-reported buy/sell capture popup (Stage 4, ADR 0011).
 *
 * The site instructs; the user executes on their OWN broker and reports the fill here. Two modes:
 *
 *  - BUY:  quantity + buy price, pre-filled with the sizer's suggested qty and the model's entry.
 *  - SELL: quantity sold + sell price, PARTIAL-AWARE — pre-filled with the tranche the model just
 *          flagged (e.g. 40% of the remaining at the +2R level) and showing the running remainder,
 *          because config P exits in three tranches (40%@2R / 40% pattern / 20% runner).
 *
 * The disciplined default is pre-filled so confirming is one action; editing is the exception (spec §2).
 * Validation is soft — an out-of-range price or oversell shows an inline warning but never blocks the
 * save (spec §3); the durable warnings come back from the server and surface as toasts via the hook.
 */
import React, { useEffect, useMemo, useState } from 'react';
import { Dialog, DialogContent } from '@/components/ui/dialog';
import { useExecutionPosition, useRecordBuy, useRecordSell } from '@/hooks/queries/useExecution';
import { DISCIPLINE } from '@/lib/signalCopy';

const TRANCHE_LABEL = {
  target: 'Tranche 1 · 40% at the +2R target',
  pattern: 'Tranche 2 · 40% on a blow-off / exhaustion week',
  runner: 'Tranche 3 · 20% runner to the 44-week SMA',
  manual: 'Manual sell',
};

const money = (n) =>
  n == null || Number.isNaN(n) ? '—' : `₹${Math.round(n).toLocaleString('en-IN')}`;

export default function ExecutionCaptureModal({
  open, mode = 'buy', sig, sizerQty = null, tranche = null, dayRange = null, onClose, onRecorded,
}) {
  const isSell = mode === 'sell';
  const signalId = sig?.signalId || sig?._signalId || null;

  // For a sell we need the current remaining qty (truth from the ledger) to pre-fill the tranche
  // and show the remainder. Only fetched while the sell popup is open.
  const posQuery = useExecutionPosition(isSell ? signalId : null, { enabled: open && isSell });
  const remaining = posQuery.data?.remaining_qty ?? null;

  const recordBuy = useRecordBuy();
  const recordSell = useRecordSell();
  const busy = recordBuy.isPending || recordSell.isPending;

  const [qty, setQty] = useState('');
  const [price, setPrice] = useState('');
  // Stage 6: co-instructed resting orders (buy mode). Instruct-only (ADR 0011) — the checkbox
  // records what the user says they did; unticked never blocks the save.
  const [restingPlaced, setRestingPlaced] = useState(false);

  // The disciplined default price: buy → the model entry; sell → the flagged tranche's level.
  const defaultPrice = useMemo(() => {
    if (!sig) return '';
    if (!isSell) return sig.entry ?? '';
    if (tranche === 'target') return sig.target ?? sig.exitLevel ?? sig.entry ?? '';
    return sig.exitLevel ?? sig.target ?? sig.current_price ?? '';
  }, [sig, isSell, tranche]);

  // The disciplined default qty: buy → the sizer qty; sell → the tranche fraction of the remainder.
  const defaultQty = useMemo(() => {
    if (!isSell) return sizerQty || '';
    if (remaining == null) return '';
    const frac = tranche === 'runner' ? 0.20 : 0.40;   // 40% target/pattern, 20% runner
    return Math.max(1, Math.round(remaining * frac));
  }, [isSell, sizerQty, remaining, tranche]);

  // Re-seed the fields whenever the popup (re)opens or its computed defaults land.
  useEffect(() => {
    if (!open) return;
    setQty(String(defaultQty ?? ''));
    setPrice(String(defaultPrice ?? ''));
    setRestingPlaced(false);
  }, [open, defaultQty, defaultPrice]);

  const qtyNum = Number(qty);
  const priceNum = Number(price);
  const validQty = Number.isFinite(qtyNum) && qtyNum > 0;
  const validPrice = Number.isFinite(priceNum) && priceNum > 0;

  const remainderAfter = isSell && remaining != null && validQty ? remaining - qtyNum : null;

  // Stage 6 behavioral guards. R at this sell price (1R = entry - stop, from the frozen card).
  const rAtPrice = useMemo(() => {
    const e = Number(sig?.entry), s = Number(sig?.stop);
    return validPrice && e > 0 && s > 0 && e > s ? (priceNum - e) / (e - s) : null;
  }, [sig, validPrice, priceNum]);
  // Winner-cut / fat-tail interstitial: a manual (off-plan) sell, or one that closes the whole
  // position while in profit — the single most expensive user behaviour in the research record.
  const showFatTail = isSell && (tranche === 'manual' || !tranche
    || (remainderAfter != null && remainderAfter <= 0 && tranche === 'runner'))
    && (rAtPrice == null || rAtPrice > 0);
  // Pattern-exit reframe: the blow-off exit always fires after a down-week, so it FEELS like
  // selling the bottom — reframe with the R captured, on schedule.
  const showPatternReframe = isSell && tranche === 'pattern';
  // Co-instructed resting orders (buy mode): the 2R partial limit + the stop.
  const restingLevels = useMemo(() => {
    const e = Number(sig?.entry), s = Number(sig?.stop);
    if (!(e > 0 && s > 0 && e > s)) return null;
    return { limit2r: Number(sig?.target) || e + 2 * (e - s), stop: s };
  }, [sig]);

  // Inline soft warnings (mirror the server's; shown live so the user sees them before saving).
  const warn = useMemo(() => {
    const w = [];
    if (isSell && remaining != null && validQty && qtyNum > remaining)
      w.push(`You're selling ${qtyNum} but only ${remaining} remain.`);
    if (validPrice && dayRange?.low && dayRange?.high && !(priceNum >= dayRange.low && priceNum <= dayRange.high))
      w.push(`Price ${priceNum} is outside today's range [${dayRange.low}, ${dayRange.high}].`);
    return w;
  }, [isSell, remaining, validQty, qtyNum, validPrice, priceNum, dayRange]);

  if (!sig) return null;

  const submit = () => {
    if (!signalId || !validQty || !validPrice) return;
    const done = (res) => { onRecorded?.(res, { mode, signalId }); onClose?.(); };
    if (isSell) {
      recordSell.mutate(
        { signal_id: signalId, qty: qtyNum, price: priceNum, tranche: tranche || 'manual',
          day_low: dayRange?.low, day_high: dayRange?.high },
        { onSuccess: done },
      );
    } else {
      recordBuy.mutate(
        { signal_id: signalId, ticker: sig.sym, qty: qtyNum, price: priceNum,
          note: restingLevels ? `resting orders placed: ${restingPlaced ? 'yes' : 'no'}` : undefined },
        { onSuccess: done },
      );
    }
  };

  return (
    <Dialog open={open} onOpenChange={(o) => !o && onClose?.()}>
      <DialogContent className="border-0 p-0 rsm-dialog" style={{ maxWidth: 400 }}
                     srTitle={`${isSell ? 'Record a sell' : 'Record a buy'} — ${sig.sym}`}>
        <div className="rsm ecm">
          <div className="rsm-h">
            <span>{isSell ? 'Record a sell' : 'Record a buy'} · {sig.sym}</span>
            <span className="rsm-hsub">self-reported · your broker fill</span>
          </div>

          {isSell && (
            <div className="ecm-tranche">
              {TRANCHE_LABEL[tranche] || TRANCHE_LABEL.manual}
              {remaining != null && <span className="ecm-rem tnum"> · {remaining} held</span>}
            </div>
          )}

          <div className="ecm-fields">
            <label className="ecm-field">
              <span>Quantity {isSell ? 'sold' : ''}</span>
              <input
                type="number" min="1" step="1" inputMode="numeric" className="ecm-input tnum"
                value={qty} onChange={(e) => setQty(e.target.value)} autoFocus
              />
            </label>
            <label className="ecm-field">
              <span>{isSell ? 'Sell' : 'Buy'} price</span>
              <input
                type="number" min="0" step="0.05" inputMode="decimal" className="ecm-input tnum"
                value={price} onChange={(e) => setPrice(e.target.value)}
              />
            </label>
          </div>

          <div className="ecm-summary tnum">
            {validQty && validPrice && (
              <span>{isSell ? 'Proceeds' : 'Cost'} ≈ {money(qtyNum * priceNum)}</span>
            )}
            {remainderAfter != null && (
              <span className={remainderAfter < 0 ? 'num-bear' : ''}>
                {' '}· {Math.max(0, remainderAfter)} left after
              </span>
            )}
          </div>

          {warn.map((w, i) => (
            <div key={i} className="ecm-warn num-warn">⚠ {w}</div>
          ))}

          {/* Stage 6 — behavioral guards. Copy nudges; never block (their capital, their report). */}
          {showFatTail && (
            <div className="ecm-guard ecm-guard-bear">{DISCIPLINE.fatTail}</div>
          )}
          {showPatternReframe && (
            <div className="ecm-guard ecm-guard-info">{DISCIPLINE.patternExitReframe(rAtPrice)}</div>
          )}
          {!isSell && restingLevels && (
            <div className="ecm-coinstruct">
              <div className="ecm-guard ecm-guard-info">{DISCIPLINE.coInstruct}</div>
              <div className="ecm-coinstruct-orders tnum">
                <span>1 · SELL 40% limit @ {money(restingLevels.limit2r)} (the +2R target)</span>
                <span>2 · Stop-loss @ {money(restingLevels.stop)}</span>
              </div>
              <label className="ecm-coinstruct-check">
                <input type="checkbox" checked={restingPlaced}
                       onChange={(e) => setRestingPlaced(e.target.checked)} />
                <span>I placed both resting orders on my broker</span>
              </label>
            </div>
          )}

          <div className="ecm-actions">
            <button type="button" className="ri-btn" onClick={() => onClose?.()} disabled={busy}>
              Cancel
            </button>
            <button
              type="button" className="ri-sizer-btn ecm-confirm"
              onClick={submit} disabled={!validQty || !validPrice || busy}
            >
              {busy ? 'Saving…' : isSell ? 'Record sell' : 'Record buy'}
            </button>
          </div>

          <div className="rsm-note">
            You execute on your own broker; this records what you did. It’s your capital and your
            report — the number you enter is what’s kept.
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
