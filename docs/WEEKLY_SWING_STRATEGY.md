# Weekly Swing — Strategy Document

*Model: `weekly-swing-0094-rank` · Status: **FORWARD-WATCH (paper)** · Inception 2026-07-04*

This is the plain-English, end-to-end description of the Weekly Swing strategy — what it
buys, when, how much, when it sells, and how honest we are about the numbers. Every rule
and value below is taken directly from the frozen config (`models/bhanushali_weekly/config.json`)
and the engine code (`scripts/run_bhanushali_weekly_rank.py`), not from memory.

---

## 1. The one-paragraph version

Once a week, after Friday's close, the strategy scans a large universe of Indian stocks and
looks for a specific setup: a stock in a **rising long-term uptrend** that has just **pulled
back to its trend line and bounced off it with a strong up-week**, and that is **outperforming
the market**. When it finds those, it buys them early the following week, risks a fixed small
slice of capital on each, sells half at a set profit target, lets the rest run behind a trailing
stop, and caps every trade at about three months. It makes all its decisions on **weekly** bars
and only acts **once a week**.

It is a **trend-following swing system**, not a day-trading or intraday system.

---

## 2. What it can buy (the universe)

- **Point-in-time Nifty-500 members** — the large- and mid-cap segment of the Indian market,
  using each stock's index membership *as it was on that historical date* (no hindsight about
  who's in the index today).
- Liquidity is handled through **cost**, not a hard cutoff: bigger, more liquid names pay less
  slippage; smaller names pay more (see §9). Each stock's 20-day average traded value (ADV)
  decides its liquidity tier.

---

## 3. The core idea

Three things have to be true at the same time for a buy. Think of them as **trend, pullback,
and leadership**:

1. **Trend** — the stock is in a durable, *rising* uptrend.
2. **Pullback + bounce** — it recently dipped back toward its trend line and closed the week
   back above it, with a strong (green) week — i.e. buyers showed up right where they should.
3. **Leadership** — it is beating the market (Nifty-50), not just drifting up with it.

The strategy is deliberately picky. In most weeks only a handful of stocks pass all three.

---

## 4. The entry rules (exact)

All of these are measured on **weekly bars** (each bar = one Mon–Fri), at the **Friday close**
of the "setup week."

| # | Rule | Exact condition |
|---|------|-----------------|
| 1 | **Rising trend** | The **44-week** simple moving average (SMA) of the weekly close is sloping **up by at least 3% over the last 13 weeks**. |
| 2 | **Above the trend** | The weekly close is **above** the 44-week SMA. |
| 3 | **Pullback / touch** | The week's **low dipped to within 7%** of the 44-week SMA (it came back and tested the trend line) — but still **closed above** it. |
| 4 | **Quality green week** | The week closed **higher than it opened**, *and* closed in the **upper half** of the week's range (strong finish, not a fade). |
| 5 | **Relative strength (CRS)** | The stock's **relative-strength line** vs the Nifty-50 (RS = stock's weekly close ÷ Nifty-50) is **above its own 40-week SMA** — i.e. it has been leading the market, not lagging. |

If all five are true on a stock's Friday, it becomes a **signal** for the **following week**.

### How the buy actually happens

- The signal is valid for the **whole next trading week (Mon–Fri)**.
- Each day that week, if the stock's **opening price is inside the setup week's range**
  `[setup-week low, setup-week high]`, you **buy at that open**. This is the "buy it early, near
  where it based" rule — you don't chase it if it gaps far above the range.
- The **buy price = that day's open**. If the open never falls inside the range all week, the
  signal simply **expires with no trade** (no harm done — capital was never committed).

---

## 5. How much it buys (position sizing)

- **Fixed risk of 2% of current equity per trade.** Equity = your cash + the value already in
  open positions.
