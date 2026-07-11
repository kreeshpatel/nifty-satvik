# The Bhanushali Swing Strategy — Full Reference

*A complete, detailed reference for the swing method taught by Siddharth Bhanushali, how we
reconstructed it into the live `weekly-swing-0094-rank` book, and what we honestly measured when we
tested it. Sources: the transcript capture in [`research/bhanushali_swing_rules.md`](../research/bhanushali_swing_rules.md),
the engine scripts (`scripts/run_bhanushali_*`), and findings `0020`–`0038`, `0095`–`0096`.*

This document has three parts, kept deliberately separate so they never blur:

- **Part I — The method as taught.** What Bhanushali actually teaches.
- **Part II — Our live implementation.** The exact rules of the book running on the dashboard.
- **Part III — The honest evidence.** What carried an edge on our data and what did not.

---

# Part I — The method as taught

Bhanushali teaches swing trading as a **6-step discipline**, not a signal. The signal is a small
part; most of the teaching is mindset, risk, and process. The through-line: *trade a clearly rising
trend, buy strength pulling back (not weakness), respect risk absolutely, give winners room, and
treat the exit as where money is actually made.*

## 1. Mindset (Step 1)

- **Losses are part of the game — be a learner, not a blamer.** Every loss is feedback. Trade to
  *learn*, not to *win*.
- **Detach from money, attach to mastery.** Money is a by-product. Attachment makes you hold losers,
  book winners early, and over-size.
- **Set realistic expectations.** The best compounders run ~12–20%/year (Buffett ~19–20% over
  decades). Consistent 12–20% puts you in the top ~5%. Expecting 20%/month guarantees frustration.
  The goal is to *become a consistent, disciplined trader*, not to "make a crore." It's a marathon.

## 2. Risk management (Step 2 — "execute like a pro")

- **Risk no more than 1–2% of capital per trade.** On ₹1L, that is ₹1,000–2,000 of risk per position.
- **Set the stop the moment you enter** (his rule: within ~5 seconds). Stops are never optional.
- **Never lose *big*.** Losses are inevitable; large losses are not. At 1–2% risk, ten losses in a
  row still leave 80–90% of capital — a comeback is possible. **Survival is the real success.**
- **Exit a loser without hesitation** when the chart says so (candle low broken, support broken, MA
  broken). The biggest losses come from *hoping*, not from price falling.
- **Don't fear the "stop-loss hunt."** Institutions trading thousands of crores will not move a
  large-cap to take a retail-sized stop.
- **Cautionary tales of no-stop holding:** Reliance Infra, DLF, Suzlon, Yes Bank (blue-chip →
  penny), Satyam (delisted). A stop would have saved each.

## 3. The strategy on the chart

### The trend filter — the watchlist

- **44-period Simple Moving Average (SMA).** Trend timeframe is **weekly** for the RSI system; the
  pullback system uses the **daily** 44-SMA (weekly optional as you advance).
- **Only trade a *rising* 44-SMA.** A falling MA means a downtrend — avoid. Analogy: bet on the
  student whose marks rose 55→94 every year, not the one falling 99→38.
- **It must be a *visible, sustained* uptrend — not a marginal up-tick.** He stresses "clearly
  rising." (Our tests confirm this matters enormously — see Part III.)
- **Weekend routine:** over the weekend (Fri 3:30pm → Mon 9:15am), scan the universe (Nifty
  100/200/500 or a screener), keep only the **clearly-rising-MA** names in a watchlist (~25–50
  stocks). Then Mon–Fri, check only those — about 15 minutes a day.

### The two entry setups

1. **44-SMA pullback (the core setup).** Price pulls back to the rising 44-SMA (support) and forms a
   **green candle** → **buy ₹1 above that candle's high**, **stop ₹1 below its low**.
2. **RSI setup.** On the daily chart, RSI(14) with bands at **75 / 35**. Wait for RSI to dip **below
   35**, then tick back up **with a green candle** → **buy ₹1 above the green candle's high**, **stop
   ₹1 below its low**. (He uses 35, not the classic 30, because in a bull trend stocks often bounce
   from 33–35.)

