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


/**
 * The drawdown halt, as the pre-registration actually defines it.
 *
 * CORRECTED 2026-08-29. The UI carried 15%, sourced from a comment claiming it was "documented in
 * CLAUDE.md". CLAUDE.md documents no such thing, and both governing documents say −50%:
 *
 *   forward/prereg.md §4        — "live max drawdown breaches −50% ... halt new entries
 *                                  immediately; hold existing positions"
 *   forward/prereg_swing.md §5  — "draws down −50% from its logged peak NAV, halt new entries"
 *
 * 15% was not merely unverified, it was inside the range the pre-registration explicitly names as
 * normal: "A −35% or −40% live DD is NOT a halt condition — it is inside designed-for experience
 * (worst realized 12m return −29%; 31% of days spent >20% underwater). Firing there would sell
 * normal pain." With 31% of days beyond 20% underwater, a 15% trigger fires on roughly a third of
 * all days, and its 9% warning band more often than that. An alarm at that rate is not a
 * guardrail; it is noise that trains the reader to ignore the panel.
 *
 * THE WORDING WAS INVERTED TOO. The badge said HARD KILL, which reads as "sell". §4 is explicitly
 * "halt-not-liquidate": "an automatic liquidation at −50% crystallizes the bottom ... The halt
 * stops adding risk and forces a human decision; it does not pre-commit to selling." A risk panel
 * that tells you to do the opposite of the governing rule is worse than one that says nothing.
 *
 * The warning band is the BACKTEST MAX, not an invented fraction of the halt: §4's own rationale
 * calls −50% "a margin beyond the −46.26% backtest max — i.e. the point at which the backtest no
 * longer bounds the realized risk". Crossing −46.26% is therefore a real, documented boundary —
 * you are outside anything the book has been measured through — and it is the only second level
 * these documents support. Nothing here is chosen; both numbers are quoted.
 */
export const DRAWDOWN_HALT_PCT = 50;      // forward/prereg.md §4 · forward/prereg_swing.md §5
export const DRAWDOWN_BACKTEST_MAX_PCT = 46.26;  // forward/prereg.md §3 reference metrics

/** Status for a live drawdown, as a POSITIVE percentage (12.3 means −12.3%). */
export function drawdownStatus(ddPct) {
  if (ddPct === null || ddPct === undefined || !Number.isFinite(Number(ddPct))) return 'unknown';
  const dd = Math.abs(Number(ddPct));
  if (dd >= DRAWDOWN_HALT_PCT) return 'hard';
  if (dd >= DRAWDOWN_BACKTEST_MAX_PCT) return 'soft';
  return 'ok';
}

/** The words. "HALT NEW ENTRIES" because that is the action §4 prescribes — not liquidation. */
export function drawdownLabel(status) {
  switch (status) {
    case 'hard': return 'HALT NEW ENTRIES';
    case 'soft': return 'BEYOND BACKTEST MAX';
    case 'ok':   return 'DRAWDOWN OK';
    default:     return 'DRAWDOWN NOT EVALUATED';
  }
}
