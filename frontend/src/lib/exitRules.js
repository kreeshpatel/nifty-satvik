// frontend/src/lib/exitRules.js
const pct = (n, sign = true) =>
  n == null || isNaN(n) ? '' : `${sign && n > 0 ? '+' : ''}${Number(n).toFixed(1)}%`;
const rupee = (n) =>
  n == null || isNaN(n) ? '—' : `₹${Number(n).toLocaleString('en-IN', { maximumFractionDigits: 0 })}`;
const grab = (re, str, i = 1) => {
  const m = typeof str === 'string' ? str.match(re) : null;
  return m ? parseFloat(m[i]) : null;
};

export function explainExitRules(signal = {}) {
  const s = signal || {};
  const raw = typeof s.exit_rules === 'string' ? s.exit_rules : '';
  const rules = [];

  if (s.target != null) rules.push({
    id: 'target', icon: '🎯', title: 'Target', tone: 'bull',
    text: `The model is aiming for ${rupee(s.target)}${s.target_pct != null ? ` (${pct(s.target_pct)})` : ''}. ` +
          `We don't blindly hold for it — the rules below can exit sooner.`,
  });

  if (s.stop != null || s.stop_pct != null) rules.push({
    id: 'stop', icon: '🛑', title: 'Cut losses', tone: 'bear',
    text: `We sell if it closes below ${rupee(s.stop)}${s.stop_pct != null ? ` (${pct(s.stop_pct)})` : ''}. ` +
          `This is the most you're risking per share.`,
  });

  const trailPct = grab(/Trail:\s*([\d.]+)%/i, raw);
  const trailAfter = grab(/after\s*\+?([\d.]+)%\s*gain/i, raw);
  if (trailPct != null) rules.push({
    id: 'trail', icon: '🔒', title: 'Protect gains', tone: 'bull',
    text: trailAfter != null
      ? `Once it's up about ${pct(trailAfter, false)}, we lock in profit — selling if it slips ${pct(trailPct, false)} from its peak.`
      : `We trail a ${pct(trailPct, false)} stop below the peak to protect profit.`,
  });

  const partialPct = grab(/Partial:\s*sell\s*([\d.]+)%/i, raw);
  const partialAt = grab(/at\s*\+?([\d.]+)%/i, raw);
  if (partialPct != null && partialPct > 0) rules.push({
    id: 'partial', icon: '✂️', title: 'Take some off', tone: 'neutral',
    text: `At ${pct(partialAt, false)} we sell ${pct(partialPct, false)} and move the stop to breakeven, ` +
          `so the rest rides risk-free.`,
  });

  const reeval = grab(/re-eval at day\s*(\d+)/i, raw) ?? s.hold_days ?? null;
  const maxDay = grab(/extend to\s*(\d+)d/i, raw) ?? s.time_stop_hard_max_days ?? null;
  const extendMin = grab(/pnl\s*>=\s*\+?([\d.]+)%/i, raw);
  if (reeval != null) rules.push({
    id: 'time', icon: '⏱️', title: 'Time check', tone: 'neutral',
    text: `We reassess around day ${reeval}${maxDay ? `, holding at most to day ${maxDay}` : ''}` +
          `${extendMin != null ? `, and only hold longer if it's up at least ${pct(extendMin, false)}` : ''}.`,
  });
  return rules;
}

export function exitRulesSummary(signal = {}) {
  const { target_pct: t, stop_pct: st } = signal || {};
  return t == null || st == null
    ? 'Managed exit with a stop-loss and trailing protection.'
    : `Target ${pct(t)} · stop ${pct(st)} · trailed once in profit.`;
}
