/**
 * Pure position-sizing allocator for the Signals page sizer.
 *
 * Risk-as-%-of-capital, funded strongest-first (signals arrive CRS-sorted), with a
 * single-position cap so a tight stop can't concentrate the book. No React, no I/O —
 * every edge case is unit-tested in sizing.test.js.
 *
 * qty(name) = floor( min( riskRupees / (entry - stop),   // risk-based size
 *                         capPct * capital / entry ) )    // single-position cap
 * where riskRupees = tierPct * capital.
 *
 * Then funded strongest-first against remaining cash; a name that can't afford ≥1 share
 * at its capped size is marked 'not-funded' and we CONTINUE to cheaper later names.
 *
 * Status per row (single enum the modal renders off):
 *   'funded'        sized, qty > 0            (rangeUnknown flag if LTP/buyHigh missing)
 *   'not-funded'    insufficient cash left    (qty 0)
 *   'out-of-range'  LTP is above the buy-range high — chased; excluded (qty 0)
 *   'bought'        already held; excluded from allocation (qty 0)
 *   'no-capital'    no capital entered; can't size (qty 0)
 */

export const SIZER_STATUS = {
  FUNDED: 'funded',
  NOT_FUNDED: 'not-funded',
  OUT_OF_RANGE: 'out-of-range',
  BOUGHT: 'bought',
  NO_CAPITAL: 'no-capital',
};

const floorPos = (x) => (Number.isFinite(x) && x > 0 ? Math.floor(x) : 0);

/**
 * @param {Object}   args
 * @param {Array}    args.signals  CRS-sorted open Grade-A signals. Each:
 *                                 { signalId, sym, entry, stop, buyHigh, ltp }
 * @param {string[]} args.heldSignalIds  signal_ids the user already holds (excluded from allocation)
 * @param {number}   args.capital  FREE capital for new buys
 * @param {number}   args.tierPct  per-trade risk as a fraction of capital (e.g. 0.02)
 * @param {number}   args.capPct   single-position cap as a fraction of capital (e.g. 0.20)
 * @returns {{ rows: Array, totals: Object }}
 */
export function sizePortfolio({ signals = [], heldSignalIds = [], capital = 0, tierPct = 0.02, capPct = 0.20 }) {
  const held = new Set(heldSignalIds || []);
  const cap = Number(capital) || 0;
  const riskRupees = cap > 0 ? tierPct * cap : 0;
  const capNotional = cap > 0 ? capPct * cap : 0;

  let remaining = cap;
  let deployed = 0;
  let atRisk = 0;
  let namesFunded = 0;

  const rows = (signals || []).map((s) => {
    const base = { signalId: s.signalId, sym: s.sym, entry: s.entry, stop: s.stop, qty: 0, cost: 0, risk: 0 };

    if (held.has(s.signalId)) return { ...base, status: SIZER_STATUS.BOUGHT };
    if (cap <= 0) return { ...base, status: SIZER_STATUS.NO_CAPITAL };

    // Range check: only a POSITIVE "LTP above buy-range high" excludes. Missing LTP or
    // buyHigh is "unknown" (a flag) — never silently treated as in-range.
    const rangeUnknown = s.ltp == null || s.buyHigh == null;
    if (!rangeUnknown && s.ltp > s.buyHigh) {
      return { ...base, status: SIZER_STATUS.OUT_OF_RANGE, rangeUnknown: false };
    }

    const entry = Number(s.entry) || 0;
    const perShareRisk = entry - (Number(s.stop) || 0);
    // Zero/negative risk (entry <= stop) ⇒ risk term is Infinity ⇒ the cap binds. No divide-by-zero.
    const byRisk = perShareRisk > 0 ? riskRupees / perShareRisk : Infinity;
    const byCap = entry > 0 ? capNotional / entry : 0;
    const wanted = floorPos(Math.min(byRisk, byCap));
    const affordable = entry > 0 ? Math.floor(remaining / entry) : 0;
    const qty = Math.max(0, Math.min(wanted, affordable));

    if (qty < 1) {
      // Skip-and-continue: this name can't be funded from the cash left, but a cheaper
      // later name still might, so we do NOT stop the loop.
      return { ...base, status: SIZER_STATUS.NOT_FUNDED, rangeUnknown };
    }

    const cost = qty * entry;
    const risk = qty * Math.max(0, perShareRisk);
    remaining -= cost;
    deployed += cost;
    atRisk += risk;
    namesFunded += 1;
    return { ...base, qty, cost, risk, status: SIZER_STATUS.FUNDED, rangeUnknown };
  });

  return {
    rows,
    totals: {
      deployed,
      atRisk,
      atRiskPct: cap > 0 ? (atRisk / cap) * 100 : 0,
      cashLeft: Math.max(0, remaining),
      namesFunded,
    },
  };
}

export default sizePortfolio;