- **Targets:** **1:2 and 1:3** reward-to-risk — 2× and 3× the entry-to-stop distance. Entry ₹100 /
  stop ₹90 → book at ₹120 and ₹130.
- **Entry is always a stop order above the candle high**, never a market buy on the close.

## 4. Patience & timing (Step 4)

- **Wait for the setup; don't force trades.** "Not every ball is hit for six." No setup → skip the
  day. Use resting limit/stop orders (buy-above-high *is* a resting order — set it and leave it).
- **Missed trades are fine.** Don't chase. Patience is the ultimate weapon.

## 5. Position management & exits (Step 5)

- **Check open positions at most twice a day.** Watching more only feeds emotion.
- **Hold ~3–10 days for the target.** **Do not exit on a single red day or a shooting star** — one
  bearish candle doesn't move the economy. Exit only at **target or stop**, unless you have a defined
  trailing rule.
- **Optional trailing stop** to lock profit as price rises — ideally ratcheting up to each new
  **higher swing low** (see §8).
- **The exit is where money is made.** Focus as much on *when to sell* as on *what to buy*.

## 6. RSI — the deeper reading

RSI (Wilder, 1978) measures whether a market is *tired* (overbought) or *oversold*; range 0–100,
period 14.

- **Zones:** 0–30 oversold (a bounce is *possible*, not guaranteed); 30–70 neutral (wait); 70–100
  overbought (a pullback is *possible*).
- **The 50-line is trend context, not an entry.** Consistently above 50 = bullish regime. Don't
  trade every crossover — use it to read the stock's environment.
- **Do NOT blind-short 70/75.** In a strong uptrend, price crosses 70/75 repeatedly and keeps
  rising. Overbought ≠ sell.
- **Bullish divergence:** price makes a lower low, RSI a higher low → momentum strengthening → buy
  (confirm with a green candle).
- **Hidden (continuation) divergence:** in an uptrend, price makes a higher low but RSI a lower low →
  the move has room to continue.
- Divergence must be **confirmed by price action** — never traded alone.
- **Practice:** mark 100 charts per strategy before risking capital.

## 7. Combining tools ("RSI alone is raw rice")

No single indicator makes money. He teaches RSI **with**: Bollinger Bands (buy the lower band in a
bullish regime), Fibonacci (buy the 50% retracement in a confirmed trend), **volume** (buy the
breakout on a high-volume candle), and price action (double bottom, trendline break, support).
"Indicators don't make money; position sizing and risk management do."

## 8. Swing structure & Dow Theory (the foundation under everything)

- **Charles Dow's swing high / swing low is the base of all technical analysis.** Price moves in
  **swings**, never straight — an up-swing, then a down-swing, repeating.
- **An uptrend = Higher High + Higher Low.** A higher low forms first; the higher high is *confirmed*
  only when price breaks the prior swing high. Downtrend = lower high + lower low.
- **Price action is the father of every indicator** — MAs, RSI, patterns all derive from swing
  structure. Every breakout is a swing-high break; every support is a swing low.
- **The retest (one of the best entries).** In an established uptrend, when price returns to a
  **proven prior swing low** (a support it has already respected) and holds → a high-quality buy —
  *proven* price, not a fresh breakout. Repeated tests of one zone = smart-money accumulation.
- **The "magical placement":** a swing-low retest that **coincides with a rising 44-SMA** → buy above
  the green candle's high, stop below its low, target 1:2 / 1:3. This is the heart of the method.
- **Swing Failure Pattern (SFP / trap):** a breakout that fails — a strong green breakout candle then
  a big red candle back into the range — institutions trapping breakout-buyers. If long, exit; it is
  also a short setup. (Reverse for a failed breakdown that snaps back = buy.)

## 9. Volume & HVC — "Price is God, but Volume is the Voice of God"

- **Volume = shares traded in a day** (one buy+sell = 1 unit). It shows **activity, not direction** —
  direction comes from price; volume **confirms the conviction** behind the move.
