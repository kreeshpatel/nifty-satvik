import React from 'react';
import { cn } from '@/lib/utils';

/**
 * RegimeHeader — the editorial statement at the top of Dashboard + Signals.
 *
 * This is the one place where Reckless Neue gets to show off. The pattern:
 *   "Market is <REGIME>."
 * with the regime word rendered in a tone color (bull → green, bear → red,
 * range → brand blue). Everything below is metadata in DM Sans.
 *
 * Not a card. No border, no shadow, no glass. Just a statement with a
 * hairline rule under it — this is the page establishing its voice.
 *
 * A subtle strength bar under the metadata row gives a second dimension
 * to the regime. 0-100 scale; below 40 turns neutral (regime is weak even
 * if direction is known).
 *
 * Props
 * -----
 * regime:   'Bullish' | 'Bearish' | 'Ranging' | string   display word
 * tone:     'bull' | 'bear' | 'brand' | 'muted'           color of regime word
 * strength: number (0-100)                                strength bar fill
 * vix:      number
 * breadth:  number (percent)
 * fiiFlow:  string                                         pre-formatted "+₹210cr"
 * metadata: ReactNode                                      fully custom metadata row (overrides above)
 */
const TONE_COLOR = {
  bull:  'var(--bull)',
  bear:  'var(--bear)',
  brand: 'var(--brand-hi)',
  muted: 'var(--text-2)',
};

function pickToneForRegime(regime) {
  if (!regime) return 'muted';
  const r = regime.toLowerCase();
  if (r.includes('bull')) return 'bull';
  if (r.includes('bear')) return 'bear';
  return 'brand';
}

export function RegimeHeader({
  regime,
  tone,
  strength,
  vix,
  breadth,
  fiiFlow,
  metadata,
  className,
  scanTime,
}) {
  const resolvedTone = tone ?? pickToneForRegime(regime);
  const regimeColor = TONE_COLOR[resolvedTone];
  const strengthColor =
    typeof strength !== 'number'
      ? 'var(--text-3)'
      : strength < 40
        ? 'var(--text-3)'
        : resolvedTone === 'bull'
          ? 'var(--bull)'
          : resolvedTone === 'bear'
            ? 'var(--bear)'
            : 'var(--brand)';

  return (
    <header
      className={cn('relative', className)}
      style={{ paddingTop: 32, paddingBottom: 24 }}
    >
      <h2
        className="t-title-1"
        style={{
          display: 'inline-flex',
          alignItems: 'baseline',
          gap: 8,
          color: 'var(--text-1)',
          margin: 0,
        }}
      >
        <span>Market is</span>
        <span style={{ color: regimeColor, fontWeight: 500 }}>{regime ?? '—'}</span>
        <span style={{ color: 'var(--text-2)' }}>.</span>
      </h2>

      {metadata != null ? (
        <div className="t-ui-footnote" style={{ color: 'var(--text-2)', marginTop: 10 }}>
          {metadata}
        </div>
      ) : (
        <div
          className="t-ui-footnote flex items-center flex-wrap"
          style={{ color: 'var(--text-2)', marginTop: 10, gap: 14 }}
        >
          {typeof strength === 'number' && (
            <span>
              Strength <span style={{ color: 'var(--text-1)', fontFamily: 'var(--font-mono)' }}>{strength}</span>
            </span>
          )}
          {typeof vix === 'number' && (
            <>
              <span style={{ color: 'var(--text-4)' }}>·</span>
              <span>
                VIX <span style={{ color: 'var(--text-1)', fontFamily: 'var(--font-mono)' }}>{vix.toFixed(1)}</span>
              </span>
            </>
          )}
          {typeof breadth === 'number' && (
            <>
              <span style={{ color: 'var(--text-4)' }}>·</span>
              <span>
                Breadth <span style={{ color: 'var(--text-1)', fontFamily: 'var(--font-mono)' }}>{Math.round(breadth)}%</span>
              </span>
            </>
          )}
          {fiiFlow && (
            <>
              <span style={{ color: 'var(--text-4)' }}>·</span>
              <span>
                FII <span style={{ color: 'var(--text-1)', fontFamily: 'var(--font-mono)' }}>{fiiFlow}</span>
              </span>
            </>
          )}
          {scanTime && (
            <>
              <span style={{ color: 'var(--text-4)' }}>·</span>
              <span>Last scan {scanTime}</span>
            </>
          )}
        </div>
      )}

      {typeof strength === 'number' && (
        <div
          className="flex items-center"
          style={{ marginTop: 16, gap: 12, maxWidth: 480 }}
          aria-label={`Regime strength ${strength} of 100`}
        >
          <div
            role="progressbar"
            aria-valuemin="0"
            aria-valuemax="100"
            aria-valuenow={strength}
            style={{
              flex: 1,
              height: 6,
              borderRadius: 3,
              background: 'var(--surface-2)',
              overflow: 'hidden',
            }}
          >
            <div
              style={{
                width: `${Math.max(0, Math.min(100, strength))}%`,
                height: '100%',
                background: strengthColor,
                borderRadius: 3,
                transition: 'width var(--dur-enter) var(--ease-out-quart)',
              }}
            />
          </div>
          <span
            className="t-num-small"
            style={{ color: 'var(--text-2)', minWidth: 56, textAlign: 'right' }}
          >
            {strength}/100
          </span>
        </div>
      )}

      <div
        role="presentation"
        style={{
          marginTop: 24,
          borderBottom: '1px solid var(--edge-1)',
          width: '100%',
        }}
      />
    </header>
  );
}

export default RegimeHeader;
