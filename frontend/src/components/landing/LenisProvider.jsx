import { useEffect, useRef } from "react";
import { useLocation } from "react-router-dom";

/**
 * Wraps the landing page (or any page that wants smooth scrolling) with Lenis.
 * Automatically destroys Lenis when the user navigates away from the landing page,
 * because the dashboard pages have their own scroll containers.
 */
export default function LenisProvider({ children }) {
  const lenisRef = useRef(null);
  const location = useLocation();

  useEffect(() => {
    let lenis;
    let rafId;

    // Only enable on landing page
    if (location.pathname !== "/") {
      return;
    }

    let cancelled = false;
    (async () => {
      try {
        const mod = await import("lenis");
        if (cancelled) return;
        const Lenis = mod.default;

        lenis = new Lenis({
          duration: 1.2,
          easing: (t) => Math.min(1, 1.001 - Math.pow(2, -10 * t)),
          smoothWheel: true,
          smoothTouch: false,
          wheelMultiplier: 1,
          touchMultiplier: 2,
        });

        lenisRef.current = lenis;

        const raf = (time) => {
          lenis.raf(time);
          rafId = requestAnimationFrame(raf);
        };
        rafId = requestAnimationFrame(raf);
      } catch (e) {
        // Lenis not installed or failed — fall back to native scroll
        console.warn("Lenis not available, using native scroll");
      }
    })();

    return () => {
      cancelled = true;
      if (rafId) cancelAnimationFrame(rafId);
      if (lenis) lenis.destroy();
      lenisRef.current = null;
    };
  }, [location.pathname]);

  return children;
}
