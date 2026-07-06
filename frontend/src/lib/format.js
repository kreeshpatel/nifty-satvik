/**
 * Shared number/date formatting utilities for Nifty Satvik.
 * Use these everywhere instead of inline toLocaleString/toFixed.
 */

/**
 * Smart INR formatting with L/Cr suffixes.
 * fmtINR(2450000) → "₹24.5L"
 * fmtINR(120000000) → "₹12.0Cr"
 * fmtINR(8420) → "₹8,420"
 * fmtINR(-1875) → "-₹1,875"
 */
export const fmtINR = (v) => {
  if (v == null || isNaN(v)) return "₹0";
  const abs = Math.abs(v);
  const sign = v < 0 ? "-" : "";
  if (abs >= 10000000) return `${sign}₹${(abs / 10000000).toFixed(2)} Cr`;
  if (abs >= 100000) return `${sign}₹${(abs / 100000).toFixed(2)}L`;
  return `${sign}₹${abs.toLocaleString("en-IN")}`;
};

/**
 * Format a raw number as INR price (always shows decimals).
 * fmtPrice(24867.5) → "₹24,867.50"
 */
export const fmtPrice = (v) => {
  if (v == null || isNaN(v)) return "₹0";
  return `₹${Number(v).toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
};

/**
 * Percentage with explicit sign.
 * fmtPct(4.2) → "+4.20%"
 * fmtPct(-1.8) → "-1.80%"
 */
export const fmtPct = (v, decimals = 2) => {
  if (v == null || isNaN(v)) return "0.00%";
  const num = Number(v);
  return `${num >= 0 ? "+" : ""}${num.toFixed(decimals)}%`;
};

/**
 * Volume formatting with Cr/L suffixes.
 * fmtVolume(263363794) → "26.3Cr"
 * fmtVolume(845000) → "8.5L"
 * fmtVolume(42000) → "42,000"
 */
export const fmtVolume = (v) => {
  if (v == null || isNaN(v)) return "0";
  const abs = Math.abs(v);
  if (abs >= 10000000) return `${(abs / 10000000).toFixed(1)}Cr`;
  if (abs >= 100000) return `${(abs / 100000).toFixed(1)}L`;
  return abs.toLocaleString("en-IN");
};

/**
 * Parse an ISO timestamp from the backend, treating naive (no-timezone) strings
 * as UTC. The Python backend writes `datetime.utcnow().isoformat()` which
 * produces e.g. "2026-04-27T10:46:45.711535" — a UTC instant with no `Z`
 * suffix. JavaScript's Date parser interprets such strings as LOCAL time,
 * which silently shifts every backend timestamp by the user's UTC offset
 * (e.g. -5.5h in IST). Forcing the `Z` suffix when no timezone marker is
 * present makes the parse correct.
 */
const parseBackendTs = (s) => {
  if (typeof s !== "string") return s instanceof Date ? s : null;
  // Already has a timezone marker (Z or ±HH:MM / ±HHMM) — trust as-is.
  if (/Z$|[+-]\d{2}:?\d{2}$/.test(s)) return new Date(s);
  // ISO-shaped without timezone — treat as UTC.
  if (/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}/.test(s)) return new Date(s + "Z");
  // Fallback (date-only or other) — let the engine handle it.
  return new Date(s);
};

/**
 * Relative time from a date string or Date object.
 * fmtRelTime("2026-04-10T01:30:00") → "3m ago"
 */
export const fmtRelTime = (dateInput) => {
  if (!dateInput) return "";
  // If already a relative string like "2h ago", return as-is
  if (typeof dateInput === "string" && /\d+[mhd]\s*ago|yesterday|just now/i.test(dateInput)) {
    return dateInput;
  }
  const date = typeof dateInput === "string" ? parseBackendTs(dateInput) : dateInput;
  if (!date || isNaN(date.getTime())) return dateInput || "";
  const now = new Date();
  const diffMs = now - date;
  const diffMin = Math.floor(diffMs / 60000);
  const diffHr = Math.floor(diffMs / 3600000);
  const diffDay = Math.floor(diffMs / 86400000);

  if (diffMin < 1) return "Just now";
  if (diffMin < 60) return `${diffMin}m ago`;
  if (diffHr < 24) return `${diffHr}h ago`;
  if (diffDay === 1) return "Yesterday";
  if (diffDay < 7) return `${diffDay}d ago`;
  return date.toLocaleDateString("en-IN", { day: "numeric", month: "short" });
};
