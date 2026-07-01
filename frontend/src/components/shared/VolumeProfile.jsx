/**
 * VolumeProfile — today's volume vs 20-day average + unusual-volume flag.
 *
 * Why traders care:
 *   Volume is the most reliable confirmation of intent. A breakout on
 *   2× normal volume is a real breakout; on average volume it's noise.
 *   Showing today's volume relative to its own history is the cleanest
 *   one-glance read of "is something happening here right now."
 *
 * Inputs:
 *   - todayVolume      — number, current session aggregate
 *   - history          — array of { date, volume } for the last ~20 sessions
 *                        (we average volumes from this; expects daily candles
 *                        from the existing useStockData period='1M' fetch)
 *   - unusualThreshold — multiplier above which we badge "UNUSUAL VOLUME"
 *                        Default 1.5× — calibrated so it triggers on real
 *                        breakouts without false-flagging an ordinary day.
 *
 * Visualization:
 *   - Big number: today's volume in human format (12.4Cr, 8.5L, etc.)
 *   - Below: ratio vs 20d avg with a horizontal bar (clamped to 3× max)
 *   - Below that: a 20-bar histogram of recent days' volumes with today's
 *     bar highlighted in amber
 *   - Top-right corner: 🔥 UNUSUAL VOLUME chip when ratio > threshold
 *
 * Empty / missing data renders a tasteful note rather than zero values.
 */
import React, { useMemo } from 'react';
import { Flame } from 'lucide-react';
import { fmtVolume } from '@/lib/format';

