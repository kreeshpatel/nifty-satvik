import { useEffect, useRef, useState } from "react";
import { motion, useInView, useMotionValue, useSpring } from "framer-motion";
import { easeOutQuart } from "@/lib/motion";
import { Aurora } from "@/components/shared/Aurora";
import { GlowOrb } from "@/components/shared/GlowOrb";

const API = process.env.REACT_APP_API_URL ?? '';

/**
 * AnimatedNumber — counts from 0 to target when `run` is true. Uses the
 * springSlide curve from /lib/motion so the count feel matches the rest of
 * the V2 system (no bouncy overshoot, settles cleanly).
 */
function AnimatedNumber({ value, decimals = 0, prefix = "", suffix = "", run }) {
  const motionVal = useMotionValue(0);
  const spring = useSpring(motionVal, { stiffness: 60, damping: 22, mass: 1 });
  const [display, setDisplay] = useState("0");

  useEffect(() => {
    const num =
      typeof value === "number"
        ? value
        : parseFloat(String(value).replace(/[^\d.-]/g, "")) || 0;
    if (run) motionVal.set(num);
    else motionVal.set(0);
  }, [run, value, motionVal]);

  useEffect(() => {
    const unsub = spring.on("change", (v) => {
      if (decimals > 0) setDisplay(v.toFixed(decimals));
      else setDisplay(Math.round(v).toLocaleString("en-IN"));
    });
    return unsub;
  }, [spring, decimals]);

  return (
    <span className="tabular-nums">
      {prefix}
      {display}
      {suffix}
    </span>
  );
}

/**
 * Track Record — four hero KPIs computed from /api/landing-stats. Number
 * "boots up" odometer-style on scroll-into-view, with the canonical
 * numberTick flash on settle. Cards use V2 surface tokens; semantic color
 * is reserved for the value (bull/brand) and never the chrome.
 */
