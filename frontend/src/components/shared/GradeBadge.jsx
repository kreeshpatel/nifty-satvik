import React from 'react';
import { cn } from '@/lib/utils';

/**
 * GradeBadge — signal quality grade in a 26px rounded square.
 *
 * Renders `A+`, `A`, `B+`, `B`, `C` from any of:
 *   - literal grade string
 *   - v7_score numeric (0-25 scale, mapped below)
 *   - ml_score numeric (0-1 scale, mapped below)
 *
 * Grade → color per design tokens:
 *   A+ / A   → brand (blue outline)
 *   B+ / B   → text-2 (neutral, no special treatment)
 *   C / none → text-3 (muted)
 *
 * Always monospace so A+ / A / B+ / B / C visually align inside the square.
 */
const GRADE_THRESHOLDS = [
  // [min v7_score, min ml_score, label]
  [20, 0.90, 'A+'],
  [15, 0.80, 'A'],
  [10, 0.70, 'B+'],
  [5,  0.60, 'B'],
  [0,  0,    'C'],
];

export function gradeFromScores({ grade, v7_score, ml_score }) {
  if (grade) return grade;
  const v = typeof v7_score === 'number' ? v7_score : null;
  const m = typeof ml_score === 'number' ? ml_score : null;
  for (const [v7min, mlmin, label] of GRADE_THRESHOLDS) {
    if ((v != null && v >= v7min) || (m != null && m >= mlmin)) return label;
  }
  return 'C';
}

function isBrandGrade(g) {
  return g === 'A+' || g === 'A';
}
function isMutedGrade(g) {
  return g === 'C' || !g;
}

export function GradeBadge({ grade, v7_score, ml_score, className, size = 'md' }) {
  const label = gradeFromScores({ grade, v7_score, ml_score });
  const brand = isBrandGrade(label);
  const muted = isMutedGrade(label);

  const dim = size === 'sm' ? 22 : size === 'lg' ? 32 : 26;
  const fontPx = size === 'sm' ? 11 : size === 'lg' ? 14 : 12;

  return (
    <span
      className={cn('inline-flex items-center justify-center font-mono', className)}
      style={{
        width: dim,
        height: dim,
        borderRadius: 'var(--r-chip)',
        border: `1px solid ${brand ? 'var(--brand-edge)' : 'var(--edge-1)'}`,
        color: brand ? 'var(--brand-hi)' : muted ? 'var(--text-3)' : 'var(--text-2)',
        background: brand ? 'var(--brand-soft)' : 'transparent',
        fontSize: fontPx,
        fontFamily: 'var(--font-mono)',
        fontWeight: 500,
        lineHeight: 1,
        letterSpacing: '-0.01em',
        boxShadow: brand ? 'var(--shadow-sm)' : 'none',
      }}
      aria-label={`Grade ${label}`}
    >
      {label}
    </span>
  );
}

export default GradeBadge;
