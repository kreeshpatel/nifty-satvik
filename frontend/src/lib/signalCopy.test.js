import { buyPlan } from './signalCopy';

// The backend added `no_chase_above` (2026-08-11) as the buy-card twin of `max_entry`: the ceiling
// past which chasing a wide signal-week band distorts R. buyPlan must surface it so the "don't chase
// above" guidance reaches both the compact card and the detail drawer with no per-view change.
describe('buyPlan — no_chase_above threading', () => {
  const f = (v) => `₹${v}`;

  test('uses no_chase_above as the buy ceiling when max_entry is absent', () => {
    const p = buyPlan({ entry: 100, no_chase_above: 103 }, f);
    expect(p.state).toBe('ok');
    expect(p.head).toBe('Buy ≤ ₹103');
    expect(p.sub).toMatch(/don.t chase/i);
  });

  test('flags "above limit" when price ran past no_chase_above', () => {
    const p = buyPlan({ entry: 100, no_chase_above: 103, current_price: 108 }, f);
    expect(p.state).toBe('past');
    expect(p.tone).toBe('warn');
    expect(p.head).toContain('103');
  });

  test('max_entry still wins when both are present (no behaviour change to existing feeds)', () => {
    const p = buyPlan({ entry: 100, max_entry: 105, no_chase_above: 103 }, f);
    expect(p.head).toBe('Buy ≤ ₹105');
  });

  test('falls back to "Buy near entry" when neither ceiling is present', () => {
    expect(buyPlan({ entry: 100 }, f).head).toBe('Buy near ₹100');
  });

  test('returns null with no entry reference at all', () => {
    expect(buyPlan({}, f)).toBeNull();
  });
});
