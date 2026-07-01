import React from 'react';
import { motion, MotionConfig } from 'framer-motion';
import { TooltipProvider } from '@/components/ui/tooltip';
import { Aurora } from '@/components/shared/Aurora';
import { GlowOrb } from '@/components/shared/GlowOrb';
import { cn } from '@/lib/utils';
import { staggerContainer } from '@/lib/motion';
import { DISCLAIMER } from '@/lib/signalCopy';

/**
 * PageShell — wraps every authenticated app page with a consistent shell.
 *
 *   <Header />
 *   [atmospheric hero band, tone-driven, ~320px tall, behind content]
 *   <motion.main> with stagger container for the page's immediate children
 *
 * The atmospheric hero band is on by default (heroTone='brand') so every
 * V2 page picks up the cinematic backdrop without per-page changes. Set
 * heroTone={null} on pages that need a clean top (e.g. modal-only routes).
 *
 * Props
 * -----
 * title:        string              visually-hidden page heading (H1)
 * ambient:      'amber' | 'none'    (legacy, deprecated)
 * hero:         boolean             wrap first child in a hero zone
 * heroChildren: ReactNode           rendered inside the hero zone
 * heroTone:     'brand'|'bull'|'bear'|'info'|'warn'|null   atmospheric tone
 *                                                          (default 'brand')
 * heroHeight:   number              px tall (default 360)
 * className:    string              extends the page-container className
 */
export function PageShell({
  title,
  ambient = 'none',
  hero = false,
  heroTone = 'brand',
  heroHeight = 360,
  className,
  children,
  heroChildren,
  disclaimer = false,
}) {
  return (
    <MotionConfig reducedMotion="user">
    <TooltipProvider delayDuration={250} skipDelayDuration={100}>
      <div className="min-h-screen relative has-mobile-nav overflow-x-clip">
        {/* Atmospheric hero band — sits above the page background, behind
            everything else. Bounded to ~heroHeight so the rest of the page
            stays clean. Tone-driven so distinct pages read chromatically. */}
        {heroTone && (
          <div
            aria-hidden="true"
            className="absolute left-0 right-0 top-0 pointer-events-none page-shell-hero"
            style={{ height: heroHeight, overflow: 'hidden', zIndex: 0 }}
          >
            <Aurora tone={heroTone} intensity={0.7} />
            <GlowOrb
              tone={heroTone}
              size={760}
              x="50%"
              y="38%"
              blur={170}
              pulse
              style={{ opacity: 0.6 }}
            />
            <GlowOrb
              tone={heroTone === 'brand' ? 'info' : 'brand'}
              size={420}
              x="12%"
              y="22%"
              blur={130}
              style={{ opacity: 0.35 }}
            />
            <GlowOrb
              tone={heroTone === 'info' ? 'brand' : 'info'}
              size={380}
              x="88%"
              y="28%"
              blur={120}
              style={{ opacity: 0.3 }}
            />
            {/* Soft fade-to-black at the bottom of the band so the
                atmospheric layer dissolves into the page surface. */}
            <div
              style={{
                position: 'absolute',
                left: 0,
                right: 0,
                bottom: 0,
                height: 120,
                background:
                  'linear-gradient(to bottom, transparent 0%, var(--surface-0) 100%)',
              }}
            />
          </div>
        )}

        <div className={cn('page-container relative', className)} style={{ zIndex: 1 }}>
          {/* Global TopBar (App.js → ProtectedAppLayout) is the only chrome.
              The in-page Header here was a holdover from the sidebar era — removed
              2026-05-21 so /dashboard, /signals etc don't render two stacked bars. */}

          {title && <h1 className="sr-only">{title}</h1>}

          {hero && (
            <motion.div
              variants={staggerContainer}
              initial="hidden"
              animate="visible"
              className="relative z-10"
            >
              {heroChildren}
            </motion.div>
          )}

          <motion.main
            variants={staggerContainer}
            initial="hidden"
            animate="visible"
            className={cn('relative z-10', hero ? 'mt-6' : 'mt-6')}
          >
            {children}
            {/* COMPLIANCE: opt-in SEBI disclaimer footer for pages that show
                performance / financial figures (Analytics, Backtest, Track
                Record, Stock Detail). Default off so pages with their own
                disclaimer (Signals, Portfolio, Dashboard) don't double up. */}
            {disclaimer && (
              <div style={{ marginTop: 40, paddingTop: 16, borderTop: '1px solid var(--edge-1)' }}>
                <div style={{ fontFamily: 'var(--font-mono)', fontSize: 11, fontStyle: 'italic', color: 'var(--text-3)', lineHeight: 1.5 }}>
                  {DISCLAIMER}
                </div>
                <div style={{ fontFamily: 'var(--font-mono)', fontSize: 11, color: 'var(--text-4)', marginTop: 6 }}>
                  SEBI Research Analyst · Model-generated signals · Research output only · NSE data delayed 15 min · v2026.06
                </div>
              </div>
            )}
          </motion.main>
        </div>
      </div>
    </TooltipProvider>
    </MotionConfig>
  );
}
