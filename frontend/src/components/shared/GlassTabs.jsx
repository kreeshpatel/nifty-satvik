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
        'inline-flex items-center gap-0 p-0 rounded',
        className
      )}
      style={{
        background: 'transparent',
        border: '1px solid var(--n4)',   /* v7 segmented control: ruled, no pill (brief §10) */
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
              'relative rounded-none font-medium transition-colors duration-200 whitespace-nowrap',
              'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#F0B429] focus-visible:ring-offset-0',
              'inline-flex items-center',
              sizing,
              isActive ? 'text-[#E6E9EE]' : 'text-[#7A8494] hover:text-[#E6E9EE]'
            )}
          >
            {isActive && (
              <motion.span
                layoutId={layoutId}
                className="absolute inset-0"
                style={{
                  background: 'var(--n3)', boxShadow: 'inset 0 -2px 0 var(--acc)',
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
