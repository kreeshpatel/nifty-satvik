import { useMemo } from "react";
import { motion } from "framer-motion";

/**
 * CalendarHeatmap — fxreplay's signature visualization, adapted.
 *
 * 26 columns (weeks) × 5 rows (Mon-Fri). Each cell is a trading day,
 * colored by whether that day's signal was a win, soft win, loss, or
 * had no signal at all.
 *
 * Two-column section: left side has the headline + copy + legend, right
 * side has the heatmap card with win-rate / streak stats at the bottom.
 *
 * Data is generated deterministically so the layout doesn't shift
 * between renders. Real wiring would consume `results/signals_history.json`.
 */

const WEEKS = 26;
const DAYS = 5;

function generateGrid() {
  let s = 23;
  const r = () => {
    s = (s * 1103515245 + 12345) & 0x7fffffff;
    return s / 0x7fffffff;
  };
  const cells = [];
  for (let week = 0; week < WEEKS; week++) {
    for (let day = 0; day < DAYS; day++) {
      const x = r();
      let cls = "";
      if (x < 0.5) cls = "";
      else if (x < 0.72) cls = "win";
      else if (x < 0.86) cls = "win-soft";
      else if (x < 0.95) cls = "loss-soft";
      else cls = "loss";
      cells.push({ week, day, cls });
    }
  }
  return cells;
}

function computeStats(cells) {
  const winCells = cells.filter((c) => c.cls === "win" || c.cls === "win-soft");
  const lossCells = cells.filter((c) => c.cls === "loss" || c.cls === "loss-soft");
  const tradedDays = winCells.length + lossCells.length;
  const winRate = tradedDays > 0 ? (winCells.length / tradedDays) * 100 : 0;

  // Longest consecutive winning streak
  let streak = 0;
  let bestStreak = 0;
  // Walk by day order (oldest → newest) — original generation order
  cells.forEach((c) => {
    if (c.cls === "win" || c.cls === "win-soft") {
      streak += 1;
      bestStreak = Math.max(bestStreak, streak);
    } else if (c.cls === "loss" || c.cls === "loss-soft") {
      streak = 0;
    }
  });
  return {
    winRate: Math.round(winRate),
    bestStreak,
    tradedDays,
    totalCells: cells.length,
  };
}

export default function CalendarHeatmap() {
  const cells = useMemo(() => generateGrid(), []);
  const stats = useMemo(() => computeStats(cells), [cells]);

  const weekLabel = (w) => {
    if (w === 0) return "26w ago";
    if (w === WEEKS - 1) return "now";
    if (w % 4 === 0) return `-${WEEKS - w}w`;
    return "";
  };

  return (
    <section className="calhmap">
      <div className="calhmap-inner">
        <motion.div
          initial={{ opacity: 0, y: 22 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-15%" }}
          transition={{ duration: 0.7, ease: [0.22, 1, 0.36, 1] }}
          className="calhmap-copy"
        >
          <h2>
            Every signal day, <span>in the record.</span>
          </h2>
          <p>
            Six months of signal outcomes laid out as a calendar heatmap. Green
            is a win on close, red is a loss, faded greys are no-signal days.
            Hover any cell to see the signal that day.
          </p>
          <div className="calhmap-legend">
            <span className="calhmap-legend-item">
              <span
                className="calhmap-legend-swatch"
                style={{ background: "var(--bull)" }}
              />
              Win
            </span>
            <span className="calhmap-legend-item">
              <span
                className="calhmap-legend-swatch"
                style={{ background: "rgba(63, 221, 138, 0.6)" }}
              />
              Small win
            </span>
            <span className="calhmap-legend-item">
              <span
                className="calhmap-legend-swatch"
                style={{ background: "rgba(255, 92, 122, 0.6)" }}
              />
              Small loss
            </span>
            <span className="calhmap-legend-item">
              <span
                className="calhmap-legend-swatch"
                style={{ background: "var(--bear)" }}
              />
              Loss
            </span>
            <span className="calhmap-legend-item">
              <span
                className="calhmap-legend-swatch"
                style={{ background: "rgba(255, 255, 255, 0.06)" }}
              />
              No signal
            </span>
          </div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 26 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-15%" }}
          transition={{ duration: 0.8, delay: 0.15, ease: [0.22, 1, 0.36, 1] }}
          className="calhmap-card"
        >
          <div className="calhmap-card-head">
            <div className="calhmap-card-title">Signal outcomes</div>
            <div className="calhmap-card-meta">Last 26 weeks · Mon-Fri</div>
          </div>

          <div
            className="calhmap-grid"
            style={{
              gridTemplateColumns: "auto " + "1fr ".repeat(WEEKS).trim(),
            }}
          >
            {/* Day labels (Mon Tue Wed Thu Fri) on the left as a stacked y-axis */}
            {/* We instead emit a single row label per row, prefix style */}
            {Array.from({ length: DAYS }).map((_, day) => (
              <Row key={day} day={day} cells={cells.filter((c) => c.day === day)} />
            ))}
          </div>

          <div className="calhmap-card-foot">
            <div className="calhmap-stat">
              <span className="calhmap-stat-val">{stats.winRate}%</span>
              <span className="calhmap-stat-lbl">Hit rate</span>
            </div>
            <div className="calhmap-stat">
              <span className="calhmap-stat-val">{stats.tradedDays}</span>
              <span className="calhmap-stat-lbl">Signal days</span>
            </div>
            <div className="calhmap-stat">
              <span className="calhmap-stat-val">{stats.bestStreak}</span>
              <span className="calhmap-stat-lbl">Best streak</span>
            </div>
            <div className="calhmap-stat">
              <span className="calhmap-stat-val">
                {stats.totalCells - stats.tradedDays}
              </span>
              <span className="calhmap-stat-lbl">No-signal days</span>
            </div>
          </div>
        </motion.div>
      </div>
    </section>
  );
}

function Row({ day, cells }) {
  const dayName = ["Mon", "Tue", "Wed", "Thu", "Fri"][day];
  return (
    <>
      <span className="calhmap-week-label">{dayName}</span>
      {cells.map((c) => (
        <span
          key={`${c.week}-${c.day}`}
          className={`calhmap-cell ${c.cls}`}
          title={
            c.cls
              ? `${dayName}, week ${c.week + 1}: ${c.cls.replace("-", " ")}`
              : `${dayName}, week ${c.week + 1}: no signal`
          }
        />
      ))}
    </>
  );
}
