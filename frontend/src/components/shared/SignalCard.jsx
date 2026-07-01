import React from 'react';
import { motion } from 'framer-motion';
import { cn } from '@/lib/utils';
import { hoverLiftV2, press } from '@/lib/motion';
import { fmtPrice, fmtPct, fmtRelTime } from '@/lib/format';
import { buildAnchorRow, buyPlan, actionChip, holdingChip, CONVICTION, TIER } from '@/lib/signalCopy';
import { exitRulesSummary } from '@/lib/exitRules';
import { StatusChip } from './StatusChip';
import { GradeBadge } from './GradeBadge';
import { PriceArc } from './PriceArc';
import { SentimentChip } from './SentimentChip';

/**
 * SignalCard — the retail-pro trade-idea tear-sheet.
 *
 * Anatomy (top to bottom):
 *   1. HEADER   — ticker (Reckless) · grade · status chip · optional sector/tag
 *   2. ACTION CHIP — thin pill strip: what the user should do right now
 *   3. CONVICTION — tier label · conviction level
 *   4. PRICE ARC — intraday path since signal fire (meaningful, not decorative)
 *   5. ANCHOR   — dot-separated mono row: Entry · Target (--bull) · Stop (--bear) · R:R · ~Nd
 *   6. EXIT TEASER — one-line plain-English exit summary
 *   7. THESIS   — 2-line plain-English explanation (Untitled body, clamp 2)
 *   8. FOOTER   — ML score · pillars · scanned-at · risk amount, followed by [Why?] [Buy]
 *
 * Card elevation:
 *   - FRESH status gets --brand-edge border + blue glow
 *   - default surface with hairline border
 *   - hoverLiftV2 on framer-motion: y -2 with shadow crossfade
 *
 * Click behavior:
 *   - Card body click (anywhere outside buttons) → onOpenDetail
 *   - [Why?] (ghost btn) → onOpenDetail
 *   - [Buy]  (solid blue) → onOpenOrderPad
 *
 * Expects a raw signal object shape from /api/signals. Any missing field
 * degrades gracefully (fewer metadata lines, dashed price arc, etc.).
 */
function statusTone(status) {
  switch ((status || '').toUpperCase()) {
    case 'FRESH':       return 'info';
    case 'IN_ZONE':
    case 'IN ZONE':     return 'brand';
    case 'CHASE':
    case 'NEAR_TARGET': return 'warn';
    case 'HIT_TARGET':
    case 'FILLED':      return 'bull';
    case 'HIT_STOP':
    case 'REJECTED':    return 'bear';
    case 'EXPIRED':
    case 'CANCELLED':
    default:            return 'muted';
  }
}

function statusLabel(status) {
  if (!status) return 'PENDING';
  return String(status).replace(/_/g, ' ').toUpperCase();
}

/** Map tone string to CSS custom-property color. */
function toneColor(tone) {
  switch (tone) {
    case 'brand':   return 'var(--brand)';
    case 'bull':    return 'var(--bull)';
    case 'bear':    return 'var(--bear)';
    case 'warn':    return 'var(--warn)';
    case 'neutral': return 'var(--text-2)';
    default:        return 'var(--text-3)';
  }
}

/** Alpha (14%) background for the action chip. */
function toneAlpha(tone) {
  switch (tone) {
    case 'brand':   return 'oklch(78% 0.16 70 / 0.14)';
    case 'bull':    return 'oklch(72% 0.18 145 / 0.14)';
    case 'bear':    return 'oklch(66% 0.21 25 / 0.14)';
    case 'warn':    return 'oklch(75% 0.15 55 / 0.14)';
    default:        return 'oklch(70% 0 0 / 0.10)';
  }
}

