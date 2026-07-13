import { sizePortfolio, SIZER_STATUS } from './sizing';

// helper: a signal with a ~stopPct stop below entry and an in-range LTP
const sig = (id, entry, stopPct, extra = {}) => ({
  signalId: id, sym: id.split('__')[0], entry,
  stop: entry * (1 - stopPct), buyHigh: entry * 1.02, ltp: entry, ...extra,
});

const byId = (rows) => Object.fromEntries(rows.map((r) => [r.signalId, r]));

describe('sizePortfolio', () => {
  test('risk-based qty = tierPct*capital / perShareRisk when below the cap', () => {
    // 10L capital, 2% risk = 20k; 10% stop on a 500 stock → perShareRisk 50 → 400 shares.
    // cap term: 20% of 10L = 2L / 500 = 400 → both give 400 (cap-bound exactly at 10% stop).
    const { rows } = sizePortfolio({ signals: [sig('A__2026-05-29', 500, 0.10)], capital: 1_000_000, tierPct: 0.02, capPct: 0.20 });
    expect(rows[0].status).toBe(SIZER_STATUS.FUNDED);
    expect(rows[0].qty).toBe(400);
    expect(rows[0].risk).toBeCloseTo(20_000, 0);
  });

  test('20% single-position cap binds on a tight stop (risk term would be huge)', () => {
    // 4% stop → risk term wants 20k/(0.04*500)=1000 shares; cap term 2L/500=400 → capped to 400.
    const { rows } = sizePortfolio({ signals: [sig('A__2026-05-29', 500, 0.04)], capital: 1_000_000, tierPct: 0.02, capPct: 0.20 });
    expect(rows[0].qty).toBe(400);                 // cap, not the 1000 risk wants
    expect(rows[0].cost).toBe(200_000);            // exactly 20% of capital
  });

  test('entry == stop (zero risk) → cap binds, no NaN/Infinity', () => {
    const { rows } = sizePortfolio({ signals: [{ signalId: 'A__2026-05-29', sym: 'A', entry: 500, stop: 500, buyHigh: 510, ltp: 500 }],
      capital: 1_000_000, tierPct: 0.02, capPct: 0.20 });
    expect(rows[0].qty).toBe(400);                 // 2L / 500
    expect(Number.isFinite(rows[0].cost)).toBe(true);
    expect(rows[0].risk).toBe(0);
  });

  test('out-of-range (LTP above buy-range high) is excluded', () => {
    const s = sig('A__2026-05-29', 500, 0.10, { buyHigh: 505, ltp: 520 }); // chased
    const { rows, totals } = sizePortfolio({ signals: [s], capital: 1_000_000 });
    expect(rows[0].status).toBe(SIZER_STATUS.OUT_OF_RANGE);
    expect(rows[0].qty).toBe(0);
    expect(totals.namesFunded).toBe(0);
  });

  test('range unknown when LTP or buyHigh missing → funded but flagged (never silently in-range)', () => {
    const noLtp = sig('A__2026-05-29', 500, 0.10, { ltp: null });
    const noHi = sig('B__2026-05-29', 500, 0.10, { buyHigh: null });
    const { rows } = sizePortfolio({ signals: [noLtp, noHi], capital: 1_000_000 });
    rows.forEach((r) => {
      expect(r.status).toBe(SIZER_STATUS.FUNDED);
      expect(r.rangeUnknown).toBe(true);
    });
  });

  test('strongest-first funds in order, then skip-and-continue when cash short', () => {
    // Tiny capital: fund the first affordable name, a pricey one gets not-funded, a cheap
    // later one still funds (skip-and-continue, not stop).
    const signals = [
      sig('BIG__2026-05-29', 100_000, 0.10),  // 1 share = 1L; unaffordable after first buy
      sig('CHEAP__2026-05-29', 100, 0.10),    // cheap — fundable from the remainder
    ];
    const { rows } = sizePortfolio({ signals, capital: 120_000, tierPct: 0.02, capPct: 0.20 });
    const m = byId(rows);
    // BIG: cap 20% of 120k = 24k / 100k = 0 shares → not funded
    expect(m['BIG__2026-05-29'].status).toBe(SIZER_STATUS.NOT_FUNDED);
    // CHEAP still funds from remaining cash (loop continued past BIG)
    expect(m['CHEAP__2026-05-29'].status).toBe(SIZER_STATUS.FUNDED);
    expect(m['CHEAP__2026-05-29'].qty).toBeGreaterThan(0);
  });

  test('already-held names are excluded from allocation, shown as bought', () => {
    const s = sig('A__2026-05-29', 500, 0.10);
    const { rows, totals } = sizePortfolio({ signals: [s], heldSignalIds: ['A__2026-05-29'], capital: 1_000_000 });
    expect(rows[0].status).toBe(SIZER_STATUS.BOUGHT);
    expect(rows[0].qty).toBe(0);
    expect(totals.namesFunded).toBe(0);
  });

  test('no capital → every row is no-capital (mark-only), no crash', () => {
    const { rows, totals } = sizePortfolio({ signals: [sig('A__2026-05-29', 500, 0.10)], capital: 0 });
    expect(rows[0].status).toBe(SIZER_STATUS.NO_CAPITAL);
    expect(totals.deployed).toBe(0);
  });

  test('Medium 2% vs High 3%: identical for a ≤10% stop (cap-bound), High larger for a wide stop', () => {
    const tight = sig('T__2026-05-29', 500, 0.10);   // cap binds at both tiers
    const med = sizePortfolio({ signals: [tight], capital: 1_000_000, tierPct: 0.02, capPct: 0.20 });
    const hi = sizePortfolio({ signals: [tight], capital: 1_000_000, tierPct: 0.03, capPct: 0.20 });
    expect(med.rows[0].qty).toBe(hi.rows[0].qty);     // both cap-bound at 400

    const wide = sig('W__2026-05-29', 500, 0.20);     // 20% stop → risk term below cap at 2%
    const medW = sizePortfolio({ signals: [wide], capital: 1_000_000, tierPct: 0.02, capPct: 0.20 });
    const hiW = sizePortfolio({ signals: [wide], capital: 1_000_000, tierPct: 0.03, capPct: 0.20 });
    expect(hiW.rows[0].qty).toBeGreaterThan(medW.rows[0].qty);  // High risks more where the cap doesn't bind
  });

  test('totals reconcile: deployed + cashLeft ≈ capital; atRiskPct sane', () => {
    const signals = [sig('A__2026-05-29', 500, 0.10), sig('B__2026-05-29', 800, 0.12), sig('C__2026-05-29', 300, 0.08)];
    const { rows, totals } = sizePortfolio({ signals, capital: 1_000_000, tierPct: 0.02, capPct: 0.20 });
    const deployed = rows.reduce((a, r) => a + r.cost, 0);
    expect(totals.deployed).toBeCloseTo(deployed, 0);
    expect(totals.deployed + totals.cashLeft).toBeLessThanOrEqual(1_000_000 + 1);
    expect(totals.atRiskPct).toBeGreaterThan(0);
  });
});
