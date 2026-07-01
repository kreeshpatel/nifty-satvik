import React, { useEffect, useRef, useState } from 'react';
import { cn } from '@/lib/utils';
import { fmtPct, fmtPrice } from '@/lib/format';

/**
 * TickerTape — a Bloomberg-style marquee for live quotes.
 *
 * NOT a crypto-dashboard "infinite scroller" — the animation is done
 * with a single `transform: translateX` driven by requestAnimationFrame
 * so we can pause on hover instantly and restart from the same offset.
 * Also cheap: one transform, one GPU layer.
 *
 * Input shape:
 *   items = [
 *     { symbol, price, change, changePct, tone?: 'bull'|'bear'|'muted' },
 *     ...
 *   ]
 *
 * Tone is derived from change unless explicitly passed. A dim bullet
 * separator between items; a 32px track height to sit on top of the
 * page shell without eating vertical space.
 */
function classifyTone({ change, tone }) {
  if (tone) return tone;
  if (typeof change !== 'number') return 'muted';
  if (change > 0) return 'bull';
  if (change < 0) return 'bear';
  return 'muted';
}

const TONE_COLOR = {
  bull:  'var(--bull)',
  bear:  'var(--bear)',
  muted: 'var(--text-2)',
};

export function TickerTape({ items = [], speed = 40, className }) {
  const trackRef = useRef(null);
  const offsetRef = useRef(0);
  const lastTsRef = useRef(0);
  const rafRef = useRef(null);
  const [paused, setPaused] = useState(false);

  // Duplicate the item list so the translateX loop can wrap seamlessly
  // once the first copy has scrolled fully off to the left.
  const duplicated = items.length ? [...items, ...items] : [];

  useEffect(() => {
    if (!trackRef.current || duplicated.length === 0) return;
    const track = trackRef.current;
    const tick = (ts) => {
      if (!lastTsRef.current) lastTsRef.current = ts;
      const dt = ts - lastTsRef.current;
      lastTsRef.current = ts;
      if (!paused) {
        offsetRef.current -= (speed * dt) / 1000;
        const halfWidth = track.scrollWidth / 2;
        if (Math.abs(offsetRef.current) >= halfWidth) {
          offsetRef.current = 0;
        }
        track.style.transform = `translateX(${offsetRef.current}px)`;
      }
      rafRef.current = requestAnimationFrame(tick);
    };
    rafRef.current = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(rafRef.current);
  }, [duplicated.length, paused, speed]);

  if (!items.length) return null;

  return (
    <div
      className={cn('relative overflow-hidden', className)}
      style={{
        height: 32,
        background: 'var(--surface-1)',
        borderTop: '1px solid var(--edge-1)',
        borderBottom: '1px solid var(--edge-1)',
      }}
      onMouseEnter={() => setPaused(true)}
      onMouseLeave={() => setPaused(false)}
      aria-label="Live market ticker"
    >
      <div
        ref={trackRef}
        className="flex items-center whitespace-nowrap"
        style={{ height: '100%', gap: 32, paddingLeft: 16, willChange: 'transform' }}
      >
        {duplicated.map((item, i) => {
          const tone = classifyTone(item);
          const color = TONE_COLOR[tone];
          const changePct = typeof item.changePct === 'number' ? item.changePct : null;
          return (
            <div key={`${item.symbol}-${i}`} className="flex items-center" style={{ gap: 8 }}>
              <span
                style={{
                  fontFamily: 'var(--font-sans)',
                  fontSize: 12,
                  fontWeight: 600,
                  color: 'var(--text-2)',
                  letterSpacing: '0.02em',
                }}
              >
                {item.symbol}
              </span>
              <span
                className="t-num-small"
                style={{ color: 'var(--text-1)', fontSize: 12 }}
              >
                {typeof item.price === 'number' ? fmtPrice(item.price).replace('₹', '') : item.price}
              </span>
              {changePct != null && (
                <span
                  className="t-num-small"
                  style={{ color, fontSize: 12 }}
                >
                  {fmtPct(changePct, 2)}
                </span>
              )}
              {/* Bullet separator. 8px circle-dot with muted color so it reads as a soft divider,
                  not a punctuation mark. */}
              <span
                aria-hidden="true"
                style={{ color: 'var(--text-4)', fontSize: 12, marginLeft: 12 }}
              >
                ·
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

export default TickerTape;