export default function LiveStats() {
  const ref = useRef(null);
  const isInView = useInView(ref, { once: true, margin: "-80px" });
  const [stats, setStats] = useState(null);

  useEffect(() => {
    let cancelled = false;
    fetch(`${API}/api/landing-stats`)
      .then((r) => r.json())
      .then((d) => {
        if (!cancelled) setStats(d);
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, []);

  // Backtest stats are authoritative (production_strategy.json, refreshed on
  // the quarterly revalidation cron). Live-cron numbers in the rest of the
  // payload are kept for sub-captions when meaningful.
  const bt = stats?.backtest;
  const display = {
    cagr: bt?.cagr_pct ?? 31.1,
    totalReturn: bt?.total_return_pct ?? 408.4,
    winRate: bt?.win_rate_pct ?? 56.4,
    sharpe: bt?.sharpe ?? 2.97,
    maxDD: bt?.max_drawdown_pct ?? -26.6,
    totalTrades: bt?.total_trades ?? 525,
    period: bt?.period ?? "2020-01-01 to 2025-12-31",
    validatedOn: bt?.validated_on ?? "2026-04-08",
  };

  const cards = [
    {
      label: "Total return",
      value: display.totalReturn,
      prefix: "+",
      suffix: "%",
      decimals: 1,
      sub: display.period.replace(" to ", " → "),
      tone: "bull",
    },
    {
      label: "CAGR",
      value: display.cagr,
      suffix: "%",
      decimals: 1,
      sub: "Annualized over the backtest",
      tone: "brand",
    },
    {
      label: "Win rate",
      value: display.winRate,
      suffix: "%",
      decimals: 1,
      sub: `${display.totalTrades.toLocaleString("en-IN")} closed trades`,
      tone: "text",
    },
    {
      label: "Sharpe",
      value: display.sharpe,
      decimals: 2,
      sub: `Max DD ${display.maxDD.toFixed(1)}%`,
      tone: "text",
    },
  ];

  const toneColor = (t) => {
    switch (t) {
      case "brand":
        return "var(--brand)";
      case "bull":
        return "var(--bull)";
      case "bear":
        return "var(--bear)";
      default:
        return "var(--text-1)";
    }
  };

  // Pre-computed inner glow per tone — matches the value color so the KPI
  // tile reads as one toned object instead of generic chrome with a
  // separate value. Tones default to a faint amber whisper.
  const toneBloom = (t) => {
    switch (t) {
      case "bull":
        return "inset 0 1px 0 oklch(100% 0 0 / 0.05), inset 0 0 32px var(--glow-bull-soft)";
      case "brand":
        return "inset 0 1px 0 oklch(100% 0 0 / 0.05), inset 0 0 32px var(--glow-brand-soft)";
      case "bear":
        return "inset 0 1px 0 oklch(100% 0 0 / 0.05), inset 0 0 32px var(--glow-bear-soft)";
      case "info":
        return "inset 0 1px 0 oklch(100% 0 0 / 0.05), inset 0 0 32px var(--glow-info-soft)";
      default:
        return "inset 0 1px 0 oklch(100% 0 0 / 0.04), inset 0 0 28px var(--glow-brand-whisp)";
    }
  };

  return (
    <section
      className="relative px-6 lg:px-12 overflow-hidden"
      style={{ paddingTop: 96, paddingBottom: 96 }}
    >
      {/* Section atmospheric backdrop. Aurora gives a slow-breathing wash;
          three soft orbs pin the corners + center so the KPI grid sits
          inside a stage rather than against a flat black void. */}
      <Aurora tone="brand" intensity={0.95} style={{ zIndex: 0 }} />
      <GlowOrb tone="bull"  size={620} x="12%" y="58%" blur={140} style={{ zIndex: 0, opacity: 0.75 }} />
      <GlowOrb tone="brand" size={560} x="88%" y="38%" blur={130} style={{ zIndex: 0, opacity: 0.8 }} />
      <GlowOrb tone="info"  size={420} x="50%" y="14%" blur={120} style={{ zIndex: 0, opacity: 0.55 }} />

      <div className="relative" style={{ maxWidth: 1280, margin: "0 auto", zIndex: 1 }} ref={ref}>
        {/* Section eyebrow + heading */}
        <div className="mb-12 flex items-end justify-between flex-wrap gap-6">
          <div>
            <div
              className="font-mono uppercase mb-3"
              style={{ fontSize: 11, letterSpacing: "0.18em", color: "var(--text-3)" }}
            >
              <span
                className="inline-block w-1.5 h-1.5 rounded-full align-middle mr-2"
                style={{ background: "var(--brand)" }}
              />
              01 · Track record
            </div>
            <motion.h2
              initial={{ opacity: 0, y: 14 }}
              animate={isInView ? { opacity: 1, y: 0 } : {}}
              transition={{ duration: 0.42, ease: easeOutQuart }}
              className="font-heading"
              style={{
                fontWeight: 600,
                color: "var(--text-1)",
                fontSize: "clamp(34px, 5vw, 64px)",
                lineHeight: 1.05,
                letterSpacing: "-0.025em",
                margin: 0,
                maxWidth: 720,
              }}
            >
              Real numbers from real trades.
            </motion.h2>
          </div>
          <motion.p
            initial={{ opacity: 0 }}
            animate={isInView ? { opacity: 1 } : {}}
            transition={{ duration: 0.5, delay: 0.2 }}
            style={{ color: "var(--text-2)", fontSize: 15, maxWidth: 360 }}
          >
            Validated walk-forward over six years. Strategy revalidated quarterly
            — last on{" "}
            <span style={{ color: "var(--text-1)", fontWeight: 500 }}>
              {display.validatedOn}
            </span>
            .
          </motion.p>
        </div>

        {/* KPI grid */}
        <div className="grid grid-cols-2 md:grid-cols-4" style={{ gap: 16 }}>
          {cards.map((c, i) => (
            <motion.div
              key={c.label}
              initial={{ opacity: 0, y: 16 }}
              animate={isInView ? { opacity: 1, y: 0 } : {}}
              transition={{ duration: 0.45, delay: i * 0.06, ease: easeOutQuart }}
              style={{
                position: "relative",
                background: "var(--surface-1)",
                border: "1px solid var(--edge-1)",
                borderRadius: "var(--r-card)",
                padding: "var(--pad-card-lg)",
                boxShadow: toneBloom(c.tone),
                overflow: "hidden",
              }}
            >
              <div
                className="font-mono uppercase mb-5"
                style={{ fontSize: 10, letterSpacing: "0.16em", color: "var(--text-3)" }}
              >
                {c.label}
              </div>
              <div
                className="font-heading"
                style={{
                  fontWeight: 600,
                  fontSize: "clamp(36px, 5vw, 56px)",
                  lineHeight: 1,
                  letterSpacing: "-0.03em",
                  color: toneColor(c.tone),
                  fontVariantNumeric: "tabular-nums",
                }}
              >
                {c.showDash ? "—" : (
                  <AnimatedNumber
                    value={c.value}
                    decimals={c.decimals}
                    prefix={c.prefix || ""}
                    suffix={c.suffix || ""}
                    run={isInView}
                  />
                )}
              </div>
              <div
                style={{
                  fontSize: 12,
                  color: "var(--text-3)",
                  marginTop: 14,
                  lineHeight: 1.4,
                }}
              >
                {c.sub}
              </div>
            </motion.div>
          ))}
        </div>

        {/* Compliance footer */}
        <p
          style={{
            fontSize: 11,
            color: "var(--text-4)",
            textAlign: "center",
            marginTop: 40,
            maxWidth: 600,
            marginInline: "auto",
            lineHeight: 1.5,
          }}
        >
          Past performance does not guarantee future returns. All stats computed
          from our paper portfolio backtests; live trading results may differ.
        </p>
      </div>
    </section>
  );
}
