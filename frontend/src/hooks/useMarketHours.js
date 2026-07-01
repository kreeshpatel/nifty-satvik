import { useEffect, useState } from "react";

/**
 * IST timezone: UTC+5:30.
 * Nifty market hours: 09:15 to 15:30 IST, Mon-Fri.
 * (Pre-open 09:00-09:15 and post-close are intentionally excluded here.)
 */
export function isMarketHours(date = new Date()) {
  // Convert to IST components using Intl to avoid local-timezone bugs.
  const parts = new Intl.DateTimeFormat("en-GB", {
    timeZone: "Asia/Kolkata",
    weekday: "short",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  }).formatToParts(date);

  const map = Object.fromEntries(parts.map((p) => [p.type, p.value]));
  const weekday = map.weekday;
  const hour = parseInt(map.hour, 10);
  const minute = parseInt(map.minute, 10);

  if (weekday === "Sat" || weekday === "Sun") return false;

  const mins = hour * 60 + minute;
  return mins >= 9 * 60 + 15 && mins <= 15 * 60 + 30;
}

/**
 * Minutes until the next market event (open or close).
 * Returns { minutesUntil, label } — e.g. { 128, "market opens" } or { 45, "market closes" }.
 */
export function minutesUntilMarketEvent(date = new Date()) {
  const istNow = new Date(date.toLocaleString("en-US", { timeZone: "Asia/Kolkata" }));
  const hour = istNow.getHours();
  const minute = istNow.getMinutes();
  const day = istNow.getDay(); // 0 = Sun, 6 = Sat
  const mins = hour * 60 + minute;
  const OPEN = 9 * 60 + 15;
  const CLOSE = 15 * 60 + 30;

  if (day >= 1 && day <= 5) {
    if (mins < OPEN) return { minutesUntil: OPEN - mins, label: "market opens" };
    if (mins <= CLOSE) return { minutesUntil: CLOSE - mins, label: "market closes" };
  }
  // Find next weekday open
  let d = new Date(istNow);
  d.setHours(9, 15, 0, 0);
  d.setDate(d.getDate() + 1);
  while (d.getDay() === 0 || d.getDay() === 6) d.setDate(d.getDate() + 1);
  const diff = Math.round((d.getTime() - istNow.getTime()) / 60000);
  return { minutesUntil: diff, label: "market opens" };
}

/**
 * Reactive hook — returns { isOpen, minutesUntil, label }.
 * Re-evaluates every 30 seconds so the UI reflects minute ticks without
 * a hard refresh loop.
 */
export default function useMarketHours() {
  const [state, setState] = useState(() => ({
    isOpen: isMarketHours(),
    ...minutesUntilMarketEvent(),
  }));

  useEffect(() => {
    const tick = () => {
      setState({ isOpen: isMarketHours(), ...minutesUntilMarketEvent() });
    };
    tick();
    const id = setInterval(tick, 30_000);
    return () => clearInterval(id);
  }, []);

  return state;
}
