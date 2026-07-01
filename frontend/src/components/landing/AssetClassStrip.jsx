import { motion } from "framer-motion";

/**
 * AssetClassStrip — section divider between hero and feature grid.
 *
 * fxreplay shows Forex / Futures / Stocks / Crypto / Indexes / Energy
 * as an asset-class tab strip. We translate to NIFTY-shaped tabs:
 * Largecap / Midcap / Smallcap / Sector. Each tab carries a count of
 * how many stocks in that bucket pass the universe filter.
 *
 * No interaction — pure presentation. Sits as a quiet "what we cover"
 * statement before the deeper feature explanations.
 */

const TABS = [
  { label: "Largecap", count: "100 stocks" },
  { label: "Midcap", count: "150 stocks" },
  { label: "Smallcap", count: "191 stocks" },
  { label: "Sector ETFs", count: "12 tracked" },
];

export default function AssetClassStrip() {
  return (
    <section className="acstrip">
      <div className="acstrip-inner">
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-15%" }}
          transition={{ duration: 0.6, ease: [0.22, 1, 0.36, 1] }}
          className="acstrip-eyebrow"
        >
          We cover the entire NIFTY 500
        </motion.div>
        <div className="acstrip-tabs">
          {TABS.map((t, i) => (
            <motion.div
              key={t.label}
              initial={{ opacity: 0, y: 14 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, margin: "-15%" }}
              transition={{
                duration: 0.6,
                delay: 0.05 + i * 0.08,
                ease: [0.22, 1, 0.36, 1],
              }}
              className="acstrip-tab"
            >
              <span className="acstrip-tab-label">{t.label}</span>
              <span className="acstrip-tab-count">{t.count}</span>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}
