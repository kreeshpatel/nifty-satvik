import React, { useMemo, useState } from 'react';
import * as DialogPrimitive from '@radix-ui/react-dialog';
import { useQuery } from '@tanstack/react-query';
import { X, TrendingUp, AlertTriangle, Newspaper, ChevronDown, ChevronRight } from 'lucide-react';
import { cn } from '@/lib/utils';
import { fmtPrice, fmtPct } from '@/lib/format';
import { buildAnchorRow, EXPECTATION, DISCLAIMER, TOOLTIPS, actionChip, holdingChip } from '@/lib/signalCopy';
import { explainExitRules } from '@/lib/exitRules';
import { yahooHistorical } from '@/services/api';
import { normCandle } from '@/lib/candles';
import { GradeBadge } from './GradeBadge';
import { StatusChip } from './StatusChip';
import { PriceArc } from './PriceArc';
import { PriceChart } from './PriceChart';
import { SentimentChip } from './SentimentChip';
import { useIsMobile } from '@/hooks/useIsMobile';

/**
 * SignalDetailDrawer — 440px right-anchored drawer showing the full
 * v7 breakdown for a signal.
 *
 * Sections top→bottom:
 *   1. Header: ticker + grade + status + close btn
 *   2. The plan — plain-English buy/hold/exit summary
 *   3. Price context: current price, intraday arc, delta vs entry
 *   4. Mini price chart (3mo daily bars)
 *   5. Anchor row (entry/stop/target)
 *   6. ATR / pillars footnote
 *   7. Why this stock — p9_news_reason + SentimentChip
 *   8. The risks — p9_news_risk + elevated-risk chip
 *   9. Exit plan timeline — explainExitRules rows with tone borders
 *  10. Your position — 4-tile grid (shares, position value, risk/share, max risk)
 *  11. Model Internals (collapsible) — v7 analytical breakdown
 *  12. What to expect — EXPECTATION prose panel
 *  13. Disclaimer footer — DISCLAIMER in --text-3, 11px italic
 *  14. Sticky footer — Buy CTA
 *
 * Built on Radix Dialog so it inherits focus trap + ESC + overlay click
 * to close. Motion: 280ms slide-in from right using our --ease-panel.
 */
function FactorRow({ item, tone = 'bull' }) {
  const color = tone === 'bull' ? 'var(--bull)' : 'var(--bear)';
  const softColor = tone === 'bull' ? 'var(--bull-soft)' : 'var(--bear-soft)';
  const strength = typeof item?.strength === 'number' ? item.strength : 0;
  const pct = Math.round(Math.max(0, Math.min(1, strength)) * 100);
  return (
    <div
      style={{
        background: 'var(--surface-2)',
        border: '1px solid var(--edge-1)',
        borderRadius: 'var(--r-chip)',
        padding: '12px 14px',
      }}
    >
      <div className="flex items-start justify-between" style={{ gap: 12 }}>
        <div className="min-w-0 flex-1">
          <div
            className="t-ui-subhead"
            style={{ color: 'var(--text-1)', marginBottom: 4 }}
          >
            {item.type || 'Factor'}
          </div>
          {item.evidence && (
            <div
              className="t-ui-footnote"
              style={{ color: 'var(--text-2)' }}
            >
              {item.evidence}
            </div>
          )}
        </div>
        <div
          className="t-num-small"
          style={{ color, minWidth: 36, textAlign: 'right' }}
        >
          {pct}%
        </div>
      </div>
      <div
        role="progressbar"
        aria-valuemin="0"
        aria-valuemax="100"
        aria-valuenow={pct}
        style={{
          marginTop: 10,
          height: 3,
          background: softColor,
          borderRadius: 3,
          overflow: 'hidden',
        }}
      >
        <div
          style={{
            width: `${pct}%`,
            height: '100%',
            background: color,
          }}
        />
      </div>
    </div>
  );
}

function Section({ title, icon, children, ...rest }) {
  return (
    <section style={{ marginTop: 24 }} {...rest}>
      <div className="flex items-center" style={{ gap: 8, marginBottom: 12 }}>
        {icon}
        <h3 className="t-ui-micro" style={{ color: 'var(--text-3)' }}>
          {title}
        </h3>
      </div>
      {children}
    </section>
  );
}

