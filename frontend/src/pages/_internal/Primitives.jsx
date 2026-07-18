import React, { useState } from 'react';
import { Activity, Radar, RefreshCcw } from 'lucide-react';
import { StatusChip } from '@/components/shared/StatusChip';
import { GradeBadge } from '@/components/shared/GradeBadge';
import { PriceArc } from '@/components/shared/PriceArc';
import { EmptyState } from '@/components/shared/EmptyState';
import { TickerTape } from '@/components/shared/TickerTape';
import { KPICard } from '@/components/shared/KPICard';
import { ChartCard } from '@/components/shared/ChartCard';
import { DataTable } from '@/components/shared/DataTable';
import { RegimeHeader } from '@/components/shared/RegimeHeader';
import { SignalCard } from '@/components/shared/SignalCard';
import { SignalDetailDrawer } from '@/components/shared/SignalDetailDrawer';
import { CommandBar } from '@/components/shared/CommandBar';
import { fmtPrice, fmtINR, fmtPct } from '@/lib/format';

/**
 * Phase 1 QA showcase — every primitive rendered in isolation at route
 * `/_primitives`. Not in the Sidebar, not linked in production. Used for:
 *   - Visual regression screenshots
 *   - Interaction smoke-testing (drawer open, order placement, Cmd-K)
 *   - Onboarding new contributors to the design system
 *
 * The fixture data below mirrors the real /api/signals + /api/trades
 * shapes so components built against it will also render in production.
 */

const SAMPLE_ARC_UP = [365, 364, 367, 369, 368, 371, 373, 372, 375, 378, 376, 380];
const SAMPLE_ARC_DOWN = [380, 378, 377, 374, 371, 372, 369, 367, 366, 364, 363, 361];
const SAMPLE_ARC_FLAT = [368, 367, 369, 368, 367, 368, 369, 368, 367, 368, 367, 368];

const SAMPLE_SIGNAL = {
  ticker: 'RAYMOND',
  sector: 'Textile',
  status: 'FRESH',
  grade: 'A+',
  ml_score: 0.87,
  v7_score: 18.37,
  v7_conviction: 'MEDIUM',
  v7_layers_agreeing: 5,
  v7_catalysts: [
    { type: 'Revenue Growth',   strength: 0.7, evidence: 'Q3 revenue +24% YoY, beating consensus by 8%.' },
    { type: 'Sector Rotation',  strength: 0.8, evidence: 'Textile sector +6.2% over 20 sessions vs Nifty +1.4%.' },
    { type: 'Momentum',         strength: 0.6, evidence: 'MACD histogram positive for 9 consecutive sessions.' },
  ],
  v7_risks: [
    { type: 'Earnings Deterioration', strength: 0.8, evidence: 'Operating margin compressed 140bps in Q3.' },
    { type: 'FII Outflow',            strength: 0.5, evidence: 'FII 5-day net flow -₹20,710cr, headwind for mid-caps.' },
  ],
  v7_macro_summary: 'FII 5-day flow -₹20,710cr. Nifty breadth soft.',
  v7_technical_summary: 'RSI balanced at 58. MACD histogram positive (bullish momentum). EMA-21 > EMA-50 since 3 weeks.',
  v7_llm_rationale: 'Strong momentum with bullish MACD and sector rotation into textiles. FII flows are negative but breadth in the sector suggests domestic funds are stepping in. Stop placed below 21EMA support at ₹322.',
  entry: 367.48,
  stop: 322.43,
  target: 441.67,
  stop_pct: -12.26,
  target_pct: 20.19,
  rr: 1.65,
  atr: 19.59,
  hold_days: 28,
  signal_date: '2026-04-24',
  current_price: 372.40,
  exit_rules: 'Stop: close < entry - 2.3xATR (-12.26%).\nTrail: 4.0% below peak after +5.5% gain.\nPartial: sell 35% at +6.5%, move stop to breakeven.\nTime: close after 28 days.',
};

const SAMPLE_SIGNAL_IN_ZONE = {
  ...SAMPLE_SIGNAL,
  ticker: 'NEWGEN',
  sector: 'IT Services',
  status: 'IN_ZONE',
  grade: 'A',
  ml_score: 0.82,
  current_price: 458.0,
  entry: 458.0,
};

