/**
 * The risk-guardrail verdict: what you may conclude from a partially-evaluated kill panel.
 *
 * WHY THIS IS ITS OWN FILE. The Portfolio card computed this inline, with a reducer seeded at
 * 'ok' that returned the accumulator unchanged for an `unknown` cell. Three of the five kill
 * limits are not computed anywhere, so they were permanently `unknown`, so they contributed
 * nothing — and the card printed ALL CLEAR on a 2-of-5 sample.
 *
 * That is the same defect as a monitor reporting `n_missed_exits: 0` after a failed download:
 * "we did not look" rendered as "nothing found". It matters more here, because the sentence a
 * reader takes away is about whether their capital is inside its risk limits.
 *
 * An unknown is not a pass. It is not a breach either — claiming one would be its own
 * fabrication. It is a third thing, and the verdict has to be able to say so.
 */

/** Verdict ranks, worst first. `partial` sits between a real warning and a real all-clear. */
export const VERDICT = {
  HARD: 'hard',
  SOFT: 'soft',
  PARTIAL: 'partial',
  OK: 'ok',
};

/**
 * Reduce guardrail cells to one verdict.
 *
 * A real breach always wins — an unevaluated limit never masks a limit that HAS tripped. Absent
 * any breach, the presence of even one unknown caps the verdict at `partial`: the panel may say
 * "nothing has tripped among the ones I can see", never "all clear".
 */
export function guardrailVerdict(cells = []) {
  if (cells.some((c) => c?.status === 'hard')) return VERDICT.HARD;
  if (cells.some((c) => c?.status === 'soft')) return VERDICT.SOFT;
  if (cells.some((c) => c?.status === 'unknown')) return VERDICT.PARTIAL;
  return cells.length ? VERDICT.OK : VERDICT.PARTIAL;   // nothing evaluated is not an all-clear
}

/** How many cells carry a real answer, for the honest "n of m" the header should state. */
export function guardrailCoverage(cells = []) {
  const known = cells.filter((c) => c?.status && c.status !== 'unknown').length;
  return { known, total: cells.length };
}

/** The words the card shows. `partial` deliberately never contains "clear" or "all". */
export function verdictLabel(verdict, { known, total } = {}) {
  switch (verdict) {
    case VERDICT.HARD: return 'HARD KILL';
    case VERDICT.SOFT: return 'SOFT WARNING';
    case VERDICT.OK:   return 'ALL CLEAR';
    default:           return total ? `NO BREACH IN ${known} OF ${total}` : 'NOT EVALUATED';
  }
}