- **Big volume spikes are institutional footprints.** Retail is noise.
- **Volume should expand in the trend's direction** — an uptrend is healthy when green candles carry
  heavy volume and red candles light. The "rocket" needs the fire underneath.
- **HVC — High Volume Candle** (candle thickness ∝ volume). The setups:
  - **HVC at support / at the rising 44-SMA → institutional buying** → buy above its high.
  - **HVC breakout** of a tight base → momentum-continuation buy.
  - **HVC at resistance → institutional selling** → avoid.
- **Big-candle stop rule:** if the HVC is very large (6–8% on the day), don't stop below its full low
  — put the **stop at 50% of the candle's range** (₹1 below the midpoint). Still buy above the high.
- **Fake vs real breakout:** a breakout **without volume tends to fail** (the SFP trap); **with
  volume it runs.** Volume is the filter between the two.
- **Liquidity filter (don't get fished):** require a consistent, liquid counter (~≥1 lakh average
  daily volume); avoid circuit-prone / illiquid penny stocks even on a hot tip. Stay in Nifty
  200–500 quality names.

## 10. The daily 6-point checklist (before every trade)

1. Is the **44-MA rising**?
2. Did **price take support on the 44-MA**?
3. Am I **emotionally calm**?
4. Is this **my own analysis** (not a tip)?
5. **Is my stop-loss set** (and will I punch it)?
6. **Can I accept this loss** if it hits?

All six "yes" → take the trade. Any "no" → skip.

## 11. Explicit cautions

Don't blind-buy RSI < 35 (without the trend filter he shows 11 straight stop-outs). Don't blind-short
RSI > 75. Don't use RSI alone. Don't hop timeframes randomly ("a suicide mission"). Don't expect any
indicator to call the exact top/bottom. Don't marry a stock — plan the exit *before* entry. Trend is
your friend until it bends.

---

# Part II — Our live implementation (`weekly-swing-0094-rank`)

The live book on the dashboard is our **faithful-in-spirit reconstruction** of the pullback method,
rebuilt as a **fully-weekly** system and hardened by the repo's research discipline. It keeps the
principles that our tests vindicated and drops the mechanics that lost. It is a **forward-watch paper
book** (inception 2026-07-04), not live capital.

Where it deliberately differs from the letter of the teaching, Part III explains why (each change is
a measured result, not a preference).

## What it buys — the universe
Point-in-time Nifty-500 large- and mid-cap members. Liquidity is handled through **cost** (tiered
slippage by 20-day traded value), which already enforces his "stay in liquid Nifty 200–500 names"
rule — our base universe *is* his operator-avoidance filter.

## The entry — five conditions, all on **weekly** bars (measured at Friday's close)
1. **Rising trend:** the **44-week** SMA is sloping up ≥ **3% over the last 13 weeks** (his "visibly
   rising MA," made precise).
2. **Above trend:** the weekly close is above the 44-week SMA.
3. **Pullback / touch:** the week's low dipped to within **7%** of the 44-week SMA (it tested the
   trend line) but still **closed above it** — his 44-SMA pullback.
4. **Quality green week:** the week closed higher than it opened *and* in the upper half of its range
   — his "green candle" confirmation, weekly.
5. **Relative strength (CRS):** the stock's RS line vs the **Nifty-50** (RS = stock ÷ Nifty-50) is
   above its own 40-week SMA — it is leading the market. This is his "trade the leaders" idea, made
   into a hard filter.

If all five hold on a Friday, it becomes a **signal for the next week**.

### How the buy happens
The signal is valid the **whole next trading week**. Each day, if the stock's **open is inside the
setup week's range** `[low, high]`, buy at that open — his "buy strength pulling back, don't chase"
rule. If the open never falls in range all week, the signal **expires with no trade**.

## Position sizing
**Fixed 2% risk of current equity per trade** (his 1–2% rule). Stop = the setup week's low; risk per
share = entry − stop; **shares = (2% × equity) ÷ (entry − stop)**, rounded down. Leverage (E-margin)
changes how many positions you can *afford*, never the 2% you *risk*.

