/**
 * Onboarding journey (Stage 6c), moved out of the retired SignalsV3 page so it survives the
 * redesign. Durable per-user memory: GET/POST /api/journey (server-side flags, any device).
 *
 *   <ColdStartDialog />  — "Before your first trade — what normal looks like", shown once per user,
 *                          dismissable only by the acknowledgement (flag `cold_start_acked`).
 *   useLessons()         — returns onRecorded(res, { mode, signalId }, tranche) for
 *                          ExecutionCaptureModal: one-time tips after the user's FIRST recorded
 *                          buy and FIRST profitable +2R partial sell (flags = LESSONS keys).
 */
import { toast } from 'sonner';
import { Dialog, DialogContent } from '@/components/ui/dialog';
import { useJourney } from '@/hooks/queries/useJourney';
import { COLD_START, LESSONS, DISCLAIMER } from '@/lib/signalCopy';

export function ColdStartDialog() {
  const journey = useJourney();
  const open = !journey.isLoading && !journey.seen('cold_start_acked');
  return (
    <Dialog open={open} onOpenChange={() => {}}>
      <DialogContent className="ob-dialog" style={{ maxWidth: 480 }} srTitle={COLD_START.title} hideClose
        onEscapeKeyDown={(e) => e.preventDefault()} onPointerDownOutside={(e) => e.preventDefault()}>
        <div className="ob">
          <h2 className="ob-h">{COLD_START.title}</h2>
          <ul className="ob-points">{COLD_START.points.map((p, i) => <li key={i}>{p}</li>)}</ul>
          <button type="button" className="pf-btn ob-ack" onClick={() => journey.mark('cold_start_acked')}>{COLD_START.ack}</button>
          <p className="ob-note">{DISCLAIMER}</p>
        </div>
      </DialogContent>
    </Dialog>
  );
}

export function useLessons() {
  const journey = useJourney();
  const fire = (flag) => {
    if (journey.isLoading || journey.seen(flag) || !LESSONS[flag]) return;
    const l = LESSONS[flag];
    toast.info(l.title, { description: l.body, duration: 12000 });
    journey.mark(flag);
  };
  // signature matches ExecutionCaptureModal's onRecorded(res, { mode, signalId })
  return (res, { mode, signalId } = {}, tranche = null) => {
    const pos = res?.position;
    if (!signalId || !pos) return;
    if (mode === 'buy') fire('lesson_first_buy');
    if (mode === 'sell' && tranche === 'target' && (pos.realized_pnl ?? 0) > 0) fire('lesson_first_2r');
  };
}
