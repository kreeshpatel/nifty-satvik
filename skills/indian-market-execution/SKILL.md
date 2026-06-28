---
name: indian-market-execution
description: >
  Indian NSE market mechanics, transaction costs, compliance, and execution
  realism for the NiftyQuant long-horizon strategy. Covers STT, brokerage,
  micro-costs, circuit limits, T+1 settlement, NSE holidays, F&O membership,
  tick/DPR guards, SEBI compliance language, and tax treatment — grounded in
  the actual code (config.py, execution_model.py, signal_tracker.py) and the
  Phase-1 wiring audit.

  Use when the topic involves: Indian market, NSE, STT, circuit limit, F&O,
  lot size, settlement, stamp duty, SEBI, transaction tax, delivery cost,
  market hours, tick size, circuit breaker, STCG, LTCG.

triggers:
  - indian market
  - NSE
  - STT
  - circuit limit
  - F&O
  - lot size
  - settlement
  - stamp duty
  - SEBI
  - tick size
  - STCG
  - LTCG
  - circuit breaker
  - T+1
  - transaction cost
---

# Indian Market Execution — NiftyQuant Long-Horizon

This skill covers every Indian-market-specific execution detail that matters
for the long-horizon scanner. It is complementary to, and does not duplicate,
`skills/kite-execution` (which covers Kite OAuth, fill realism, and live edge
cases). That skill owns the broker layer; this skill owns the regulatory and
market-structure layer.

*Adapted from the Apache-2.0 `indian-algo-trading` skill (v1.1.14, repo:
`algo_ai_skill/plugins/indian-algo-trading`). No verbatim chunks copied.
Indian-market facts cross-checked against SEBI/NSE schedules (FY25-26) and
reconciled against our live code.*

---

## 1. Transaction cost model — what we actually charge

This is the load-bearing number for post-tax ΔSharpe in every harness
verdict. Every component must be deliberately modelled or deliberately
omitted. **Do not change this table without re-running a golden-master
regeneration.**

### The five cost buckets

| Cost | Rate | Applied | Code location |
|---|---|---|---|
| Brokerage | **0.03% per leg** (Zerodha: ₹20 flat or 0.03%, whichever is lower; at our ₹1–3L positions the % almost always wins) | Both buy and sell | `config.BROKERAGE_PCT = 0.0003` |
| STT (Securities Transaction Tax) | **0.10% per leg** | Both buy AND sell on **delivery equity** | `config.STT_PCT = 0.001`; `config.delivery_leg_cost()` applies on both legs |
| Exchange txn charge | ~0.003% | Both legs | **Omitted from backtester** — documented as immaterial; ~3.5 bps round-trip |
| SEBI turnover fee | ~0.0001% | Both legs | **Omitted** — immaterial (~0.2 bps) |
| Stamp duty | ~0.003% buy-side only | Buy leg | **Omitted** — electronic, small |
| Tiered slippage | 0.05% / 0.22% / 0.40% | Entry and exit | `execution_model.SLIPPAGE` (LARGE / MID / SMALL) |
| Market impact (sqrt-law) | η=1.0 × σ_daily × √(value/ADV) per leg | When position > 0.5% of 20d rupee ADV | `config.IMPACT_ETA`, `long_horizon/backtest/portfolio.py _slip` |
| Position cap | 5% of name's 20d rupee ADV | Hard cap on shares | `config.MAX_ADV_PARTICIPATION = 0.05` |

### STT — the most commonly misunderstood line item

STT on **equity delivery** is 0.10% on **every leg** — both the buy and the
sell. This is different from:
- Equity intraday: 0.025% **sell-side only**
- Equity futures: 0.05% sell-side (tripled in Budget 2024 from 0.02%)
- Index futures: 0.02% sell-side

`config.delivery_leg_cost(notional)` is the single source of truth for one
leg of a delivery trade: `notional × (BROKERAGE_PCT + STT_PCT)` = 0.13% per
leg. Both the paper broker and the backtest engine call this function — they
cannot drift apart.

**The source `indian-algo-trading` references delivery STT as "buy-side,
paid on both buy and sell" (their Table §1 is internally inconsistent).
Resolved against the actual SEBI/Zerodha schedule: delivery equity is 0.1%
on EACH leg. Our code is correct.**

### Round-trip friction by tier

