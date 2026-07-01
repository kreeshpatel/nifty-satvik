import { useState, useEffect } from "react";
import { motion, useScroll, useTransform } from "framer-motion";
import { TrendingUp, TrendingDown } from "lucide-react";

const API = process.env.REACT_APP_API_URL ?? '';

const MiniSparkline = ({ data, positive }) => {
  if (!data || data.length < 2) return null;
  const min = Math.min(...data);
  const max = Math.max(...data);
  const range = max - min || 1;
  const h = 16;
  const w = 48;
  const points = data
    .map((v, i) => `${(i / (data.length - 1)) * w},${h - ((v - min) / range) * h}`)
    .join(" ");

  return (
    <svg width={w} height={h} className="inline-block ml-1">
      <polyline
        points={points}
        fill="none"
        stroke={positive ? "oklch(72% 0.19 145)" : "oklch(66% 0.21 25)"}
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
};

export default function LiveTicker() {
  const [indices, setIndices] = useState([
    { name: "NIFTY 50", value: 24867.5, change: 1.24, sparkline: [] },
    { name: "BANK NIFTY", value: 52345.8, change: -0.32, sparkline: [] },
    { name: "SENSEX", value: 81456.2, change: 0.89, sparkline: [] },
    { name: "INDIA VIX", value: 13.25, change: -2.15, sparkline: [] },
  ]);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const res = await fetch(`${API}/api/yahoo/index-sparklines`);
        if (!res.ok) return;
        const data = await res.json();
        if (!data || typeof data !== "object") return;

        setIndices(prev => prev.map(idx => {
          const live = data[idx.name];
          if (!live) return idx;
          return {
            ...idx,
            value: live.ltp || idx.value,
            change: live.change_pct ?? idx.change,
            sparkline: Array.isArray(live.sparkline) ? live.sparkline : idx.sparkline,
          };
        }));
      } catch (e) {
        // Silently fall back to default data
      }
    };
    fetchData();
    const interval = setInterval(fetchData, 30000);
    return () => clearInterval(interval);
  }, []);

  // Scroll-driven collapse: full bar → thin colored line
  const { scrollY } = useScroll();
  const height = useTransform(scrollY, [0, 120], [36, 3]);
  const contentOpacity = useTransform(scrollY, [0, 80], [1, 0]);
  const barOpacity = useTransform(scrollY, [80, 120], [0, 1]);

  return (
    <motion.div
      data-testid="live-ticker"
      className="fixed top-0 left-0 right-0 z-[60]"
      style={{ height, paddingTop: "env(safe-area-inset-top)" }}
    >
      {/* Full ticker content — fades out on scroll */}
      <motion.div
        className="absolute inset-0"
        style={{
          opacity: contentOpacity,
          background: "rgba(0,0,0,0.95)",
          borderBottom: "1px solid var(--edge-1)",
          backdropFilter: "blur(8px)",
          WebkitBackdropFilter: "blur(8px)",
        }}
      >
        <div className="h-9 max-w-7xl mx-auto px-6 flex items-center justify-center gap-8 overflow-x-auto ticker-scroll">
          {indices.map((idx, i) => (
            <div
              key={i}
              className="flex items-center gap-2 whitespace-nowrap"
            >
              <span className="text-[11px] font-mono tracking-wider text-[color:var(--text-3)]">
                {idx.name}
              </span>
              <span className="text-[11px] font-mono font-medium text-white tabular-nums">
                {typeof idx.value === "number"
                  ? idx.value.toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })
                  : idx.value}
              </span>
              <span
                className={`text-[11px] font-mono flex items-center gap-0.5 ${
                  idx.change >= 0 ? "text-[color:var(--bull)]" : "text-[color:var(--bear)]"
                }`}
              >
                {idx.change >= 0 ? (
                  <TrendingUp className="w-3 h-3" />
                ) : (
                  <TrendingDown className="w-3 h-3" />
                )}
                {idx.change >= 0 ? "+" : ""}
                {Number(idx.change).toFixed(2)}%
              </span>
              {idx.sparkline && idx.sparkline.length > 0 && (
                <MiniSparkline data={idx.sparkline} positive={idx.change >= 0} />
              )}
            </div>
          ))}
          <div className="flex items-center gap-1.5">
            <span className="w-1.5 h-1.5 rounded-full bg-[color:var(--bull)] animate-pulse" />
            <span className="text-[10px] font-mono text-[color:var(--text-3)]">LIVE</span>
          </div>
        </div>
      </motion.div>

      {/* Collapsed state — thin amber line */}
      <motion.div
        className="absolute inset-x-0 top-0 h-[3px]"
        style={{ opacity: barOpacity, background: "var(--brand)" }}
      />
    </motion.div>
  );
}
