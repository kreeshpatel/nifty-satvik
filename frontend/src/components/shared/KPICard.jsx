import React from 'react';
import { motion } from 'framer-motion';
import { cn } from '@/lib/utils';
import { hoverLiftV2, numberTick } from '@/lib/motion';

/**
 * KPICard — the single canonical KPI tile.
 *
 * Retail-pro hierarchy (not generic admin):
 *   1. ui-micro uppercase LABEL (e.g. "TODAY'S P&L")
 *   2. num-hero VALUE in Berkeley Mono with semantic tone color
 *   3. ui-footnote CONTEXT line (e.g. "+1.21%  Best: INFY +3.4%")
 *
 * Tone drives VALUE color only — bull/bear/neutral. Secondary deltas in
 * the context line color themselves via their own tone.
 *
 * Hover lift is a +2px translate-y with shadow crossfade — shipped via
 * framer-motion variant, so reduced-motion users see no transform.
 *
 * No sparkline by default. Opt in with <KPICard trailing={<PriceArc ... />} />
 * when the mini chart IS the data story. Follows impeccable's "no decorative
 * sparklines" rule.
 *
 * Props
 * -----
 * label:    string                uppercase micro label
 * value:    string | ReactNode    the big number — caller formats via fmtINR/fmtPrice
 * tone:     'neutral'|'bull'|'bear'|'brand'
 * context:  string | ReactNode    sub-line (delta + context)
 * trailing: ReactNode             optional right-side slot (PriceArc, icon, menu)
 * footer:   ReactNode             optional bottom strip (action buttons, timestamps)
 * tickKey:  string | number       change this prop to trigger numberTick on value
 * onClick:  fn                    makes whole card interactive; adds keyboard handler
 */
const TONE_COLOR = {
  neutral: 'var(--text-1)',
  bull:    'var(--bull)',
  bear:    'var(--bear)',
  brand:   'var(--brand-hi)',
};

export function KPICard({
  label,
  value,
  tone = 'neutral',
  context,
  trailing,
  footer,
  tickKey,
  onClick,
  className,
  children,
}) {
  const interactive = typeof onClick === 'function';

  return (
    <motion.div
      variants={interactive ? hoverLiftV2 : undefined}
      initial="rest"
      whileHover={interactive ? 'hover' : undefined}
      onClick={onClick}
      onKeyDown={interactive
        ? (e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); onClick(e); } }
        : undefined}
      tabIndex={interactive ? 0 : undefined}
      role={interactive ? 'button' : undefined}
      className={cn(
        'relative flex flex-col',
        interactive && 'cursor-pointer',
        className,
      )}
      style={{
        background: 'var(--surface-1)',
        border: '1px solid var(--edge-1)',
        borderRadius: 'var(--r-card)',
        padding: 'var(--pad-card)',
        boxShadow: 'var(--shadow-sm)',
        transition: `box-shadow var(--dur-hover) var(--ease-out-cubic), border-color var(--dur-hover) var(--ease-out-cubic)`,
      }}
    >
      <div className="flex items-start justify-between" style={{ gap: 12 }}>
        <div className="min-w-0 flex-1">
          {label && (
            <div className="t-ui-micro" style={{ color: 'var(--text-3)', marginBottom: 8 }}>
              {label}
            </div>
          )}
          {value != null && (
            <motion.div
              key={tickKey}
              variants={numberTick}
              initial={tickKey != null ? 'initial' : undefined}
              animate={tickKey != null ? 'animate' : undefined}
              className="t-num-hero"
              style={{ color: TONE_COLOR[tone], lineHeight: 1.06 }}
            >
              {value}
            </motion.div>
          )}
          {context && (
            <div
              className="t-ui-footnote"
              style={{ color: 'var(--text-3)', marginTop: 8 }}
            >
              {context}
            </div>
          )}
        </div>
        {trailing && (
          <div className="flex-shrink-0 flex items-start" style={{ marginTop: -4 }}>
            {trailing}
          </div>
        )}
      </div>

      {children && <div className="mt-3">{children}</div>}

      {footer && (
        <div
          className="mt-4 pt-3 flex items-center"
          style={{ borderTop: '1px solid var(--edge-1)', gap: 8 }}
        >
          {footer}
        </div>
      )}
    </motion.div>
  );
}

export default KPICard;
