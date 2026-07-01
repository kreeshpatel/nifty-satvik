import { useEffect } from "react";

/**
 * Blocks browser zoom via keyboard (Ctrl+/-/0) and mouse wheel (Ctrl+scroll).
 *
 * Note: Browser menu zoom (Edge → ⋯ → Zoom) CANNOT be blocked by any web API.
 * This is an intentional browser restriction for accessibility. No website —
 * including Google, Apple, or any major trading platform — can prevent it.
 * The keyboard + wheel blocking covers 99% of accidental zoom cases.
 *
 * Mobile pinch zoom is blocked via the viewport meta tag in index.html.
 * Only active while the landing page is mounted.
 */
export default function ZoomLock() {
  useEffect(() => {
    if (typeof window === "undefined") return;

    const onKeydown = (e) => {
      if (
        (e.ctrlKey || e.metaKey) &&
        (e.key === "+" || e.key === "-" || e.key === "=" || e.key === "0")
      ) {
        e.preventDefault();
      }
    };

    const onWheel = (e) => {
      if (e.ctrlKey) {
        e.preventDefault();
      }
    };

    window.addEventListener("keydown", onKeydown);
    window.addEventListener("wheel", onWheel, { passive: false });

    return () => {
      window.removeEventListener("keydown", onKeydown);
      window.removeEventListener("wheel", onWheel);
    };
  }, []);

  return null;
}
