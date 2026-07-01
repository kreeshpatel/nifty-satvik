/**
 * ConvictionGauge — visual answer to "why are there no Buy signals today?"
 *
 * Sits below RegimeHeader on the Signals page. Shows the day's strongest
 * candidate's ML score plotted against the entry gate (0.92), so users
 * understand the system isn't broken — the bar just isn't met.
 *
 * In CHOPPY/BEAR regimes, top conviction routinely sits 0.82-0.88. In BULL
 * regimes, several names break 0.92 daily. The gauge makes that distinction
 * visceral instead of leaving the user staring at an empty "Today's Picks"
 * section.
 *
 * Composition:
 *
 *   ┌────────────────────────────────────────────────────────────────┐
 *   │  Conviction gauge      Top candidate: INTELLECT                │
 *   │  ──────────────────────────────────────────────────────────    │
 *   │  0.860 ┃━━━━━━━━━━━━━━━━━━━━━━━━━━┃ 0.920 (gate)               │
 *   │                                  ▲ gap 0.060                   │
 *   │  Entry gate cleared at 0.92 conf + 8% return.                  │
 *   │  Today's gap means no buys — the model is monitoring.          │
 *   └────────────────────────────────────────────────────────────────┘
 *
 * No card, no border. Just a hairline rule + the gauge bar. Voice matches
 * the editorial RegimeHeader sitting above it.
 *
 * Props
 * -----
 * topCandidate: { ticker, ml_score, predicted_return_pct } | null
 * cleared:      boolean — true when topCandidate already cleared the gate
 *                         (i.e. there's a real entry signal today)
 * gateConf:     number  — defaults to 0.92 (live entry gate)
 * gateRetPct:   number  — defaults to 8 (live return gate)
 */
import React from 'react';
import { StatusChip } from './StatusChip';

const DEFAULT_GATE_CONF = 0.92;
const DEFAULT_GATE_RET_PCT = 8.0;

// Scale the bar's x-axis to 0.70..1.00 so the action happens in the middle.
// Anything below 0.70 is so far from the gate it doesn't merit a visual.
const SCALE_MIN = 0.70;
const SCALE_MAX = 1.00;

function pctOnScale(value) {
  const clamped = Math.max(SCALE_MIN, Math.min(SCALE_MAX, value));
  return ((clamped - SCALE_MIN) / (SCALE_MAX - SCALE_MIN)) * 100;
}

