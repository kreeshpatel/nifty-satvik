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
 *   CITES forward/prereg.md: "live max drawdown breaches **−50%**"
 *   CITES forward/prereg.md: "halt **new entries** immediately; **hold** existing positions"
 *   CITES forward/prereg_swing.md: "draws down **−50%** from its logged peak NAV"
 *
 * 15% was not merely unverified, it was inside the range the pre-registration explicitly names as
 * normal:
 *   CITES forward/prereg.md: "A −35% or −40% live DD is NOT a halt condition"
 *   CITES forward/prereg.md: "31% of days spent >20% underwater"
 *   CITES forward/prereg.md: "Firing there would sell normal pain."
 * With 31% of days beyond 20% underwater, a 15% trigger fires on roughly a third of
 * all days, and its 9% warning band more often than that. An alarm at that rate is not a
 * guardrail; it is noise that trains the reader to ignore the panel.
 *
 * THE WORDING WAS INVERTED TOO. The badge said HARD KILL, which reads as "sell". §4 is explicitly
 * "halt-not-liquidate":
 *   CITES forward/prereg.md: "an automatic liquidation at −50% crystallizes the bottom"
 *   CITES forward/prereg.md: "it does not pre-commit to selling"
 * A risk panel that tells you to do the opposite of the governing rule is worse than one that
 * says nothing.
 *
 * NO WARNING BAND (owner decision, 2026-08-29). A −46.26% level was briefly added here, reasoning
 * that §4's rationale — −50% is "a margin beyond the −46.26% backtest max" — made the backtest max
 * a second boundary. It does not. §4 registers ONE condition, and the backtest max appears there
 * to explain where −50% came from, not as a threshold of its own. Deriving a second level from a
 * sentence explaining the first is exactly the goalpost-invention the pre-registration exists to
 * prevent, and it was my inference rather than the document's.
 *
 * So: one registered condition, one status change. Proximity is still visible — the card renders
 * the drawdown's magnitude and a fill bar against the halt — but proximity is a number the reader
 * reads, not a verdict the panel issues.
 */
export const DRAWDOWN_HALT_PCT = 50;      // forward/prereg.md §4 · forward/prereg_swing.md §5

/** Status for a live drawdown, as a POSITIVE percentage (12.3 means −12.3%). */
export function drawdownStatus(ddPct) {
  if (ddPct === null || ddPct === undefined || !Number.isFinite(Number(ddPct))) return 'unknown';
  const dd = Math.abs(Number(ddPct));
  // One registered condition, so one boundary. Anything short of it is "not a halt condition",
  // which is the document's own phrasing — see the block comment above.
  return dd >= DRAWDOWN_HALT_PCT ? 'hard' : 'ok';
}

/** The words. "HALT NEW ENTRIES" because that is the action §4 prescribes — not liquidation. */
export function drawdownLabel(status) {
  switch (status) {
    case 'hard': return 'HALT NEW ENTRIES';
    case 'ok':   return 'DRAWDOWN OK';
    default:     return 'DRAWDOWN NOT EVALUATED';
  }
}