| Tier | ADV criterion | Slippage/leg | Total round-trip (slip+cost only) |
|---|---|---|---|
| LARGE | ≥ ₹50 cr/day | 0.05% | ~0.36% |
| MID (typical holding) | ₹5–50 cr/day | 0.22% | ~0.70% |
| SMALL (below universe floor) | < ₹5 cr/day | 0.40% | ~1.06% |

*Plus market impact if position > 0.5% ADV. The ADV ≥ ₹5 cr filter means
the SMALL tier should never enter the live book; it exists as a safety rail.*

The average long-horizon trade earns ~2.9% mean return (research backtest).
A 2× cost stress test still shows 26.5% CAGR / 1.01 Sharpe (STRATEGY_FULL.md
§10.3). The micro-costs (exchange + SEBI + stamp ≈ 3.5 bps round-trip) are
immaterial at this edge magnitude; documenting their omission here keeps the
decision conscious, not accidental.

---

## 2. Circuit limits — what they mean for a held long position

The scanner is a **long-only, close-only, 63-day-hold delivery strategy**.
This section describes what circuits do to holdings, not to intraday shorts.

### Individual stock circuit bands

NSE imposes percentage-based bands from the previous day's close:

| Band | Move threshold | Effect |
|---|---|---|
| 5% | ±5% | Available for some names (e.g., SME segment) |
| 10% | ±10% | Most Nifty-500 names; 45-min halt if triggered |
| 20% | ±20% | Standard maximum for most equity names |
| No circuit | F&O-listed names | Index futures / large-cap options names have no individual circuit |

**For a held long that hits the lower circuit:** the stop fires at the circuit
price (usually at or below the ATR stop). The exit order queues at that price.
If the next session the halt lifts, the order executes; if the name locks
limit-down multiple sessions, the position ages toward the 63-day hard cap
before a fill is possible.

**Current code behaviour:** `signal_tracker` evaluates the stop on the
daily close. If close ≤ stop, it books the exit at `min(open, stop)` (the
gap-fill fix from W-05, Phase-1, commit b653f52). For a circuit-locked name,
open and close converge to the circuit price — the exit is recorded at that
level regardless of whether a counterparty fill was actually possible. This
is realistic for normal lower-circuit events; the "no fill in a 5-day
lock-limit-down" scenario remains unhandled.

**Operational note from the audit:** `execution_model.is_circuit_day()` flags
days where `|close − open| / open > 10%` — a coarse intraday-volatility heuristic,
not a precise circuit-lock detector. Do not rely on it for exit logic. The W-05
fix in `signal_tracker` is the authoritative exit path.

**F&O-only universe (open decision):** names listed on NSE F&O have no
individual circuit limits. A future universe restriction to F&O-listed names
would eliminate the circuit-lock tail risk on holdings. This is listed as an
open decision in STRATEGY_FULL.md §17, gated on PIT F&O membership data
(currently being built as part of the vol-carry arc). Do not implement this
restriction until the F&O membership PKL is complete and tested.

### Market-wide circuit breakers (index-level)

| NIFTY50 / SENSEX decline | Halt |
|---|---|
| −10% | 1 hour (or to 3:30 PM if triggered after 2:30 PM) |
| −15% | 2 hours (or to 3:30 PM) |
| −20% | Market closes for the day |

For a 63-day-hold strategy, a single-day market halt does not trigger any
scanner action. The cron runs at 4:15 PM IST; if the market closed early,
the most-recent close prices are the halt prices. The signal tracker ages
positions normally on that day's data.

---

## 3. Market hours and the scanner's position in the day

| Phase | Time (IST) | Scanner action |
|---|---|---|
| Pre-open | 9:00–9:15 AM | No action |
| Regular session | 9:15 AM–3:30 PM | No action (EOD only) |
| Post-close | 3:30–4:15 PM | yfinance OHLCV settles; cron begins at ~4:15 PM |
| Scanner run | 4:15 PM | `.github/workflows/cron-scanner.yml` → `long_horizon_cron.py` |
| After-market orders (AMO) | 3:45 PM–8:57 AM next day | Available for manual trade placement via Kite |

**The scanner signals are generated from the closing price of the current
session.** The published entry is `close(t) × (1 + base_slippage)` —
indicative only. The actual fill is the **T+1 open**. The buy window is T+1
to T+3 (three trading sessions); signals older than T+3 are stale.

`config.MAX_ENTRY_RR_FLOOR = 1.2` defines the limit price beyond which the
R:R has decayed to an unacceptable level. This is advisory guidance surfaced
to the manual trader as "Buy LIMIT <= ₹X" — it does not gate the backtest.