export function SignalCard({
  signal,
  priceSeries,
  onOpenDetail,
  onOpenOrderPad,
  heldByUser = false,
  // 'buy' (default) | 'sell' | 'research' — controls the right-side CTA.
  // 'research' is used for watchlist signals: button is greyed out and
  // labelled 'Research', click routes to onOpenDetail (NOT OrderPad)
  // since v1.2 lock disallows trading 0.75-0.92 confidence candidates.
  ctaMode = 'buy',
  // Optional 2px top accent in a semantic tone, so cards sitting under
  // different section headers read chromatically distinct at a glance
  // without claiming a full border (which would compete with the FRESH
  // brand-edge treatment). Values: 'bull' | 'info' | 'warn' | undefined.
  // FRESH cards always win — their blue all-around treatment is the
  // strongest signal and takes precedence over any tier tone.
  tierAccent,
  className,
}) {
  if (!signal) return null;

  const {
    ticker,
    sector,
    status,
    grade,
    ml_score,
    v7_score,
    v7_layers_agreeing,
    v7_llm_rationale,
    entry,
    entry_high,
    stop,
    target,
    stop_pct,
    target_pct,
    rr,
    hold_days,
    signal_date,
    current_price,
    p9_sentiment,
    p9_news_reason,
    p9_news_risk,
    p9_headlines_used,
    risk_amount,
    conviction,
    tier,
  } = signal;

  const tone = statusTone(status);
  const label = statusLabel(status);
  const isFresh = tone === 'info';

  // Anchor row segments — computed from signalCopy so strings stay compliant.
  const anchorSegments = buildAnchorRow(signal, fmtPrice, fmtPct);

  // Action chip — what the user should do right now.
  const chip = heldByUser ? { text: holdingChip(signal), tone: 'bull' } : actionChip(signal);

  // Buy-plan block — the prominent buy-limit ceiling + T+1 rule. Only for fresh,
  // buyable signals (not held positions, sells, or watchlist research items).
  const plan = ctaMode === 'buy' && !heldByUser ? buyPlan(signal, fmtPrice) : null;

  // Conviction label — derive from `conviction` field or grade fallback.
  const derivedConviction = conviction
    ? conviction
    : grade === 'A'
      ? 'HIGH'
      : grade === 'B'
        ? 'MED'
        : 'LOW';

  // Thesis = first line of LLM rationale. If missing, fall back to a
  // computed one-liner from available structured fields.
  const thesis = v7_llm_rationale
    ? v7_llm_rationale.split('\n')[0]
    : `Entry ${fmtPrice(entry)}, stop ${fmtPrice(stop)}, target ${fmtPrice(target)}. ${
        typeof v7_layers_agreeing === 'number' ? `${v7_layers_agreeing} of 6 pillars agreeing.` : ''
      }`.trim();

  // Exit teaser — one-line summary of the exit strategy.
  const exitTeaser = exitRulesSummary(signal);

  return (
    <motion.article
      variants={hoverLiftV2}
      initial="rest"
      whileHover="hover"
      onClick={(e) => {
        // Clicks on buttons don't bubble to card-level action.
        if (e.target.closest('button')) return;
        onOpenDetail?.(signal);
      }}
      className={cn('flex flex-col relative', className)}
      style={{
        background: 'var(--surface-1)',
        // FRESH cards already carry an all-sides brand-edge border; tier
        // accent applies a 2px top accent in the matching tone instead,
        // so non-FRESH cards aren't visually identical across tiers. Top
        // border only — side stripes >1px are an impeccable absolute ban.
        border: `1px solid ${isFresh ? 'var(--brand-edge)' : 'var(--edge-1)'}`,
        borderTop:
          !isFresh && tierAccent === 'bull' ? '2px solid var(--bull)' :
          !isFresh && tierAccent === 'info' ? '2px solid var(--info)' :
          !isFresh && tierAccent === 'warn' ? '2px solid var(--warn)' :
          undefined,
        borderRadius: 'var(--r-card)',
        padding: 'var(--pad-card)',
        boxShadow: isFresh
          ? 'var(--shadow-glow-lg)'
          : 'var(--shadow-sm)',
        cursor: onOpenDetail ? 'pointer' : 'default',
        minHeight: 280,
      }}
      role="article"
      aria-label={`Signal for ${ticker}, status ${label}`}
    >
      {/* HEADER — grid layout so the status chip column never gets
          squeezed and the left chip row wraps cleanly when narrow.
          Previous flex justify-between + flex-1 min-w-0 let the inner
          chips OVERFLOW their column and visually collide with the
          status chip on the right when ticker + grade + sentiment +
          HELD couldn't fit on one line. */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'minmax(0, 1fr) auto',
          gap: 12,
          alignItems: 'start',
        }}
      >
        <div style={{ minWidth: 0 }}>
          <div
            className="flex items-center"
            style={{
              gap: 8,
              rowGap: 6,
              flexWrap: 'wrap',
            }}
          >
            <h3
              className="t-title-2"
              style={{ margin: 0, color: 'var(--text-1)', letterSpacing: '-0.01em' }}
            >
              {ticker}
            </h3>
            <GradeBadge grade={grade} v7_score={v7_score} ml_score={ml_score} size="sm" />
            <SentimentChip
              score={p9_sentiment}
              headlinesUsed={p9_headlines_used}
              reason={p9_news_reason || (p9_news_risk && p9_news_risk !== 'none' ? p9_news_risk : undefined)}
            />
            {heldByUser && <StatusChip tone="bull">HELD</StatusChip>}
          </div>
          {sector && (
            <div
              className="t-ui-footnote"
              style={{ color: 'var(--text-3)', marginTop: 4 }}
            >
              {sector}
            </div>
          )}
        </div>
        {/* Status chip stays in its own auto-sized column, never shrinks. */}
        <StatusChip tone={tone}>{label}</StatusChip>
      </div>

      {/* ACTION CHIP — thin pill strip: the single most important action.
          --brand appears ONLY here on the card. Tone colors the text and
          a 14% alpha version fills the pill background. */}
      <div style={{ marginTop: 12 }}>
        <span
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            height: 28,
            padding: '0 10px',
            borderRadius: 'var(--r-chip)',
            background: toneAlpha(chip.tone),
            color: toneColor(chip.tone),
            fontFamily: 'var(--font-mono)',
            fontSize: 10,
            fontVariantNumeric: 'tabular-nums lining-nums',
            letterSpacing: '0.06em',
            textTransform: 'uppercase',
          }}
        >
          {chip.text}
        </span>
      </div>

      {/* BUY PLAN — the buy-limit ceiling + the T+1 execution rule, made prominent on the
          card face (was previously only in the detail drawer). 'past' state warns when the
          price already ran above the limit (don't chase the gap-up — the KIRLOSENG case). */}
      {plan && (
        <div
          style={{
            marginTop: 8,
            padding: '8px 10px',
            borderRadius: 'var(--r-chip)',
            background: plan.tone === 'warn' ? toneAlpha('warn') : 'var(--surface-2)',
            border: `1px solid ${plan.tone === 'warn' ? toneColor('warn') : 'var(--edge-1)'}`,
            display: 'flex',
            flexDirection: 'column',
            gap: 2,
          }}
        >
          <span
            style={{
              fontFamily: 'var(--font-mono)',
              fontSize: 13,
              fontWeight: 600,
              color: plan.tone === 'warn' ? toneColor('warn') : 'var(--text-1)',
              fontVariantNumeric: 'tabular-nums lining-nums',
              letterSpacing: '-0.01em',
            }}
          >
            {plan.head}
          </span>
          <span
            style={{
              fontSize: 10.5,
              color: 'var(--text-3)',
              textTransform: 'uppercase',
              letterSpacing: '0.04em',
            }}
          >
            {plan.sub}
          </span>
        </div>
      )}

      {/* CONVICTION LINE — tier · conviction level, small meta under the chip. */}
      <div
        style={{
          marginTop: 6,
          display: 'flex',
          alignItems: 'center',
          gap: 4,
          color: 'var(--text-2)',
          fontSize: 11,
          lineHeight: 1.4,
        }}
      >
        <span
          style={{
            fontFamily: 'var(--font-mono)',
            textTransform: 'uppercase',
            letterSpacing: '0.05em',
            color: 'var(--text-2)',
          }}
        >
          {TIER[tier]?.label || 'SIGNAL'}
        </span>
        <span style={{ color: 'var(--text-4)', margin: '0 2px' }}>·</span>
        <span style={{ fontFamily: 'var(--font-sans)', color: 'var(--text-2)' }}>
          {CONVICTION[derivedConviction]?.label || 'Moderate conviction'}
        </span>
      </div>

      {/* PRICE ARC + current price context */}
      <div
        className="flex items-center justify-between"
        style={{ marginTop: 16, marginBottom: 16, gap: 12 }}
      >
        <PriceArc
          series={priceSeries}
          entry={entry}
          size="sm"
          ariaLabel={`${ticker} intraday price path`}
        />
        {typeof current_price === 'number' && typeof entry === 'number' && (
          <div className="text-right" style={{ minWidth: 0 }}>
            <div className="t-num-large" style={{ color: 'var(--text-1)' }}>
              {fmtPrice(current_price)}
            </div>
            <div
              className="t-ui-footnote"
              style={{
                color:
                  current_price > entry
                    ? 'var(--bull)'
                    : current_price < entry
                      ? 'var(--bear)'
                      : 'var(--text-3)',
                marginTop: 2,
              }}
            >
              {fmtPct(((current_price - entry) / entry) * 100)} vs entry
            </div>
          </div>
        )}
      </div>

      {/* ANCHOR — dot-separated mono row replacing the former 3-col grid.
          Format: Entry ₹180–182 · Target ₹209 (+16%) · Stop ₹161 (−11%) · R:R 1.5 · ~15d
          Target segment is --bull, Stop is --bear, rest --text-2/3.
          font-variant-numeric forces tabular lining digits for alignment
          across siblings in a card grid. */}
      {anchorSegments.length > 0 && (
        <div
          style={{
            fontFamily: 'var(--font-mono)',
            fontSize: 12,
            fontVariantNumeric: 'tabular-nums lining-nums',
            lineHeight: 1.5,
            marginBottom: 8,
            display: 'flex',
            flexWrap: 'wrap',
            alignItems: 'center',
            gap: '0 0',
          }}
        >
          {anchorSegments.map((seg, i) => (
            <React.Fragment key={i}>
              {i > 0 && (
                <span style={{ color: 'var(--text-4)', margin: '0 6px' }}>·</span>
              )}
              <span style={{ color: seg.color ?? 'var(--text-2)' }}>{seg.text}</span>
            </React.Fragment>
          ))}
        </div>
      )}

      {/* EXIT TEASER — one-line plain-English exit summary, separate from thesis. */}
      {exitTeaser && (
        <div
          className="t-ui-footnote"
          style={{
            color: 'var(--text-3)',
            fontStyle: 'italic',
            marginBottom: 10,
          }}
        >
          {exitTeaser}
        </div>
      )}

      {/* THESIS */}
      {thesis && (
        <div
          className="t-ui-body"
          style={{
            color: 'var(--text-2)',
            marginBottom: 14,
            display: '-webkit-box',
            WebkitLineClamp: 2,
            WebkitBoxOrient: 'vertical',
            overflow: 'hidden',
          }}
        >
          {thesis}
        </div>
      )}

      {/* FOOTER — metadata then actions */}
      <div
        className="t-ui-footnote"
        style={{
          color: 'var(--text-3)',
          borderTop: '1px solid var(--edge-1)',
          paddingTop: 12,
          marginTop: 'auto',
          display: 'flex',
          gap: 10,
          alignItems: 'center',
          flexWrap: 'wrap',
        }}
      >
        {typeof ml_score === 'number' && (
          <span>
            ML <span style={{ color: 'var(--text-2)', fontFamily: 'var(--font-mono)' }}>{ml_score.toFixed(2)}</span>
          </span>
        )}
        {typeof v7_layers_agreeing === 'number' && (
          <>
            <span style={{ color: 'var(--text-4)' }}>·</span>
            <span>{v7_layers_agreeing} of 6 pillars</span>
          </>
        )}
        {signal_date && (
          <>
            <span style={{ color: 'var(--text-4)' }}>·</span>
            {/* "Signaled" instead of "Scanned" because signal_date is when this
                idea fired, not the last cron run. The cron may have run today
                without producing fresh signals — surfacing "Scanned 14d ago"
                would falsely imply the scanner is stale. */}
            <span>Signaled {fmtRelTime(signal_date)}</span>
          </>
        )}
        {/* MAX RISK — shown in warn color; visible financial exposure for sizing decisions. */}
        {risk_amount != null && !isNaN(Number(risk_amount)) && (
          <>
            <span style={{ color: 'var(--text-4)' }}>·</span>
            <span style={{ color: 'var(--warn)' }}>
              max risk ≈ ₹{Number(risk_amount).toLocaleString('en-IN')}
            </span>
          </>
        )}
      </div>

      <div className="flex items-center" style={{ gap: 8, marginTop: 14 }}>
        <motion.button
          type="button"
          variants={press}
          initial="rest"
          whileTap="press"
          onClick={() => onOpenDetail?.(signal)}
          className="t-ui-callout"
          style={{
            flex: 1,
            padding: '10px 14px',
            background: 'transparent',
            color: 'var(--text-2)',
            border: '1px solid var(--edge-1)',
            borderRadius: 'var(--r-chip)',
            cursor: 'pointer',
          }}
        >
          Why?
        </motion.button>
        {ctaMode === 'research' ? (
          // Watchlist signals — research-only per v1.2 lock. Greyed-out
          // button that opens the detail drawer instead of OrderPad.
          // Visually distinct from the active brand-blue Buy button so
          // users don't mistake monitoring for actionable.
          <motion.button
            type="button"
            variants={press}
            initial="rest"
            whileTap="press"
            onClick={() => onOpenDetail?.(signal)}
            className="t-ui-callout"
            style={{
              flex: 1,
              padding: '10px 14px',
              background: 'var(--surface-3)',
              color: 'var(--text-3)',
              border: '1px dashed var(--edge-1)',
              borderRadius: 'var(--r-chip)',
              fontWeight: 500,
              cursor: 'pointer',
              letterSpacing: '0.04em',
            }}
            title="Watchlist signals are below the entry confidence gate (0.92). Research only."
          >
            Research
          </motion.button>
        ) : (
          <motion.button
            type="button"
            variants={press}
            initial="rest"
            whileTap="press"
            onClick={() => onOpenOrderPad?.(signal)}
            className="t-ui-callout"
            style={{
              flex: 1,
              padding: '10px 14px',
              background: 'var(--brand-grad)',
              color: 'var(--brand-fg)',
              border: '1px solid var(--brand)',
              borderRadius: 'var(--r-chip)',
              fontWeight: 600,
              cursor: 'pointer',
            }}
          >
            {ctaMode === 'sell' ? 'Sell' : 'Buy'}
          </motion.button>
        )}
      </div>
    </motion.article>
  );
}

export default SignalCard;
