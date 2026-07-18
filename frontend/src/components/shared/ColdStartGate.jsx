/**
 * ColdStartGate — the forward-honest expectations briefing, shown once per user.
 *
 * This used to live inside SignalsV3, which meant it only fired if the user happened to visit
 * /premove. Post-login lands on /this-week, so a user could record their first buy having never
 * seen the "roughly 4 in 10 positions hit their stop" briefing — the single most important copy in
 * the product, skippable by walking straight ahead.
 *
 * Mounted in the authenticated layout instead, so it gates every route. Dismissable only via the
 * acknowledgement (no overlay/Esc close) — this is a one-time read, not a notification.
 */
import React from 'react';
import { Dialog, DialogContent } from '@/components/ui/dialog';
import { useJourney } from '@/hooks/queries/useJourney';
import { COLD_START, DISCLAIMER } from '@/lib/signalCopy';

export default function ColdStartGate() {
  const journey = useJourney();

  // Never flash the modal while the flag is still loading — a returning user must not see it blink.
  if (journey.isLoading || journey.seen('cold_start_acked')) return null;

  return (
    <Dialog open onOpenChange={() => {}}>
      <DialogContent
        className="border-0 p-0 rsm-dialog"
        style={{ maxWidth: 460 }}
        srTitle={COLD_START.title}
      >
        <div className="rsm ecm">
          <div className="rsm-h"><span>{COLD_START.title}</span></div>
          <ul className="ecm-coldstart-points">
            {COLD_START.points.map((p, i) => <li key={i}>{p}</li>)}
          </ul>
          <div className="ecm-actions" style={{ gridTemplateColumns: '1fr' }}>
            <button
              type="button"
              className="ri-sizer-btn ecm-confirm"
              onClick={() => journey.mark('cold_start_acked')}
            >
              {COLD_START.ack}
            </button>
          </div>
          <div className="rsm-note">{DISCLAIMER}</div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
