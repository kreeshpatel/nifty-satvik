import React from 'react';
import { motion } from 'framer-motion';
import { ArrowUp, ArrowDown } from 'lucide-react';
import { cn } from '@/lib/utils';
import { GlassCard } from './GlassCard';
import { fadeInUp } from '@/lib/motion';

/**
 * GlassKPIRow — 4 equal KPI cards in a responsive grid.
 *
 * Benchmark: DWISON / LittleBee dashboard layouts — a row of uniform
 * KPI cards, each with an icon chip, label, big display number, and
 * a trend arrow + context line below. No hero variant; all cards are
 * first-class peers.
 *
 * metric shape:
 *   {
 *     label:         string
 *     value:         string           pre-formatted display value
 *     icon:          LucideIcon       small chip icon (top-left)
 *     iconTone:      'brand'|'muted'  chip background tint (default 'brand')
 *     deltaText:     string           e.g. "0.37%" (no sign — sign comes from deltaPositive)
 *     deltaPositive: boolean          true → green ↑ chip, false → red ↓ chip
 *     subtitle:      string           secondary context line (muted)
 *   }[]
 */
export function GlassKPIRow({ metrics, className }) {
  const cols =
    metrics.length === 2
      ? 'sm:grid-cols-2'
      : metrics.length === 3
      ? 'sm:grid-cols-3'
      : 'sm:grid-cols-2 lg:grid-cols-4';

  return (
    <div className={cn('grid grid-cols-1 gap-4 lg:gap-5', cols, className)}>
      {metrics.map((m, i) => (
        <motion.div key={m.label} variants={fadeInUp} custom={i}>
          <KPICard metric={m} />
        </motion.div>
      ))}
    </div>
  );
}

function KPICard({ metric }) {
  const Icon = metric.icon;
  const chipBg =
    metric.iconTone === 'muted'
      ? 'rgba(255, 255, 255, 0.06)'
      : 'rgba(34, 221, 136, 0.12)';
  const chipFg = metric.iconTone === 'muted' ? '#94A3B8' : '#22DD88';

  return (
    <GlassCard tier={1} hoverLift className="px-5 py-5 sm:px-6 sm:py-6 flex flex-col gap-4">
      {/* Top row: icon chip + label */}
      <div className="flex items-center gap-3">
        {Icon && (
          <div
            className="h-10 w-10 rounded-xl flex items-center justify-center shrink-0"
            style={{ background: chipBg }}
          >
            <Icon className="h-[18px] w-[18px]" style={{ color: chipFg }} strokeWidth={2} />
          </div>
        )}
        <p className="text-[13px] text-nq-text-secondary truncate">{metric.label}</p>
      </div>

      {/* Big value */}
      <p
        className="font-bold tabular-nums text-white"
        style={{
          fontSize: 'clamp(28px, 2.8vw, 34px)',
          letterSpacing: '-0.02em',
          lineHeight: 1.05,
        }}
      >
        {metric.value}
      </p>

      {/* Trend chip + context */}
      {(metric.deltaText || metric.subtitle) && (
        <div className="flex items-center gap-2 text-[12px] min-h-[18px]">
          {metric.deltaText && (
            <TrendChip
              positive={metric.deltaPositive}
              text={metric.deltaText}
            />
          )}
          {metric.subtitle && (
            <span className="text-nq-text-muted truncate">{metric.subtitle}</span>
          )}
        </div>
      )}
    </GlassCard>
  );
}

function TrendChip({ positive, text }) {
  const Icon = positive ? ArrowUp : ArrowDown;
  return (
    <span
      className="inline-flex items-center gap-0.5 font-semibold text-[12px] tabular-nums"
      style={{ color: positive ? '#22DD88' : '#EF4444' }}
    >
      <Icon className="h-3 w-3" strokeWidth={3} />
      {text}
    </span>
  );
}