const SAMPLE_SIGNAL_CHASE = {
  ...SAMPLE_SIGNAL,
  ticker: 'TATAMOT',
  sector: 'Auto',
  status: 'CHASE',
  grade: 'B+',
  ml_score: 0.71,
  current_price: 1012.30,
  entry: 982.0,
};

const TICKER_ITEMS = [
  { symbol: 'NIFTY',     price: 22145.8,  changePct:  0.34 },
  { symbol: 'BANKNIFTY', price: 47890.2,  changePct: -0.12 },
  { symbol: 'INDIAVIX',  price: 12.82,    changePct: -2.10 },
  { symbol: 'USDINR',    price: 83.42,    changePct:  0.08 },
  { symbol: 'RELIANCE',  price: 2890.5,   changePct:  0.65 },
  { symbol: 'TCS',       price: 4120.0,   changePct:  0.28 },
  { symbol: 'HDFCBANK',  price: 1542.7,   changePct: -0.45 },
];

const TABLE_ROWS = [
  { id: 1, ticker: 'RELIANCE', qty: 35, entry: 2850.0, current: 2902.5, pnl:  1837.5, pnlPct:  1.84 },
  { id: 2, ticker: 'TCS',      qty: 12, entry: 4050.0, current: 4120.0, pnl:   840.0, pnlPct:  1.73 },
  { id: 3, ticker: 'INFY',     qty: 48, entry: 1580.0, current: 1620.0, pnl:  1920.0, pnlPct:  2.53 },
  { id: 4, ticker: 'HDFCBANK', qty: 22, entry: 1605.0, current: 1542.7, pnl: -1370.6, pnlPct: -3.88 },
];