## The four exits (decided at the weekly close, executed at Monday's open)
1. **Stop-loss** — weekly close at/below the setup-week low → exit the whole position (place it as a
   resting broker stop for intra-week protection).
2. **First target (+2R)** — at entry + 2×(entry − stop), **sell half** and lock the gain (his 1:2).
3. **Trailing stop on the runner** — the remaining half rides a **ratchet** at `20-day SMA × (1 −
   4%)`, never moving down; a weekly close below it sells the runner. This is his swing-low ratchet
   trail, and the one place a *daily* average feeds the system.
4. **Time cap** — any position open after **13 weeks (~3 months)** is closed. Capital should work,
   not stall.

**No rotation, one position per name** — a held name is never re-bought.

## Which signals get funded first — CRS ranking
In a good week the scan may fire more signals than cash can fund. It funds the **strongest leaders
first**: each signal carries a **CRS distance** = `RS ÷ SMA40(RS) − 1`, and candidates are funded in
descending CRS distance until cash runs out. The **top 5 are flagged Grade A**. This ordering alone
lifted the book from Sharpe 0.90 → **1.13** (finding 0038).

## The weekly rhythm
A cron runs **Saturday 6pm IST**: refresh prices → build weekly bars → publish the buy list, updated
stops/trails, and any sell instructions. Mon–Fri you act on resting orders; the dashboard re-prices
the fixed levels daily via the intra-week **monitor** cron. Weekly cadence is a *decision* cadence,
not a data limit — the bot ingests every daily bar each run and chooses to act once a week, exactly
as it was tested.

## Costs & taxes modelled
Per leg: brokerage 0.03% + STT 0.10%, plus slippage by liquidity tier (large 0.05%, mid 0.22%, small
0.40%, +0.10% impact above 0.5% of daily traded value). Because holds are under a year, gains are
short-term (STCG) — a real drag folded into the after-tax numbers.

---

# Part III — The honest evidence (what carried an edge, and what did not)

We tested his system three ways — letter-faithful, method-faithful, and practitioner-process — and
then hardened the surviving pieces through the repo's Deflated-Sharpe (DSR) gate and forward wall.
The headline: **his principles hold up; his specific mean-reversion entries do not; the assembled
recipe is real but not yet certifiable in-sample.**

## What we measured on the raw entries (findings 0020 / 0021)
- **Buying weakness loses.** The RSI < 35 cross-up (−0.24 to −0.42pp/20d vs the universe) and the
  Bollinger lower-band entry (−0.42pp) both **underperform** — they catch falling knives.
- **Buying strength continuing wins, modestly.** Hidden divergence (+0.39pp/20d) and the **HVC
  volume breakout (+0.56pp/20d)** beat the universe. Volume was the single most useful of his tools.
- **His "visible uptrend" emphasis is empirically right.** A weak "MA ticked up" filter gives ~0
  edge; a *strong sustained* 44-SMA uptrend filter **doubled** the pullback edge (−0.11 → +0.48pp).
- **His tight candle-low stop destroys the edge** (it exits on 2–3% noise, Sharpe −0.18). Replacing
  it with a **wide ATR stop + letting winners run** flips the strong-filter pullback to Sharpe
  ~+0.5–0.9 — matching our own let-winners-run results.

## The three faithful tests
- **Letter-faithful (0022).** Both complete systems run exactly as taught are **break-even gross**
  (no edge) and lose net, purely from ~5,100%/yr turnover compounding costs. The mean-reversion
  *mechanics* have no edge. (An early "catastrophic capital-destroyer" framing was a cost/sizing-bug
  over-statement, corrected here.)
- **Method-faithful (0023).** Add the *core* he actually teaches — trailing stops / let winners run,
  volume confirmation, curated liquid watchlist, 2% sizing — and Engine B (the 44-SMA pullback) has a
  **genuine positive gross edge (Sharpe +0.39 / CAGR +5.9%)**, because the trailing stop finally
  rides the rockets (max winner 18–28R, not a capped +2R). **Volume is load-bearing** (remove it →
  −0.90 Sharpe). Net of costs it is modest and sits inside the base strategy's Sharpe.