After-market orders placed via Kite queue for the pre-open auction the
following session. For the typical long-horizon entry (market order at open
or a limit just above the previous close), AMO is the practical mechanism
when the owner is not available at 9:15 AM.

---

## 4. T+1 settlement and what it means for cash management

All NSE equity delivery trades settle on **T+1**: payment debits (on buy) and
credits (on sell) are applied one business day after the trade date. NSE
Nifty-500 names are also eligible for optional **T+0 settlement** (same-day),
but this is rarely used and has no bearing on the signal scanner or backtest.

**Implications for the paper trading model:**
- Proceeds from an exit on day D are not available for new entries until D+1.
- The paper book (`paper_portfolio.json`) tracks `cash` and `equity_value`
  separately. The backtest engine does not model settlement lag (it assumes
  instant re-deployment of exit proceeds). This is a minor optimism in
  a 63-day-hold strategy where turnover is ~154 trades/year and same-day
  reinvestment pressure is low.
- If the owner is managing live capital: sell proceeds from T are available
  for new buys starting T+1 morning. Do not size a new entry that requires
  today's sell proceeds if settlement has not occurred.

---

## 5. NSE holidays and trading-day accounting

The signal tracker (`signal_tracker.py`) ages positions in **trading days**,
not calendar days. The hold period (min 10 / max 63 trading days) is
therefore calendar-invariant with respect to holidays and weekends.

`config.NSE_HOLIDAYS` contains the holiday list for the relevant years.
`config.WEAK_MONTHS = [7]` (July: 25.5% historical WR) is a seasonal
observation, not a hard entry gate — it is a hypothesis to be monitored, not
a wired filter.

The GitHub Actions cron (`.github/workflows/cron-scanner.yml`) runs on
`cron: "45 10 * * 1-5"` (10:45 UTC = 4:15 PM IST, weekdays). It does NOT
automatically skip NSE holidays. If the exchange is closed, yfinance returns
no new OHLCV bar for that date; the incremental updater handles this
gracefully (it will not push a row without data, so position ages do not
advance on holidays). Verify this in the incremental update logic before
relying on it.

**Practical rule:** always check the NSE holiday calendar before any live
order placement. Do not assume Monday-to-Friday = 5 trading days.

---

## 6. Tick size and DPR — live execution guards

These matter for **Kite order placement**, not for the backtest. The
backtest assumes fills at the modelled prices; Kite's OMS will reject
orders outside these bounds.

### Tick size

Every NSE equity instrument has a minimum price increment. For most
Nifty-500 equities: **₹0.05**. Low-priced stocks may use ₹0.01.

The F2 stop-rounding bug (found in the audit, fixed in `execution_model.round_stop_price`)
was exactly this: `round(raw_stop, 2)` can give a stop that coincides with
or exceeds the entry price on penny stocks. The fix adds a ₹0.01 floor
below entry. For live order placement, also round to the instrument's tick:

```python
def round_to_tick(price: float, tick: float = 0.05) -> float:
    """Round to nearest valid NSE tick. Call on every Kite order price."""
    return round(round(price / tick) * tick, 2)
```

Never hardcode `tick = 0.05`; read it from Kite's instrument master
(`kiteconnect.get_instruments("NSE")`) for the specific symbol.

### Daily Price Range (DPR)

The DPR is the exchange-set order price band for the day:
`[prev_close × (1 − circuit%), prev_close × (1 + circuit%)]`.

Kite's OMS rejects limit orders and stop-loss trigger prices outside the DPR
before they reach the exchange. This affects our wide ATR stops and percentage
targets in two realistic scenarios:

1. **Deep ATR stop on a 10%-band name:** a stop at −22% for a name with a 20%
   circuit will be DPR-rejected. This is unlikely at 3.5× ATR on the target
   names but possible after a large recent gap.
2. **Target >20% on a 20%-band name:** the profit-target limit order will be
   rejected on the first day it's placed; re-place when the DPR shifts.

**Current code:** no DPR validation exists in the signal emitter or paper
broker. For live order placement, validate manually or add a Kite-API-backed
pre-flight check in `refresh_kite_session.py` / the order route.

The rule: when placing a Kite order with a stop or target far from the
current price, check the DPR from the previous close and the name's circuit
band. Place AMO with a DPR-compatible limit; re-place if the band shifts.