export default function PrimitivesShowcase() {
  const [detailOpen, setDetailOpen] = useState(false);
  const [orderOpen, setOrderOpen] = useState(false);
  const [commandOpen, setCommandOpen] = useState(false);
  const [period, setPeriod] = useState('1M');
  const [selectedSignal, setSelectedSignal] = useState(SAMPLE_SIGNAL);

  return (
    <div style={{ background: 'var(--surface-0)', minHeight: '100vh', color: 'var(--text-1)' }}>
      <TickerTape items={TICKER_ITEMS} />

      <div style={{ maxWidth: 1280, margin: '0 auto', padding: '32px 24px 96px' }}>
        <div style={{ marginBottom: 32 }}>
          <div className="t-ui-micro" style={{ color: 'var(--text-3)', marginBottom: 8 }}>
            NIFTYQUANT · PHASE 1 QA
          </div>
          <h1 className="t-title-1" style={{ margin: 0 }}>Primitive Library</h1>
          <p className="t-ui-body t-prose" style={{ color: 'var(--text-2)', marginTop: 8 }}>
            Every bespoke component rendered in isolation against the new design tokens. Not linked
            from production navigation — reach this page directly at <code style={{ background: 'var(--surface-2)', padding: '2px 6px', borderRadius: 4, fontFamily: 'var(--font-mono)' }}>/_primitives</code>.
          </p>
        </div>

        <RegimeHeader
          regime="Bullish"
          tone="bull"
          strength={75}
          vix={12.8}
          breadth={60}
          fiiFlow="+₹210cr"
          scanTime="4:15 PM IST"
        />

        {/* CHIPS & BADGES */}
        <Section title="Status chips · grade badges">
          <div className="flex items-center flex-wrap" style={{ gap: 10 }}>
            <StatusChip tone="info">FRESH</StatusChip>
            <StatusChip tone="brand">IN ZONE</StatusChip>
            <StatusChip tone="warn">CHASE</StatusChip>
            <StatusChip tone="bull">FILLED</StatusChip>
            <StatusChip tone="bear">REJECTED</StatusChip>
            <StatusChip tone="muted">EXPIRED</StatusChip>
          </div>
          <div className="flex items-center flex-wrap" style={{ gap: 10, marginTop: 16 }}>
            <GradeBadge grade="A+" />
            <GradeBadge grade="A" />
            <GradeBadge grade="B+" />
            <GradeBadge grade="B" />
            <GradeBadge grade="C" />
          </div>
        </Section>

        {/* PRICE ARC */}
        <Section title="Price arc — intraday shape, not decoration">
          <div className="flex items-center" style={{ gap: 32 }}>
            <div>
              <div className="t-ui-micro" style={{ color: 'var(--text-3)', marginBottom: 6 }}>ABOVE ENTRY</div>
              <PriceArc series={SAMPLE_ARC_UP} entry={365} />
            </div>
            <div>
              <div className="t-ui-micro" style={{ color: 'var(--text-3)', marginBottom: 6 }}>BELOW ENTRY</div>
              <PriceArc series={SAMPLE_ARC_DOWN} entry={380} />
            </div>
            <div>
              <div className="t-ui-micro" style={{ color: 'var(--text-3)', marginBottom: 6 }}>NEUTRAL ZONE</div>
              <PriceArc series={SAMPLE_ARC_FLAT} entry={368} />
            </div>
            <div>
              <div className="t-ui-micro" style={{ color: 'var(--text-3)', marginBottom: 6 }}>WIDE VARIANT</div>
              <PriceArc series={SAMPLE_ARC_UP} entry={365} size="wide" />
            </div>
          </div>
        </Section>

        {/* KPI CARDS */}
        <Section title="KPI cards — 4-up ledger row">
          <div
            className="grid"
            style={{ gridTemplateColumns: 'repeat(4, minmax(0, 1fr))', gap: 16 }}
          >
            <KPICard
              label="TOTAL CAPITAL"
              value={fmtINR(1042367)}
              tone="neutral"
              context="Peak ₹10.5L · 3.9% from peak"
            />
            <KPICard
              label="TODAY'S P&L"
              value={`+${fmtINR(12430)}`}
              tone="bull"
              context="+1.21%   Best: INFY +3.4%"
            />
            <KPICard
              label="DEPLOYED"
              value="84.3%"
              tone="neutral"
              context="₹8.78L across 9 positions"
            />
            <KPICard
              label="CASH AVAILABLE"
              value={fmtINR(163892)}
              tone="neutral"
              context="15.7% of capital · ready to deploy"
            />
          </div>
        </Section>

        {/* CHART CARD */}
        <Section title="Chart card — period pills, hairline axis">
          <ChartCard
            title="Equity Curve"
            badge={<StatusChip tone="info">LIVE</StatusChip>}
            periods={[
              { label: '1W', value: '1W', active: period === '1W' },
              { label: '1M', value: '1M', active: period === '1M' },
              { label: '3M', value: '3M', active: period === '3M' },
              { label: '1Y', value: '1Y', active: period === '1Y' },
              { label: 'All',value: 'All',active: period === 'All' },
            ]}
            onPeriodChange={setPeriod}
            height={280}
            footer={
              <>
                <span className="t-ui-footnote" style={{ color: 'var(--text-3)' }}>
                  Since 2026-01-01 · 114 days live
                </span>
              </>
            }
          >
            <div
              className="flex items-center justify-center h-full"
              style={{ color: 'var(--text-3)' }}
            >
              [ Recharts ResponsiveContainer goes here in real page ]
            </div>
          </ChartCard>
        </Section>

        {/* DATA TABLE */}
        <Section title="Data table — sticky header, sortable, keyboard nav">
          <DataTable
            columns={[
              { key: 'ticker',  header: 'Ticker',   sortable: true,  width: '120px' },
              { key: 'qty',     header: 'Qty',      sortable: true,  align: 'right', width: '80px' },
              { key: 'entry',   header: 'Entry',    sortable: true,  align: 'right', render: (v) => fmtPrice(v) },
              { key: 'current', header: 'Current',  sortable: true,  align: 'right', render: (v) => fmtPrice(v) },
              {
                key: 'pnl',
                header: 'P&L',
                sortable: true,
                align: 'right',
                render: (v) => (
                  <span style={{ color: v >= 0 ? 'var(--bull)' : 'var(--bear)' }}>
                    {v >= 0 ? '+' : ''}{fmtINR(v)}
                  </span>
                ),
              },
              {
                key: 'pnlPct',
                header: 'P&L %',
                sortable: true,
                align: 'right',
                render: (v) => (
                  <span style={{ color: v >= 0 ? 'var(--bull)' : 'var(--bear)' }}>{fmtPct(v)}</span>
                ),
              },
            ]}
            rows={TABLE_ROWS}
            initialSort={{ key: 'pnl', dir: 'desc' }}
            onRowClick={(row) => console.log('clicked', row)}
          />
        </Section>

        {/* SIGNAL CARDS */}
        <Section title="Signal cards — retail-pro tear-sheets">
          <div
            className="grid"
            style={{ gridTemplateColumns: 'repeat(3, minmax(0, 1fr))', gap: 16 }}
          >
            <SignalCard
              signal={SAMPLE_SIGNAL}
              priceSeries={SAMPLE_ARC_UP}
              onOpenDetail={(s) => { setSelectedSignal(s); setDetailOpen(true); }}
            />
            <SignalCard
              signal={SAMPLE_SIGNAL_IN_ZONE}
              priceSeries={SAMPLE_ARC_FLAT}
              heldByUser
              onOpenDetail={(s) => { setSelectedSignal(s); setDetailOpen(true); }}
            />
            <SignalCard
              signal={SAMPLE_SIGNAL_CHASE}
              priceSeries={SAMPLE_ARC_UP}
              onOpenDetail={(s) => { setSelectedSignal(s); setDetailOpen(true); }}
            />
          </div>
        </Section>

        {/* EMPTY STATE */}
        <Section title="Empty state — editorial, not cartoon">
          <div
            style={{
              background: 'var(--surface-1)',
              border: '1px solid var(--edge-1)',
              borderRadius: 'var(--r-card)',
            }}
          >
            <EmptyState
              icon={<Radar />}
              title="No signals yet today"
              body="Next scan at 4:15 PM IST. Signals drop after market close when our model processes the day's OHLCV data across 441 tradeable Nifty 500 tickers."
              cta={
                <button
                  type="button"
                  className="t-ui-callout"
                  style={{
                    padding: '10px 18px',
                    background: 'var(--brand)',
                    color: 'var(--brand-fg)',
                    border: '1px solid var(--brand)',
                    borderRadius: 'var(--r-chip)',
                    cursor: 'pointer',
                    fontWeight: 600,
                  }}
                >
                  Check scan status
                </button>
              }
            />
          </div>
        </Section>

        {/* COMMAND BAR TRIGGER */}
        <Section title="Command bar — Cmd-K palette">
          <div className="flex items-center" style={{ gap: 12 }}>
            <button
              type="button"
              onClick={() => setCommandOpen(true)}
              className="t-ui-callout"
              style={{
                padding: '10px 16px',
                background: 'var(--surface-2)',
                color: 'var(--text-2)',
                border: '1px solid var(--edge-1)',
                borderRadius: 'var(--r-chip)',
                cursor: 'pointer',
                display: 'inline-flex',
                alignItems: 'center',
                gap: 8,
              }}
            >
              Open command palette
              <kbd
                style={{
                  background: 'var(--surface-3)',
                  border: '1px solid var(--edge-1)',
                  borderRadius: 3,
                  padding: '1px 6px',
                  fontFamily: 'var(--font-mono)',
                  fontSize: 10,
                  color: 'var(--text-3)',
                }}
              >
                ⌘K
              </kbd>
            </button>
            <span className="t-ui-footnote" style={{ color: 'var(--text-3)' }}>
              Try typing "buy reliance 10" or "signals" or "RELIANCE".
            </span>
          </div>
        </Section>
      </div>

      {/* Drawers / overlays */}
      <SignalDetailDrawer
        signal={selectedSignal}
        priceSeries={SAMPLE_ARC_UP}
        open={detailOpen}
        onOpenChange={setDetailOpen}
      />
      <CommandBar
        open={commandOpen}
        onOpenChange={setCommandOpen}
        tickers={TICKER_ITEMS.map((t) => ({ symbol: t.symbol }))}
        actions={[
          { id: 'scan',    title: 'Run scan now',     subtitle: 'Refresh signals',   icon: <Activity />, run: () => console.log('scan') },
          { id: 'refresh', title: 'Refresh quotes',   subtitle: 'Force WS reconnect', icon: <RefreshCcw />, run: () => console.log('refresh') },
        ]}
        onPlaceOrder={(parsed) => {
          setSelectedSignal({ ...SAMPLE_SIGNAL, ticker: parsed.ticker });
          setCommandOpen(false);
          setTimeout(() => setOrderOpen(true), 200);
        }}
      />
    </div>
  );
}

function Section({ title, children }) {
  return (
    <section style={{ marginTop: 40 }}>
      <h2
        className="t-ui-headline"
        style={{ color: 'var(--text-2)', marginBottom: 16, fontWeight: 500 }}
      >
        {title}
      </h2>
      {children}
    </section>
  );
}
