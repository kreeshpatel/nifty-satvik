import { monthlyReturnsFromCurve, monthlyRFromTrades, monthlySeries } from './monthly';

describe('the defect this replaces', () => {
  it('no longer turns five +10% trades into a +50% month', () => {
    // The old code did `sum += return_pct`. These five trades were a +50% bar.
    const trades = Array.from({ length: 5 }, (_, i) => ({
      exit_date: `2026-07-${10 + i}`, return_pct: 10, r_multiple: 1,
    }));
    const [july] = monthlyRFromTrades(trades);
    expect(july.value).toBe(5);          // +5R, which is a real quantity
    expect(july.value).not.toBe(50);
  });

  it('does not let trade COUNT masquerade as performance', () => {
    // Two months of identical average quality, different volume. Under the old sum-of-percent
    // the busy month looked four times better; in R it is four times more risk taken, which is
    // what actually happened, and the equity curve settles it properly when present.
    const busy = Array.from({ length: 8 }, (_, i) => ({ exit_date: `2026-06-0${(i % 9) + 1}`, r_multiple: 0.5 }));
    const quiet = Array.from({ length: 2 }, (_, i) => ({ exit_date: `2026-07-0${i + 1}`, r_multiple: 0.5 }));
    const [jun, jul] = monthlyRFromTrades([...busy, ...quiet]);
    expect(jun.count).toBe(8);
    expect(jul.count).toBe(2);
  });
});

describe('monthlyReturnsFromCurve', () => {
  const history = [
    { date: '2026-05-29', value: 1000 },
    { date: '2026-06-15', value: 1050 },
    { date: '2026-06-30', value: 1100 },   // month-end June
    { date: '2026-07-31', value: 1155 },   // +5% on June
  ];

  it('measures month-end to month-end, not from a mid-month point', () => {
    const out = monthlyReturnsFromCurve(history);
    expect(out.map((d) => d.key)).toEqual(['2026-06', '2026-07']);
    expect(out[0].value).toBeCloseTo(10, 6);   // 1000 -> 1100
    expect(out[1].value).toBeCloseTo(5, 6);    // 1100 -> 1155
  });

  it('omits the first month rather than inventing a baseline for it', () => {
    expect(monthlyReturnsFromCurve(history).some((d) => d.key === '2026-05')).toBe(false);
  });

  it('is empty for a single month — one point is not a return', () => {
    expect(monthlyReturnsFromCurve([{ date: '2026-06-30', value: 1000 }])).toEqual([]);
  });

  it('ignores non-numeric points instead of scoring them as zero', () => {
    const dirty = [{ date: '2026-06-30', value: 1000 }, { date: '2026-07-31', value: null },
                   { date: '2026-08-31', value: 1200 }];
    expect(monthlyReturnsFromCurve(dirty).map((d) => d.key)).toEqual(['2026-08']);
  });
});

describe('monthlyRFromTrades', () => {
  it('skips a trade with no r_multiple rather than counting it flat', () => {
    const out = monthlyRFromTrades([
      { exit_date: '2026-07-01', r_multiple: 2 },
      { exit_date: '2026-07-02' },                 // unmeasured
    ]);
    expect(out[0].value).toBe(2);
    expect(out[0].count).toBe(1);
  });

  it('reads close_date when exit_date is absent (the weekly record uses close_date)', () => {
    const out = monthlyRFromTrades([{ close_date: '2026-07-27', r_multiple: -0.93 }]);
    expect(out[0].key).toBe('2026-07');
    expect(out[0].value).toBeCloseTo(-0.93, 6);
  });
});

describe('monthlySeries', () => {
  it('prefers the equity curve and says so', () => {
    const s = monthlySeries({
      history: [{ date: '2026-06-30', value: 100 }, { date: '2026-07-31', value: 110 }],
      trades: [{ exit_date: '2026-07-05', r_multiple: 3 }],
    });
    expect(s.unit).toBe('pct');
    expect(s.data[0].value).toBeCloseTo(10, 6);
  });

  it('falls back to R and labels the unit, so it cannot be read as a percentage', () => {
    const s = monthlySeries({ history: [], trades: [{ exit_date: '2026-07-05', r_multiple: 3 }] });
    expect(s.unit).toBe('R');
    expect(s.source).toMatch(/not a percentage/);
  });

  it('returns nothing rather than a misleading empty chart', () => {
    expect(monthlySeries({}).data).toEqual([]);
  });
});