export function VolumeProfile({
  todayVolume,
  history = [],
  unusualThreshold = 1.5,
  height = 320,
}) {
  // Compute 20-day average from `history`. Filter out today's bar to avoid
  // self-inclusion biasing the baseline. We assume `history` is ordered
  // oldest → newest; the last entry is "today".
  const { avg20, ratio, recentBars, todayIdx, isUnusual } = useMemo(() => {
    const rows = (history || []).filter((r) => r && Number(r.volume) > 0);
    if (rows.length < 2) {
      return { avg20: null, ratio: null, recentBars: [], todayIdx: -1, isUnusual: false };
    }
    const lookback = rows.slice(-20);
    // Exclude the most recent bar from the avg if it equals today's volume
    // (avoids double-counting).
    const baseline = lookback.length > 1 ? lookback.slice(0, -1) : lookback;
    const avg = baseline.reduce((s, r) => s + (Number(r.volume) || 0), 0) / baseline.length;
    const todayVol = todayVolume ?? lookback[lookback.length - 1]?.volume ?? 0;
    const r = avg > 0 ? todayVol / avg : null;
    return {
      avg20: avg,
      ratio: r,
      recentBars: lookback,
      todayIdx: lookback.length - 1,
      isUnusual: r != null && r >= unusualThreshold,
    };
  }, [history, todayVolume, unusualThreshold]);

  const todayVol = todayVolume ?? recentBars[todayIdx]?.volume ?? null;

  // Bar height normalization for the mini histogram.
  const maxBarVol = Math.max(...recentBars.map((b) => Number(b.volume) || 0), 1);
  const ratioBarPct = ratio != null ? Math.min(100, (ratio / 3) * 100) : 0;

  return (
    <div
      style={{
        background: 'var(--surface-1)',
        border: '1px solid var(--edge-1)',
        borderRadius: 'var(--r-card)',
        boxShadow: 'var(--shadow-sm)',
        height,
        display: 'flex',
        flexDirection: 'column',
        overflow: 'hidden',
      }}
    >
      <header
        className="flex items-start justify-between"
        style={{ padding: '12px 14px', borderBottom: '1px solid var(--edge-1)', flexShrink: 0 }}
      >
        <div>
          <h3 className="t-ui-headline" style={{ margin: 0, color: 'var(--text-1)' }}>
            Volume profile
          </h3>
          <div className="t-ui-footnote" style={{ color: 'var(--text-3)', marginTop: 2 }}>
            Today vs 20-day average
          </div>
        </div>
        {isUnusual && (
          <span
            className="t-ui-micro flex items-center"
            style={{
              gap: 4,
              padding: '4px 8px',
              background: 'var(--warn-soft)',
              border: `1px solid var(--warn)`,
              borderRadius: 'var(--r-chip)',
              color: 'var(--warn)',
              fontWeight: 600,
            }}
          >
            <Flame size={11} strokeWidth={2} /> UNUSUAL
          </span>
        )}
      </header>

      <div style={{ padding: 14, flex: 1, display: 'flex', flexDirection: 'column' }}>
        {/* Headline number */}
        <div>
          <div
            className="t-num-hero"
            style={{ color: isUnusual ? 'var(--warn)' : 'var(--text-1)', lineHeight: 1.05 }}
          >
            {todayVol != null ? fmtVolume(todayVol) : '—'}
          </div>
          <div className="t-ui-footnote" style={{ color: 'var(--text-3)', marginTop: 4 }}>
            today's volume
          </div>
        </div>

        {/* Ratio bar */}
        {ratio != null && avg20 != null ? (
          <div style={{ marginTop: 16 }}>
            <div className="flex items-baseline justify-between" style={{ marginBottom: 6 }}>
              <span className="t-ui-micro" style={{ color: 'var(--text-3)' }}>
                vs {fmtVolume(avg20)} avg
              </span>
              <span
                className="t-num-body"
                style={{
                  fontSize: 14,
                  color: ratio >= unusualThreshold
                    ? 'var(--warn)'
                    : ratio >= 1
                      ? 'var(--text-1)'
                      : 'var(--text-3)',
                }}
              >
                {ratio.toFixed(2)}×
              </span>
            </div>
            <div
              role="progressbar"
              aria-valuemin="0"
              aria-valuemax="3"
              aria-valuenow={Math.min(3, ratio)}
              style={{
                position: 'relative',
                height: 6,
                background: 'var(--surface-2)',
                borderRadius: 3,
                overflow: 'hidden',
              }}
            >
              <div
                style={{
                  width: `${ratioBarPct}%`,
                  height: '100%',
                  background: ratio >= unusualThreshold
                    ? 'var(--warn)'
                    : ratio >= 1
                      ? 'var(--bull)'
                      : 'var(--text-3)',
                  borderRadius: 3,
                  transition: 'width var(--dur-enter) var(--ease-out-quart)',
                }}
              />
              {/* threshold marker */}
              <div
                style={{
                  position: 'absolute',
                  top: -2,
                  bottom: -2,
                  left: `${(unusualThreshold / 3) * 100}%`,
                  width: 1,
                  background: 'var(--warn)',
                  opacity: 0.6,
                }}
                aria-hidden="true"
              />
            </div>
            <div
              className="t-ui-footnote"
              style={{ color: 'var(--text-4)', marginTop: 4, display: 'flex', justifyContent: 'space-between' }}
            >
              <span>0×</span>
              <span style={{ color: 'var(--warn)' }}>{unusualThreshold}× threshold</span>
              <span>3×+</span>
            </div>
          </div>
        ) : (
          <div className="t-ui-footnote" style={{ color: 'var(--text-3)', marginTop: 16 }}>
            Need ≥2 days of history for a baseline.
          </div>
        )}

        {/* Mini histogram of last ~20 days */}
        {recentBars.length > 0 && (
          <div style={{ marginTop: 'auto', paddingTop: 16 }}>
            <div
              className="flex items-end"
              style={{ gap: 2, height: 56 }}
              aria-label="Recent volumes"
            >
              {recentBars.map((b, i) => {
                const v = Number(b.volume) || 0;
                const h = maxBarVol > 0 ? Math.max(2, (v / maxBarVol) * 100) : 0;
                const isToday = i === todayIdx;
                return (
                  <div
                    key={i}
                    title={`${b.date ?? ''} · ${fmtVolume(v)}`}
                    style={{
                      flex: 1,
                      height: `${h}%`,
                      background: isToday
                        ? (isUnusual ? 'var(--warn)' : 'var(--brand)')
                        : 'var(--surface-3)',
                      borderRadius: 1,
                    }}
                  />
                );
              })}
            </div>
            <div
              className="t-ui-footnote"
              style={{ color: 'var(--text-4)', marginTop: 6, display: 'flex', justifyContent: 'space-between' }}
            >
              <span>~20 days back</span>
              <span style={{ color: 'var(--brand-hi)' }}>today</span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default VolumeProfile;