/**
 * Collapsible wrapper that groups V7 model-internal sections under a single
 * disclosure header so they don't compete visually with the primary
 * Catalysts / News / Exit sections. Collapsed by default.
 */
function ModelInternals({ children }) {
  const [open, setOpen] = useState(false);
  return (
    <section style={{ marginTop: 24 }}>
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="flex items-center"
        style={{
          gap: 6,
          background: 'transparent',
          border: 'none',
          cursor: 'pointer',
          padding: 0,
          color: 'var(--text-3)',
          width: '100%',
          textAlign: 'left',
        }}
        aria-expanded={open}
      >
        {open
          ? <ChevronDown size={13} strokeWidth={1.75} />
          : <ChevronRight size={13} strokeWidth={1.75} />}
        <span className="t-ui-micro" style={{ letterSpacing: '0.08em' }}>
          MODEL INTERNALS
        </span>
      </button>
      {open && (
        <div style={{ marginTop: 4 }}>
          {children}
        </div>
      )}
    </section>
  );
}

function statusTone(status) {
  switch ((status || '').toUpperCase()) {
    case 'FRESH': return 'info';
    case 'IN_ZONE': case 'IN ZONE': return 'brand';
    case 'CHASE': case 'NEAR_TARGET': return 'warn';
    case 'HIT_TARGET': case 'FILLED': return 'bull';
    case 'HIT_STOP': case 'REJECTED': return 'bear';
    default: return 'muted';
  }
}

/** Tone → border/text color for exit rule rows. */
function ruleToneColor(tone) {
  switch (tone) {
    case 'bull':    return 'var(--bull)';
    case 'bear':    return 'var(--bear)';
    default:        return 'var(--text-2)';
  }
}

/** Format a date string for display in the plan section. */
function fmtDate(d) {
  if (!d) return null;
  try {
    return new Date(d).toLocaleDateString('en-IN', {
      weekday: 'short',
      day: 'numeric',
      month: 'short',
    });
  } catch {
    return d;
  }
}

