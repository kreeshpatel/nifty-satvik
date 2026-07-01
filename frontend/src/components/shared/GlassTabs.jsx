import React from 'react';
import { motion } from 'framer-motion';
import { cn } from '@/lib/utils';
import { useTablistKeyboard } from '@/lib/useTablistKeyboard';

/**
 * GlassTabs — pill-style tab bar with spring-animated amber indicator.
 *
 * Full keyboard support via useTablistKeyboard (arrows, Home/End).
 * Focus ring visible on keyboard-only focus. Touch targets ≥ 44px on
 * mobile (below sm breakpoint) per WCAG 2.5.5.
 */
export function GlassTabs({
  tabs,
  active,
  onChange,
  size = 'md',
  className,
  layoutId = 'glass-tabs-pill',
}) {
  const normalized = tabs.map((t) =>
    typeof t === 'string' ? { key: t, label: t } : t
  );

  const onKeyDown = useTablistKeyboard(normalized, active, onChange);

  // Touch target ≥ 44px on mobile, denser on desktop.
  const sizing =
    size === 'sm'
      ? 'text-[11px] min-h-[36px] sm:min-h-[28px] px-3'
      : size === 'lg'
      ? 'text-sm min-h-[44px] sm:min-h-[40px] px-5'
      : 'text-[13px] min-h-[44px] sm:min-h-[32px] px-4';

  return (
    <div
      role="tablist"
      onKeyDown={onKeyDown}
      className={cn(
        'inline-flex items-center gap-1 p-1 rounded-full',
        className
      )}
      style={{
        background: 'rgba(255, 255, 255, 0.035)',
        border: '1px solid rgba(255, 255, 255, 0.05)',
      }}
    >
      {normalized.map(({ key, label }) => {
        const isActive = active === key;
        return (
          <motion.button
            key={key}
            role="tab"
            aria-selected={isActive}
            tabIndex={isActive ? 0 : -1}
            onClick={() => onChange(key)}
            className={cn(
              'relative rounded-full font-semibold transition-colors duration-200 whitespace-nowrap',
              'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#22DD88]/70 focus-visible:ring-offset-2 focus-visible:ring-offset-[#0F172A]',
              'inline-flex items-center',
              sizing,
              isActive ? 'text-[#0F172A]' : 'text-nq-text-muted hover:text-nq-text-primary'
            )}
          >
            {isActive && (
              <motion.span
                layoutId={layoutId}
                className="absolute inset-0 rounded-full"
                style={{
                  background: '#22DD88',
                }}
                transition={{
                  type: 'spring',
                  stiffness: 420,
                  damping: 30,
                  mass: 0.7,
                }}
              />
            )}
            <span className="relative z-10">{label}</span>
          </motion.button>
        );
      })}
    </div>
  );
}
