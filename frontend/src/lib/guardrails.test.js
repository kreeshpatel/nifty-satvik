import { guardrailVerdict, guardrailCoverage, verdictLabel, VERDICT } from './guardrails';

const ok = { status: 'ok' };
const soft = { status: 'soft' };
const hard = { status: 'hard' };
const unknown = { status: 'unknown' };

describe('guardrailVerdict', () => {
  it('does not call a partially-evaluated panel all clear', () => {
    // The live shape: drawdown and win rate computed, three kill limits not computed anywhere.
    // The old inline reducer seeded at 'ok' and returned it unchanged for unknowns.
    const live = [ok, ok, unknown, unknown, unknown];
    expect(guardrailVerdict(live)).toBe(VERDICT.PARTIAL);
    expect(guardrailVerdict(live)).not.toBe(VERDICT.OK);
  });

  it('says all clear only when every limit was actually evaluated', () => {
    expect(guardrailVerdict([ok, ok, ok, ok, ok])).toBe(VERDICT.OK);
  });

  it('lets a real breach win over an unknown — an unevaluated limit must not mask a tripped one', () => {
    expect(guardrailVerdict([unknown, soft, unknown])).toBe(VERDICT.SOFT);
    expect(guardrailVerdict([unknown, soft, hard])).toBe(VERDICT.HARD);
  });

  it('treats hard as worse than soft regardless of order', () => {
    expect(guardrailVerdict([soft, hard])).toBe(VERDICT.HARD);
    expect(guardrailVerdict([hard, soft])).toBe(VERDICT.HARD);
  });

  it('does not report an all clear for an empty panel', () => {
    expect(guardrailVerdict([])).toBe(VERDICT.PARTIAL);
  });
});

describe('guardrailCoverage', () => {
  it('counts only cells that carry a real answer', () => {
    expect(guardrailCoverage([ok, ok, unknown, unknown, unknown])).toEqual({ known: 2, total: 5 });
  });
});

describe('verdictLabel', () => {
  it('never says "clear" or "all" for a partial panel', () => {
    const label = verdictLabel(VERDICT.PARTIAL, { known: 2, total: 5 });
    expect(label).toBe('NO BREACH IN 2 OF 5');
    expect(label.toLowerCase()).not.toContain('clear');
    expect(label.toLowerCase()).not.toContain('all');
  });

  it('states the breach plainly when there is one', () => {
    expect(verdictLabel(VERDICT.HARD)).toBe('HARD KILL');
    expect(verdictLabel(VERDICT.SOFT)).toBe('SOFT WARNING');
  });

  it('reserves ALL CLEAR for a fully evaluated panel', () => {
    expect(verdictLabel(VERDICT.OK)).toBe('ALL CLEAR');
  });
});