export function ConvictionGauge({
  topCandidate,
  cleared = false,
  gateConf = DEFAULT_GATE_CONF,
  gateRetPct = DEFAULT_GATE_RET_PCT,
}) {
  const conf = Number(topCandidate?.ml_score ?? topCandidate?.confidence ?? 0);
  const ret = Number(topCandidate?.predicted_return_pct ?? 0);
  const ticker = topCandidate?.ticker;

  const hasCandidate = !!ticker && conf > 0;
  const gap = gateConf - conf;
  const confPct = pctOnScale(conf);
  const gatePct = pctOnScale(gateConf);

  // Bar color reflects how close the top candidate is to gate.
  //   cleared      → bull green
  //   gap < 0.04   → brand amber (close — could promote soon)
  //   gap >= 0.04  → muted (typical CHOPPY-regime conviction)
  const barColor =
    cleared           ? 'var(--bull)' :
    gap < 0.04        ? 'var(--brand)' :
    'var(--text-3)';

  return (
    <section
      aria-label="Conviction gauge"
      style={{
        marginTop: 16,
        marginBottom: 8,
        paddingBottom: 16,
        borderBottom: '1px solid var(--edge-1)',
      }}
    >
      {/* HEADER row — left label, right candidate ticker */}
      <div
        className="flex items-baseline"
        style={{ gap: 12, justifyContent: 'space-between', flexWrap: 'wrap' }}
      >
        <div className="flex items-baseline" style={{ gap: 10 }}>
          <h3
            className="t-ui-headline"
            style={{ margin: 0, color: 'var(--text-2)' }}
          >
            Conviction
          </h3>
          {cleared && <StatusChip tone="bull">Gate cleared</StatusChip>}
          {!cleared && hasCandidate && gap < 0.04 && (
            <StatusChip tone="brand">Near gate</StatusChip>
          )}
          {!cleared && hasCandidate && gap >= 0.04 && (
            <StatusChip tone="muted">Below gate</StatusChip>
          )}
        </div>

        {hasCandidate ? (
          <div
            className="flex items-baseline"
            style={{ gap: 8, color: 'var(--text-2)' }}
          >
            <span className="t-ui-footnote" style={{ color: 'var(--text-3)' }}>
              Top candidate
            </span>
            <span className="t-ui-callout" style={{ color: 'var(--text-1)', fontWeight: 600 }}>
              {ticker}
            </span>
            <span
              className="t-num-small"
              style={{ color: 'var(--text-2)', fontFamily: 'var(--font-mono)' }}
            >
              {conf.toFixed(3)}
            </span>
            <span
              className="t-num-small"
              style={{
                color: ret >= gateRetPct ? 'var(--bull)' : 'var(--text-3)',
                fontFamily: 'var(--font-mono)',
              }}
            >
              {ret >= 0 ? '+' : ''}{ret.toFixed(1)}%
            </span>
          </div>
        ) : (
          <span className="t-ui-footnote" style={{ color: 'var(--text-3)' }}>
            No candidates today
          </span>
        )}
      </div>

      {/* GAUGE bar — subordinate to RegimeHeader's strength bar above. Width
          capped + thinner so the page doesn't read as two stacked
          horizontal-meter widgets. The gate tick (light hairline) is the
          element that draws the eye, not the fill itself. */}
      <div
        style={{
          position: 'relative',
          marginTop: 12,
          height: 4,
          width: 480,
          maxWidth: '100%',
          background: 'var(--surface-2)',
          borderRadius: 2,
          overflow: 'visible',
        }}
      >
        {hasCandidate && (
          <div
            style={{
              position: 'absolute',
              left: 0,
              top: 0,
              bottom: 0,
              width: `${confPct}%`,
              background: barColor,
              borderRadius: 2,
              transition: 'width var(--dur-page) var(--ease-out-cubic)',
            }}
          />
        )}
        {/* Gate marker — taller than the bar so it reads as a fixed
            reference line, not part of the fill geometry. */}
        <div
          aria-label={`Entry gate at ${gateConf.toFixed(2)}`}
          style={{
            position: 'absolute',
            left: `${gatePct}%`,
            top: -6,
            bottom: -6,
            width: 1,
            background: 'var(--text-1)',
            transform: 'translateX(-0.5px)',
          }}
        />
      </div>

      {/* Caption — one line. Reserved the multi-sentence version for the
          first-time empty state; users seeing this every day need glance-
          value, not a paragraph. */}
      <p
        className="t-ui-footnote"
        style={{ margin: '12px 0 0', color: 'var(--text-3)', maxWidth: '64ch' }}
      >
        {cleared ? (
          <>
            Gate <strong style={{ color: 'var(--bull)' }}>cleared</strong>. See <strong style={{ color: 'var(--text-2)' }}>Today's picks</strong> below.
          </>
        ) : hasCandidate ? (
          <>
            Top conviction <strong style={{ color: 'var(--text-2)' }}>{conf.toFixed(3)}</strong>, gate <strong style={{ color: 'var(--text-2)' }}>{gateConf.toFixed(2)}</strong>. Gap <strong style={{ color: 'var(--text-2)' }}>{gap.toFixed(3)}</strong> — model is monitoring.
          </>
        ) : (
          <>
            No candidates above the watchlist floor today.
          </>
        )}
      </p>
    </section>
  );
}

export default ConvictionGauge;