- **Practitioner-process (0024).** Add the *portfolio process* — weekly frozen top-50 watchlist,
  no-overtrade throttle, index regime pause. Overtrading vanishes (**260 → 21 trades/yr**) and
  drawdown collapses (**−92% → −19%**) — the watchlist confluence is itself the throttle. But the
  method **cannot deploy capital**: tight stops + no leverage → ~1% realized risk → gross +4.5%/yr,
  **net +1.4%/yr**. His RSI system, correctly watchlisted, fires a few trades a year **and loses**
  (27% win, expR −0.18) — the oversold entry is the edgeless part, again.

**Net of the arc:** his *principles* — clear uptrend, respect risk, give winners room, volume is the
voice of god, the exit makes the money, price leads news — largely hold and match our own validated
findings. His *mechanical mean-reversion entries* (RSI-oversold, Bollinger) carry no edge here; the
*momentum-continuation* pieces (pullback/retest in a strong uptrend, HVC/volume breakout) do.

## How the live book scored, and its status
The fully-weekly reconstruction evolved through a long ladder (findings 0031–0038). The current
`weekly-swing-0094-rank` book, on the **corrected/backfilled** universe (2017–2026, in-sample):

| Metric | Value |
|--------|-------|
| Net CAGR | **+24.7%** |
| Net Sharpe | **1.13** |
| Max drawdown | **−42.4%** |
| Win rate | **59.2%** |
| Sharpe 95% CI low | +0.47 |
| Deflated Sharpe (DSR) | **0.894** |

**Read the caveats:** these are **in-sample** — the best case, not a promise. Our bar to call an edge
real is **DSR > 0.95**; this scores **0.894** — the closest the whole program has come, but still
**under the bar**. That is why it is a **forward-watch paper book**, not live capital. A −42% drawdown
happened in the backtest and can happen again; returns are lumpy (a few strong-trend years carry the
total). The only thing that can certify it is **forward, out-of-sample** performance.

## Two swing levers we tried on the live book — both killed (2026-07-09)
Being disciplined means recording what *doesn't* work:
- **Vol-target sizing (0095).** Porting the promoted portfolio vol-target to this book **cut Sharpe
  1.13 → 0.73 and CAGR 24.7% → 13.8%** for a trivial 2pp drawdown gain. On this cash-constrained,
  concentrated book, de-grossing frees cash that funds *more, weaker* trades — the opposite of its
  effect on the fully-invested base. **KILL.**
- **Sector-relative CRS (0096).** Ranking on RS-vs-own-sector instead of RS-vs-Nifty-50 **cut Sharpe
  1.13 → 0.46** — residualising the sector strips exactly the sector/mid-cap trend tailwind the book
  rides. **KILL.** (Broadening the denominator to Nifty-500-TRI also lost earlier, 0037.) The
  CRS-denominator axis is now settled: **market-relative RS vs the large-cap Nifty-50 is correct.**

The book's edge is **concentrated and factor-driven** and resists intra-book re-engineering. The
remaining lever is portfolio-level allocation, decided on the forward wall.

## The certification path
The book is judged on **pre-committed** gates (`forward/prereg.md`), surfaced live on the dashboard's
**Forward Review** tile and refreshed each Saturday. The next decision is the **2026-10-01 review**:
readiness at ≥40 closed trades or 4 quarters; **promote** if net expectancy > +0.10R and drawdown
shallower than −25%; **kill** if net Sharpe < 0; a mechanical −50% drawdown halt runs continuously.
Between reviews: log and leave it alone. No in-sample number promotes it — the forward wall is the
only certifier.

---

*This document describes a research strategy on paper and a body of measurements. It is not
investment advice, and backtested or past performance does not indicate future results. Part I
synthesises a publicly-taught method for internal reference; Parts II–III are our own implementation
and findings.*
