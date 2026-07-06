import { useState, useMemo } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Search,
  Bell,
  ChevronDown,
  ChevronRight,
  Rocket,
  ArrowUpRight,
  ArrowDownRight,
  TrendingUp,
  FileText,
  LayoutDashboard,
  Radio,
  Briefcase,
  BookOpen,
  Activity,
  Trophy,
  Settings,
  Sliders,
  Zap,
  Shield,
  Filter,
  Plus,
  Check,
  X,
  AlertTriangle,
  Clock,
  Link2,
  RefreshCw,
  User,
  Mail,
  Phone,
  Lock,
  ToggleLeft,
  ToggleRight,
  StickyNote,
  BarChart2,
  Calendar,
} from "lucide-react";
import "@/styles/preview-dashboard.css";

/**
 * PreviewDashboard — full SmartAlgo-style layout with left-rail nav +
 * sub-tab strip + meaningful quant-signal sections.
 *
 * Layout:
 *   ┌────────┬──────────────────────────────────────────────┐
 *   │ brand  │                  header                       │
 *   ├────────┼──────────────────────────────────────────────┤
 *   │  nav   │                sub-tab strip                  │
 *   │  rail  ├──────────────────────────────────────────────┤
 *   │        │              main content                     │
 *   │  with  │   (changes based on active sub-tab)           │
 *   │  sub-  │                                                │
 *   │  tabs  │                                                │
 *   └────────┴──────────────────────────────────────────────┘
 */

const NAV_TREE = [
  {
    id: "dashboard",
    label: "Dashboard",
    icon: LayoutDashboard,
    subtabs: [
      { id: "overview", label: "Overview" },
      { id: "today", label: "Today's signals" },
      { id: "performance", label: "Performance" },
      { id: "sectors", label: "Sectors" },
      { id: "risk", label: "Risk" },
    ],
  },
  {
    id: "signals",
    label: "Signals",
    icon: Radio,
    subtabs: [
      { id: "all", label: "All signals" },
      { id: "active", label: "Active" },
      { id: "watchlist", label: "Watchlist" },
      { id: "rejected", label: "Rejected" },
    ],
  },
  {
    id: "portfolio",
    label: "Portfolio",
    icon: Briefcase,
    subtabs: [
      { id: "positions", label: "Positions" },
      { id: "holdings", label: "Holdings" },
      { id: "orders", label: "Orders" },
    ],
  },
  {
    id: "backtest",
    label: "Backtest",
    icon: Activity,
    subtabs: [
      { id: "runs", label: "Runs" },
      { id: "compare", label: "Compare" },
      { id: "create", label: "Create new" },
    ],
  },
  {
    id: "journal",
    label: "Journal",
    icon: BookOpen,
    subtabs: [
      { id: "calendar", label: "Calendar" },
      { id: "trades", label: "Trades" },
      { id: "notes", label: "Notes" },
    ],
  },
  {
    id: "track-record",
    label: "Track record",
    icon: Trophy,
    subtabs: [
      { id: "summary", label: "Summary" },
      { id: "monthly", label: "Monthly" },
      { id: "yearly", label: "Yearly" },
    ],
  },
  {
    id: "settings",
    label: "Settings",
    icon: Settings,
    subtabs: [
      { id: "account", label: "Account" },
      { id: "kite", label: "Kite link" },
      { id: "alerts", label: "Alerts" },
    ],
  },
];

export default function PreviewDashboard() {
  const [activeNav, setActiveNav] = useState("dashboard");
  const [activeSub, setActiveSub] = useState("overview");

  const activeNavObj = NAV_TREE.find((n) => n.id === activeNav);

  return (
    <div className="pd2-root">
      <div className="pd2-wordmark" aria-hidden>Nifty Satvik</div>
      <div className="pd2-bloom" aria-hidden />

      <div className="pd2-shell">
        {/* Left rail */}
        <LeftRail
          activeNav={activeNav}
          activeSub={activeSub}
          onSelectNav={(id) => {
            setActiveNav(id);
            const nav = NAV_TREE.find((n) => n.id === id);
            setActiveSub(nav?.subtabs[0]?.id || "");
          }}
          onSelectSub={setActiveSub}
        />

        {/* Main column */}
        <div className="pd2-col">
          <Header />
          <SubTabStrip
            tabs={activeNavObj?.subtabs || []}
            active={activeSub}
            onSelect={setActiveSub}
            navLabel={activeNavObj?.label}
          />

          <AnimatePresence mode="wait">
            <motion.div
              key={`${activeNav}-${activeSub}`}
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -8 }}
              transition={{ duration: 0.35, ease: [0.22, 1, 0.36, 1] }}
            >
              {renderMain(activeNav, activeSub)}
            </motion.div>
          </AnimatePresence>
        </div>
      </div>
    </div>
  );
}

/* ---------------- Left rail ---------------- */

function LeftRail({ activeNav, activeSub, onSelectNav, onSelectSub }) {
  return (
    <aside className="pd2-rail">
      <div className="pd2-rail-brand">
        <div className="pd2-brand-mark">
          <TrendingUp size={18} strokeWidth={2.5} />
        </div>
        <span className="pd2-brand-name">Nifty Satvik</span>
      </div>

      <nav className="pd2-rail-nav">
        {NAV_TREE.map((item) => {
          const Icon = item.icon;
          const isActive = activeNav === item.id;
          return (
            <div key={item.id} className="pd2-rail-section">
              <button
                type="button"
                className={`pd2-rail-btn ${isActive ? "active" : ""}`}
                onClick={() => onSelectNav(item.id)}
              >
                <Icon size={16} />
                <span>{item.label}</span>
                {isActive ? (
                  <ChevronDown size={12} className="pd2-rail-chev" />
                ) : (
                  <ChevronRight size={12} className="pd2-rail-chev" />
                )}
              </button>
              {isActive && (
                <div className="pd2-rail-subs">
                  {item.subtabs.map((s) => (
                    <button
                      key={s.id}
                      type="button"
                      className={`pd2-rail-sub ${activeSub === s.id ? "active" : ""}`}
                      onClick={() => onSelectSub(s.id)}
                    >
                      {s.label}
                    </button>
                  ))}
                </div>
              )}
            </div>
          );
        })}
      </nav>

      <div className="pd2-rail-foot">
        <div className="pd2-rail-status">
          <span className="pd2-status-dot" />
          <span>Bull regime · Live</span>
        </div>
      </div>
    </aside>
  );
}

/* ---------------- Top header ---------------- */

function Header() {
  return (
    <header className="pd2-header">
      <div className="pd2-search">
        <Search size={16} />
        <input type="text" placeholder="Search stocks, signals, dates…" />
        <kbd>⌘K</kbd>
      </div>

      <div className="pd2-header-actions">
        <button type="button" className="pd2-icon-btn" aria-label="Reports">
          <FileText size={16} />
        </button>
        <button type="button" className="pd2-icon-btn" aria-label="Notifications">
          <Bell size={16} />
          <span className="pd2-icon-dot" />
        </button>
        <div className="pd2-user">
          <div className="pd2-user-meta">
            <div className="pd2-user-greeting">Hello <span aria-hidden>👋</span></div>
            <div className="pd2-user-name">Kreesh Vasistha</div>
          </div>
          <div className="pd2-user-avatar">K</div>
          <ChevronDown size={14} />
        </div>
      </div>
    </header>
  );
}

/* ---------------- Sub-tab strip ---------------- */

function SubTabStrip({ tabs, active, onSelect, navLabel }) {
  return (
    <div className="pd2-subtabs">
      <div className="pd2-subtabs-crumb">
        <span>{navLabel}</span>
        <ChevronRight size={12} />
      </div>
      <div className="pd2-subtabs-row">
        {tabs.map((t) => (
          <button
            key={t.id}
            type="button"
            className={`pd2-subtab ${active === t.id ? "active" : ""}`}
            onClick={() => onSelect(t.id)}
          >
            {t.label}
            {active === t.id && <span className="pd2-subtab-underline" />}
          </button>
        ))}
      </div>
    </div>
  );
}

/* ---------------- Main router ---------------- */

function renderMain(nav, sub) {
  const k = `${nav}/${sub}`;
  const map = {
    "dashboard/overview": <DashboardOverview />,
    "dashboard/today": <TodaySignals />,
    "dashboard/performance": <PerformanceView />,
    "dashboard/sectors": <SectorsView />,
    "dashboard/risk": <RiskView />,
    // Signals
    "signals/all": <SignalsAll />,
    "signals/active": <SignalsActive />,
    "signals/watchlist": <SignalsWatchlist />,
    "signals/rejected": <SignalsRejected />,
    // Portfolio
    "portfolio/positions": <PortfolioPositions />,
    "portfolio/holdings": <PortfolioHoldings />,
    "portfolio/orders": <PortfolioOrders />,
    // Backtest
    "backtest/runs": <BacktestRuns />,
    "backtest/compare": <BacktestCompare />,
    "backtest/create": <BacktestCreate />,
    // Journal
    "journal/calendar": <JournalCalendar />,
    "journal/trades": <JournalTrades />,
    "journal/notes": <JournalNotes />,
    // Track record
    "track-record/summary": <TrackSummary />,
    "track-record/monthly": <TrackMonthly />,
    "track-record/yearly": <TrackYearly />,
    // Settings
    "settings/account": <SettingsAccount />,
    "settings/kite": <SettingsKite />,
    "settings/alerts": <SettingsAlerts />,
  };
  return map[k] || <Placeholder nav={nav} sub={sub} />;
}

/* ---------------- Dashboard overview (main view) ---------------- */

function DashboardOverview() {
  return (
    <div className="pd2-main">
      <KPIRow />

      {/* Single 2-column grid so Today's signals can pull up beside the
          right column instead of waiting for the tallest right-column
          card to finish. No big empty gaps under the strategy row. */}
      <section className="pd2-dash-grid">
        <div className="pd2-dash-left">
          <TrendingStrategies />
          <StockTable />
        </div>
        <aside className="pd2-dash-right">
          <BacktestCard />
          <BrokeragesRow />
          <MarketActivity />
          <NextScanCard />
          <BalanceCard />
        </aside>
      </section>
    </div>
  );
}

/* ---------------- KPI row ---------------- */

const KPIS = [
  { label: "Active signals", value: "3", delta: "+1 today", up: true, icon: Radio },
  { label: "Hit rate · 30d", value: "68%", delta: "+4pp", up: true, icon: Trophy },
  { label: "Open P&L", value: "+₹ 18,420", delta: "+2.4%", up: true, icon: Briefcase },
  { label: "Sharpe · 90d", value: "1.84", delta: "-0.12", up: false, icon: Sliders },
];