---

## 7. F&O membership — future universe decision

A name listed on NSE F&O (equity futures and options) has **no individual
circuit limit**. This eliminates the scenario where a held position locks at
the lower circuit for multiple sessions with no exit.

F&O membership is also relevant to the vol-carry arc (harvesting IV>realized
on individual stock options) and to the delivery-% data (NSE reports
delivery-% only for equity segment, not F&O).

**Current status (as of 2026-06-27):**
- `src/data/fo_bhavcopy.py` can ingest F&O bhavcopy data (Phase-0 of the
  vol-carry arc).
- PIT F&O membership data (which names were F&O-listed on which dates) is
  not yet built into `fundamentals_pit_screener.pkl`.
- The live scanner does NOT restrict to F&O names.

**Do not add an F&O-only universe restriction until:**
1. PIT F&O membership data is complete and tested.
2. A backtest confirms the restriction does not materially reduce trade
   count or CAGR (removing non-F&O names from a top-15 cross-sectional
   rank can change the portfolio composition significantly).
3. A golden-master regeneration is run.

---

## 8. SEBI compliance language — what we must and must not say

NiftyQuant is a paid signal service. SEBI regulations on algorithmic trading
and investment advisory apply. Use this language consistently in the UI, in
email communications, and in any documentation shown to users:

**Correct language:**
- "model-generated signal"
- "research recommendation"
- "decision-support output"
- "indicative entry level"
- "research backtest — never traded live"
- "paper trading observation period"
- "past performance does not guarantee future results"

**Prohibited language:**
- "guaranteed returns" (any form)
- "SEBI-registered advisor" (we are not — if this changes, update this section
  immediately and add the SEBI registration number to the footer)
- Any specific CAGR / return projection to a user that implies it is a
  guarantee or a live track record (the 26.1% gross / 23.1% after-tax is a research backtest
  number; it must always be labeled as such — the previously-reported 30.3% is superseded, 2026-06-27)
- "buy this stock" as a direct imperative without a disclosure

**SEBI OTR (Order-to-Trade Ratio):** maximum 50:1. The long-horizon scanner
generates one signal batch per day; the volume of orders placed by users from
those signals is far below this threshold. This is not a concern for the
current scale (~10 users, ~15 signals/day).

**Upfront margin collection:** brokers must collect full margin before order
execution. The OrderPad in the dashboard checks `overMargin` (Kite margins
API) before surfacing a Buy button. Backend also validates margin before
forwarding to Kite. Do not bypass this check.

---

## 9. Tax treatment — what matters for our holding horizon

The long-horizon strategy holds for **min 10 / max 63 trading days (~2–3
calendar months)**. This is firmly short-term capital gains territory.

### STCG (Short-Term Capital Gains) — applies to all our trades

Equity delivery held **< 12 months**: taxed at **20% + 4% cess = 20.8%
effective** (Section 111A).

The backtest's post-tax reporting should apply this rate. Verify that the
backtester's CAGR and Sharpe are computed on **net-of-cost** returns (slippage
+ STT + brokerage), and that any "post-tax" headline applies the 20.8% STCG
rate on realized gains — not a generic 15% or 30% assumption.

### LTCG (Long-Term Capital Gains) — does NOT apply to the core strategy

Equity delivery held **≥ 12 months**: 12.5% tax with ₹1,25,000 annual
exemption (Section 112A).

The 7.5 percentage-point STCG→LTCG gap is not exploitable with our current
63-day hard cap. A "let winners run past 365 days" overlay is a registerable
hypothesis (the mechanism is fully explainable and the tax saving is
quantified) but it would:
- Extend hold period and turnover
- Require a different exit logic (no 63-day cap)
- Need to clear the full promotion bar (ΔSharpe≥+0.10, ΔCalmar≥+0.05,
  2022-26 positive, WF≥60%)

Register before building; do not implement ad-hoc.

### Tax-loss harvesting

No wash-sale rules apply in India. Losses in a FY can be harvested (sell to
realise the loss, repurchase immediately) and offset against capital gains.
The paper book (`paper_portfolio.json`) does not currently track tax lots.
This is a future accounting feature, not a scanner concern.

### F&O taxation (future vol-carry arc)

F&O gains are taxed as **business income** (slab rates, typically 30% for
individuals in a high bracket), not capital gains. This is less favourable
than delivery equity LTCG (12.5%) and complicates the vol-carry arc's
post-tax returns comparison against the equity momentum leg. Account for this
when sizing the vol-carry sleeve relative to the equity leg.