export function SignalDetailDrawer({ signal, priceSeries, open, onOpenChange, onOpenOrderPad }) {
  const isMobile = useIsMobile();
  // Hooks must run unconditionally — destructure with a fallback so `signal`
  // can be null/undefined without breaking the hook order. The render branch
  // below short-circuits on missing signal.
  const {
    ticker, sector, status, grade, ml_score, v7_score, v7_layers_agreeing,
    v7_llm_rationale, v7_catalysts, v7_risks, v7_macro_summary, v7_technical_summary,
    entry, entry_high, max_entry, stop, target, stop_pct, target_pct, rr, atr, hold_days, current_price,
    exit_rules, signal_date, buy_window_until,
    // Position / risk sizing fields.
    shares, position_value, risk_per_share, risk_amount,
    // Risk flag from the cron.
    high_risk,
    // P9 news sentiment (stamped by cron via src/data/news_analyzer.py).
    p9_sentiment, p9_news_reason, p9_news_risk, p9_headlines_used,
  } = signal || {};

  // Anchor row segments — source of truth for all price/level copy in the drawer.
  const anchorSegments = buildAnchorRow(signal || {}, fmtPrice, fmtPct);

  // Exit rules — iterable array of rule descriptors.
  const exitRules = useMemo(() => explainExitRules(signal || {}), [signal]);

  // 3 months of daily bars is enough context to read the signal — short enough
  // to load fast, long enough to show whether entry sits inside a recent base
  // or after an extended run. Inline rather than reusing useStockData because
  // the drawer doesn't need holdings / orders / live ticks.
  const { data: rawCandles = [] } = useQuery({
    queryKey: ['yahoo', 'historical', ticker, '1d', '3mo'],
    queryFn: () => yahooHistorical(ticker, '1d', '3mo'),
    staleTime: 5 * 60 * 1000,
    enabled: !!open && !!ticker,
  });

  const drawerCandles = useMemo(
    () =>
      (Array.isArray(rawCandles) ? rawCandles : [])
        .map(normCandle)
        .filter((c) => c && c.value > 0),
    [rawCandles],
  );

  const drawerSignal = useMemo(
    () => ({
      entry:  Number(entry),
      stop:   Number(stop),
      target: Number(target),
    }),
    [entry, stop, target],
  );

  if (!signal) return null;

  const tone = statusTone(status);
  const label = (status || 'PENDING').replace(/_/g, ' ').toUpperCase();

  // Build "The plan" paragraph.
  const planBuyStart = fmtDate(signal_date);
  const planBuyEnd = buy_window_until
    ? fmtDate(buy_window_until)
    : null;
  const planBuyRange = planBuyStart && planBuyEnd
    ? `Buy between ${planBuyStart} – ${planBuyEnd}.`
    : planBuyStart
      ? `Buy from ${planBuyStart}. If you missed that, buy in the next 2-3 trading days.`
      : 'Buy today or in the next 2-3 trading days.';
  // Execution discipline: the buy-limit ceiling — chasing a gap-up above
  // max_entry decays the trade's reward:risk below the floor.
  const planBuyLimit =
    typeof max_entry === 'number' && typeof entry === 'number' && max_entry > entry
      ? ` Use a LIMIT order at or below ₹${Number(max_entry).toLocaleString('en-IN')} — don't chase a gap-up above it (the stop & target are priced off ₹${Number(entry).toLocaleString('en-IN')}, so paying more collapses the reward:risk).`
      : typeof entry === 'number'
        ? ` Use a LIMIT order at or below ₹${Number(entry).toLocaleString('en-IN')} — don't pay above it; the reward:risk is already tight here.`
        : '';
  const planHold = hold_days ? ` Hold ~${hold_days} days.` : '';
  const planExit = ' The model alerts when it is time to sell.';
  const planOutcome = (target != null || stop != null)
    ? ` Outcome: ${target != null ? `target ₹${Number(target).toLocaleString('en-IN')}${target_pct != null ? ` (${target_pct > 0 ? '+' : ''}${Number(target_pct).toFixed(1)}%)` : ''}` : ''}${target != null && stop != null ? ' or ' : ''}${stop != null ? `stop ₹${Number(stop).toLocaleString('en-IN')}${stop_pct != null ? ` (${Number(stop_pct).toFixed(1)}%)` : ''}` : ''}.`
    : '';
  const planText = planBuyRange + planBuyLimit + planHold + planExit + planOutcome;

  const hasPositionData = shares != null || position_value != null || risk_per_share != null || risk_amount != null;

  return (
    <DialogPrimitive.Root open={open} onOpenChange={onOpenChange}>
      <DialogPrimitive.Portal>
        <DialogPrimitive.Overlay
          className="fixed inset-0 z-50"
          style={{ background: 'oklch(0% 0 0 / 0.6)', backdropFilter: 'blur(4px)' }}
        />
        <DialogPrimitive.Content
          className={cn(
            'fixed z-50 flex flex-col',
            isMobile
              ? 'left-0 right-0 bottom-0'
              : 'top-0 right-0 h-full'
          )}
          style={
            isMobile
              ? {
                  width: '100vw',
                  maxHeight: '90dvh',
                  background: 'var(--surface-modal)',
                  backdropFilter: 'blur(24px)',
                  WebkitBackdropFilter: 'blur(24px)',
                  borderTop: '1px solid var(--edge-2)',
                  borderTopLeftRadius: 'var(--r-panel)',
                  borderTopRightRadius: 'var(--r-panel)',
                  boxShadow: 'var(--shadow-lg)',
                  paddingBottom: 'env(safe-area-inset-bottom)',
                }
              : {
                  width: 'min(440px, 100vw)',
                  maxHeight: '100dvh',
                  background: 'var(--surface-modal)',
                  backdropFilter: 'blur(24px)',
                  WebkitBackdropFilter: 'blur(24px)',
                  borderLeft: '1px solid var(--edge-2)',
                  boxShadow: 'var(--shadow-lg)',
                }
          }
          aria-describedby={undefined}
        >
          {/* HEADER */}
          <header
            className="flex items-start justify-between"
            style={{
              padding: '20px 24px 16px',
              borderBottom: '1px solid var(--edge-1)',
              flexShrink: 0,
            }}
          >
            <div className="min-w-0">
              <div className="flex items-center" style={{ gap: 10, marginBottom: 4 }}>
                <DialogPrimitive.Title
                  className="t-title-2"
                  style={{ margin: 0, color: 'var(--text-1)' }}
                >
                  {ticker}
                </DialogPrimitive.Title>
                <GradeBadge grade={grade} v7_score={v7_score} ml_score={ml_score} size="sm" />
                <StatusChip tone={tone}>{label}</StatusChip>
              </div>
              <div className="t-ui-footnote" style={{ color: 'var(--text-3)' }}>
                {sector ? `${sector} · ` : ''}Scanned {signal_date}
              </div>
            </div>
            <DialogPrimitive.Close
              aria-label="Close"
              style={{
                background: 'transparent',
                border: 'none',
                cursor: 'pointer',
                color: 'var(--text-3)',
                padding: 4,
              }}
            >
              <X size={18} strokeWidth={1.75} />
            </DialogPrimitive.Close>
          </header>

          {/* SCROLLABLE BODY */}
          <div
            className="flex-1 overflow-y-auto"
            style={{ padding: '20px 24px' }}
          >
            {/* THE PLAN — plain-English buy/hold/exit summary, first thing visible. */}
            <section style={{ marginBottom: 24 }}>
              <h3
                className="t-ui-micro"
                style={{ color: 'var(--text-3)', marginBottom: 10 }}
              >
                THE PLAN
              </h3>
              <p
                className="t-ui-body t-prose"
                style={{ color: 'var(--text-2)', margin: 0, lineHeight: 1.6 }}
              >
                {planText}
              </p>
            </section>

            {/* PRICE + ARC */}
            <div
              className="flex items-end justify-between"
              style={{ gap: 16, marginBottom: 20 }}
            >
              <div>
                <div className="t-ui-micro" style={{ color: 'var(--text-3)', marginBottom: 6 }}>
                  CURRENT PRICE
                </div>
                <div className="t-num-hero" style={{ color: 'var(--text-1)' }}>
                  {fmtPrice(current_price ?? entry)}
                </div>
                {typeof current_price === 'number' && typeof entry === 'number' && (
                  <div
                    className="t-ui-footnote"
                    style={{
                      color:
                        current_price > entry
                          ? 'var(--bull)'
                          : current_price < entry
                            ? 'var(--bear)'
                            : 'var(--text-3)',
                      marginTop: 4,
                    }}
                  >
                    {fmtPct(((current_price - entry) / entry) * 100)} vs entry
                  </div>
                )}
              </div>
              <PriceArc series={priceSeries} entry={entry} size="wide" />
            </div>

            {/* MINI PRICE CHART — 3mo daily bars with entry/stop/target overlays.
                Tells the trader where the signal levels sit relative to the
                last quarter of price action without leaving the drawer. */}
            {drawerCandles.length > 0 && (
              <div
                style={{
                  marginBottom: 20,
                  background: 'var(--surface-2)',
                  border: '1px solid var(--edge-1)',
                  borderRadius: 'var(--r-chip)',
                  padding: 8,
                }}
              >
                <PriceChart
                  candles={drawerCandles}
                  height={180}
                  chartType="candle"
                  showVolume={false}
                  signal={drawerSignal}
                  ltp={typeof current_price === 'number' ? current_price : null}
                  tone={tone}
                  intraday={false}
                  ariaLabel={`3-month price chart for ${ticker}`}
                />
              </div>
            )}

            {/* ANCHOR ROW — dot-separated mono line replacing the former 3-col grid.
                Format: Entry ₹180–182 · Target ₹209 (+16%) · Stop ₹161 (−11%) · R:R 1.5 · ~15d
                Target is --bull, Stop is --bear, rest --text-2/3. */}
            {anchorSegments.length > 0 && (
              <div
                style={{
                  fontFamily: 'var(--font-mono)',
                  fontSize: 13,
                  fontVariantNumeric: 'tabular-nums lining-nums',
                  lineHeight: 1.6,
                  marginBottom: 16,
                  display: 'flex',
                  flexWrap: 'wrap',
                  alignItems: 'center',
                  padding: '10px 14px',
                  background: 'var(--surface-2)',
                  border: '1px solid var(--edge-1)',
                  borderRadius: 'var(--r-chip)',
                }}
              >
                {anchorSegments.map((seg, i) => (
                  <React.Fragment key={i}>
                    {i > 0 && (
                      <span style={{ color: 'var(--text-4)', margin: '0 7px' }}>·</span>
                    )}
                    <span style={{ color: seg.color ?? 'var(--text-2)' }}>{seg.text}</span>
                  </React.Fragment>
                ))}
              </div>
            )}

            {/* ATR — kept separately since it's a sizing input, not a level */}
            {typeof atr === 'number' && (
              <div
                className="t-ui-footnote"
                style={{ color: 'var(--text-3)', marginBottom: 16 }}
              >
                ATR <span style={{ color: 'var(--text-2)', fontFamily: 'var(--font-mono)', fontVariantNumeric: 'tabular-nums lining-nums' }}>{fmtPrice(atr)}</span>
                {typeof v7_layers_agreeing === 'number' && (
                  <>
                    <span style={{ color: 'var(--text-4)', margin: '0 8px' }}>·</span>
                    <span style={{ color: 'var(--text-2)', fontFamily: 'var(--font-mono)' }}>{v7_layers_agreeing}</span> of 6 pillars
                  </>
                )}
              </div>
            )}
            {typeof atr !== 'number' && typeof v7_layers_agreeing === 'number' && (
              <div
                className="t-ui-footnote"
                style={{ color: 'var(--text-3)', marginBottom: 16 }}
              >
                <span style={{ color: 'var(--text-2)', fontFamily: 'var(--font-mono)' }}>{v7_layers_agreeing}</span> of 6 pillars
              </div>
            )}

            {/* WHY THIS STOCK — p9_news_reason, primary qualitative signal.
                Claude Haiku scored from last 5 headlines (src/data/news_analyzer.py).
                Cache TTL 30d per ticker. */}
            {p9_news_reason && (
              <Section
                title="Why this stock"
                icon={<TrendingUp size={14} strokeWidth={1.75} style={{ color: 'var(--bull)' }} />}
              >
                {/* SentimentChip as subscript context when sentiment data exists. */}
                {p9_headlines_used > 0 && typeof p9_sentiment === 'number' && (
                  <div className="flex items-center" style={{ gap: 8, marginBottom: 8 }}>
                    <SentimentChip
                      score={p9_sentiment}
                      headlinesUsed={p9_headlines_used}
                      size="sm"
                    />
                    <span className="t-ui-footnote" style={{ color: 'var(--text-3)' }}>
                      {p9_headlines_used} headline{p9_headlines_used !== 1 ? 's' : ''} analyzed
                    </span>
                  </div>
                )}
                <p
                  className="t-ui-body t-prose"
                  style={{ color: 'var(--text-2)', margin: 0 }}
                >
                  {p9_news_reason}
                </p>
              </Section>
            )}

            {/* THE RISKS — p9_news_risk, same visual weight as "Why this stock". */}
            {p9_news_risk && p9_news_risk !== 'none' && (
              <Section
                title="The risks"
                icon={<AlertTriangle size={14} strokeWidth={1.75} style={{ color: 'var(--bear)' }} />}
              >
                {/* Elevated risk banner — rendered before the body when flagged. */}
                {high_risk && (
                  <div style={{ marginBottom: 10 }}>
                    <StatusChip tone="warn">ELEVATED RISK</StatusChip>
                  </div>
                )}
                <p
                  className="t-ui-body t-prose"
                  style={{ color: 'var(--text-2)', margin: 0 }}
                >
                  {p9_news_risk}
                </p>
              </Section>
            )}

            {/* EXIT PLAN TIMELINE — each exit rule as a tone-bordered row. */}
            {exitRules.length > 0 && (
              <Section
                title="Exit plan"
                icon={<Newspaper size={14} strokeWidth={1.75} style={{ color: 'var(--text-2)' }} />}
              >
                <div className="flex flex-col" style={{ gap: 10 }}>
                  {exitRules.map((rule) => {
                    const ruleColor = ruleToneColor(rule.tone);
                    return (
                      <div
                        key={rule.id}
                        style={{
                          display: 'flex',
                          alignItems: 'flex-start',
                          gap: 12,
                          padding: '10px 14px',
                          background: 'var(--surface-2)',
                          border: '1px solid var(--edge-1)',
                          borderLeft: `3px solid ${ruleColor}`,
                          borderRadius: 'var(--r-chip)',
                        }}
                      >
                        <span
                          role="img"
                          aria-label={rule.title}
                          style={{ fontSize: 16, lineHeight: 1, flexShrink: 0, marginTop: 1 }}
                        >
                          {rule.icon}
                        </span>
                        <div style={{ minWidth: 0 }}>
                          <div
                            className="t-ui-subhead"
                            style={{ color: ruleColor, marginBottom: 3 }}
                          >
                            {rule.title}
                          </div>
                          <div
                            className="t-ui-footnote"
                            style={{ color: 'var(--text-2)', lineHeight: 1.5 }}
                          >
                            {rule.text}
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </Section>
            )}

            {/* YOUR POSITION — 4-tile grid for position sizing context. */}
            {hasPositionData && (
              <Section title="Your position">
                <div
                  style={{
                    display: 'grid',
                    gridTemplateColumns: '1fr 1fr',
                    gap: 8,
                  }}
                >
                  {[
                    {
                      label: 'Shares',
                      value: shares != null ? Number(shares).toLocaleString('en-IN') : '—',
                      color: 'var(--text-1)',
                    },
                    {
                      label: 'Position value',
                      value: position_value != null
                        ? `₹${Number(position_value).toLocaleString('en-IN')}`
                        : '—',
                      color: 'var(--text-1)',
                    },
                    {
                      label: 'Risk per share',
                      value: risk_per_share != null
                        ? `₹${Number(risk_per_share).toLocaleString('en-IN', { maximumFractionDigits: 2 })}`
                        : '—',
                      color: 'var(--warn)',
                    },
                    {
                      label: 'Max risk',
                      value: risk_amount != null
                        ? `₹${Number(risk_amount).toLocaleString('en-IN')}`
                        : '—',
                      color: 'var(--warn)',
                    },
                  ].map(({ label: tileLabel, value, color }) => (
                    <div
                      key={tileLabel}
                      style={{
                        padding: '10px 12px',
                        background: 'var(--surface-2)',
                        border: '1px solid var(--edge-1)',
                        borderRadius: 'var(--r-chip)',
                      }}
                    >
                      <div
                        className="t-ui-micro"
                        style={{ color: 'var(--text-3)', marginBottom: 6 }}
                      >
                        {tileLabel.toUpperCase()}
                      </div>
                      <div
                        style={{
                          fontFamily: 'var(--font-mono)',
                          fontSize: 15,
                          fontVariantNumeric: 'tabular-nums lining-nums',
                          color,
                        }}
                      >
                        {value}
                      </div>
                    </div>
                  ))}
                </div>
              </Section>
            )}

            {/* MODEL INTERNALS — V7 analytical breakdown, collapsed by default.
                Catalysts, Risks, Technical, Macro, and LLM Rationale are model
                internals: useful for advanced inspection but not needed for a
                buy/hold/sell decision. Downranked under a disclosure toggle so
                the primary sections above breathe. */}
            {(Array.isArray(v7_catalysts) && v7_catalysts.length > 0) ||
             (Array.isArray(v7_risks) && v7_risks.length > 0) ||
             v7_technical_summary || v7_macro_summary || v7_llm_rationale
              ? (
              <ModelInternals>
                {/* CATALYSTS */}
                {Array.isArray(v7_catalysts) && v7_catalysts.length > 0 && (
                  <Section
                    title="Catalysts"
                    icon={<TrendingUp size={14} strokeWidth={1.75} style={{ color: 'var(--bull)' }} />}
                  >
                    <div className="flex flex-col" style={{ gap: 8 }}>
                      {v7_catalysts.map((c, i) => (
                        <FactorRow key={i} item={c} tone="bull" />
                      ))}
                    </div>
                  </Section>
                )}

                {/* RISKS */}
                {Array.isArray(v7_risks) && v7_risks.length > 0 && (
                  <Section
                    title="Risks"
                    icon={<AlertTriangle size={14} strokeWidth={1.75} style={{ color: 'var(--bear)' }} />}
                  >
                    <div className="flex flex-col" style={{ gap: 8 }}>
                      {v7_risks.map((r, i) => (
                        <FactorRow key={i} item={r} tone="bear" />
                      ))}
                    </div>
                  </Section>
                )}

                {/* TECHNICAL SUMMARY */}
                {v7_technical_summary && (
                  <Section title="Technical">
                    <p className="t-ui-body t-prose" style={{ color: 'var(--text-2)' }}>
                      {v7_technical_summary}
                    </p>
                  </Section>
                )}

                {/* MACRO SUMMARY */}
                {v7_macro_summary && (
                  <Section title="Macro">
                    <p className="t-ui-body t-prose" style={{ color: 'var(--text-2)' }}>
                      {v7_macro_summary}
                    </p>
                  </Section>
                )}

                {/* LLM RATIONALE — editorial pull-quote */}
                {v7_llm_rationale && (
                  <Section title="Rationale">
                    <blockquote
                      className="t-prose"
                      style={{
                        fontFamily: 'var(--font-display)',
                        fontSize: 18,
                        lineHeight: 1.45,
                        fontStyle: 'italic',
                        color: 'var(--text-2)',
                        margin: 0,
                        paddingLeft: 16,
                        borderLeft: '1px solid var(--edge-1)',
                      }}
                    >
                      {v7_llm_rationale}
                    </blockquote>
                  </Section>
                )}
              </ModelInternals>
            ) : null}

            {/* WHAT TO EXPECT — backtested expectation prose, subtle box. */}
            <section style={{ marginTop: 32 }}>
              <h3
                className="t-ui-micro"
                style={{ color: 'var(--text-3)', marginBottom: 10 }}
              >
                WHAT TO EXPECT FROM THESE SIGNALS
              </h3>
              <div
                style={{
                  padding: '14px 16px',
                  background: 'var(--surface-1)',
                  border: '1px solid var(--edge-1)',
                  borderRadius: 'var(--r-chip)',
                }}
              >
                <p
                  className="t-ui-body t-prose"
                  style={{ color: 'var(--text-2)', margin: 0, lineHeight: 1.65 }}
                >
                  {EXPECTATION}
                </p>
              </div>
            </section>

            {/* DISCLAIMER — persistent informational footer before the sticky CTA. */}
            <div style={{ marginTop: 20, marginBottom: 8 }}>
              <p
                style={{
                  fontSize: 11,
                  fontStyle: 'italic',
                  color: 'var(--text-3)',
                  lineHeight: 1.55,
                  margin: 0,
                }}
              >
                {DISCLAIMER}
              </p>
            </div>
          </div>

          {/* FOOTER — sticky Buy CTA */}
          {onOpenOrderPad && (
            <footer
              style={{
                flexShrink: 0,
                padding: 20,
                borderTop: '1px solid var(--edge-1)',
                background: 'var(--surface-modal)',
              }}
            >
              <button
                type="button"
                onClick={() => onOpenOrderPad(signal)}
                className="t-ui-headline w-full"
                style={{
                  padding: '12px 16px',
                  background: 'var(--brand)',
                  color: 'var(--brand-fg)',
                  border: '1px solid var(--brand)',
                  borderRadius: 'var(--r-chip)',
                  cursor: 'pointer',
                  fontWeight: 600,
                }}
              >
                Buy {ticker}
              </button>
            </footer>
          )}
        </DialogPrimitive.Content>
      </DialogPrimitive.Portal>
    </DialogPrimitive.Root>
  );
}

export default SignalDetailDrawer;