function KPIRow() {
  return (
    <div className="pd2-kpis">
      {KPIS.map((k) => {
        const Icon = k.icon;
        return (
          <div key={k.label} className="pd2-kpi">
            <div className="pd2-kpi-head">
              <span className="pd2-kpi-label">{k.label}</span>
              <Icon size={14} className="pd2-kpi-icon" />
            </div>
            <div className="pd2-kpi-row">
              <div className="pd2-kpi-value">{k.value}</div>
              <div className={`pd2-kpi-delta ${k.up ? "up" : "down"}`}>
                {k.up ? <ArrowUpRight size={11} /> : <ArrowDownRight size={11} />}
                {k.delta}
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}

/* ---------------- Trending strategies (kept) ---------------- */

const TRENDING = [
  { ticker: "RELIANCE", name: "Reliance Industries", initial: "R", accent: "#1565C0", reward: "48.23%", delta: "-6.25", deltaPct: "2.25%", direction: "down", points: [40,38,42,41,39,36,34,32,30,28,26,24,22] },
  { ticker: "HDFCBANK", name: "HDFC Bank", initial: "H", accent: "#D32F2F", reward: "48.23%", delta: "+10.25", deltaPct: "2.25%", direction: "up", points: [20,24,22,28,32,30,36,40,42,46,50,54,58] },
  { ticker: "TCS", name: "Tata Consultancy", initial: "T", accent: "#1976D2", reward: "48.23%", delta: "+2.85", deltaPct: "2.25%", direction: "up", points: [30,28,32,36,38,42,40,44,42,46,50,48,52] },
];

function TrendingStrategies() {
  return (
    <div className="pd2-top-strategies">
      <div className="pd2-row-head">
        <h2 className="pd2-row-title">Top trending strategy</h2>
        <button type="button" className="pd2-week-pill">
          Week <ChevronDown size={14} />
        </button>
      </div>
      <div className="pd2-strategies">
        {TRENDING.map((s) => <StrategyCard key={s.ticker} strategy={s} />)}
      </div>
    </div>
  );
}

function StrategyCard({ strategy }) {
  const up = strategy.direction === "up";
  return (
    <article className="pd2-strategy">
      <div className="pd2-strategy-head">
        <div className="pd2-strategy-logo" style={{ background: strategy.accent }}>{strategy.initial}</div>
        <div className="pd2-strategy-meta">
          <div className="pd2-strategy-name">{strategy.name}</div>
          <div className="pd2-strategy-tag">Backtest tested</div>
        </div>
        <div className={`pd2-pill ${up ? "pd2-pill-up" : "pd2-pill-down"}`}>
          {up ? <ArrowUpRight size={12} /> : <ArrowDownRight size={12} />}
          <span>{strategy.deltaPct}</span>
        </div>
      </div>
      <div className="pd2-strategy-value-row">
        <div className="pd2-strategy-reward-value">{strategy.reward}</div>
        <div className={`pd2-strategy-delta ${up ? "up" : "down"}`}>{strategy.delta}</div>
      </div>
      <Sparkline points={strategy.points} up={up} />
    </article>
  );
}

function Sparkline({ points, up }) {
  const w = 240, h = 60;
  const min = Math.min(...points), max = Math.max(...points);
  const range = Math.max(1, max - min);
  const stepX = w / (points.length - 1);
  const path = points.map((p, i) => {
    const x = i * stepX;
    const y = h - ((p - min) / range) * h;
    return `${i === 0 ? "M" : "L"} ${x.toFixed(1)} ${y.toFixed(1)}`;
  }).join(" ");
  const lastY = h - ((points[points.length - 1] - min) / range) * h;
  const stroke = up ? "var(--bull, #3FDD8A)" : "var(--bear, #FF5C7A)";
  const fill = up ? "rgba(63,221,138,0.18)" : "rgba(255,92,122,0.18)";
  return (
    <div className="pd2-spark">
      <svg viewBox={`0 0 ${w} ${h}`} className="pd2-spark-svg" preserveAspectRatio="none">
        <path d={`${path} L ${w} ${h} L 0 ${h} Z`} fill={fill} />
        <path d={path} stroke={stroke} strokeWidth="2" fill="none" />
        <circle cx={w} cy={lastY} r="3.5" fill={stroke} />
      </svg>
    </div>
  );
}

/* ---------------- Backtest hero ---------------- */

function BacktestCard() {
  return (
    <article className="pd2-backtest">
      <div className="pd2-backtest-body">
        <h3 className="pd2-backtest-title">Backtest</h3>
        <p className="pd2-backtest-desc">
          Replay every signal against history. Walk-forward, transaction costs included.
        </p>
        <button type="button" className="pd2-backtest-cta">
          Create strategy
          <span className="pd2-backtest-cta-arrow">→</span>
        </button>
      </div>
      <div className="pd2-backtest-art" aria-hidden>
        <Rocket size={48} className="pd2-rocket" />
        <div className="pd2-bars">
          {[40, 55, 70, 85].map((h, i) => (
            <span key={i} className="pd2-bar" style={{ height: `${h}%`, animationDelay: `${i * 0.12}s` }} />
          ))}
        </div>
      </div>
    </article>
  );
}

/* ---------------- Brokerages ---------------- */

const BROKERAGES = [
  { name: "Zerodha", short: "Z", color: "#387ED1" },
  { name: "Groww", short: "G", color: "#00D09C" },
  { name: "Upstox", short: "U", color: "#622FB7" },
  { name: "AngelOne", short: "A", color: "#FF5A33" },
];

function BrokeragesRow() {
  return (
    <article className="pd2-brokerages">
      <div className="pd2-brokerages-title">
        Link your brokerage account to execute signals in real-time.
      </div>
      <div className="pd2-brokerages-row">
        {BROKERAGES.map((b) => (
          <div key={b.name} className="pd2-broker">
            <div className="pd2-broker-logo" style={{ background: b.color }}>{b.short}</div>
            <div className="pd2-broker-name">{b.name}</div>
          </div>
        ))}
        <div className="pd2-broker pd2-broker-more">
          <div className="pd2-broker-logo pd2-broker-logo-more">+23</div>
          <div className="pd2-broker-name">more</div>
        </div>
      </div>
    </article>
  );
}

/* ---------------- Stock table — now Today's Signals ---------------- */

const SIGNAL_ROWS = [
  { ticker: "RELIANCE",  name: "Reliance Industries", confidence: 0.94, entry: "₹ 2,872", target: "+6.3%", stop: "-2.8%", sector: "Energy",     series: [1, -1, 1, 1, 1] },
  { ticker: "HDFCBANK",  name: "HDFC Bank",           confidence: 0.93, entry: "₹ 1,675", target: "+5.8%", stop: "-2.4%", sector: "Banking",    series: [1, 1, 1, -1, 1] },
  { ticker: "TCS",       name: "Tata Consultancy",    confidence: 0.92, entry: "₹ 4,055", target: "+4.9%", stop: "-2.1%", sector: "IT",         series: [1, 1, -1, 1, 1] },
];

function StockTable() {
  return (
    <article className="pd2-table">
      <div className="pd2-table-titlebar">
        <h3 className="pd2-table-title">Today's signals</h3>
        <span className="pd2-table-subtitle">3 stocks cleared the 0.92 confidence floor</span>
      </div>
      <div className="pd2-table-head">
        <div className="pd2-th col-name">Ticker</div>
        <div className="pd2-th col-num">Confidence</div>
        <div className="pd2-th col-num">Entry</div>
        <div className="pd2-th col-num">Target</div>
        <div className="pd2-th col-num">Stop</div>
        <div className="pd2-th col-num">Sector</div>
        <div className="pd2-th col-series">5d perf</div>
      </div>
      <div className="pd2-table-body">
        {SIGNAL_ROWS.map((row, idx) => (
          <div key={idx} className="pd2-tr">
            <div className="pd2-td col-name">
              <div className="pd2-tr-ticker">{row.ticker}</div>
              <div className="pd2-tr-name">{row.name}</div>
            </div>
            <div className="pd2-td col-num">
              <span className="pd2-conf-pill">{row.confidence}</span>
            </div>
            <div className="pd2-td col-num">{row.entry}</div>
            <div className="pd2-td col-num pos">{row.target}</div>
            <div className="pd2-td col-num neg">{row.stop}</div>
            <div className="pd2-td col-num">{row.sector}</div>
            <div className="pd2-td col-series">
              <div className="pd2-series">
                {row.series.map((v, i) => (
                  <span key={i} className={`pd2-series-cell ${v > 0 ? "up" : "down"}`} />
                ))}
              </div>
            </div>
          </div>
        ))}
      </div>
    </article>
  );
}

/* ---------------- Market activity ---------------- */

const MARKET_BUBBLES = [
  { label: "Banking",     pct: "73%", color: "#4F8CFF", size: 150, x: "6%",  y: "2%" },
  { label: "IT & Tech",   pct: "65%", color: "#7B5BFF", size: 130, x: "58%", y: "16%" },
  { label: "Energy",      pct: "51%", color: "#0F1538", border: "#2A3060", size: 100, x: "30%", y: "54%" },
];

function MarketActivity() {
  return (
    <article className="pd2-card pd2-market">
      <h3 className="pd2-card-title">Today's market activity</h3>
      <div className="pd2-bubbles">
        {MARKET_BUBBLES.map((b) => (
          <div
            key={b.label}
            className="pd2-bubble"
            style={{
              width: b.size,
              height: b.size,
              left: b.x,
              top: b.y,
              background: b.color,
              border: b.border ? `1px solid ${b.border}` : "none",
              color: b.label === "Energy" ? "var(--text-1)" : "#0a0d22",
            }}
          >
            <div className="pd2-bubble-pct">{b.pct}</div>
            <div className="pd2-bubble-label">{b.label}</div>
          </div>
        ))}
      </div>
    </article>
  );
}

function NextScanCard() {
  return (
    <article className="pd2-card pd2-next">
      <h3 className="pd2-card-title">Next scan</h3>
      <div className="pd2-next-value">3h 22m</div>
      <div className="pd2-next-meta">Tomorrow · 4:15 PM IST</div>
      <div className="pd2-next-progress">
        <span style={{ width: "62%" }} />
      </div>
    </article>
  );
}

function BalanceCard() {
  return (
    <article className="pd2-card pd2-balance">
      <h3 className="pd2-card-title">Available balance</h3>
      <div className="pd2-balance-rows">
        <div className="pd2-balance-row"><span>Backtests</span><strong>24</strong></div>
        <div className="pd2-balance-row"><span>Credits</span><strong>15</strong></div>
        <div className="pd2-balance-row"><span>Plan</span><strong>Operator (₹2,499/mo)</strong></div>
      </div>
    </article>
  );
}

/* ---------------- Today's Signals view (dedicated sub-tab) ---------------- */

function TodaySignals() {
  return (
    <div className="pd2-main">
      <KPIRow />
      <section className="pd2-bottom-grid">
        <StockTable />
        <aside className="pd2-side">
          <NextScanCard />
          <BalanceCard />
        </aside>
      </section>
    </div>
  );
}

/* ---------------- Performance view ---------------- */

function PerformanceView() {
  return (
    <div className="pd2-main">
      <div className="pd2-grid-two">
        <article className="pd2-card pd2-card-big">
          <div className="pd2-card-head">
            <div>
              <div className="pd2-tag">Equity curve · 1Y</div>
              <h3 className="pd2-card-title-row">+38.4%</h3>
            </div>
            <div className="pd2-card-meta">
              <span>Sharpe <strong>1.84</strong></span>
              <span>Max DD <strong className="neg">-9.2%</strong></span>
              <span>Hit rate <strong className="pos">68%</strong></span>
            </div>
          </div>
          <EquityCurveSVG />
        </article>

        <article className="pd2-card">
          <h3 className="pd2-card-title">Hit rate · 26 weeks</h3>
          <MiniHeatmap />
        </article>
      </div>

      <div className="pd2-grid-three">
        <MetricTile label="Trades / month" value="6.2" caption="below industry avg of 14" />
        <MetricTile label="Avg holding" value="7.3d" caption="swing horizon" />
        <MetricTile label="Win/loss ratio" value="2.1x" caption="₹ per win vs ₹ per loss" />
      </div>
    </div>
  );
}

function MetricTile({ label, value, caption }) {
  return (
    <article className="pd2-metric">
      <div className="pd2-metric-label">{label}</div>
      <div className="pd2-metric-value">{value}</div>
      <div className="pd2-metric-caption">{caption}</div>
    </article>
  );
}

function EquityCurveSVG() {
  // Deterministic monotonic-ish growing curve
  const pts = useMemo(() => {
    const out = [];
    let p = 100;
    let s = 31;
    const r = () => { s = (s * 1103515245 + 12345) & 0x7fffffff; return s / 0x7fffffff; };
    for (let i = 0; i < 80; i++) {
      const drift = 0.45 + r() * 0.7;
      const noise = (r() - 0.4) * 3.5;
      p += drift + noise;
      out.push(p);
    }
    return out;
  }, []);
  const w = 800, h = 220;
  const min = Math.min(...pts), max = Math.max(...pts);
  const range = max - min;
  const step = w / (pts.length - 1);
  const path = pts.map((p, i) => {
    const x = i * step;
    const y = h - ((p - min) / range) * (h - 12) - 6;
    return `${i === 0 ? "M" : "L"} ${x.toFixed(1)} ${y.toFixed(1)}`;
  }).join(" ");
  return (
    <svg viewBox={`0 0 ${w} ${h}`} className="pd2-equity" preserveAspectRatio="none">
      <defs>
        <linearGradient id="pd2-equity-grad" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="var(--brand, #4F8CFF)" stopOpacity="0.35" />
          <stop offset="100%" stopColor="var(--brand, #4F8CFF)" stopOpacity="0" />
        </linearGradient>
      </defs>
      {[0.2, 0.4, 0.6, 0.8].map((g) => (
        <line key={g} x1="0" x2={w} y1={h * g} y2={h * g} stroke="rgba(255,255,255,0.04)" />
      ))}
      <path d={`${path} L ${w} ${h} L 0 ${h} Z`} fill="url(#pd2-equity-grad)" />
      <path d={path} stroke="var(--brand)" strokeWidth="2" fill="none" />
    </svg>
  );
}

function MiniHeatmap() {
  const cells = useMemo(() => {
    let s = 73;
    const r = () => { s = (s * 1103515245 + 12345) & 0x7fffffff; return s / 0x7fffffff; };
    return Array.from({ length: 26 * 5 }, () => {
      const x = r();
      if (x < 0.55) return "";
      if (x < 0.78) return "win";
      if (x < 0.89) return "win-soft";
      if (x < 0.96) return "loss-soft";
      return "loss";
    });
  }, []);
  return (
    <div className="pd2-heatmap">
      <div className="pd2-heatmap-grid">
        {cells.map((c, i) => (<span key={i} className={`pd2-heatmap-cell ${c}`} />))}
      </div>
    </div>
  );
}

/* ---------------- Sectors view ---------------- */

const SECTOR_EXPOSURE = [
  { name: "Banking", pct: 28, signals: 4, color: "#4F8CFF" },
  { name: "IT & Tech", pct: 22, signals: 3, color: "#7B5BFF" },
  { name: "Energy",  pct: 18, signals: 2, color: "#3FDD8A" },
  { name: "Pharma",  pct: 12, signals: 1, color: "#F472B6" },
  { name: "Auto",    pct: 10, signals: 1, color: "#FFB454" },
  { name: "Other",   pct: 10, signals: 1, color: "#6B7280" },
];

function SectorsView() {
  return (
    <div className="pd2-main">
      <article className="pd2-card pd2-card-big">
        <h3 className="pd2-card-title">Sector exposure</h3>
        <p className="pd2-card-sub">
          Hard cap: 30% per sector. Banking, IT, Energy are leaning hot today.
        </p>
        <div className="pd2-sector-bars">
          {SECTOR_EXPOSURE.map((s) => (
            <div key={s.name} className="pd2-sector-row">
              <div className="pd2-sector-label">{s.name}</div>
              <div className="pd2-sector-track">
                <div
                  className="pd2-sector-fill"
                  style={{ width: `${(s.pct / 30) * 100}%`, background: s.color }}
                />
              </div>
              <div className="pd2-sector-meta">
                <span>{s.pct}%</span>
                <span className="pd2-sector-signals">{s.signals} sig</span>
              </div>
            </div>
          ))}
        </div>
      </article>
    </div>
  );
}

/* Drawdown over time — SVG red filled area below 0% baseline */
function DrawdownChart() {
  const w = 800, h = 130;
  // Fixed drawdown series: starts at 0, dips to various troughs, recovers
  const pts = [
    0, -0.4, -1.2, -0.8, -2.1, -3.4, -2.9, -1.8, -0.6, 0,
    -0.3, -1.5, -3.8, -5.1, -4.2, -2.7, -1.1, 0, -0.2, -0.8,
    -2.3, -4.6, -7.9, -9.2, -8.1, -6.3, -3.7, -1.4, 0, -0.5,
    -1.9, -3.2, -5.8, -7.4, -6.1, -4.0, -2.1, -0.7, 0, -0.3,
    -0.9, -2.4, -4.8, -6.6, -5.2, -3.1, -1.2, 0,
  ];
  const minV = Math.min(...pts); // most negative, e.g. -9.2
  // Y: 0% maps to y=8 (top), minV maps to y=h-8 (bottom)
  const topPad = 8, botPad = 8;
  const chartH = h - topPad - botPad;
  const step = w / (pts.length - 1);
  const toY = (v) => topPad + ((0 - v) / (0 - minV)) * chartH;
  const zeroY = toY(0);

  const pathD = pts.map((p, i) => {
    const x = (i * step).toFixed(1);
    const y = toY(p).toFixed(1);
    return `${i === 0 ? "M" : "L"} ${x} ${y}`;
  }).join(" ");

  // Y-axis labels: 0, -5%, -10% (approx)
  const yLabels = [
    { pct: 0,   label: "0%" },
    { pct: -5,  label: "−5%" },
    { pct: -10, label: "−10%" },
  ].filter((l) => l.pct >= minV - 1);

  return (
    <article className="pd2-card">
      <div className="pd2-dd-head">
        <h3 className="pd2-card-title" style={{ margin: 0 }}>Drawdown over time</h3>
        <span className="pd2-dd-peak-label">Peak: −9.2%</span>
      </div>
      <div className="pd2-dd-chart-wrap">
        {/* Y-axis labels */}
        <div className="pd2-dd-yaxis">
          {yLabels.map((l) => (
            <span
              key={l.pct}
              className="pd2-dd-ylabel"
              style={{ top: `${toY(l.pct)}px` }}
            >
              {l.label}
            </span>
          ))}
        </div>
        <svg viewBox={`0 0 ${w} ${h}`} className="pd2-dd-svg" preserveAspectRatio="none">
          {/* Zero baseline */}
          <line x1="0" x2={w} y1={zeroY} y2={zeroY} stroke="rgba(255,255,255,0.12)" strokeWidth="1" />
          {/* Filled area below zero */}
          <path
            d={`${pathD} L ${(pts.length - 1) * step} ${zeroY} L 0 ${zeroY} Z`}
            fill="rgba(255,92,122,0.18)"
          />
          {/* Drawdown line */}
          <path d={pathD} stroke="var(--bear, #FF5C7A)" strokeWidth="1.5" fill="none" />
          {/* Mark peak drawdown */}
          <circle cx={((pts.indexOf(minV)) * step).toFixed(1)} cy={toY(minV).toFixed(1)} r="3.5" fill="var(--bear, #FF5C7A)" />
          <line x1={((pts.indexOf(minV)) * step).toFixed(1)} x2={((pts.indexOf(minV)) * step).toFixed(1)} y1={zeroY} y2={toY(minV).toFixed(1)} stroke="rgba(255,92,122,0.3)" strokeWidth="1" strokeDasharray="3 2" />
        </svg>
      </div>
    </article>
  );
}

/* ---------------- Risk view ---------------- */

function RiskView() {
  return (
    <div className="pd2-main">
      <div className="pd2-grid-four">
        <MetricTile label="Portfolio risk" value="2.4%" caption="of capital at risk" />
        <MetricTile label="Largest position" value="8.2%" caption="HDFCBANK" />
        <MetricTile label="Open positions" value="3" caption="of 5 max" />
        <MetricTile label="Cash" value="62%" caption="dry powder" />
      </div>

      <DrawdownChart />

      <article className="pd2-card">
        <h3 className="pd2-card-title">Active risk controls</h3>
        <div className="pd2-risk-rows">
          <RiskRow icon={Shield} label="Max position size" value="20% of portfolio" status="ok" />
          <RiskRow icon={Shield} label="Sector exposure cap" value="30% per sector" status="ok" />
          <RiskRow icon={Shield} label="Per-trade risk" value="1% of capital" status="ok" />
          <RiskRow icon={Zap} label="Circuit breaker" value="Trips at 5% portfolio DD in a day" status="ok" />
          <RiskRow icon={Shield} label="Banking exposure" value="28% of 30% used" status="warn" />
        </div>
      </article>
    </div>
  );
}

function RiskRow({ icon: Icon, label, value, status }) {
  return (
    <div className={`pd2-risk-row ${status}`}>
      <Icon size={14} />
      <span className="pd2-risk-label">{label}</span>
      <span className="pd2-risk-value">{value}</span>
      <span className={`pd2-risk-status ${status}`}>
        {status === "ok" ? "OK" : status === "warn" ? "Watch" : "Block"}
      </span>
    </div>
  );
}

/* ---------------- Placeholder for non-implemented tabs ---------------- */

function Placeholder({ nav, sub }) {
  return (
    <div className="pd2-main">
      <article className="pd2-card pd2-placeholder">
        <h3 className="pd2-card-title">
          {nav} · {sub}
        </h3>
        <p className="pd2-card-sub">
          This sub-tab is part of the prototype navigation but isn't wired in this preview.
          The Dashboard tab is the full mockup &mdash; try the sub-tabs across the top.
        </p>
      </article>
    </div>
  );
}

/* ================================================================
   SIGNALS — All
   ================================================================ */

const ALL_SIGNALS_DATA = [
  { date: "2025-11-28", ticker: "RELIANCE",     name: "Reliance Industries", conf: 0.96, entry: "₹2,872", target: "₹3,053", stop: "₹2,791", outcome: "Win",    pnl: "+₹18,120" },
  { date: "2025-11-21", ticker: "HDFCBANK",     name: "HDFC Bank",           conf: 0.95, entry: "₹1,675", target: "₹1,772", stop: "₹1,635", outcome: "Win",    pnl: "+₹9,700" },
  { date: "2025-11-14", ticker: "TCS",          name: "Tata Consultancy",    conf: 0.94, entry: "₹4,055", target: "₹4,254", stop: "₹3,942", outcome: "Win",    pnl: "+₹14,950" },
  { date: "2025-11-07", ticker: "INFY",         name: "Infosys",             conf: 0.93, entry: "₹1,842", target: "₹1,951", stop: "₹1,793", outcome: "Loss",   pnl: "−₹4,900" },
  { date: "2025-10-31", ticker: "BHARTIARTL",   name: "Bharti Airtel",       conf: 0.92, entry: "₹1,562", target: "₹1,655", stop: "₹1,521", outcome: "Win",    pnl: "+₹9,300" },
  { date: "2025-10-24", ticker: "LT",           name: "Larsen & Toubro",     conf: 0.94, entry: "₹3,412", target: "₹3,600", stop: "₹3,320", outcome: "Win",    pnl: "+₹11,280" },
  { date: "2025-10-17", ticker: "KOTAKBANK",    name: "Kotak Mahindra",      conf: 0.93, entry: "₹1,924", target: "₹2,036", stop: "₹1,872", outcome: "Loss",   pnl: "−₹5,200" },
  { date: "2025-10-10", ticker: "ITC",          name: "ITC Limited",         conf: 0.92, entry: "₹487",   target: "₹516",   stop: "₹473",   outcome: "Win",    pnl: "+₹4,350" },
  { date: "2025-10-03", ticker: "HINDUNILVR",   name: "Hindustan Unilever",  conf: 0.95, entry: "₹2,642", target: "₹2,795", stop: "₹2,568", outcome: "Win",    pnl: "+₹15,300" },
  { date: "2025-09-26", ticker: "ASIANPAINT",   name: "Asian Paints",        conf: 0.93, entry: "₹2,893", target: "₹3,057", stop: "₹2,812", outcome: "Loss",   pnl: "−₹8,100" },
  { date: "2025-09-19", ticker: "MARUTI",       name: "Maruti Suzuki",       conf: 0.94, entry: "₹12,450", target: "₹13,199", stop: "₹12,102", outcome: "Win", pnl: "+₹22,470" },
  { date: "2025-09-12", ticker: "SBIN",         name: "State Bank of India", conf: 0.92, entry: "₹823",  target: "₹872",   stop: "₹801",   outcome: "Active", pnl: "+₹3,920" },
  { date: "2025-09-05", ticker: "AXISBANK",     name: "Axis Bank",           conf: 0.93, entry: "₹1,198", target: "₹1,268", stop: "₹1,164", outcome: "Active", pnl: "+₹5,600" },
  { date: "2025-08-29", ticker: "BAJFINANCE",   name: "Bajaj Finance",       conf: 0.96, entry: "₹7,814", target: "₹8,283", stop: "₹7,604", outcome: "Win",    pnl: "+₹18,800" },
  { date: "2025-08-22", ticker: "ICICIBANK",    name: "ICICI Bank",          conf: 0.94, entry: "₹1,324", target: "₹1,404", stop: "₹1,285", outcome: "Active", pnl: "+₹6,400" },
];

function OutcomeChip({ outcome }) {
  const cfg = {
    Win:    { cls: "pd2-outcome-win",    label: "Win" },
    Loss:   { cls: "pd2-outcome-loss",   label: "Loss" },
    Active: { cls: "pd2-outcome-active", label: "Active" },
  };
  const { cls, label } = cfg[outcome] || cfg.Active;
  return <span className={`pd2-outcome-chip ${cls}`}>{label}</span>;
}

function SignalsAll() {
  const [filter, setFilter] = useState("All");
  const [query, setQuery] = useState("");

  const filters = ["All", "Wins", "Losses", "Active"];
  const filtered = ALL_SIGNALS_DATA.filter((r) => {
    const matchFilter =
      filter === "All" ||
      (filter === "Wins"   && r.outcome === "Win")   ||
      (filter === "Losses" && r.outcome === "Loss")  ||
      (filter === "Active" && r.outcome === "Active");
    const matchQuery = query === "" || r.ticker.includes(query.toUpperCase()) || r.name.toLowerCase().includes(query.toLowerCase());
    return matchFilter && matchQuery;
  });

  return (
    <div className="pd2-main">
      <div className="pd2-toolbar">
        <div className="pd2-filter-chips">
          {filters.map((f) => (
            <button
              key={f}
              type="button"
              className={`pd2-filter-chip ${filter === f ? "active" : ""}`}
              onClick={() => setFilter(f)}
            >
              {f}
            </button>
          ))}
        </div>
        <div className="pd2-search-bar">
          <Search size={14} />
          <input
            type="text"
            placeholder="Search ticker…"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
        </div>
      </div>

      <article className="pd2-card">
        <div className="pd2-full-table">
          <div className="pd2-full-thead">
            <div className="pd2-th">Date</div>
            <div className="pd2-th">Ticker</div>
            <div className="pd2-th col-num">Confidence</div>
            <div className="pd2-th col-num">Entry</div>
            <div className="pd2-th col-num">Target</div>
            <div className="pd2-th col-num">Stop</div>
            <div className="pd2-th">Outcome</div>
            <div className="pd2-th col-num">P&amp;L</div>
          </div>
          {filtered.map((r, i) => (
            <div key={i} className="pd2-full-tr">
              <div className="pd2-td pd2-date-col">{r.date}</div>
              <div className="pd2-td">
                <div className="pd2-tr-ticker">{r.ticker}</div>
                <div className="pd2-tr-name">{r.name}</div>
              </div>
              <div className="pd2-td col-num">
                <span className="pd2-conf-pill">{r.conf}</span>
              </div>
              <div className="pd2-td col-num">{r.entry}</div>
              <div className="pd2-td col-num pos">{r.target}</div>
              <div className="pd2-td col-num neg">{r.stop}</div>
              <div className="pd2-td"><OutcomeChip outcome={r.outcome} /></div>
              <div className={`pd2-td col-num ${r.pnl.startsWith("+") ? "pos" : r.pnl.startsWith("−") ? "neg" : ""}`}>{r.pnl}</div>
            </div>
          ))}
        </div>
      </article>
    </div>
  );
}

/* ================================================================
   SIGNALS — Active
   ================================================================ */

const ACTIVE_SIGNALS = [
  {
    ticker: "SBIN", name: "State Bank of India", sector: "Banking",
    entry: 823, live: 837, target: 872, stop: 801, conf: 0.92, days: 16,
  },
  {
    ticker: "AXISBANK", name: "Axis Bank", sector: "Banking",
    entry: 1198, live: 1224, target: 1268, stop: 1164, conf: 0.93, days: 23,
  },
  {
    ticker: "ICICIBANK", name: "ICICI Bank", sector: "Banking",
    entry: 1324, live: 1341, target: 1404, stop: 1285, conf: 0.94, days: 9,
  },
];

function ActiveProgressBar({ entry, live, target, stop }) {
  const totalRange = target - stop;
  const currentProgress = Math.max(0, Math.min(1, (live - stop) / totalRange));
  const entryPct = ((entry - stop) / totalRange) * 100;
  const pct = currentProgress * 100;
  const isGain = live >= entry;
  return (
    <div className="pd2-progress-wrap">
      <div className="pd2-progress-track">
        <div
          className={`pd2-progress-fill ${isGain ? "gain" : "loss"}`}
          style={{ width: `${pct}%` }}
        />
        <div className="pd2-progress-entry-mark" style={{ left: `${entryPct}%` }} />
      </div>
      <div className="pd2-progress-labels">
        <span className="neg">Stop ₹{stop.toLocaleString("en-IN")}</span>
        <span className="pos">Target ₹{target.toLocaleString("en-IN")}</span>
      </div>
    </div>
  );
}

function SignalsActive() {
  // Aggregate summary
  const totals = ACTIVE_SIGNALS.reduce(
    (a, s) => {
      const pl = (s.live - s.entry) / s.entry;
      a.gain += pl;
      if (pl >= 0) a.wins += 1;
      return a;
    },
    { gain: 0, wins: 0 }
  );
  const avgGain = ((totals.gain / ACTIVE_SIGNALS.length) * 100).toFixed(2);

  return (
    <div className="pd2-main">
      {/* Header strip */}
      <div className="pd2-active-summary">
        <div className="pd2-active-sum-item">
          <div className="pd2-metric-label">Open positions</div>
          <div className="pd2-active-sum-val">{ACTIVE_SIGNALS.length}</div>
        </div>
        <div className="pd2-active-sum-item">
          <div className="pd2-metric-label">Avg open gain</div>
          <div className={`pd2-active-sum-val ${parseFloat(avgGain) >= 0 ? "pos" : "neg"}`}>
            {parseFloat(avgGain) >= 0 ? "+" : ""}{avgGain}%
          </div>
        </div>
        <div className="pd2-active-sum-item">
          <div className="pd2-metric-label">Winning</div>
          <div className="pd2-active-sum-val">{totals.wins} / {ACTIVE_SIGNALS.length}</div>
        </div>
        <div className="pd2-active-sum-item">
          <div className="pd2-metric-label">Sector limit</div>
          <div className="pd2-active-sum-val">3 / 30%</div>
        </div>
      </div>

      {/* Row cards */}
      <div className="pd2-active-rows">
        {ACTIVE_SIGNALS.map((s) => {
          const gainPct = ((s.live - s.entry) / s.entry) * 100;
          const isGain = gainPct >= 0;
          const distToTarget = ((s.target - s.live) / s.live) * 100;
          const distToStop = ((s.live - s.stop) / s.live) * 100;
          return (
            <article key={s.ticker} className="pd2-active-row">
              {/* Identity */}
              <div className="pd2-active-id">
                <div className="pd2-active-id-top">
                  <span className="pd2-active-ticker">{s.ticker}</span>
                  <span className="pd2-active-side">Long</span>
                </div>
                <div className="pd2-active-id-meta">{s.name} · {s.sector}</div>
                <div className="pd2-active-id-foot">
                  <span className="pd2-conf-pill">{s.conf}</span>
                  <span className="pd2-active-days-chip">{s.days}d held</span>
                </div>
              </div>

              {/* Price block */}
              <div className="pd2-active-price-block">
                <div className="pd2-active-stat">
                  <div className="pd2-metric-label">Entry</div>
                  <div className="pd2-active-stat-val">
                    ₹{s.entry.toLocaleString("en-IN")}
                  </div>
                </div>
                <div className="pd2-active-stat">
                  <div className="pd2-metric-label">Live</div>
                  <div className="pd2-active-stat-val">
                    ₹{s.live.toLocaleString("en-IN")}
                  </div>
                </div>
                <div className="pd2-active-stat">
                  <div className="pd2-metric-label">P&amp;L</div>
                  <div className={`pd2-active-stat-val ${isGain ? "pos" : "neg"}`}>
                    {isGain ? "+" : ""}{gainPct.toFixed(2)}%
                  </div>
                </div>
              </div>

              {/* Progress + distance */}
              <div className="pd2-active-progress-block">
                <ActiveProgressBar
                  entry={s.entry}
                  live={s.live}
                  target={s.target}
                  stop={s.stop}
                />
                <div className="pd2-active-distance">
                  <span className="neg">
                    <span className="pd2-active-distance-label">Stop</span>{" "}
                    {distToStop.toFixed(1)}%
                  </span>
                  <span className="pos">
                    <span className="pd2-active-distance-label">Target</span>{" "}
                    {distToTarget.toFixed(1)}%
                  </span>
                </div>
              </div>

              {/* Actions */}
              <div className="pd2-active-actions">
                <button type="button" className="pd2-btn-ghost">Modify SL</button>
                <button type="button" className="pd2-btn-primary">Close</button>
              </div>
            </article>
          );
        })}
      </div>
    </div>
  );
}

/* ================================================================
   SIGNALS — Watchlist
   ================================================================ */

const WATCHLIST_DATA = [
  { ticker: "HINDUNILVR", name: "Hindustan Unilever", conf: 0.91, sector: "FMCG",         reason: "Macro headwind" },
  { ticker: "ASIANPAINT", name: "Asian Paints",       conf: 0.90, sector: "FMCG",         reason: "Volume thin" },
  { ticker: "BAJFINANCE", name: "Bajaj Finance",      conf: 0.91, sector: "Financial Svcs", reason: "Sector cap hit" },
  { ticker: "MARUTI",     name: "Maruti Suzuki",      conf: 0.89, sector: "Auto",          reason: "Needs sector confluence" },
  { ticker: "LT",         name: "Larsen & Toubro",    conf: 0.90, sector: "Capital Goods", reason: "Earnings near" },
  { ticker: "WIPRO",      name: "Wipro",              conf: 0.88, sector: "IT",            reason: "Macro headwind" },
  { ticker: "SUNPHARMA",  name: "Sun Pharma",         conf: 0.89, sector: "Pharma",        reason: "Volume thin" },
  { ticker: "TITAN",      name: "Titan Company",      conf: 0.91, sector: "Consumer",      reason: "Needs sector confluence" },
];

const REASON_COLORS = {
  "Macro headwind":           "pd2-reason-macro",
  "Volume thin":              "pd2-reason-volume",
  "Sector cap hit":           "pd2-reason-sector",
  "Needs sector confluence":  "pd2-reason-confluence",
  "Earnings near":            "pd2-reason-earnings",
};

function SignalsWatchlist() {
  return (
    <div className="pd2-main">
      <article className="pd2-card">
        <div className="pd2-table-titlebar">
          <h3 className="pd2-card-title">Watchlist — near-floor signals</h3>
          <span className="pd2-table-subtitle">Confidence 0.88–0.92 · didn't clear live gate</span>
        </div>
        <div className="pd2-wl-thead">
          <div className="pd2-th">Ticker</div>
          <div className="pd2-th col-num">Confidence</div>
          <div className="pd2-th">Sector</div>
          <div className="pd2-th">Why not</div>
        </div>
        {WATCHLIST_DATA.map((r, i) => (
          <div key={i} className="pd2-wl-tr">
            <div className="pd2-td">
              <div className="pd2-tr-ticker">{r.ticker}</div>
              <div className="pd2-tr-name">{r.name}</div>
            </div>
            <div className="pd2-td col-num">
              <span className="pd2-conf-pill pd2-conf-warn">{r.conf}</span>
            </div>
            <div className="pd2-td pd2-sector-badge">{r.sector}</div>
            <div className="pd2-td">
              <span className={`pd2-reason-chip ${REASON_COLORS[r.reason] || ""}`}>{r.reason}</span>
            </div>
          </div>
        ))}
      </article>
    </div>
  );
}

/* ================================================================
   SIGNALS — Rejected
   ================================================================ */

const REJECTED_DATA = [
  { ticker: "ONGC",      name: "ONGC",            conf: 0.71, sector: "Energy",    reason: "Low conf" },
  { ticker: "POWERGRID", name: "Power Grid Corp",  conf: 0.68, sector: "Utilities", reason: "Regime block" },
  { ticker: "NTPC",      name: "NTPC",             conf: 0.64, sector: "Utilities", reason: "Regime block" },
  { ticker: "HCLTECH",   name: "HCL Technologies", conf: 0.74, sector: "IT",        reason: "Low conf" },
  { ticker: "TECHM",     name: "Tech Mahindra",    conf: 0.69, sector: "IT",        reason: "Low conf" },
  { ticker: "TATAMOTORS",name: "Tata Motors",      conf: 0.72, sector: "Auto",      reason: "Earnings near" },
  { ticker: "M&M",       name: "Mahindra & Mahindra", conf: 0.65, sector: "Auto",  reason: "Low conf" },
  { ticker: "JSWSTEEL",  name: "JSW Steel",        conf: 0.67, sector: "Metals",   reason: "Sector cap hit" },
  { ticker: "TATASTEEL", name: "Tata Steel",       conf: 0.62, sector: "Metals",   reason: "Sector cap hit" },
  { ticker: "COALINDIA", name: "Coal India",        conf: 0.58, sector: "Energy",  reason: "Low conf" },
];

const REJECT_REASON_COLORS = {
  "Low conf":      "pd2-rej-low",
  "Sector cap hit":"pd2-rej-sector",
  "Regime block":  "pd2-rej-regime",
  "Earnings near": "pd2-rej-earnings",
};

function SignalsRejected() {
  return (
    <div className="pd2-main">
      <article className="pd2-card">
        <div className="pd2-table-titlebar">
          <h3 className="pd2-card-title">Rejected today</h3>
          <span className="pd2-table-subtitle">Scanned {REJECTED_DATA.length} · failed gate</span>
        </div>
        <div className="pd2-rej-thead">
          <div className="pd2-th">Ticker</div>
          <div className="pd2-th col-num">Confidence</div>
          <div className="pd2-th">Sector</div>
          <div className="pd2-th">Reason</div>
        </div>
        {REJECTED_DATA.map((r, i) => (
          <div key={i} className="pd2-rej-tr">
            <div className="pd2-td">
              <div className="pd2-tr-ticker pd2-tr-dimmed">{r.ticker}</div>
              <div className="pd2-tr-name">{r.name}</div>
            </div>
            <div className="pd2-td col-num">
              <span className="pd2-conf-pill pd2-conf-low">{r.conf}</span>
            </div>
            <div className="pd2-td pd2-sector-badge pd2-sector-dim">{r.sector}</div>
            <div className="pd2-td">
              <span className={`pd2-reason-chip ${REJECT_REASON_COLORS[r.reason] || ""}`}>{r.reason}</span>
            </div>
          </div>
        ))}
      </article>
    </div>
  );
}

/* ================================================================
   PORTFOLIO — Positions
   ================================================================ */

const POSITIONS_DATA = [
  { ticker: "SBIN",     name: "SBI",              qty: 100, avg: 823,   ltp: 837,   dayChg: "+1.2%", openPnl: "+₹1,400",  openPct: "+1.70%", trend: [820,825,830,833,837] },
  { ticker: "AXISBANK", name: "Axis Bank",         qty: 50,  avg: 1198,  ltp: 1224,  dayChg: "+0.8%", openPnl: "+₹1,300",  openPct: "+2.17%", trend: [1195,1205,1210,1218,1224] },
  { ticker: "ICICIBANK",name: "ICICI Bank",        qty: 75,  avg: 1324,  ltp: 1341,  dayChg: "+0.5%", openPnl: "+₹1,275",  openPct: "+1.28%", trend: [1320,1328,1322,1335,1341] },
  { ticker: "RELIANCE", name: "Reliance",          qty: 20,  avg: 2872,  ltp: 2841,  dayChg: "−0.9%", openPnl: "−₹620",    openPct: "−1.08%", trend: [2872,2860,2855,2848,2841] },
  { ticker: "TCS",      name: "Tata Consultancy",  qty: 10,  avg: 4055,  ltp: 4102,  dayChg: "+0.6%", openPnl: "+₹470",    openPct: "+1.16%", trend: [4058,4065,4070,4088,4102] },
];

/* Small 5-day trend sparkline for positions table */
function PosTrendSpark({ pts }) {
  const w = 80, h = 24;
  const min = Math.min(...pts), max = Math.max(...pts);
  const range = Math.max(1, max - min);
  const step = w / (pts.length - 1);
  const path = pts.map((p, i) => {
    const x = (i * step).toFixed(1);
    const y = (h - ((p - min) / range) * (h - 4) - 2).toFixed(1);
    return `${i === 0 ? "M" : "L"} ${x} ${y}`;
  }).join(" ");
  const up = pts[pts.length - 1] >= pts[0];
  const stroke = up ? "var(--bull,#3FDD8A)" : "var(--bear,#FF5C7A)";
  return (
    <svg viewBox={`0 0 ${w} ${h}`} width={w} height={h} style={{ display: "block" }}>
      <path d={path} stroke={stroke} strokeWidth="1.5" fill="none" />
      <circle cx={(4 * step).toFixed(1)} cy={(h - ((pts[4] - min) / range) * (h - 4) - 2).toFixed(1)} r="2.5" fill={stroke} />
    </svg>
  );
}

/* Sector allocation donut chart */
const DONUT_SECTORS = [
  { name: "Banking", pct: 32, color: "#4F8CFF" },
  { name: "IT",      pct: 24, color: "#7B5BFF" },
  { name: "Energy",  pct: 18, color: "#3FDD8A" },
  { name: "Auto",    pct: 14, color: "#FFB454" },
  { name: "Pharma",  pct: 12, color: "#F472B6" },
];

function AllocationDonut() {
  const cx = 110, cy = 110, r = 76, innerR = 50;
  let cumAngle = -90; // start at top
  const slices = DONUT_SECTORS.map((s) => {
    const startAngle = cumAngle;
    const sweep = (s.pct / 100) * 360;
    cumAngle += sweep;
    const endAngle = cumAngle;
    return { ...s, startAngle, endAngle };
  });

  const polarToXY = (angleDeg, radius) => {
    const rad = (angleDeg * Math.PI) / 180;
    return {
      x: (cx + radius * Math.cos(rad)).toFixed(2),
      y: (cy + radius * Math.sin(rad)).toFixed(2),
    };
  };

  const makeArcPath = (start, end, outerR, inner) => {
    const largeArc = end - start > 180 ? 1 : 0;
    const s1 = polarToXY(start, outerR);
    const e1 = polarToXY(end, outerR);
    const s2 = polarToXY(end, inner);
    const e2 = polarToXY(start, inner);
    return `M ${s1.x} ${s1.y} A ${outerR} ${outerR} 0 ${largeArc} 1 ${e1.x} ${e1.y} L ${s2.x} ${s2.y} A ${inner} ${inner} 0 ${largeArc} 0 ${e2.x} ${e2.y} Z`;
  };

  return (
    <article className="pd2-card pd2-donut-card">
      <h3 className="pd2-card-title">Sector allocation</h3>
      <div className="pd2-donut-layout">
        <svg viewBox="0 0 220 220" className="pd2-donut-svg">
          {slices.map((s, i) => (
            <path
              key={i}
              d={makeArcPath(s.startAngle, s.endAngle - 1.5, r, innerR)}
              fill={s.color}
              opacity="0.88"
            />
          ))}
          {/* Center label */}
          <text x={cx} y={cy - 6} textAnchor="middle" fontSize="11" fill="var(--text-3,#7A82A5)" fontWeight="600">Total</text>
          <text x={cx} y={cy + 10} textAnchor="middle" fontSize="13" fill="var(--text-1,#F1F5FF)" fontWeight="700"
            style={{ fontFeatureSettings: "'tnum','lnum'", fontVariantNumeric: "tabular-nums lining-nums" }}>
            ₹6.4L
          </text>
        </svg>
        <div className="pd2-donut-legend">
          {DONUT_SECTORS.map((s) => (
            <div key={s.name} className="pd2-donut-leg-row">
              <span className="pd2-donut-leg-dot" style={{ background: s.color }} />
              <span className="pd2-donut-leg-name">{s.name}</span>
              <span className="pd2-donut-leg-pct">{s.pct}%</span>
            </div>
          ))}
        </div>
      </div>
    </article>
  );
}

function PortfolioPositions() {
  return (
    <div className="pd2-main">
      <div className="pd2-port-summary">
        <div className="pd2-port-kpi">
          <div className="pd2-metric-label">Total invested</div>
          <div className="pd2-port-kpi-val">₹3,28,650</div>
        </div>
        <div className="pd2-port-kpi">
          <div className="pd2-metric-label">Open P&amp;L</div>
          <div className="pd2-port-kpi-val pos">+₹3,825</div>
        </div>
        <div className="pd2-port-kpi">
          <div className="pd2-metric-label">Day's change</div>
          <div className="pd2-port-kpi-val pos">+₹1,240 (+0.38%)</div>
        </div>
      </div>

      <AllocationDonut />

      <article className="pd2-card">
        <div className="pd2-pos-thead">
          <div className="pd2-th">Ticker</div>
          <div className="pd2-th col-num">Qty</div>
          <div className="pd2-th col-num">Avg entry</div>
          <div className="pd2-th col-num">LTP</div>
          <div className="pd2-th col-num">Day's chg</div>
          <div className="pd2-th col-num">Open P&amp;L</div>
          <div className="pd2-th col-num">5d trend</div>
        </div>
        {POSITIONS_DATA.map((r, i) => (
          <div key={i} className="pd2-pos-tr">
            <div className="pd2-td">
              <div className="pd2-tr-ticker">{r.ticker}</div>
              <div className="pd2-tr-name">{r.name}</div>
            </div>
            <div className="pd2-td col-num">{r.qty}</div>
            <div className="pd2-td col-num">₹{r.avg.toLocaleString("en-IN")}</div>
            <div className="pd2-td col-num">₹{r.ltp.toLocaleString("en-IN")}</div>
            <div className={`pd2-td col-num ${r.dayChg.startsWith("+") ? "pos" : "neg"}`}>{r.dayChg}</div>
            <div className={`pd2-td col-num ${r.openPnl.startsWith("+") ? "pos" : "neg"}`}>
              {r.openPnl} <span className="pd2-pct-small">{r.openPct}</span>
            </div>
            <div className="pd2-td col-num">
              <PosTrendSpark pts={r.trend} />
            </div>
          </div>
        ))}
      </article>
    </div>
  );
}

/* ================================================================
   PORTFOLIO — Holdings
   ================================================================ */

const HOLDINGS_DATA = [
  { ticker: "RELIANCE",   name: "Reliance Industries",  qty: 20,  avg: 2812,  ltp: 2841,  dayChg: "−0.9%",  openPnl: "+₹580",   openPct: "+2.07%", days: 48 },
  { ticker: "HDFCBANK",   name: "HDFC Bank",            qty: 50,  avg: 1640,  ltp: 1675,  dayChg: "+0.4%",  openPnl: "+₹1,750", openPct: "+2.13%", days: 62 },
  { ticker: "TCS",        name: "Tata Consultancy",     qty: 10,  avg: 3980,  ltp: 4102,  dayChg: "+0.6%",  openPnl: "+₹1,220", openPct: "+3.07%", days: 34 },
  { ticker: "INFY",       name: "Infosys",              qty: 40,  avg: 1798,  ltp: 1842,  dayChg: "+0.3%",  openPnl: "+₹1,760", openPct: "+2.45%", days: 71 },
  { ticker: "BHARTIARTL", name: "Bharti Airtel",        qty: 30,  avg: 1520,  ltp: 1562,  dayChg: "+0.7%",  openPnl: "+₹1,260", openPct: "+2.76%", days: 29 },
  { ticker: "ITC",        name: "ITC Limited",          qty: 200, avg: 471,   ltp: 487,   dayChg: "+1.1%",  openPnl: "+₹3,200", openPct: "+3.40%", days: 88 },
  { ticker: "HINDUNILVR", name: "Hindustan Unilever",   qty: 20,  avg: 2710,  ltp: 2642,  dayChg: "−0.3%",  openPnl: "−₹1,360","openPct": "−2.51%", days: 41 },
  { ticker: "MARUTI",     name: "Maruti Suzuki",        qty: 5,   avg: 12100, ltp: 12450, dayChg: "+0.8%",  openPnl: "+₹1,750", openPct: "+2.89%", days: 19 },
];

function PortfolioHoldings() {
  return (
    <div className="pd2-main">
      <article className="pd2-card">
        <div className="pd2-table-titlebar">
          <h3 className="pd2-card-title">Long-term holdings</h3>
          <span className="pd2-table-subtitle">{HOLDINGS_DATA.length} positions</span>
        </div>
        <div className="pd2-hold-thead">
          <div className="pd2-th">Ticker</div>
          <div className="pd2-th col-num">Qty</div>
          <div className="pd2-th col-num">Avg entry</div>
          <div className="pd2-th col-num">LTP</div>
          <div className="pd2-th col-num">Day's chg</div>
          <div className="pd2-th col-num">Days held</div>
          <div className="pd2-th col-num">Open P&amp;L</div>
        </div>
        {HOLDINGS_DATA.map((r, i) => (
          <div key={i} className="pd2-hold-tr">
            <div className="pd2-td">
              <div className="pd2-tr-ticker">{r.ticker}</div>
              <div className="pd2-tr-name">{r.name}</div>
            </div>
            <div className="pd2-td col-num">{r.qty}</div>
            <div className="pd2-td col-num">₹{r.avg.toLocaleString("en-IN")}</div>
            <div className="pd2-td col-num">₹{r.ltp.toLocaleString("en-IN")}</div>
            <div className={`pd2-td col-num ${r.dayChg.startsWith("+") ? "pos" : "neg"}`}>{r.dayChg}</div>
            <div className="pd2-td col-num pd2-days-pill">{r.days}d</div>
            <div className={`pd2-td col-num ${r.openPnl.startsWith("+") ? "pos" : "neg"}`}>{r.openPnl}</div>
          </div>
        ))}
      </article>
    </div>
  );
}

/* ================================================================
   PORTFOLIO — Orders
   ================================================================ */

const ORDERS_DATA = [
  { time: "09:16:43", ticker: "SBIN",     type: "Buy",  qty: 100, price: "₹823.00",  status: "Filled" },
  { time: "09:22:11", ticker: "AXISBANK", type: "Buy",  qty: 50,  price: "₹1,198.50", status: "Filled" },
  { time: "10:05:32", ticker: "ICICIBANK",type: "Buy",  qty: 75,  price: "₹1,324.00", status: "Filled" },
  { time: "11:34:19", ticker: "ASIANPAINT",type:"Sell", qty: 15,  price: "₹2,893.00", status: "Filled" },
  { time: "13:01:05", ticker: "KOTAKBANK",type: "Buy",  qty: 30,  price: "₹1,924.00", status: "Pending" },
  { time: "14:47:22", ticker: "INFY",     type: "Sell", qty: 20,  price: "₹1,855.00", status: "Cancelled" },
];

function OrderStatusChip({ status }) {
  const cfg = { Filled: "pd2-ord-filled", Pending: "pd2-ord-pending", Cancelled: "pd2-ord-cancelled" };
  return <span className={`pd2-ord-chip ${cfg[status] || ""}`}>{status}</span>;
}

function PortfolioOrders() {
  return (
    <div className="pd2-main">
      <article className="pd2-card">
        <div className="pd2-table-titlebar">
          <h3 className="pd2-card-title">Today's orders</h3>
          <span className="pd2-table-subtitle">6 orders · 4 filled</span>
        </div>
        <div className="pd2-ord-thead">
          <div className="pd2-th">Time</div>
          <div className="pd2-th">Ticker</div>
          <div className="pd2-th">Type</div>
          <div className="pd2-th col-num">Qty</div>
          <div className="pd2-th col-num">Price</div>
          <div className="pd2-th">Status</div>
        </div>
        {ORDERS_DATA.map((r, i) => (
          <div key={i} className="pd2-ord-tr">
            <div className="pd2-td pd2-date-col">{r.time}</div>
            <div className="pd2-td pd2-tr-ticker">{r.ticker}</div>
            <div className={`pd2-td pd2-type-chip ${r.type === "Buy" ? "pd2-type-buy" : "pd2-type-sell"}`}>{r.type}</div>
            <div className="pd2-td col-num">{r.qty}</div>
            <div className="pd2-td col-num">{r.price}</div>
            <div className="pd2-td"><OrderStatusChip status={r.status} /></div>
          </div>
        ))}
      </article>
    </div>
  );
}

/* ================================================================
   BACKTEST — Runs
   ================================================================ */

const BT_RUNS = [
  { name: "Bull-run 2023",     date: "Nov 2025", period: "Jan–Dec 2023", sharpe: "2.45", cagr: "41.2%", maxdd: "−7.8%", trades: 94,  status: "Passed" },
  { name: "Post-COVID momentum",date: "Oct 2025", period: "Apr–Dec 2021", sharpe: "4.21", cagr: "68.4%", maxdd: "−5.2%", trades: 61,  status: "Passed" },
  { name: "Choppy year",        date: "Oct 2025", period: "Jan–Dec 2022", sharpe: "0.73", cagr: "9.7%",  maxdd: "−14.1%",trades: 78,  status: "Passed" },
  { name: "Bear retest 2018",   date: "Sep 2025", period: "Jan–Dec 2018", sharpe: "−0.76",cagr: "−11.2%",maxdd: "−22.4%",trades: 42,  status: "Failed" },
  { name: "Full walk-forward",  date: "Sep 2025", period: "2019–2024",    sharpe: "1.63", cagr: "28.7%", maxdd: "−12.6%",trades: 162, status: "Passed" },
  { name: "2024 live sim",      date: "Aug 2025", period: "Jan–Dec 2024", sharpe: "1.49", cagr: "22.3%", maxdd: "−9.4%", trades: 39,  status: "Passed" },
];

/* Deterministic LCG seeded per run index — 24 equity-curve points */
function genRunEquity(seed, positive) {
  let s = seed * 7919 + 1;
  const r = () => { s = (s * 1103515245 + 12345) & 0x7fffffff; return s / 0x7fffffff; };
  const out = [100];
  for (let i = 1; i < 24; i++) {
    const drift = positive ? 0.6 + r() * 0.6 : -0.5 - r() * 0.5;
    const noise = (r() - 0.42) * 3;
    out.push(Math.max(10, out[i - 1] + drift + noise));
  }
  return out;
}

/* Helper: small equity sparkline, edge-to-edge inside the run card */
function MiniEquitySpark({ points, positive }) {
  const w = 300, h = 40;
  const min = Math.min(...points), max = Math.max(...points);
  const range = Math.max(1, max - min);
  const step = w / (points.length - 1);
  const path = points.map((p, i) => {
    const x = (i * step).toFixed(1);
    const y = (h - ((p - min) / range) * (h - 4) - 2).toFixed(1);
    return `${i === 0 ? "M" : "L"} ${x} ${y}`;
  }).join(" ");
  const stroke = positive ? "var(--bull, #3FDD8A)" : "var(--bear, #FF5C7A)";
  const fillColor = positive ? "rgba(63,221,138,0.15)" : "rgba(255,92,122,0.15)";
  return (
    <div className="pd2-run-spark-wrap">
      <svg viewBox={`0 0 ${w} ${h}`} className="pd2-run-spark-svg" preserveAspectRatio="none">
        <path d={`${path} L ${w} ${h} L 0 ${h} Z`} fill={fillColor} />
        <path d={path} stroke={stroke} strokeWidth="1.5" fill="none" />
      </svg>
    </div>
  );
}

function BacktestRuns() {
  return (
    <div className="pd2-main">
      <div className="pd2-bt-runs-grid">
        {BT_RUNS.map((r, i) => {
          const positive = !r.cagr.startsWith("−");
          const pts = genRunEquity(i + 1, positive);
          return (
            <article key={i} className="pd2-bt-run-card">
              <div className="pd2-bt-run-head">
                <div>
                  <div className="pd2-tr-ticker">{r.name}</div>
                  <div className="pd2-tr-name">{r.date} · {r.period}</div>
                </div>
                <span className={`pd2-bt-status ${r.status === "Passed" ? "pd2-bt-pass" : "pd2-bt-fail"}`}>{r.status}</span>
              </div>
              <div className="pd2-bt-run-stats">
                <div className="pd2-bt-stat">
                  <div className="pd2-metric-label">Sharpe</div>
                  <div className={`pd2-bt-stat-val ${parseFloat(r.sharpe) >= 1 ? "pos" : "neg"}`}>{r.sharpe}</div>
                </div>
                <div className="pd2-bt-stat">
                  <div className="pd2-metric-label">CAGR</div>
                  <div className={`pd2-bt-stat-val ${r.cagr.startsWith("−") ? "neg" : "pos"}`}>{r.cagr}</div>
                </div>
                <div className="pd2-bt-stat">
                  <div className="pd2-metric-label">Max DD</div>
                  <div className="pd2-bt-stat-val neg">{r.maxdd}</div>
                </div>
                <div className="pd2-bt-stat">
                  <div className="pd2-metric-label">Trades</div>
                  <div className="pd2-bt-stat-val">{r.trades}</div>
                </div>
              </div>
              <MiniEquitySpark points={pts} positive={positive} />
            </article>
          );
        })}
      </div>
    </div>
  );
}

/* ================================================================
   BACKTEST — Compare
   ================================================================ */

const CMP_A = { name: "Full walk-forward",   sharpe: 1.53, cagr: "23.2%", maxdd: "−14.1%", trades: 101, wr: "50.7%", avgWin: "+3.8%", avgLoss: "−2.1%" };
const CMP_B = { name: "v2.0 (current live)", sharpe: 1.63, cagr: "28.7%", maxdd: "−12.6%", trades: 162, wr: "49.6%", avgWin: "+4.1%", avgLoss: "−2.0%" };

function DiffArrow({ a, b, higherBetter = true }) {
  const aNum = parseFloat(String(a).replace(/[^0-9.\-]/g, ""));
  const bNum = parseFloat(String(b).replace(/[^0-9.\-]/g, ""));
  const better = higherBetter ? bNum > aNum : bNum < aNum;
  const diff = (bNum - aNum).toFixed(2);
  const sign = diff > 0 ? "+" : "";
  return (
    <span className={`pd2-cmp-diff ${better ? "pos" : "neg"}`}>
      {better ? <ArrowUpRight size={11} /> : <ArrowDownRight size={11} />}
      {sign}{diff}
    </span>
  );
}

const CMP_ROWS = [
  { label: "Sharpe",   keyA: "sharpe", keyB: "sharpe", higherBetter: true },
  { label: "CAGR",     keyA: "cagr",   keyB: "cagr",   higherBetter: true },
  { label: "Max DD",   keyA: "maxdd",  keyB: "maxdd",  higherBetter: false },
  { label: "Trades",   keyA: "trades", keyB: "trades", higherBetter: true },
  { label: "Win rate", keyA: "wr",     keyB: "wr",     higherBetter: true },
  { label: "Avg win",  keyA: "avgWin", keyB: "avgWin", higherBetter: true },
  { label: "Avg loss", keyA: "avgLoss",keyB: "avgLoss",higherBetter: false },
];

/* Two overlapping equity curves — A (gray) underperforms B (brand blue) */
function OverlayCurves({ nameA, nameB }) {
  const w = 800, h = 160;
  // Generate deterministic curves; B clearly outperforms A
  const ptsA = useMemo(() => {
    let p = 100; let s = 17;
    const r = () => { s = (s * 1103515245 + 12345) & 0x7fffffff; return s / 0x7fffffff; };
    return Array.from({ length: 36 }, () => { const d = 0.2 + r() * 0.4; const n = (r() - 0.45) * 3.2; p += d + n; return Math.max(80, p); });
  }, []);
  const ptsB = useMemo(() => {
    let p = 100; let s = 31;
    const r = () => { s = (s * 1103515245 + 12345) & 0x7fffffff; return s / 0x7fffffff; };
    return Array.from({ length: 36 }, () => { const d = 0.55 + r() * 0.65; const n = (r() - 0.4) * 3; p += d + n; return Math.max(90, p); });
  }, []);

  const allPts = [...ptsA, ...ptsB];
  const minV = Math.min(...allPts), maxV = Math.max(...allPts);
  const range = Math.max(1, maxV - minV);
  const step = w / 35;

  const toPath = (pts) => pts.map((p, i) => {
    const x = (i * step).toFixed(1);
    const y = (h - ((p - minV) / range) * (h - 14) - 7).toFixed(1);
    return `${i === 0 ? "M" : "L"} ${x} ${y}`;
  }).join(" ");

  const pathA = toPath(ptsA);
  const pathB = toPath(ptsB);

  return (
    <article className="pd2-card pd2-overlay-card">
      <div className="pd2-overlay-head">
        <h3 className="pd2-card-title" style={{ margin: 0 }}>Equity curve comparison</h3>
        <div className="pd2-overlay-legend">
          <span className="pd2-overlay-leg pd2-overlay-leg-a">
            <svg width="20" height="2"><line x1="0" y1="1" x2="20" y2="1" stroke="var(--text-2)" strokeWidth="2" /></svg>
            {nameA}
          </span>
          <span className="pd2-overlay-leg pd2-overlay-leg-b">
            <svg width="20" height="2"><line x1="0" y1="1" x2="20" y2="1" stroke="var(--brand, #4F8CFF)" strokeWidth="2" /></svg>
            {nameB}
          </span>
        </div>
      </div>
      <svg viewBox={`0 0 ${w} ${h}`} className="pd2-overlay-svg" preserveAspectRatio="none">
        {[0.2, 0.4, 0.6, 0.8].map((g) => (
          <line key={g} x1="0" x2={w} y1={h * g} y2={h * g} stroke="rgba(255,255,255,0.04)" strokeWidth="1" />
        ))}
        {/* A — gray, fill with very low alpha */}
        <path d={`${pathA} L ${w} ${h} L 0 ${h} Z`} fill="rgba(184,192,218,0.06)" />
        <path d={pathA} stroke="var(--text-2, #B8C0DA)" strokeWidth="1.5" fill="none" strokeDasharray="4 3" />
        {/* B — brand blue */}
        <path d={`${pathB} L ${w} ${h} L 0 ${h} Z`} fill="rgba(79,140,255,0.12)" />
        <path d={pathB} stroke="var(--brand, #4F8CFF)" strokeWidth="2" fill="none" />
      </svg>
    </article>
  );
}

function BacktestCompare() {
  return (
    <div className="pd2-main">
      <OverlayCurves nameA={CMP_A.name} nameB={CMP_B.name} />
      <article className="pd2-card pd2-cmp-card">
        <div className="pd2-cmp-header">
          <div className="pd2-cmp-col-head">Metric</div>
          <div className="pd2-cmp-col-head pd2-cmp-a">{CMP_A.name}</div>
          <div className="pd2-cmp-col-head pd2-cmp-b">{CMP_B.name}</div>
          <div className="pd2-cmp-col-head">Diff</div>
        </div>
        {CMP_ROWS.map((row, i) => (
          <div key={i} className="pd2-cmp-row">
            <div className="pd2-cmp-metric-label">{row.label}</div>
            <div className="pd2-cmp-val">{CMP_A[row.keyA]}</div>
            <div className="pd2-cmp-val pd2-cmp-b-val">{CMP_B[row.keyB]}</div>
            <DiffArrow a={CMP_A[row.keyA]} b={CMP_B[row.keyB]} higherBetter={row.higherBetter} />
          </div>
        ))}
      </article>
    </div>
  );
}

/* ================================================================
   BACKTEST — Create
   ================================================================ */

function BacktestCreate() {
  const [regimes, setRegimes] = useState({ Bull: true, Choppy: true, Bear: false });
  const [sectors, setSectors] = useState({ Banking: true, IT: true, Energy: false, FMCG: false, Auto: false, Pharma: false });
  const [confFloor, setConfFloor] = useState(0.92);

  const toggleRegime = (r) => setRegimes((prev) => ({ ...prev, [r]: !prev[r] }));
  const toggleSector = (s) => setSectors((prev) => ({ ...prev, [s]: !prev[s] }));

  return (
    <div className="pd2-main">
      <article className="pd2-card pd2-form-card">
        <h3 className="pd2-card-title">Create backtest run</h3>
        <div className="pd2-form">

          <div className="pd2-form-row">
            <div className="pd2-field">
              <label className="pd2-field-label">Start date</label>
              <input type="date" className="pd2-field-input" defaultValue="2024-01-01" />
            </div>
            <div className="pd2-field">
              <label className="pd2-field-label">End date</label>
              <input type="date" className="pd2-field-input" defaultValue="2024-12-31" />
            </div>
          </div>

          <div className="pd2-field">
            <label className="pd2-field-label">Regime filter</label>
            <div className="pd2-chip-group">
              {Object.entries(regimes).map(([r, on]) => (
                <button
                  key={r}
                  type="button"
                  className={`pd2-toggle-chip ${on ? "active" : ""}`}
                  onClick={() => toggleRegime(r)}
                >
                  {on && <Check size={11} />} {r}
                </button>
              ))}
            </div>
          </div>

          <div className="pd2-field">
            <label className="pd2-field-label">Sector filter</label>
            <div className="pd2-chip-group pd2-chip-wrap">
              {Object.entries(sectors).map(([s, on]) => (
                <button
                  key={s}
                  type="button"
                  className={`pd2-toggle-chip ${on ? "active" : ""}`}
                  onClick={() => toggleSector(s)}
                >
                  {on && <Check size={11} />} {s}
                </button>
              ))}
            </div>
          </div>

          <div className="pd2-field">
            <label className="pd2-field-label">
              Confidence floor — <span className="pd2-slider-val">{confFloor.toFixed(2)}</span>
            </label>
            <input
              type="range"
              min="0.5" max="1.0" step="0.01"
              value={confFloor}
              onChange={(e) => setConfFloor(parseFloat(e.target.value))}
              className="pd2-slider"
            />
            <div className="pd2-slider-labels"><span>0.50</span><span>1.00</span></div>
          </div>

          <div className="pd2-form-actions">
            <button type="button" className="pd2-btn-ghost">Cancel</button>
            <button type="button" className="pd2-btn-primary">
              <BarChart2 size={14} /> Run backtest
            </button>
          </div>
        </div>
      </article>
    </div>
  );
}

/* ================================================================
   JOURNAL — Calendar
   ================================================================ */

const MONTHS = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];
const DAYS_IN_MONTH = [31,28,31,30,31,30,31,31,30,31,30,31];

function seedRng(seed) {
  let s = seed;
  return () => { s = (s * 1103515245 + 12345) & 0x7fffffff; return s / 0x7fffffff; };
}

function JournalCalendar() {
  const rng = useMemo(() => seedRng(42), []);
  const calData = useMemo(() => {
    return MONTHS.map((m, mi) => {
      const days = [];
      for (let d = 0; d < DAYS_IN_MONTH[mi]; d++) {
        const v = rng();
        let cls = "";
        if (v < 0.55) cls = "";
        else if (v < 0.70) cls = "cal-win";
        else if (v < 0.80) cls = "cal-win-soft";
        else if (v < 0.88) cls = "cal-loss-soft";
        else cls = "cal-loss";
        days.push(cls);
      }
      return { month: m, days };
    });
  }, [rng]);

  const bestDay   = "+₹22,470";
  const worstDay  = "−₹8,100";
  const profDays  = 94;
  const totalPnl  = "+₹1,42,860";

  return (
    <div className="pd2-main">
      <div className="pd2-cal-layout">
        <article className="pd2-card pd2-cal-card">
          <h3 className="pd2-card-title">2025 · Signal calendar</h3>
          <div className="pd2-year-cal">
            {calData.map(({ month, days }) => (
              <div key={month} className="pd2-cal-month">
                <div className="pd2-cal-month-label">{month}</div>
                <div className="pd2-cal-cells">
                  {days.map((cls, di) => (
                    <span key={di} className={`pd2-cal-cell ${cls}`} title={`${month} ${di + 1}`} />
                  ))}
                </div>
              </div>
            ))}
          </div>
          <div className="pd2-cal-legend">
            <span className="pd2-cal-leg-item"><span className="pd2-cal-cell cal-win" /> Strong win</span>
            <span className="pd2-cal-leg-item"><span className="pd2-cal-cell cal-win-soft" /> Small win</span>
            <span className="pd2-cal-leg-item"><span className="pd2-cal-cell cal-loss-soft" /> Small loss</span>
            <span className="pd2-cal-leg-item"><span className="pd2-cal-cell cal-loss" /> Big loss</span>
            <span className="pd2-cal-leg-item"><span className="pd2-cal-cell" /> No signal</span>
          </div>
        </article>

        <aside className="pd2-cal-stats">
          <article className="pd2-card">
            <h3 className="pd2-card-title">Year stats</h3>
            <div className="pd2-cal-stat-rows">
              <div className="pd2-cal-stat-row"><span>Best day</span><strong className="pos">{bestDay}</strong></div>
              <div className="pd2-cal-stat-row"><span>Worst day</span><strong className="neg">{worstDay}</strong></div>
              <div className="pd2-cal-stat-row"><span>Profitable days</span><strong>{profDays}</strong></div>
              <div className="pd2-cal-stat-row"><span>Total P&amp;L</span><strong className="pos">{totalPnl}</strong></div>
            </div>
          </article>
        </aside>
      </div>
    </div>
  );
}

/* ================================================================
   JOURNAL — Trades
   ================================================================ */

const JOURNAL_TRADES = [
  { date: "Nov 28", ticker: "RELIANCE",  entry: "₹2,872", exit: "₹3,053", hold: "6d",  outcome: "Win",  pnl: "+₹18,120" },
  { date: "Nov 21", ticker: "HDFCBANK",  entry: "₹1,675", exit: "₹1,772", hold: "5d",  outcome: "Win",  pnl: "+₹9,700"  },
  { date: "Nov 14", ticker: "TCS",       entry: "₹4,055", exit: "₹4,254", hold: "7d",  outcome: "Win",  pnl: "+₹14,950" },
  { date: "Nov 07", ticker: "INFY",      entry: "₹1,842", exit: "₹1,793", hold: "4d",  outcome: "Loss", pnl: "−₹4,900"  },
  { date: "Oct 31", ticker: "BHARTIARTL",entry: "₹1,562", exit: "₹1,655", hold: "8d",  outcome: "Win",  pnl: "+₹9,300"  },
  { date: "Oct 24", ticker: "LT",        entry: "₹3,412", exit: "₹3,600", hold: "6d",  outcome: "Win",  pnl: "+₹11,280" },
  { date: "Oct 17", ticker: "KOTAKBANK", entry: "₹1,924", exit: "₹1,872", hold: "5d",  outcome: "Loss", pnl: "−₹5,200"  },
  { date: "Oct 10", ticker: "ITC",       entry: "₹487",   exit: "₹516",   hold: "9d",  outcome: "Win",  pnl: "+₹4,350"  },
  { date: "Oct 03", ticker: "HINDUNILVR",entry: "₹2,642", exit: "₹2,795", hold: "7d",  outcome: "Win",  pnl: "+₹15,300" },
  { date: "Sep 26", ticker: "ASIANPAINT",entry: "₹2,893", exit: "₹2,812", hold: "6d",  outcome: "Loss", pnl: "−₹8,100"  },
  { date: "Sep 19", ticker: "MARUTI",    entry: "₹12,450",exit: "₹13,199",hold: "8d",  outcome: "Win",  pnl: "+₹22,470" },
  { date: "Sep 12", ticker: "SBIN",      entry: "₹798",   exit: "₹844",   hold: "11d", outcome: "Win",  pnl: "+₹9,200"  },
  { date: "Sep 05", ticker: "AXISBANK",  entry: "₹1,144", exit: "₹1,224", hold: "9d",  outcome: "Win",  pnl: "+₹12,000" },
  { date: "Aug 29", ticker: "BAJFINANCE",entry: "₹7,614", exit: "₹8,283", hold: "12d", outcome: "Win",  pnl: "+₹20,070" },
  { date: "Aug 22", ticker: "ICICIBANK", entry: "₹1,285", exit: "₹1,341", hold: "7d",  outcome: "Win",  pnl: "+₹8,400"  },
];

/* P&L distribution histogram — buckets by return % */
const PL_BUCKETS = [
  { label: "< −10%", count: 1, pct: -12 },
  { label: "−10–−5%", count: 2, pct: -7 },
  { label: "−5–0%",   count: 3, pct: -3 },
  { label: "0–+5%",   count: 4, pct: 2 },
  { label: "+5–+10%", count: 7, pct: 7 },
  { label: "+10–+15%",count: 5, pct: 12 },
  { label: "+15–+20%",count: 4, pct: 17 },
  { label: "> +20%",  count: 3, pct: 22 },
];

function PLHistogram() {
  const maxCount = Math.max(...PL_BUCKETS.map((b) => b.count));
  const barW = 32;
  const barGap = 12;
  const totalW = PL_BUCKETS.length * (barW + barGap) - barGap;
  const chartH = 80; // usable bar height
  const svgW = totalW + 40; // +40 for left y-axis margin
  const svgH = chartH + 32; // +32 for x-axis labels
  const leftPad = 28;

  return (
    <article className="pd2-card">
      <div className="pd2-plh-head">
        <h3 className="pd2-card-title" style={{ margin: 0 }}>P&amp;L distribution · 29 trades</h3>
        <span className="pd2-plh-sub">by return bucket</span>
      </div>
      <svg
        viewBox={`0 0 ${svgW} ${svgH}`}
        className="pd2-plh-svg"
        style={{ width: "100%", height: `${svgH}px` }}
      >
        {/* Y gridlines + labels */}
        {[0, Math.round(maxCount / 2), maxCount].map((v) => {
          const y = chartH - (v / maxCount) * chartH;
          return (
            <g key={v}>
              <line x1={leftPad} x2={svgW} y1={y} y2={y} stroke="rgba(255,255,255,0.05)" strokeWidth="1" />
              <text x={leftPad - 4} y={y + 4} fontSize="9" fill="var(--text-3, #7A82A5)" textAnchor="end"
                style={{ fontFeatureSettings: "'tnum','lnum'", fontVariantNumeric: "tabular-nums lining-nums" }}>
                {v}
              </text>
            </g>
          );
        })}

        {PL_BUCKETS.map((b, i) => {
          const x = leftPad + i * (barW + barGap);
          const bh = Math.max(2, (b.count / maxCount) * chartH);
          const y = chartH - bh;
          const isPos = b.pct >= 0;
          const fill = isPos ? "var(--bull, #3FDD8A)" : "var(--bear, #FF5C7A)";
          const fillAlpha = isPos ? "rgba(63,221,138,0.85)" : "rgba(255,92,122,0.85)";
          return (
            <g key={i}>
              <rect x={x} y={y} width={barW} height={bh} rx="3" fill={fillAlpha} />
              {/* count label above bar */}
              <text
                x={x + barW / 2} y={y - 3}
                fontSize="10" fill={fill} textAnchor="middle" fontWeight="600"
                style={{ fontFeatureSettings: "'tnum','lnum'", fontVariantNumeric: "tabular-nums lining-nums" }}
              >
                {b.count}
              </text>
              {/* bucket label below */}
              <text
                x={x + barW / 2} y={chartH + 14}
                fontSize="8.5" fill="var(--text-3, #7A82A5)" textAnchor="middle"
              >
                {b.label}
              </text>
            </g>
          );
        })}
        {/* Zero bucket divider — between index 2 (neg) and 3 (pos) */}
        <line
          x1={leftPad + 3 * (barW + barGap) - barGap / 2}
          x2={leftPad + 3 * (barW + barGap) - barGap / 2}
          y1={0} y2={chartH}
          stroke="rgba(255,255,255,0.14)" strokeWidth="1" strokeDasharray="3 2"
        />
      </svg>
    </article>
  );
}

function JournalTrades() {
  return (
    <div className="pd2-main">
      <PLHistogram />
      <article className="pd2-card">
        <div className="pd2-table-titlebar">
          <h3 className="pd2-card-title">Trade log</h3>
          <span className="pd2-table-subtitle">15 trades · 12W 3L</span>
        </div>
        <div className="pd2-jt-thead">
          <div className="pd2-th">Date</div>
          <div className="pd2-th">Ticker</div>
          <div className="pd2-th col-num">Entry</div>
          <div className="pd2-th col-num">Exit</div>
          <div className="pd2-th col-num">Hold</div>
          <div className="pd2-th">Outcome</div>
          <div className="pd2-th col-num">P&amp;L</div>
        </div>
        {JOURNAL_TRADES.map((r, i) => (
          <div key={i} className="pd2-jt-tr">
            <div className="pd2-td pd2-date-col">{r.date}</div>
            <div className="pd2-td pd2-tr-ticker">{r.ticker}</div>
            <div className="pd2-td col-num">{r.entry}</div>
            <div className="pd2-td col-num">{r.exit}</div>
            <div className="pd2-td col-num pd2-days-pill">{r.hold}</div>
            <div className="pd2-td"><OutcomeChip outcome={r.outcome} /></div>
            <div className={`pd2-td col-num ${r.pnl.startsWith("+") ? "pos" : "neg"}`}>{r.pnl}</div>
          </div>
        ))}
      </article>
    </div>
  );
}

/* ================================================================
   JOURNAL — Notes
   ================================================================ */

const NOTES_DATA = [
  { date: "Nov 28", ticker: "RELIANCE",   title: "Strong breakout on high volume", body: "Cleared the ₹2,850 resistance on 1.8× average volume. Momentum strong, no adverse news. Holding to target." },
  { date: "Nov 14", ticker: "TCS",        title: "Post-results momentum", body: "Q2 results beat estimates by 3%. Confidence picked up significantly overnight. Rode the gap-up cleanly." },
  { date: "Nov 07", ticker: "INFY",       title: "Stop-loss hit — weak sector day", body: "IT sector-wide selling on USD/INR move. Stopped out at ₹1,793. Exit was mechanical, no overrides." },
  { date: "Oct 24", ticker: "LT",         title: "Infrastructure theme continuation", body: "Government capex data strong. L&T order book update bullish. Model picked this 2 days before news widely circulated." },
  { date: "Oct 17", ticker: "KOTAKBANK",  title: "Failed breakout — lesson", body: "Price reversed sharply after initial breakout. Possible institutional distribution. Need to add volume confirmation check." },
  { date: "Sep 19", ticker: "MARUTI",     title: "Best trade of the quarter", body: "Auto sector revival + festival season demand. Held 8 days, exited 2% below target. ₹22,470 gain. Model accuracy high." },
];

function JournalNotes() {
  return (
    <div className="pd2-main">
      <div className="pd2-notes-list">
        {NOTES_DATA.map((n, i) => (
          <article key={i} className="pd2-note-card">
            <div className="pd2-note-meta">
              <span className="pd2-note-date">{n.date}</span>
              <span className="pd2-note-ticker">{n.ticker}</span>
            </div>
            <div className="pd2-note-title">{n.title}</div>
            <div className="pd2-note-body">{n.body}</div>
          </article>
        ))}
      </div>
    </div>
  );
}

/* ================================================================
   TRACK RECORD — Summary
   ================================================================ */

const TRACK_HERO = [
  { label: "Total signals",   value: "162",      caption: "since Jan 2024" },
  { label: "Total P&L",       value: "+₹4.2L",   caption: "+142% on ₹3L capital" },
  { label: "Sharpe ratio",    value: "1.63",      caption: "90-day rolling" },
  { label: "Max drawdown",    value: "−12.6%",    caption: "largest peak-to-trough" },
  { label: "Hit rate",        value: "67.3%",     caption: "109W / 53L" },
  { label: "Time live",       value: "18 mo",     caption: "since April 2024" },
];

function TrackSummary() {
  return (
    <div className="pd2-main">
      <div className="pd2-track-hero">
        {TRACK_HERO.map((t, i) => (
          <article key={i} className="pd2-metric">
            <div className="pd2-metric-label">{t.label}</div>
            <div className={`pd2-metric-value ${t.value.startsWith("+") ? "pos" : t.value.startsWith("−") ? "neg" : ""}`}>{t.value}</div>
            <div className="pd2-metric-caption">{t.caption}</div>
          </article>
        ))}
      </div>

      <article className="pd2-card pd2-card-big">
        <div className="pd2-card-head">
          <div>
            <div className="pd2-tag">Equity curve · all time</div>
            <h3 className="pd2-card-title-row">+142%</h3>
          </div>
          <div className="pd2-card-meta">
            <span>Sharpe <strong>1.63</strong></span>
            <span>Max DD <strong className="neg">−12.6%</strong></span>
            <span>Hit rate <strong className="pos">67.3%</strong></span>
          </div>
        </div>
        <EquityCurveSVG />
      </article>
    </div>
  );
}

/* ================================================================
   TRACK RECORD — Monthly
   ================================================================ */

const MONTHLY_RETURNS = [
  { month: "Jun 24", ret: 3.2  },
  { month: "Jul 24", ret: 5.8  },
  { month: "Aug 24", ret: -2.1 },
  { month: "Sep 24", ret: 4.7  },
  { month: "Oct 24", ret: 1.9  },
  { month: "Nov 24", ret: 7.4  },
  { month: "Dec 24", ret: -0.8 },
  { month: "Jan 25", ret: 2.3  },
  { month: "Feb 25", ret: 6.1  },
  { month: "Mar 25", ret: -1.4 },
  { month: "Apr 25", ret: 3.9  },
  { month: "May 25", ret: 8.2  },
  { month: "Jun 25", ret: 1.5  },
  { month: "Jul 25", ret: 4.4  },
  { month: "Aug 25", ret: -3.2 },
  { month: "Sep 25", ret: 5.7  },
  { month: "Oct 25", ret: 2.8  },
  { month: "Nov 25", ret: 6.3  },
];

function TrackMonthly() {
  const maxAbs = Math.max(...MONTHLY_RETURNS.map((r) => Math.abs(r.ret)));
  return (
    <div className="pd2-main">
      <article className="pd2-card pd2-card-big">
        <h3 className="pd2-card-title">Monthly returns</h3>
        <div className="pd2-month-bars">
          <div className="pd2-month-y-axis">
            {[maxAbs, maxAbs / 2, 0, -maxAbs / 2, -maxAbs].map((v, i) => (
              <span key={i} className="pd2-month-y-label">{v > 0 ? "+" : ""}{v.toFixed(1)}%</span>
            ))}
          </div>
          <div className="pd2-month-chart">
            <div className="pd2-month-zero-line" />
            <div className="pd2-month-bars-inner">
              {MONTHLY_RETURNS.map((r, i) => {
                const height = (Math.abs(r.ret) / maxAbs) * 45;
                return (
                  <div key={i} className="pd2-month-bar-col">
                    <div
                      className={`pd2-month-bar ${r.ret >= 0 ? "pd2-mbar-pos" : "pd2-mbar-neg"}`}
                      style={{
                        height: `${height}%`,
                        alignSelf: r.ret >= 0 ? "flex-end" : "flex-start",
                        marginTop: r.ret >= 0 ? "auto" : 0,
                        marginBottom: r.ret < 0 ? "auto" : 0,
                      }}
                      title={`${r.month}: ${r.ret > 0 ? "+" : ""}${r.ret}%`}
                    />
                    <div className="pd2-month-label">{r.month.slice(0, 3)}</div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      </article>
    </div>
  );
}

/* ================================================================
   TRACK RECORD — Yearly
   ================================================================ */

const YEARLY_DATA = [
  { year: "2024", signals: 39,  ret: "+22.3%", sharpe: "1.49", maxdd: "−9.4%",  best: "Nov +7.4%", worst: "Dec −0.8%" },
  { year: "2025", signals: 118, ret: "+41.6%", sharpe: "1.78", maxdd: "−5.2%",  best: "May +8.2%", worst: "Aug −3.2%" },
  { year: "2026", signals: 5,   ret: "+6.1%",  sharpe: "—",    maxdd: "−1.1%",  best: "Jan +3.9%", worst: "Mar −1.1%" },
];

/* Annual returns bar chart 2018-2025 — 8 bars, SVG */
const ANNUAL_RETURNS = [
  { year: "2018", ret: -11.2 },
  { year: "2019", ret:  14.8 },
  { year: "2020", ret:  31.4 },
  { year: "2021", ret:  68.4 },
  { year: "2022", ret:   9.7 },
  { year: "2023", ret:  41.2 },
  { year: "2024", ret:  22.3 },
  { year: "2025", ret:  41.6 },
];

function AnnualReturnsBars() {
  const barW = 32;
  const barGap = 12;
  const nBars = ANNUAL_RETURNS.length;
  const leftPad = 40; // room for y-axis labels
  const rightPad = 8;
  const topPad = 10;
  const botPad = 24; // room for year labels
  const chartH = 120; // height of the bar region (pos+neg combined)
  const svgW = leftPad + nBars * (barW + barGap) - barGap + rightPad;
  const svgH = chartH + topPad + botPad;

  // Domain: auto from data, rounded to nice bounds
  const rawMax = Math.max(...ANNUAL_RETURNS.map(d => d.ret));
  const rawMin = Math.min(...ANNUAL_RETURNS.map(d => d.ret));
  const maxRet = Math.ceil(rawMax / 10) * 10; // e.g. 68.4 → 70
  const minRet = Math.floor(rawMin / 10) * 10; // e.g. -11.2 → -20
  const domainH = maxRet - minRet;
  const zeroY = topPad + (maxRet / domainH) * chartH;

  const toBarY = (v) => {
    if (v >= 0) return topPad + ((maxRet - v) / domainH) * chartH;
    return zeroY;
  };
  const toBarH = (v) => Math.max(2, (Math.abs(v) / domainH) * chartH);

  // Y-axis labels: 20% steps across the domain
  const yTicks = [];
  for (let v = minRet; v <= maxRet; v += 20) yTicks.push(v);

  return (
    <article className="pd2-card">
      <h3 className="pd2-card-title">Annual returns · 2018–2025</h3>
      <svg
        viewBox={`0 0 ${svgW} ${svgH}`}
        className="pd2-annual-svg"
        style={{ width: "100%", height: `${svgH}px` }}
      >
        {/* Y gridlines + labels */}
        {yTicks.map((v) => {
          const y = topPad + ((maxRet - v) / domainH) * chartH;
          return (
            <g key={v}>
              <line x1={leftPad} x2={svgW - rightPad} y1={y} y2={y}
                stroke={v === 0 ? "rgba(255,255,255,0.14)" : "rgba(255,255,255,0.05)"}
                strokeWidth={v === 0 ? "1.2" : "1"}
              />
              <text x={leftPad - 5} y={y + 4} fontSize="9" fill="var(--text-3,#7A82A5)" textAnchor="end"
                style={{ fontFeatureSettings: "'tnum','lnum'", fontVariantNumeric: "tabular-nums lining-nums" }}>
                {v > 0 ? `+${v}%` : `${v}%`}
              </text>
            </g>
          );
        })}

        {ANNUAL_RETURNS.map((d, i) => {
          const x = leftPad + i * (barW + barGap);
          const isPos = d.ret >= 0;
          const bh = toBarH(d.ret);
          const by = toBarY(d.ret);
          const fill = isPos ? "rgba(63,221,138,0.82)" : "rgba(255,92,122,0.82)";
          const textFill = isPos ? "var(--bull,#3FDD8A)" : "var(--bear,#FF5C7A)";
          return (
            <g key={d.year}>
              <rect x={x} y={by} width={barW} height={bh} rx="3" fill={fill} />
              {/* Return label */}
              <text
                x={x + barW / 2}
                y={isPos ? by - 3 : by + bh + 11}
                fontSize="8.5" fill={textFill} textAnchor="middle" fontWeight="600"
                style={{ fontFeatureSettings: "'tnum','lnum'", fontVariantNumeric: "tabular-nums lining-nums" }}
              >
                {isPos ? `+${d.ret}%` : `${d.ret}%`}
              </text>
              {/* Year label */}
              <text
                x={x + barW / 2}
                y={svgH - 4}
                fontSize="9" fill="var(--text-3,#7A82A5)" textAnchor="middle"
              >
                {d.year}
              </text>
            </g>
          );
        })}
      </svg>
    </article>
  );
}

function TrackYearly() {
  return (
    <div className="pd2-main">
      <AnnualReturnsBars />
      <article className="pd2-card pd2-card-big">
        <div className="pd2-table-titlebar">
          <h3 className="pd2-card-title">Year-over-year performance</h3>
          <span className="pd2-table-subtitle">Live from April 2024</span>
        </div>
        <div className="pd2-yr-thead">
          <div className="pd2-th">Year</div>
          <div className="pd2-th col-num">Signals</div>
          <div className="pd2-th col-num">Return</div>
          <div className="pd2-th col-num">Sharpe</div>
          <div className="pd2-th col-num">Max DD</div>
          <div className="pd2-th">Best month</div>
          <div className="pd2-th">Worst month</div>
        </div>
        {YEARLY_DATA.map((r, i) => (
          <div key={i} className="pd2-yr-tr">
            <div className="pd2-td pd2-yr-year">{r.year}</div>
            <div className="pd2-td col-num">{r.signals}</div>
            <div className={`pd2-td col-num ${r.ret.startsWith("+") ? "pos" : "neg"}`}>{r.ret}</div>
            <div className="pd2-td col-num">{r.sharpe}</div>
            <div className="pd2-td col-num neg">{r.maxdd}</div>
            <div className="pd2-td pd2-yr-month pos">{r.best}</div>
            <div className="pd2-td pd2-yr-month neg">{r.worst}</div>
          </div>
        ))}
      </article>
    </div>
  );
}

/* ================================================================
   SETTINGS — Account
   ================================================================ */

function SettingsAccount() {
  return (
    <div className="pd2-main">
      <article className="pd2-card pd2-form-card">
        <h3 className="pd2-card-title">Account details</h3>
        <div className="pd2-form pd2-form-2col">

          <div className="pd2-field">
            <label className="pd2-field-label"><User size={11} /> Full name</label>
            <input type="text" className="pd2-field-input" defaultValue="Kreesh Vasistha" />
          </div>
          <div className="pd2-field">
            <label className="pd2-field-label"><Mail size={11} /> Email</label>
            <input type="email" className="pd2-field-input" defaultValue="kreeshvasistha@gmail.com" />
          </div>

          <div className="pd2-field">
            <label className="pd2-field-label"><Phone size={11} /> Phone</label>
            <input type="tel" className="pd2-field-input" defaultValue="+91 98200 00000" />
          </div>
          <div className="pd2-field">
            <label className="pd2-field-label">Trading experience</label>
            <select className="pd2-field-input pd2-select">
              <option>3–5 years</option>
              <option>1–2 years</option>
              <option>5+ years</option>
            </select>
          </div>

          <div className="pd2-field">
            <label className="pd2-field-label">Plan</label>
            <input type="text" className="pd2-field-input pd2-field-readonly" readOnly value="Operator · ₹2,499/mo" />
          </div>
          <div className="pd2-field pd2-field-action">
            <label className="pd2-field-label"><Lock size={11} /> Security</label>
            <button type="button" className="pd2-btn-ghost pd2-btn-inline">Change password →</button>
          </div>

        </div>
        <div className="pd2-form-actions pd2-form-actions-top">
          <button type="button" className="pd2-btn-ghost">Discard</button>
          <button type="button" className="pd2-btn-primary"><Check size={14} /> Save changes</button>
        </div>
      </article>
    </div>
  );
}

/* ================================================================
   SETTINGS — Kite
   ================================================================ */

function SettingsKite() {
  const [connected] = useState(true);
  return (
    <div className="pd2-main">
      <article className={`pd2-card pd2-status-card ${connected ? "pd2-status-connected" : "pd2-status-disconnected"}`}>
        <div className="pd2-status-head">
          <div className="pd2-status-brand">
            <div className="pd2-kite-logo">Z</div>
            <div>
              <div className="pd2-tr-ticker">Zerodha Kite</div>
              <div className="pd2-tr-name">Indian broker integration</div>
            </div>
          </div>
          <span className={`pd2-conn-badge ${connected ? "pd2-conn-on" : "pd2-conn-off"}`}>
            {connected ? <><span className="pd2-status-dot" /> Connected</> : <>Disconnected</>}
          </span>
        </div>

        <div className="pd2-status-rows">
          <div className="pd2-status-row">
            <span className="pd2-metric-label"><User size={12} /> User ID</span>
            <span>{connected ? "ZD1234" : "—"}</span>
          </div>
          <div className="pd2-status-row">
            <span className="pd2-metric-label"><Clock size={12} /> Last sync</span>
            <span>{connected ? "Today, 4:21 PM IST" : "Never"}</span>
          </div>
          <div className="pd2-status-row">
            <span className="pd2-metric-label"><RefreshCw size={12} /> Session expires</span>
            <span>{connected ? "Tomorrow 6:00 AM IST" : "—"}</span>
          </div>
          <div className="pd2-status-row">
            <span className="pd2-metric-label"><Link2 size={12} /> API key</span>
            <span className="pd2-api-key">••••••••{connected ? "a3f2" : "—"}</span>
          </div>
        </div>

        <div className="pd2-form-actions">
          <button type="button" className="pd2-btn-ghost">Disconnect</button>
          <button type="button" className="pd2-btn-primary">
            <RefreshCw size={14} /> Reconnect Kite
          </button>
        </div>
      </article>
    </div>
  );
}

/* ================================================================
   SETTINGS — Alerts
   ================================================================ */

const ALERT_GROUPS = [
  {
    group: "Channels",
    items: [
      { id: "email",  label: "Email notifications",     desc: "Alerts sent to kreeshvasistha@gmail.com", on: true },
      { id: "sms",    label: "SMS notifications",        desc: "Critical alerts to +91 98200 00000",      on: false },
      { id: "inapp",  label: "In-app notifications",     desc: "Browser push + dashboard bell",           on: true },
    ],
  },
  {
    group: "Events",
    items: [
      { id: "daily",  label: "Daily signal email",       desc: "Sent at 4:30 PM IST on scan days",        on: true },
      { id: "stop",   label: "Stop-loss hit",            desc: "Immediate alert when stop is triggered",  on: true },
      { id: "target", label: "Target hit",               desc: "Immediate alert when target is reached",  on: true },
      { id: "weekly", label: "Weekly summary",           desc: "Every Sunday at 9:00 AM IST",             on: false },
    ],
  },
];

function Toggle({ on, onToggle }) {
  return (
    <button
      type="button"
      className={`pd2-toggle ${on ? "pd2-toggle-on" : "pd2-toggle-off"}`}
      onClick={onToggle}
      aria-pressed={on}
    >
      <span className="pd2-toggle-thumb" />
    </button>
  );
}

function SettingsAlerts() {
  const [states, setStates] = useState(() => {
    const init = {};
    ALERT_GROUPS.forEach((g) => g.items.forEach((item) => { init[item.id] = item.on; }));
    return init;
  });
  const toggle = (id) => setStates((prev) => ({ ...prev, [id]: !prev[id] }));

  return (
    <div className="pd2-main">
      {ALERT_GROUPS.map((g) => (
        <article key={g.group} className="pd2-card">
          <h3 className="pd2-card-title">{g.group}</h3>
          <div className="pd2-alert-rows">
            {g.items.map((item) => (
              <div key={item.id} className="pd2-alert-row">
                <div className="pd2-alert-text">
                  <div className="pd2-alert-label">{item.label}</div>
                  <div className="pd2-alert-desc">{item.desc}</div>
                </div>
                <Toggle on={states[item.id]} onToggle={() => toggle(item.id)} />
              </div>
            ))}
          </div>
        </article>
      ))}
    </div>
  );
}
