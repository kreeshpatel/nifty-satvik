/**
 * DisciplineCard — the Stage-6 behavioral gauge on the Research rail.
 *
 * Renders the user's six-leg geometric discipline score as a live position on the measured Sharpe
 * null segment [0.67 … 1.03] (cherry-picked null → disciplined whole-book), plus the counterfactual
 * "taking the K names you skipped moves you to ~X". Everything comes from the backend gauge
 * (GET /api/execution/discipline) — computed from the user's own ledger, never fabricated; legs
 * without data yet simply don't render.
 */
import React from 'react';
import { useDiscipline } from '@/hooks/queries/useExecution';
import { DISCIPLINE } from '@/lib/signalCopy';

const pct = (v) => `${Math.round(v * 100)}%`;

export default function DisciplineCard() {
  const { data, isLoading } = useDiscipline();
  if (isLoading || !data) return null;

  const { legs = {}, score, sharpe_now, sharpe_floor, sharpe_ceiling,
          skipped_signal_ids = [], sharpe_if_full_coverage } = data;
  const known = Object.entries(legs).filter(([, v]) => v != null);
  if (score == null && known.length === 0) return null;   // nothing recorded yet — no gauge to show

  const span = (sharpe_ceiling ?? 1.03) - (sharpe_floor ?? 0.67);
  const pos = sharpe_now != null ? Math.max(0, Math.min(1, (sharpe_now - sharpe_floor) / span)) : null;
  const nSkipped = skipped_signal_ids.length;
  const canImprove = nSkipped > 0 && sharpe_if_full_coverage != null && sharpe_now != null
    && sharpe_if_full_coverage > sharpe_now;

  return (
    <div className="ri-card">
      <div className="ri-card-h">{DISCIPLINE.title}</div>

      {score != null && (
        <>
          <div className="ri-kv">
            <span>Discipline score</span>
            <b className="num-info tnum">{pct(score)}</b>
          </div>
          {pos != null && (
            <div className="dsc-track" title={DISCIPLINE.explain}>
              <div className="dsc-track-bar">
                <span className="dsc-track-dot" style={{ left: `${pos * 100}%` }} />
              </div>
              <div className="dsc-track-ends tnum">
                <span>{sharpe_floor}</span>
                <span className="dsc-track-now">~{sharpe_now}</span>
                <span>{sharpe_ceiling}</span>
              </div>
            </div>
          )}
          {canImprove && (
            <div className="dsc-improve num-bull">
              Taking the {nSkipped} name{nSkipped === 1 ? '' : 's'} you skipped moves you to
              ~{sharpe_if_full_coverage}.
            </div>
          )}
        </>
      )}

      {known.map(([k, v]) => (
        <div className="ri-kv" key={k}>
          <span>{DISCIPLINE.legLabels[k] || k}</span>
          <b className={`tnum ${v >= 0.9 ? 'num-bull' : v >= 0.6 ? 'num-warn' : 'num-bear'}`}>{pct(v)}</b>
        </div>
      ))}

      <div className="ri-sizer-note">{DISCIPLINE.explain}</div>
    </div>
  );
}
