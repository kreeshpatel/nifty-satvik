import { nseToday, parseCalendarDate, positionR, toTargetPct, holdWeek } from './cards';

// The real JSWSTEEL card of 2026-08-21 and its real Monday fill, which is what exposed three of
// these four defects on the live board.
const JSW = { entry: 1293.7, stop: 1250.4, target: 1380.3, buyLow: 1293.7, buyHigh: 1310.6,
              fill: 1298.0, signalDate: '2026-08-21', filledOn: '2026-08-24' };

describe('nseToday', () => {
  // 2026-08-28 02:00 IST === 2026-08-27 20:30 UTC. The old UTC-based version returned the 27th
  // for the whole 00:00-05:30 IST window, and that value gates whether a buy window is open.
  const IST_0200 = Date.UTC(2026, 7, 27, 20, 30);
  const IST_0900 = Date.UTC(2026, 7, 28, 3, 30);
  const IST_2330 = Date.UTC(2026, 7, 28, 18, 0);

  it('is the Indian calendar day in the small hours, not the UTC one', () => {
    expect(new Date(IST_0200).toISOString().slice(0, 10)).toBe('2026-08-27');  // the old answer
    expect(nseToday(IST_0200)).toBe('2026-08-28');                             // the right one
  });

  it('agrees with UTC for the rest of the day', () => {
    expect(nseToday(IST_0900)).toBe('2026-08-28');
    expect(nseToday(IST_2330)).toBe('2026-08-28');
  });
});

describe('parseCalendarDate', () => {
  it('reads a bare date as a local day, so it cannot render as the day before', () => {
    const d = parseCalendarDate('2026-08-28');
    expect([d.getFullYear(), d.getMonth(), d.getDate()]).toEqual([2026, 7, 28]);
  });
  it('returns null for nothing rather than an Invalid Date', () => {
    expect(parseCalendarDate(null)).toBeNull();
    expect(parseCalendarDate('')).toBeNull();
  });
});

describe('positionR', () => {
  it('measures gain and risk from the SAME fill', () => {
    // At the model entry the two conventions agree, which is why the bug hid.
    expect(positionR({ ltp: JSW.target, fill: JSW.entry, stop: JSW.stop })).toBeCloseTo(2.0, 2);
  });

  it('does not flatter a fill above the model entry', () => {
    // Chased 4%: dividing by the model's 43.30 risk gave +0.80R; the real figure is +0.37R.
    const chased = JSW.entry * 1.04;
    expect(positionR({ ltp: JSW.target, fill: chased, stop: JSW.stop })).toBeCloseTo(0.37, 2);
    expect((JSW.target - chased) / (JSW.entry - JSW.stop)).toBeCloseTo(0.80, 2);  // the old answer
  });

  it('is null when the fill is at or under the stop, never a flipped sign', () => {
    expect(positionR({ ltp: 1300, fill: 1250.4, stop: 1250.4 })).toBeNull();
    expect(positionR({ ltp: 1300, fill: 1200, stop: 1250.4 })).toBeNull();
  });
});

describe('toTargetPct', () => {
  it('measures from the mid while the fill is still unknown', () => {
    expect(toTargetPct({ target: JSW.target, buyLow: JSW.buyLow, buyHigh: JSW.buyHigh }))
      .toBeCloseTo(6.00, 2);
  });
  it('prefers the real fill once the window has filled', () => {
    expect(toTargetPct({ target: JSW.target, filledPrice: JSW.fill,
                         buyLow: JSW.buyLow, buyHigh: JSW.buyHigh })).toBeCloseTo(6.34, 2);
  });
  it('falls back to entry when there is no band at all', () => {
    expect(toTargetPct({ target: 110, entry: 100 })).toBeCloseTo(10, 6);
  });
});

describe('holdWeek', () => {
  const at = (iso) => new Date(`${iso}T12:00:00`).getTime();

  it('counts from the fill, not the signal', () => {
    // Signal Sat 21st, filled Mon 24th. On the 30th that is week 1 of the hold, not week 2.
    expect(holdWeek({ filledOn: JSW.filledOn, signalDate: JSW.signalDate, now: at('2026-08-30') })).toBe(1);
    expect(holdWeek({ signalDate: JSW.signalDate, now: at('2026-08-30') })).toBe(2);  // the old answer
  });

  it('falls back to bought_date, then the signal date', () => {
    expect(holdWeek({ boughtDate: '2026-08-24', now: at('2026-08-31') })).toBe(2);
    expect(holdWeek({ signalDate: '2026-08-24', now: at('2026-08-31') })).toBe(2);
  });

  it('never exceeds the cap or drops below week 1', () => {
    expect(holdWeek({ filledOn: '2026-01-01', now: at('2026-08-30') })).toBe(13);
    expect(holdWeek({ filledOn: '2026-08-24', now: at('2026-08-24') })).toBe(1);
  });

  it('is null for a start date in the future rather than a negative week', () => {
    expect(holdWeek({ filledOn: '2026-09-30', now: at('2026-08-30') })).toBeNull();
  });
});