---

## 10. Tick-size and DPR emission checklist (pre-order)

Before placing any live order via Kite from a scanner signal:

```
1. Round entry, stop, and target to the instrument's tick (read from Kite master,
   default 0.05 for most Nifty-500 names).

2. Confirm stop price <= prev_close * (1 - circuit_band) is ABOVE DPR lower bound,
   i.e., stop is inside [prev_close * 0.80, prev_close * 1.20] for a 20%-band name.
   If not, the stop order will be OMS-rejected; place a market stop-loss order
   for the first session instead.

3. Confirm target <= prev_close * (1 + circuit_band). If target > DPR upper bound,
   place a limit at the DPR cap and re-raise after the band shifts.

4. Confirm the name is not currently circuit-locked (bid=ask at the circuit price,
   zero volume). If locked, do not place a new order; wait for the halt to lift.

5. For AMO (after-market order, placed 3:45 PM–8:57 AM): it queues for the
   next session's pre-open auction. Use a limit price ≤ max_entry (the R:R floor
   from MAX_ENTRY_RR_FLOOR=1.2, surfaced by the scanner as the "do not chase"
   ceiling).
```

---

## 11. Key distinctions from the v1/intraday context

The v1 strategy was a 14-day LightGBM swing. The long-horizon strategy is
a 63-day cross-sectional delivery strategy. Several v1-era concepts are
structurally different here:

| Topic | v1 (14-day swing, DEPRECATED) | Long-horizon (current) |
|---|---|---|
| Entry timing | Same-day score→next-open fill | Close(t) indicative → T+1 open fill (T+1 to T+3 buy window) |
| Stop type | ATR×1.5, intraday evaluated | ATR×3.5, close-only + gap-fill (W-05 fix) |
| Circuit concern | Mostly intraday volatility | Lower-circuit lock on held position, multi-session |
| F&O relevance | None | Future universe decision (open) |
| Tax | STCG at 20.8% | STCG at 20.8% (LTCG inapplicable at 63-day cap) |
| Slippage model | Volume-share proxy (flawed) | ADV-tier (₹/day rupee turnover) + sqrt impact |

Do not import v1 intraday execution concepts (DPR enforcement at signal time,
gamma expiry considerations, stop-hunt windows) into the long-horizon flow.
These are structurally inapplicable.

---

## 12. Open items from the Phase-1 audit

Items where Indian-market mechanics intersect with open engineering work:

| ID | Issue | Status |
|---|---|---|
| W-04 | Financials sector silently excluded (D/E = NaN for banks/NBFCs → always solvency-dropped) | Open; policy decision deferred; cron logs `solvency_dropped_financials` |
| W-01 | VEDL-class demerger quarantine (yfinance back-adjusts demergers as splits; inflates sma200_slope) | Fixed (b653f52); root fix (clean_ohlcv not back-adjust demergers) deferred to cloud backtest gate |
| F&O universe | F&O-listed names have no individual circuits; restricting universe would remove circuit-lock tail risk | Open; gated on PIT F&O membership data |
| DPR guard | No programmatic DPR validation in signal emitter or Kite order path | Open; medium priority; manual checklist in §10 above |
| LTCG overlay | "Let winners run past 365d" for 7.5pp tax saving | Hypothesis only; not registered; do not build |

---

*Grounded in: `config.py` (BROKERAGE_PCT, STT_PCT, delivery_leg_cost, ADV tiers,
IMPACT_ETA, MAX_ENTRY_RR_FLOOR, NSE_OPEN/CLOSE_TIME), `src/trading/execution_model.py`
(SLIPPAGE tiers, round_stop_price, is_circuit_day), `long_horizon/STRATEGY.md` (cost table,
universe spec), `long_horizon/audit/wiring_issues.md` (W-01, W-04, W-05),
`skills/kite-execution/SKILL.md` (session lifecycle, fill model, edge cases),
`long_horizon/STRATEGY_FULL.md §10.3` (2× cost stress test). Source: adapted from
Apache-2.0 `indian-algo-trading` skill v1.1.14 (references/indian-market.md,
references/tax-optimization.md, references/execution-alpha.md — intraday/F&O
sections deliberately excluded as inapplicable to this strategy). Last verified:
2026-06-27 (Phase-1 audit, commit b653f52).*
