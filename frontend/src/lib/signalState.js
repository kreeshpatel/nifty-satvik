/**
 * Signal tradeable-state classifier.
 *
 * A signal's age alone doesn't tell you whether it's still actionable —
 * price position relative to the entry zone matters far more. This module
 * combines both into a single `tradeableState` label used by the UI.
 *
 * Buckets (for a signal not yet marked bought):
 *   FRESH    — issued today's scan; act at will
 *   IN_ZONE  — issued earlier, price still inside the ATR-derived buy zone
 *   CHASE    — issued earlier, price moved up but still within 1×ATR.
 *              Trade is still possible but R:R is degraded.
 *   MISSED   — price >1×ATR above entry; chasing now is bad odds.
 *   STOPPED  — price at/below stop; setup invalidated.
 *   EXPIRED  — issued too long ago (days_since >= hold_days/3). Premise is stale.
 *
 * `RUNNING` (user already bought this signal) is not returned here — that's
 * tracked in the bought localStorage map and handled separately.
 */

const STOP_MULTIPLIER = 2.0; // matches live stop_mult in models/v1/config.json (NOT the retired config.ATR_STOP_MULTIPLIER=1.5)
const IN_ZONE_ATR_MULTIPLIER = 0.25; // zone half-width
const CHASE_MAX_ATR_MULTIPLIER = 1.0; // above this, it's a missed entry
const AGE_FRACTION_OF_HOLD = 1 / 3; // expire after 1/3 of the hold window

/**
 * Classify a signal's current tradeability.
 * @param {object} sig  Signal object with entry, stop, signal_date, hold_days.
 * @param {number} [currentPrice]  Live price; if absent, age + backend status only.
 * @returns {{state: string, reason: string, degradedRR: number|null}}
 */
export function tradeableState(sig, currentPrice) {
  if (!sig || !sig.entry) {
    return { state: 'UNKNOWN', reason: 'No entry price', degradedRR: null };
  }

  // Backend has already resolved the signal's outcome
  if (sig.status === 'HIT_TARGET') return { state: 'HIT_TARGET', reason: 'Target reached', degradedRR: null };
  if (sig.status === 'HIT_STOP') return { state: 'STOPPED', reason: 'Stop triggered', degradedRR: null };
  if (sig.status === 'EXPIRED') return { state: 'EXPIRED', reason: 'Hold window closed', degradedRR: null };

  // Derive ATR from stop distance. (entry - stop) = STOP_MULTIPLIER × ATR
  const stopDist = sig.entry - sig.stop;
  if (stopDist <= 0) return { state: 'UNKNOWN', reason: 'Bad stop', degradedRR: null };
  const atr = stopDist / STOP_MULTIPLIER;

  const zoneHalf = atr * IN_ZONE_ATR_MULTIPLIER;
  const chaseMax = atr * CHASE_MAX_ATR_MULTIPLIER;

  // Age check — dynamic, relative to hold_days
  const daysSince = Number(sig.days_since ?? 0);
  const holdDays = Number(sig.hold_days ?? 30);
  const ageCap = Math.max(3, Math.floor(holdDays * AGE_FRACTION_OF_HOLD));
  const tooOld = daysSince >= ageCap;

  // Freshness: signal issued today's scan (days_since == 0)
  // We can't tell "fresh from today's scan" purely from data — UI passes it explicitly.

  const price = Number(currentPrice);
  if (!price || isNaN(price)) {
    // No live price — fall back to age/backend status only
    if (tooOld) return { state: 'EXPIRED', reason: `${daysSince}d old (cap ${ageCap}d)`, degradedRR: null };
    return { state: daysSince === 0 ? 'FRESH' : 'IN_ZONE', reason: 'No live price', degradedRR: null };
  }

  // Price-based classification
  if (price <= sig.stop) {
    return { state: 'STOPPED', reason: `Below stop ₹${sig.stop}`, degradedRR: null };
  }

  if (price > sig.entry + chaseMax) {
    return { state: 'MISSED', reason: `Price ran past buy zone`, degradedRR: null };
  }

  if (tooOld) {
    return { state: 'EXPIRED', reason: `${daysSince}d old (cap ${ageCap}d)`, degradedRR: null };
  }

  // Within buy zone — still ideal
  if (Math.abs(price - sig.entry) <= zoneHalf) {
    return { state: daysSince === 0 ? 'FRESH' : 'IN_ZONE', reason: daysSince === 0 ? 'Fresh today' : `${daysSince}d old · in zone`, degradedRR: null };
  }

  // Above zone but below chase max — degraded R:R trade
  if (price > sig.entry + zoneHalf && price <= sig.entry + chaseMax) {
    // New R:R from current price, same stop, same target
    const newRisk = price - sig.stop;
    const newReward = (sig.target || 0) - price;
    const newRR = newRisk > 0 && newReward > 0 ? Number((newReward / newRisk).toFixed(2)) : 0;
    return {
      state: 'CHASE',
      reason: `${((price - sig.entry) / sig.entry * 100).toFixed(1)}% above entry`,
      degradedRR: newRR,
    };
  }

  // Below zone but above stop — dipping into a better entry. Still tradeable.
  return { state: daysSince === 0 ? 'FRESH' : 'IN_ZONE', reason: 'Dipping toward stop', degradedRR: null };
}

