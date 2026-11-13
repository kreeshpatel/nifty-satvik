import { cardStatus } from './cards';

const hold = (over = {}, mon = {}) => ({
  ticker: 'TVSMOTOR', status: 'ACTIVE', stop: 3550.1, fill_price: 3905,
  exit_plan: { tranches: [
    { type: 'target', pct: 40, level: 4614.8, do: 'Sell 40% at Rs 4,614.80 (the +2R target)' },
    { type: 'pattern', pct: 40, do: 'Sell 40% on a blow-off week' },
    { type: 'runner', pct: 20, do: 'Hold the last 20% as a runner. Exit only on a weekly CLOSE below the 44-week SMA' },
  ] },
  exit_stage: { target_booked: false, pattern_booked: false, runner_open: true, fraction_remaining: 1, pending_exit: null },
  monitor: { kind: 'hold', stop_breached: false, target_reached: false, dist_to_stop_pct: 9.1, dist_to_target_pct: 18.2, pnl_pct: 1.2, r_multiple: 0.3, ...mon },
  ...over,
});

describe('cardStatus — open trades', () => {
  it('flags a breached stop first, with the action', () => {
    const st = cardStatus(hold({}, { stop_breached: true, dist_to_stop_pct: -1.0 }));
    expect(st.chips[0]).toEqual({ label: 'Stop hit, exit at the next open', tone: 'bear' });
    expect(st.chips.some((c) => c.label === 'Near stop')).toBe(false);
  });

  it('flags +2R reached and near stop', () => {
    expect(cardStatus(hold({}, { target_reached: true })).chips.map((c) => c.label)).toContain('+2R reached');
    expect(cardStatus(hold({}, { dist_to_stop_pct: 1.5 })).chips.map((c) => c.label)).toContain('Near stop');
  });

  it('reads the next instruction off exit_stage, not price', () => {
    expect(cardStatus(hold()).nextStep).toMatch(/\+2R target/);
    const runner = hold({ exit_stage: { target_booked: true, pattern_booked: true, runner_open: true, pending_exit: null } });
    expect(cardStatus(runner).nextStep).toMatch(/weekly CLOSE below the 44-week SMA/);
  });

  it('puts a queued exit ahead of the plan', () => {
    const q = hold({ exit_stage: { target_booked: true, pattern_booked: false, runner_open: true, pending_exit: { kind: 'full', reason: 'stop' } } });
    expect(cardStatus(q).nextStep).toBe('Sell all remaining shares at the next open (stop).');
  });

  it('carries stop, fill and distances through unchanged', () => {
    const st = cardStatus(hold());
    expect([st.stop, st.fill, st.distToStopPct, st.distToTargetPct]).toEqual([3550.1, 3905, 9.1, 18.2]);
  });

  it('prefers the monitor mid-week fill over the modelled price', () => {
    expect(cardStatus(hold({}, { filled_price: 3890 })).fill).toBe(3890);
  });
});

describe('cardStatus — buy cards', () => {
  const buy = (mon) => ({ ticker: 'KALYANKJIL', status: 'FRESH', stop: 560, buy_window: 'buy Mon–Fri this week', buy_window_until: '2026-11-15', monitor: { kind: 'buy', ...mon } });

  it('shows a filled window with its date and price', () => {
    const st = cardStatus(buy({ window_filled: true, filled_on: '2026-11-09', filled_price: 595 }));
    expect(st.window.state.label).toBe('Filled 2026-11-09 at 595');
    expect(st.window.until).toBe('2026-11-15');
    expect(st.fill).toBe(595);
  });

  it('carries the no-chase ceiling', () => {
    expect(cardStatus({ ...buy({}), no_chase_above: 609.76 }).window.noChaseAbove).toBe(609.76);
  });

  it('says when the band has not traded yet', () => {
    expect(cardStatus(buy({ buy_window_open: true, filled_today: false })).window.state.label).toBe('No open inside the band yet');
  });

  it('survives a card with no monitor block', () => {
    const st = cardStatus({ ticker: 'X', status: 'FRESH', stop: 1, buy_window: 'w' });
    expect(st.kind).toBe('buy');
    expect(st.window.text).toBe('w');
    expect(st.chips).toEqual([]);
  });
});
