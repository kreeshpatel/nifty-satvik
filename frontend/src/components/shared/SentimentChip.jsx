/**
 * SentimentChip — compact ±N.NN pill rendering P9 Claude news sentiment.
 *
 * The cron's news_analyzer (src/data/news_analyzer.py) stamps each emitted
 * signal with `p9_sentiment` (float, -1.0..+1.0), `p9_news_reason` (one
 * sentence), `p9_news_risk` (string), and `p9_headlines_used` (int). Until
 * now nothing on the frontend surfaced any of these — the cron was paying
 * for Haiku calls every day and the data was invisible.
 *
 * This chip is the smallest visible surface: a colored pill next to the
 * existing ML score / grade chips on each SignalCard. Hovering or opening
 * the detail drawer reveals the full reason/risk text.
 *
 * Buckets (mirrors the Claude-prompt guidance in news_analyzer.py:194-198):
 *   ≥ +0.5  strong-positive  bull green
 *   +0.2..+0.5  positive     bull green (lighter)
 *   −0.2..+0.2  neutral      muted gray
 *   −0.5..−0.2  negative     bear red (lighter)
 *   ≤ −0.5  strong-negative  bear red
 *
 * The chip is intentionally small — it's metadata, not the primary signal.
 * If `score` is null/undefined or `headlines_used` is 0, render nothing
 * (no news = no sentiment to show; avoid implying we have a 0.00 read).
 *
 * Props
 * -----
 * score:          number | null   p9_sentiment (-1..+1)
 * headlinesUsed:  number          p9_headlines_used; 0 → render null
 * reason:         string          p9_news_reason — surfaced as `title` for tooltip
 * size:           'sm' | 'md'     default 'sm'; 'md' for the detail drawer
 */
import React from 'react';
import { Newspaper } from 'lucide-react';

const TONES = {
  strong_pos: { bg: 'oklch(72% 0.19 145 / 0.20)', fg: 'var(--bull)',  border: 'oklch(72% 0.19 145 / 0.35)' },
  pos:        { bg: 'oklch(72% 0.19 145 / 0.10)', fg: 'var(--bull)',  border: 'oklch(72% 0.19 145 / 0.20)' },
  neutral:    { bg: 'var(--surface-3)',            fg: 'var(--text-3)', border: 'var(--edge-1)' },
  neg:        { bg: 'oklch(66% 0.21 25 / 0.10)',  fg: 'var(--bear)',  border: 'oklch(66% 0.21 25 / 0.20)' },
  strong_neg: { bg: 'oklch(66% 0.21 25 / 0.20)',  fg: 'var(--bear)',  border: 'oklch(66% 0.21 25 / 0.35)' },
};

function bucketFor(score) {
  if (score >= 0.5) return 'strong_pos';
  if (score >= 0.2) return 'pos';
  if (score >= -0.2) return 'neutral';
  if (score >= -0.5) return 'neg';
  return 'strong_neg';
}

export function SentimentChip({ score, headlinesUsed, reason, size = 'sm' }) {
  // No headlines means the analyzer returned a neutral default — don't
  // imply we have a real sentiment read. The cron only emits 0-headlines
  // entries when both yfinance AND Google News failed; never on healthy
  // production runs (today's batch shows 5 headlines per signal).
  if (score === null || score === undefined) return null;
  if (!headlinesUsed || headlinesUsed <= 0) return null;

  const n = Number(score);
  if (!Number.isFinite(n)) return null;

  const tone = TONES[bucketFor(n)];
  const sign = n > 0 ? '+' : '';
  const padding = size === 'md' ? '4px 10px' : '2px 7px';
  const fontSize = size === 'md' ? 12 : 11;
  const iconSize = size === 'md' ? 12 : 11;

  return (
    <span
      className="t-num-small"
      title={reason || undefined}
      aria-label={`News sentiment ${sign}${n.toFixed(2)}`}
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: 4,
        padding,
        background: tone.bg,
        color: tone.fg,
        border: `1px solid ${tone.border}`,
        borderRadius: 'var(--r-chip)',
        fontFamily: 'var(--font-mono)',
        fontSize,
        lineHeight: 1.2,
        whiteSpace: 'nowrap',
      }}
    >
      <Newspaper
        size={iconSize}
        strokeWidth={1.75}
        aria-hidden="true"
        style={{ opacity: 0.65, flexShrink: 0 }}
      />
      <span style={{ fontWeight: 600 }}>{sign}{n.toFixed(2)}</span>
    </span>
  );
}

export default SentimentChip;