- The **stop-loss is the setup week's low.** Your risk per share = `entry − stop`.
- **Shares = (2% × equity) ÷ (entry − stop)`**, rounded down.

So a wide stop → fewer shares, a tight stop → more shares, but the **rupees at risk are always
the same 2%**. Leverage (E-margin) can change how many positions you can *afford*, but it never
changes the 2% you *risk* — the position sizer on the dashboard enforces exactly this.

---

## 6. When it sells (the four exits)

Every decision below is **made at the weekly (Friday) close and executed at Monday's open.**

1. **Stop-loss** — if the weekly close falls to or below the **setup-week low**, exit the whole
   position. (In live trading you can place this as a resting stop order at the broker so it
   also protects you *intra-week*.)
2. **First target (+2R)** — when price reaches **entry + 2×(entry − stop)**, **sell half** the
   position and lock in the gain.
3. **Trailing stop on the runner** — the remaining half trails a **ratchet** stop: it rises to
   `20-day SMA × (1 − 4%)` and never moves back down. If a weekly close prints **below** that
   trail, the runner is sold. This is the one place a **daily** average (the 20-day SMA) feeds
   the system; it's sampled at each Friday.
4. **Time cap** — any position still open after **13 weeks (~3 months)** is closed. Capital
   should be working, not sitting in stalled trades.

**No rotation.** The strategy holds **one position per name** and never adds to a winner or
swaps a held name for a fresh one — a name you already own is never re-bought.

---

## 7. Which signals get funded first (CRS ranking)

In a good week the scan may fire more signals than your cash can fund. The strategy does **not**
pick randomly or alphabetically — it funds the **strongest leaders first**.

- Each signal carries a **CRS distance** = `RS ÷ (40-week SMA of RS) − 1` — how far above its own
  trend the stock's relative-strength line sits.
- Candidates are funded in **descending CRS distance** (strongest first) until the cash runs out.
- On the dashboard the **top 5 by CRS are flagged Grade A**; the rest are Grade B. This ordering
  was the single change that took the book from Sharpe 0.90 to **1.13** (finding 0038), and it
  survived an adversarial ordering probe (strongest-first best, weakest-first worst).

---

## 8. The weekly rhythm

| When | What happens |
|------|--------------|
| **Saturday 6 PM IST** (cron) | Refresh all daily prices → build weekly bars → run the scan → publish the week's buy list, updated stops/trails, and any sell instructions. |
| **Mon–Fri** | Buy new signals at the open when in-range; execute any sells decided at Friday's close on Monday's open. The dashboard shows **live daily prices** against the fixed levels all week. |
| **Next Saturday** | Repeat. Between runs: log and leave it alone — no intra-week decision changes. |

Weekly cadence is a **decision** cadence, not a data limitation: the bot ingests every daily
price on each run; it just chooses to act only once a week, exactly as it was tested.

---

## 9. Costs and taxes modelled

Per leg (buy and sell each), the backtest charges real frictions:

- **Brokerage** 0.03% + **STT** 0.10%.
- **Slippage by liquidity tier**: large-cap 0.05%, mid-cap 0.22%, small-cap 0.40%, plus a
  0.10% market-impact add-on when an order exceeds 0.5% of the stock's daily traded value.

The headline returns below are **after** all of these. Because holds are under a year, gains are
**short-term (STCG)** and taxed accordingly — that is a real drag on take-home returns and sits
on top of the transaction costs above.

---

## 10. The numbers — and the honesty around them

Backtest, **corrected universe, 2017–2026, in-sample**, after transaction costs:

| Metric | Value |
|--------|-------|
| Net CAGR | **+24.7%** |
| Net Sharpe | **1.13** |
| Max drawdown | **−42.4%** |
| Win rate | **59.2%** |
| Sharpe 95% CI low | +0.47 |
| Deflated Sharpe (DSR) | **0.894** |

**Read this carefully — the caveats are the point:**

- **In-sample.** These numbers were measured on the same history used to build the strategy.
  They are the *best case*, not a promise.
- **Not certified.** Our bar to call an edge "real" is DSR > 0.95. This scores **0.894** — the
  closest the whole research program has come, but still **under the bar**. That's why it is a
  **forward-watch paper book**, not live capital.
- **Deep drawdowns are normal.** A **−42%** peak-to-trough happened in the backtest and can
  happen again. Returns are **lumpy** — a few strong-trend years carry the total, with flat
  stretches in between.
- **No live track record yet.** The forward paper record started **2026-07-04**. The only thing
  that can actually certify this strategy is **out-of-sample forward performance** — real weeks,
  logged honestly — not any in-sample number.

---

## 11. A worked example

Suppose on a Friday, stock **XYZ** passes all five entry rules. Setup-week low **₹100**, high
**₹110**. You have **₹5,00,000** equity.

- **Stop** = ₹100. **Risk/share** = entry − 100.
- Monday XYZ opens at **₹104** — inside [100, 110] → **buy at ₹104**.
- Risk/share = 104 − 100 = **₹4**. Shares = (2% × 5,00,000) ÷ 4 = 10,000 ÷ 4 = **2,500 shares**
  (₹2.6L deployed; ₹10,000 = 2% at risk).
- **Target (+2R)** = 104 + 2×4 = **₹112** → at ₹112 you **sell 1,250 shares** (half).
- The other **1,250** ride a trail at `20-day SMA × 0.96`, ratcheting up, until a weekly close
  breaks it — or the **13-week cap** closes it — or the stop is hit first.

---

## 12. Glossary

- **SMA (simple moving average)** — the plain average of the last N closes; the trend line.
- **44-week SMA** — the long-term trend, on weekly bars (the entry filter).
- **20-day SMA** — a shorter, daily average used only for the runner's trailing stop.
- **R** — "one unit of risk" = entry − stop. "+2R" means a gain of twice what you risked.
- **CRS (comparative relative strength)** — the stock's price divided by the Nifty-50; rising
  CRS = the stock is beating the market.
- **DSR (deflated Sharpe ratio)** — a Sharpe ratio penalised for how many strategies we tried;
  our go-live bar is 0.95.
- **Forward-watch / paper** — traded on paper and logged, not with real money, until the forward
  record earns promotion.

---

*This document describes a research strategy on paper. It is not investment advice, and past or
backtested performance does not indicate future results.*
