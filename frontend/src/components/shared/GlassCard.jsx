import React from 'react';
import { cn } from '@/lib/utils';

/**
 * GlassCard — solid-card composition primitive.
 *
 * NOTE: the name is historical. We pivoted from liquid-glass to a
 * modern-SaaS direction with solid dark-navy cards. The API is unchanged
 * so existing call sites keep working; only the visual output shifted.
 *
 * Tiers:
 *   tier=1  → primary card surface (#1E293B navy)
 *   tier=2  → nested / secondary surface (#162032 slightly deeper)
 *   tier=3  → interactive chip / input (transparent white 5%)
 *
 * Props
 * -----
 * tier:        1 | 2 | 3          default 1
 * hoverLift:   boolean            adds lift-on-hover transition
 * ambient:     boolean            reserved (no-op in modern-SaaS direction)
 * interactive: boolean            adds pointer cursor + focus ring
 * as:          component override default 'div'
 */
export const GlassCard = React.forwardRef(function GlassCard(
  {
    tier = 1,
    hoverLift = false,
    ambient: _ambient = false,
    interactive = false,
    as: Component = 'div',
    className,
    children,
    ...props
  },
  ref
) {
  const tierClass =
    tier === 3
      ? 'surface-3'
      : tier === 2
      ? 'card-solid-2'
      : 'card-solid';

  return (
    <Component
      ref={ref}
      className={cn(
        'relative overflow-hidden transition-all duration-200',
        tierClass,
        hoverLift &&
          'hover:-translate-y-[1px] hover:border-white/10 hover:shadow-lg hover:shadow-black/30 active:scale-[0.995]',
        interactive &&
          'cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#22DD88] focus-visible:ring-offset-2 focus-visible:ring-offset-[#0F172A]',
        className
      )}
      {...props}
    >
      {children}
    </Component>
  );
});