/**
 * Human-friendly "issued at" label.
 * issuedDateLabel('2026-04-18', 3) → "Fri 18 Apr · 3d ago"
 */
export function issuedDateLabel(signalDate, daysSince) {
  if (!signalDate) return '';
  const d = new Date(signalDate);
  if (isNaN(d.getTime())) return signalDate;
  const datePart = d.toLocaleDateString('en-IN', { weekday: 'short', day: 'numeric', month: 'short' });
  const n = Number(daysSince ?? 0);
  const relPart = n === 0 ? 'today' : n === 1 ? '1d ago' : `${n}d ago`;
  return `${datePart} · ${relPart}`;
}

/**
 * Map a 0-100 quality score to a letter grade when the backend doesn't ship one.
 * Cutoffs tuned to the observed distribution in signals_history (mostly 70-95).
 */
export function deriveGrade(qualityScore) {
  const q = Number(qualityScore) || 0;
  if (q >= 85) return 'A+';
  if (q >= 75) return 'A';
  if (q >= 65) return 'B+';
  if (q >= 55) return 'B';
  return 'C';
}

/**
 * Color tokens by grade letter. Used for card borders, grade pills, and quality rings.
 */
export const GRADE_TOKENS = {
  'A+': { color: '#22C55E', bg: 'rgba(34,197,94,0.12)' },
  'A':  { color: '#60A5FA', bg: 'rgba(59,130,246,0.14)' },
  'B+': { color: '#FCD34D', bg: 'rgba(252,211,77,0.14)' },
  'B':  { color: '#FBBF24', bg: 'rgba(251,191,36,0.12)' },
  'C':  { color: '#9CA3AF', bg: 'rgba(156,163,175,0.10)' },
};

/**
 * Visual tokens for each state — used on chips across the UI.
 */
export const STATE_TOKENS = {
  FRESH:     { label: 'Fresh',      bg: 'rgba(59,130,246,0.14)', border: 'rgba(96,165,250,0.30)', text: '#93C5FD' },
  IN_ZONE:   { label: 'In zone',    bg: 'rgba(34,197,94,0.12)',  border: 'rgba(34,197,94,0.25)',  text: '#86EFAC' },
  CHASE:     { label: 'Chase',      bg: 'rgba(252,211,77,0.14)', border: 'rgba(252,211,77,0.28)', text: '#FCD34D' },
  MISSED:    { label: 'Missed',     bg: 'rgba(107,114,128,0.12)',border: 'rgba(107,114,128,0.22)',text: '#9CA3AF' },
  STOPPED:   { label: 'Stopped',    bg: 'rgba(239,68,68,0.12)',  border: 'rgba(239,68,68,0.25)',  text: '#FCA5A5' },
  EXPIRED:   { label: 'Expired',    bg: 'rgba(107,114,128,0.12)',border: 'rgba(107,114,128,0.22)',text: '#9CA3AF' },
  HIT_TARGET:{ label: 'Hit target', bg: 'rgba(34,197,94,0.18)',  border: 'rgba(34,197,94,0.30)',  text: '#86EFAC' },
  RUNNING:   { label: 'In position',bg: 'rgba(255,255,255,0.06)',border: 'rgba(255,255,255,0.12)',text: '#E5E7EB' },
  UNKNOWN:   { label: '—',          bg: 'rgba(255,255,255,0.04)',border: 'rgba(255,255,255,0.08)',text: '#9CA3AF' },
};
