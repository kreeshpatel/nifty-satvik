import { useCallback } from 'react';

/**
 * useTablistKeyboard — arrow-key navigation for ARIA tablists.
 *
 * WCAG 2.1.1 Keyboard + ARIA authoring-practices expectation:
 *   Left / Right  → move focus to previous / next tab (wraps at edges)
 *   Home / End    → first / last tab
 *   Enter / Space → activate focused tab (native <button> handles automatically)
 *
 * Usage:
 *   const onKeyDown = useTablistKeyboard(tabs, active, onChange);
 *   <div role="tablist" onKeyDown={onKeyDown}>...</div>
 *
 * tabs:     array of { key } objects OR string array
 * active:   current active key (string)
 * onChange: (key) => void
 */
export function useTablistKeyboard(tabs, active, onChange) {
  return useCallback(
    (e) => {
      const keys = tabs.map((t) => (typeof t === 'string' ? t : t.key));
      const idx = keys.indexOf(active);
      if (idx === -1) return;

      let next = null;
      switch (e.key) {
        case 'ArrowRight':
        case 'ArrowDown':
          next = keys[(idx + 1) % keys.length];
          break;
        case 'ArrowLeft':
        case 'ArrowUp':
          next = keys[(idx - 1 + keys.length) % keys.length];
          break;
        case 'Home':
          next = keys[0];
          break;
        case 'End':
          next = keys[keys.length - 1];
          break;
        default:
          return;
      }

      if (next !== null) {
        e.preventDefault();
        onChange(next);
      }
    },
    [tabs, active, onChange]
  );
}
