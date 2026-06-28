# NiftyQuant — Long-Horizon (3-Month) Strategy
### Full reference document

*Last updated: 2026-06-25. This is the comprehensive reference. The terse engineering
quick-spec is [`STRATEGY.md`](STRATEGY.md); the frozen machine-readable parameters live in
[`models/long_horizon/config.json`](../models/long_horizon/config.json).*

> **Status & honesty note.** Every performance figure in this document is from a **research
> backtest**. The strategy has **never traded a single live rupee.** Outputs are
> model-generated, decision-support signals — not advice and not a guarantee of any outcome.
> The path to real capital runs through paper-trading first (see §14).

---

## 1. Executive summary

The long-horizon strategy is a **systematic, long-only, cross-sectional trend-momentum**
strategy for Indian large- and mid-cap equities, holding positions for up to ~3 months
(63 trading days).

Each trading day it ranks a clean, liquid, solvent universe by the **slope of each stock's
200-day moving average over the last 63 sessions** (`sma200_slope_63`) and holds the
**top 15** names, managing each with an ATR-based stop, a fixed profit target, a trailing
stop, and a hard 63-day time cap. It is a **rule-based** strategy — there is no machine-
learning model and no daily re-optimisation; every operating value was derived once from
historical excursion data and then frozen.

**Headline (research backtest, solvency-corrected canonical universe — the honest,
reproduced `baseline_v0` anchor):**

The reproducible anchor is [`research/baseline_v0.json`](../research/baseline_v0.json) — the
**FROZEN cfg** re-run through the current exit-parity-unified engine on the corrected-682
universe (397 solvent names, 2017–2026):

| Metric | **Gross** | **After-tax (STCG 20%)** |
|---|---|---|
| CAGR | **26.1%** | **23.1%** ← what a client actually nets |
| Sharpe | **1.02** | **0.83** |
| Max drawdown | **−41.9%** | **−45.6%** |
| Calmar (CAGR / \|maxDD\|) | **0.62** | **0.51** |
| Win rate | **59.7%** | — |
| Reward : risk (per trade) | ~1.9 : 1 | — |
| Trades / year | ~152 (1445 total) | — |
| Avg hold | ~22 trading days | — |

> **Provenance / reconciliation.** A **~30% CAGR / ~1.15 Sharpe** figure was previously
> reported as the headline. That was measured with the **old optimistic target-fill** (the
> backtest filled a touched profit target at `max(close, target)`). The exit-parity
> unification (2026-06-26) made the backtest fill targets **conservatively at the target =
> live**, which costs **~4pp of CAGR** over the full window — see §6 and §10.1. The
> previously-reported 30.3%/35.5% solvency-correction figures are kept below for provenance
> but are **superseded by `baseline_v0` (2026-06-27)** as the current expectation. After-tax
> STCG (20%) is a further ~3pp CAGR / ~0.18 Sharpe — clients net **~23.1% / 0.83**.

The walk-forward that re-derives every operating value per fold previously printed **~32%
CAGR / 1.31 Sharpe (≥2019)** — but that too was the **optimistic-exit** number. It is now
**superseded / pending re-confirmation** under the exit-parity engine; do not present it as a
current figure until re-run. The walk-forward remains the structural argument that the edge
is not a single lucky parameter fit (stable derived parameters across folds), but its
magnitude must be re-confirmed.

This strategy **replaced** the retired v1 14-day LightGBM model on 2026-06-25 and is now the
sole live strategy.

---

## 2. Investment thesis — why it works (mechanism, not curve-fit)

The strategy harvests **intermediate-term price momentum**, the most robust and widely
documented equity-return anomaly (Jegadeesh–Titman). The economic mechanism:

- **Under-reaction & trend persistence.** Markets are slow to fully price new information.
  Stocks in established multi-month up-trends tend to keep trending for weeks-to-months as
  the information diffuses and as institutional flows accumulate. A 3-month hold is long
  enough to capture that drift and short enough to exit before the trend exhausts.
- **The 200-day-slope signal is a *trend-quality* measure, not a momentum spike.** By
  measuring how the **200-day average itself is sloping** (not the raw price), the signal
  rewards durable, low-noise up-trends and ignores sharp one-off pops that mean-revert. It
  is, in effect, "is this stock in a healthy, accelerating long-term up-trend?"
- **The solvency filter removes the momentum-crash tail.** Leverage amplifies momentum
  crashes — highly-indebted names that trend up hardest also collapse hardest when the
  regime turns. Requiring `0 ≤ Debt/Equity < 1.5` (and excluding negative-equity, i.e.
  insolvent, companies) strips out the most fragile winners. This is *not* a generic quality
  factor; it is a targeted removal of the leverage-driven left tail.
- **The liquidity filter removes the manipulation / small-cap mirage.** Restricting to
  large+mid caps by a **trailing-median** rupee-ADV floor (not spot ADV) keeps out
  flash-pumped, circuit-locked, or manipulated names whose backtested "returns" are not
  actually capturable. This is what turned an inflated ~45% headline into an
  investable figure (reported as ~30% under the old optimistic-exit fill; **26.1% gross
  under the exit-parity-unified `baseline_v0` anchor** — see §1, §6, §10.1).

In one sentence: **buy the highest-quality durable up-trends among liquid, solvent large/mid
caps, ride each for up to three months with disciplined exits, and let cross-sectional
ranking continuously rotate capital toward the strongest trends.**

---

## 3. Universe definition

The universe is built fresh every day, point-in-time (no look-ahead, no survivorship):

| Step | Filter | Rationale |
|---|---|---|
| 1 | **Nifty-500** (the 500 official NSE constituents) | The investable opportunity set. |
| 2 | **PIT index-membership mask** — each stock only eligible on dates it was actually in the index | Prevents survivorship bias and "pre-inclusion ramp" harvesting (buying a stock's run-up *before* it was actually index-eligible). |
| 3 | **Large + mid only** — trailing rolling-median 20-day rupee ADV ≥ **₹5 crore/day** | Removes the small-cap tail. Using the *trailing median* (not spot) ADV makes it spike-robust: a flash-pumped name has high spot ADV for a few weeks but a low median, so it never enters. |
| 4 | **Solvent low-debt** — `0 ≤ Debt/Equity < 1.5` (from the point-in-time Screener fundamentals store, ~90-day publication lag) | Excludes insolvent (negative-equity) and over-levered names — the leverage-amplified momentum-crash tail. |
| 5 | **Cross-sectional rank** by `sma200_slope_63`, descending | The within-day relative-strength ordering. |

On a typical day this yields **~150–200 eligible names**, from which the **top 15** are held.

The strategy **does not** use the v1 `universe_filter` (the 441-tradeable trim) — it
reimplements its own liquidity floor via `restrict_to_large_mid`, so the universe definition
is self-contained and consistent between backtest and live.

---

## 4. The signal — `sma200_slope_63`

```
sma200_slope_63(t) = ( SMA200(t) / SMA200(t − 63) − 1 ) × 100
```

- `SMA200(t)` is the 200-trading-day simple moving average of the closing price at day `t`.
- The signal is the **percentage change in that 200-day average over the last 63 trading
  days** — i.e. how steeply the long-term trend has been rising over the most recent quarter.
- It is **backward-only** (uses only data up to day `t`), so it is look-ahead-safe by
  construction.
- It needs ~263 trading days of history to be valid (200 for the average + 63 for the
  lookback), which is why the live scanner downloads a **~600-calendar-day window**.

A stock with a high `sma200_slope_63` is one whose long-term trend is not just up, but
**accelerating** — the highest-conviction expression of durable momentum.

The signal is converted to a **cross-sectional percentile rank** each day (highest slope =
rank 1.0); selection is purely relative, so the strategy always holds *the strongest trends
available today*, automatically adapting to the market's overall trend strength.

---

## 5. Entry rules

1. Each day, rank all eligible names by `sma200_slope_63` (highest = best).
2. Hold a **maximum of 15 positions**. When slots are free (because a held name exited), fill
   them with the **top-ranked names not already held**.
3. A name that **exited this same session is not re-entered the same day** (the backtest
   enforces a ≥1-session gap — exit on day *t*, earliest re-entry at *t+1*'s open).
4. **Indicative entry price** = today's close × (1 + base slippage). The published order hint
   is a **limit at the next open** (`LIMIT_AT_NEXT_OPEN`), with `max_entry` = entry × 1.01.
   - In the backtest, fills happen at the **next day's open** with a market-impact-aware
     slippage model (slippage tier by liquidity: large 0.05% / mid 0.22% / small 0.40%, plus
     an impact surcharge when the order exceeds 0.5% of ADV).
   - The live signal flags entries as **indicative** (`entry_is_indicative = true`) because a
     per-signal recommendation can't know the final fill the way the portfolio simulator can.

The signal each day is therefore a small, stable **buy list** plus the set of currently-held
positions and any that need a sell — bucketed by the dashboard into "buy today / holding /
exit".

---

## 6. Exit rules

Every position is managed by four exit conditions, evaluated each day on the **close**, with
**shared, identical logic between backtest and live**: the backtest `portfolio.simulate`
delegates the per-position stop/target/trailing/time decision to
[`src/engine/exit_logic.decide_exit`](../src/engine/exit_logic.py) — the *same* function the
live signal tracker calls — so they exit byte-identically by construction (the exit-parity
unification, 2026-06-26; before that the backtest had a near-equivalent *inline* reimplementation
that filled a touched target optimistically at `max(close, target)` — that optimism was removed
in favour of the conservative live fill *at* the target, which trimmed the golden-window CAGR
~0.5pp; the full multi-year headline was then **re-confirmed by `baseline_v0` (2026-06-27):
the exit-parity unification costs ~4pp of CAGR over the full 2017–2026 window** — the prior
~30% headline becomes **26.1% gross**. The re-confirmation loop is now closed; see §10.1):

| Exit | Rule | Notes |
|---|---|---|
| **Stop loss** | Close below `entry − 3.67 × ATR(63)` | **Close-only** — an intraday dip that recovers by the close is *not* stopped (reduces whipsaw). On a gap-down open below the stop, fills at the worse of {open, close}. **Always active — never suppressed.** |
| **Profit target** | Intraday high reaches `entry × (1 + 22.5%)` | Conservative fill *at* the target, not higher. |
| **Trailing stop** | After the position is up **+4%**, trail **4.27% below the running close-based peak** | Locks in gains on names that run, while giving them room to breathe. |
| **Time cap** | Hard exit at **63 trading days** | The 3-month horizon. No extension logic — a clean cap. |

**Minimum hold = 10 trading days.** Below 10 days held, the profit-taking exits (target,
trailing, time) are **suppressed** so a position gets a genuine chance to work — **but the
hard stop is never suppressed** (riding a blow-up to honour a min-hold would violate risk
control). This min-hold is the single most important exit parameter and was deliberately set
to 10 (see §11 and §15).

**Important:** the hold horizon is measured in **trading days**, not calendar days. The live
position tracker counts NSE trading sessions (excluding weekends + holidays) so the 63-day
cap fires at the same point live as in the backtest.

In the canonical backtest, exits break down roughly as: **trailing ~57% · stop ~20% ·
target ~19% · time ~3%** — i.e. most winners are harvested by the trailing stop, not the
fixed target, which is the signature of a "let-winners-run" trend strategy.

---

## 7. Position sizing

Sizing is **risk-budget based**, computed by a single shared function
(`base_risk_qty`) used by **both** the live scanner and the backtest, so they cannot drift:

```
shares = floor( 3% of equity / (entry − stop) )           # risk-budget
       capped by floor( 15% of equity / entry )           # max position size
       capped by floor( 5% of 20-day rupee ADV / entry )  # capacity / market-impact
```

- **Risk per trade: 3%** of equity, divided by the per-share stop distance. This makes every
  position risk roughly the same rupee amount at its stop.
- **Position cap: 15%** of equity — for high-priced, low-volatility names the risk budget
  would otherwise buy an oversized position; the cap binds and limits concentration.
- **Capacity cap: 5%** of the name's 20-day average rupee turnover — ensures the position is
  actually fillable without excessive market impact.
- The backtest additionally applies a **market-impact re-pricing** pass and a **cash-
  affordability** cap (it simulates a real, compounding ₹10-lakh book); the live per-signal
  estimate stops at the three caps above, which is why its entry is flagged *indicative*.

### 7.1 Portfolio volatility-target overlay (pre-reg 0068 — SHIPPED to paper 2026-06-26)

On top of the per-name risk budget, the book scales its **deployable sizing equity** by a
volatility-target de-gross multiplier in `[0.40, 1.0]`:

```
vol_scalar = max(0.40, min(1.0, 0.15 / realized_annualized_book_vol_42d))   # only ever scales DOWN
```

computed by the shared `portfolio.vol_target_scalar` from the trailing 42-day realized vol of the
book's equity curve — the **same function** the backtest and the live scanner call (live reads the
prior-close paper NAV from `portfolio_history.csv`, lookahead-clean), so they cannot drift. It
de-grosses during sustained high-volatility regimes **without changing stock selection or exits**.
Configured in `models/long_horizon/config.json → live_overlays` (NOT the frozen `cfg`, so research
baselines + the golden master are untouched); set `vol_target_annual=0` to disable. The published
signal stamps the applied `vol_target_scalar` and the envelope carries `sizing_capital_effective`.

**Why this and not more.** Pre-reg 0068 validated it as the **CAGR-neutral** drawdown lever
(~−45 → −39 in-backtest, best-Calmar arm). 0069 showed pure diversification cuts DD but *costs* CAGR
(KILL); 0070 showed market-state crash overlays (semivol / drawdown / breadth) plateau at a ~−38
overall floor — a SPECIFIC crash like COVID can be cut to −31 free, but no single signal generalises
across crash characters. **A dependable −30 needs the deferred defined-risk tail hedge** (the
vol-carry / options-backtester program), not another sizing/market-state overlay.

---

## 8. Risk management — and what is deliberately absent

**Present:**
- Per-trade risk budgeting (3% / stop) + position cap (15%) + capacity cap (5% ADV).
- Always-on hard stop (never gated by min-hold).
- A breadth-based market-regime read is computed and shown on the dashboard header.

**Deliberately absent (and why):**
- **No market-regime entry gate.** A dual-momentum / "sit out when the index is below its
  200-DMA" gate *was tested* — it cuts the drawdown but **also kills the CAGR**, because the
  strategy's best years are exactly the strong-trend regimes the gate would sideline. Net
  unfavourable, so it is off. (See §11.)
- **No sector-exposure caps.** The strategy buys the top-ranked names regardless of sector.
  Sector overlays were tested and **hurt** the strategy's lean years.
- **No conviction / quality multiplier on size.** Sizing is risk-only; the v1 Kelly/quality
  sizer is not used.
- **No AI / news gate.** The AI sector-regime analyst runs in **shadow only** — it writes a
  forward scorecard but touches no trade (it must prove forward skill before it could ever be
  wired in).

This minimalism is intentional: every optional overlay that was tested either failed to
improve risk-adjusted return or actively hurt it (§11). The edge is the trend signal on a
clean universe with disciplined exits — nothing more.

---

## 9. The frozen configuration (every operating value)

All values were **derived from the data** (on the pre-2017 training slice's 63-day
favorable/adverse excursion distributions) and then **frozen** — they are never re-optimised
by a live job. Source of record: `models/long_horizon/config.json`.

| Parameter | Value | How it was set |
|---|---|---|
| Signal | `sma200_slope_63` | The 3-month-horizon trend signal (IC rises toward 63d). |
| Selection | top **15** by cross-sectional rank | Where marginal breadth flattens. |
| Stop | **3.67 × ATR(63)**, close-only | ATR(63) multiple at the 5th-percentile adverse excursion of *winning* trades. |
| Profit target | **+22.5%** (fixed) | Calibrated from the 63-day favorable-excursion distribution. |
| Trailing arm | **+4%** | Excursion level where trailing starts adding value. |
| Trailing band | **4.27%** below close-peak | Give-back band beyond which winners should be cut. |
| Min hold | **10 trading days** | Bar where median favorable:adverse excursion turns favorable (sweet spot 10–14). |
| Max hold | **63 trading days** | The label horizon (≈3 months); a clean hard cap. |
| Risk / trade | **3.0%** of equity / stop | 95th-pctile single-trade loss × max concurrent ≤ drawdown budget. |
| Position cap | **15%** of equity | Concentration limit. |
| Capacity cap | **5%** of 20-day rupee ADV | Fillability / market impact. |
| Max positions | **15** | Effective-breadth plateau. |
| Expected win rate | **~63%** | `mean(triple-barrier hit)` on gated rows. |
| Expected reward:risk | **~1.9 : 1** | From the excursion distributions. |

---

## 10. Performance & validation

> All figures are research backtests on historical data. They overstate what live trading
> will deliver. The honest expectation is *lower and noisier* than the headline.

### 10.1 Canonical headline — the reproduced `baseline_v0` anchor (solvency-corrected, 682-name corrected universe)

The current, reproducible anchor is [`research/baseline_v0.json`](../research/baseline_v0.json):
the FROZEN cfg re-run through the **exit-parity-unified** engine, corrected-682 universe (397
solvent names, 2017–2026):

- **GROSS: CAGR 26.1% · Sharpe 1.02 · max drawdown −41.9% · Calmar 0.62 · 1445 trades
  (~152/yr) · win rate 59.7%.**
- **AFTER-TAX (STCG 20%): CAGR 23.1% · Sharpe 0.83 · max drawdown −45.6% · Calmar 0.51** —
  what a client actually nets.

**Reconciliation (stated, not hidden):**
- The prior **~30% / ~1.15** headline (and the close ~34.7% / 1.25 / −44.9% re-derived
  variant) was measured with the **old optimistic target-fill** — the backtest filled a
  touched target at `max(close, target)`. The exit-parity unification now fills targets
  **conservatively at the target = live**, which costs **~4pp of CAGR** over the full window.
  This is the re-confirmation §6 said was pending; `baseline_v0` **is** that re-confirmation.
- baseline_v0 **reconciles structurally** with the committed
  [`cpcv_long_horizon_final_682.json`](results/cpcv_long_horizon_final_682.json) arms — the
  `base_no_filter` arm prints 25.56% / 0.973 and this solvent arm prints 26.1% / 1.02, i.e.
  the solvency filter helps a touch (as expected).
- After-tax STCG (20%) costs a further ~3pp CAGR / ~0.18 Sharpe on top of gross.
- The previously-reported **30.3% / 35.5%** solvency-correction figures (the ~45% → investable
  story) are **optimistic-exit figures, superseded by `baseline_v0` (2026-06-27)** — preserved
  in §2 / §11 for provenance, not as the current expectation.

### 10.2 Walk-forward — the deciding test (magnitude pending re-confirmation)
Parameters re-derived on each year's **expanding** training window, then traded **one year
out-of-sample**, compounding. The structural result — **the edge survives honest
out-of-sample re-derivation, with stable derived parameters across folds** — is the key
finding and is why the headline is not single-fit luck.

- **Previously reported: ~32% CAGR / ~1.31 Sharpe / 0 negative years from 2019 onward.**
  **However, that walk-forward was also measured under the old optimistic target-fill** — so
  like the canonical headline it is **superseded / pending re-confirmation under the
  exit-parity engine** and must **not** be presented as a current figure until re-run. Expect
  it to drop by roughly the same ~4pp-CAGR exit-parity haircut.

The pre-2019 folds are mildly survivorship-biased (membership data is reliable only from
~2019) and are weighted accordingly. The Stage-B survivorship re-derivation (+284 delisted
names) will produce `baseline_v1` and will likely move the number **further DOWN** —
survivor-only data flatters returns.

### 10.3 Robustness / stress tests (all passed)

> The absolute numbers in this subsection were measured under the **old optimistic-exit
> fill** (pre-2026-06-26) and have **not** yet been re-run on the exit-parity engine — read
> them as **relative** stress responses around the old ~30% anchor, each subject to roughly
> the same ~4pp-CAGR exit-parity haircut. The conclusions (survives 2–3× costs, not a
> single-split artefact, regime-dependent but alive) are robust to that common-mode shift.

- **Transaction-cost sensitivity:** 1× → 30.7% / 1.15 · **2× → 26.5% / 1.01** · 3× → 20.5% /
  0.82. Survives 2–3× realistic costs and still beats buy-and-hold (avg trade ~2.9% ≫
  round-trip cost). Turnover is not fatal.
- **Independent second split** (derive < 2019, test 2019+): **42.4% / 1.46** — not a
  pre-2017-split artefact.
- **Sub-period stability:** 2017–2021 = 39.9% / 1.50 · **2022–2026 = 21.5% / 0.84 / −37%
  DD**. Regime-dependent (stronger in trending bulls) but **alive in the recent harder
  regime** and still beating buy-and-hold there.
- **Threshold-robust:** Debt/Equity cutoffs of 1.0, 1.5 and 2.0 all beat the unfiltered book.
- **Block bootstrap (block = 63):** Sharpe median **1.23 [0.58, 1.88]**; CAGR median
  **34.4% [13%, 57%]**.

### 10.4 Engine integrity
Three independent audit passes (an automated flaw-hunter, a backtest-validator, and a
third-party expert checklist) plus 11 correctness unit tests. Found and fixed a P1
survivorship/look-ahead bug (PIT membership had not been applied). Confirmed clean:
signal↔fill parity on cleaned OHLC (0.0 mismatch), no forward-label leakage, train/test
purge, both-leg transaction costs, no negative-cash / phantom-drawdown.

---

## 11. What was tested and rejected (the rigor — so we don't relitigate)

Each of these was measured and **killed** because it failed to improve risk-adjusted return
(or hurt it):

- **Market-regime / dual-momentum gate** — cuts drawdown but kills CAGR (sidelines the best
  trending years). Net negative.
- **Residual / beta-stripped momentum** — no improvement over raw trend.
- **Frog-in-the-pan (path-smoothness) momentum** — no edge on this universe.
- **Sector-residual momentum & sector overlays** — hurt the lean years; sector momentum IC ≈ 0.
- **All reversal / RSI / MACD / ROC signals** — no orthogonal edge for this horizon.
- **Signal-level low-volatility blending** — diluted the trend signal.
- **Heavier quality screens (earnings, ROE) on top of the debt filter** — over-filtered,
  reduced breadth without improving quality.
- **`min_hold = 20` (the originally-specified floor)** — this is the **worst** point in the
  hold sweep (~22% / 0.86). `min_hold = 10` backtests at 33–36% (these are **optimistic-exit**
  CAGRs — read the gap, ~11pp, not the absolute level; the exit-parity anchor for `min_hold=10`
  is `baseline_v0` = 26.1% gross). (See §15 — this is an open preference decision.)

The discipline: a reversed or null result is a *finding*, recorded so it isn't re-tried
without genuinely new information.

---

## 12. Data requirements & sources (audit 2026-06-25)

The strategy is **data-minimalist**. It consumes exactly **9 columns** — a small, clean
subset of the feature pipeline. It does **not** use the v1 79-feature contract, macro
features, or sector enrichment (`enrich_with_layers` is never called).

**Columns consumed:** `close`, `sma200_slope_63` (rank signal), `atr_pct_63` (stop & sizing),
`adv_rupees_20d` (liquidity tier + capacity cap), `trend_rank` (computed at run time),
`debt_equity` (solvency filter), `sector` (display) — plus `ticker` / `date`.

**Data sources** (all git-tracked, so they reach the runner even though `data/` is
gitignored):

| Source | File | Used for |
|---|---|---|
| OHLCV | `results/ohlcv_cache_lh.json` (own GitHub-backed incremental cache) | Prices, ATR, ADV, the signal |
| PIT fundamentals | `data/fundamentals_pit_screener.pkl` (~90-day publication lag) | Debt/Equity solvency filter |
| Index membership | `data/nifty500_membership.csv` | PIT membership mask |
| Sector map | `config.SECTOR_MAP` | Sector label (display) |

**Honest flags:**
- `compute_all_features` still computes ~50 technical columns + labels when only ~6 are used
  (wasteful CPU on the cron, but correct — a long-horizon-only feature mode is a future
  optimisation).
- The fundamentals pickle is **static** (manual refresh); Debt/Equity changes slowly
  (quarterly). A runtime guard now grades freshness by the latest **fiscal `period_end`** in the
  store (content-based — file mtime is unreliable, since background cache jobs touch the pickle
  without changing it) and degrades `cron_health` if it falls > 200 days behind (a missed
  quarter). As of 2026-06-26 the store is current (latest quarter 2026-03-31).
- A runtime guard fails the cron loudly if the pipeline ever stops producing a required column.

### AUD-007 — live universe vs the current index (open; observed + sequenced, not yet closed)

The cron's **download** universe is the *static* `config.NIFTY_500` snapshot (the 2025-07-20
list). The PIT membership mask (`filter_features_dict`) is applied on top — so a name in the
snapshot that has since **exited** the index is correctly masked out for today. But a name that
**entered** the index after the snapshot is never downloaded, so it is **invisible to the live
scan**. Measured 2026-06-26: **48 config names have exited** the index and **48 current index
members are absent** from `config.NIFTY_500` (the membership CSV's current set = 500, matching).

The cron now **records this divergence** in `cron_health` every run (`membership_divergence`,
`membership_current_count`) and degrades only if it blows past a pathological threshold (config
gone badly stale); the known ~48 gap is expected and below that bar.

**Why not just expand the download universe to the current members?** Because **0 of the 48 new
entrants have fundamentals coverage** in `fundamentals_pit_screener.pkl` — they would all be
dropped by the solvency filter, making the expansion a no-op. The real fix (download from the
membership store *and* extend the PIT fundamentals + delisted OHLCV to cover the entrants) is
the **Task-8 unseen-universe data work** and is sequenced there. Until then live and backtest
universes differ by this measured, recorded gap.

---

## 13. Production architecture (how it runs live)

```
GitHub Actions `.github/workflows/cron-scanner.yml`  (weekdays 4:15 PM IST; schedule "45 10 * * 1-5"; runs from main only)
  python -m src.runners.long_horizon_cron
    → download ~600d OHLCV (data/ohlcv_incremental — GitHub-cache-backed, 5d-fresh + merge
        + split-heal + trim; cold-starts the cache on first run, ~3–5 min)
    → DataStore.compute_all_features(persist=False)   # fresh features, no stale pickle
    → PIT index-membership mask
    → restrict to large+mid (ADV ≥ ₹5cr) → solvent low-debt (0 ≤ D/E < 1.5)
    → rank by sma200_slope_63 → fill free slots with the top non-held names (max 15)
    → load FROZEN cfg (models/long_horizon/config.json)
    → compute entry / stop / target / R:R + risk-based size
    → carry & track open positions (signal_tracker; trading-day aging; shared exit logic)
    → paper equity curve (always) + capital-constrained paper broker (NIFTYQUANT_PAPER_BROKER=1)
    → write results/signals_today.json + signals_history.json + signal_analytics.json
        + paper_portfolio.json + ledger + portfolio_history.csv
    → push to GitHub (LH_PUSH=1)

FastAPI backend (Render)  →  reads results/*.json  →  React dashboard (Vercel)
```

**Each signal carries the full trade plan** the dashboard renders: ticker, grade/conviction,
entry (indicative), `max_entry`, stop, target, stop%/target%, **R:R**, ATR, suggested shares
& position value, **hold window (min 10 / max 63 days)**, the exit-rule text, buy-window-until
(T+3), sector, and Debt/Equity.

Supporting crons (kept): OHLCV refresh, Kite session refresh, nightly trade-journal
post-mortem, and the weekly AI sector-regime shadow analyst. The v1 retrain & revalidator
crons were removed — the long-horizon parameters are frozen, not re-optimised by a job.

---

## 14. Paper trading & the path to real capital

Before any real capital, the strategy runs as a **capital-constrained paper portfolio**:

- The paper broker starts with a clean **₹10-lakh** book, buys signals at **T+1** (next open
  after the signal), marks to market daily, and sells the day after a model exit, applying
  realistic brokerage + STT costs and the same position caps.
- It writes `paper_portfolio.json` (live ledger), `paper_ledger_history.csv`, `paper_trades.json`,
  and a daily NAV to `portfolio_history.csv` (which also feeds the drawdown / single-day-loss
  kill-criteria).
- The old v1 paper data was wiped so the long-horizon track record starts from a clean slate.

**Gate to real capital (pre-committed):** accrue **≥ 30 paper trades / ~2 months** and review
the live-vs-backtest behaviour (fill realism, hit rates, drawdown path) *before* committing
real money. The strategy is paper-trade-ready, **not** real-capital-ready.

---

## 15. Honest caveats & risks (do not skip)

1. **It has never traded live.** All numbers are backtests. Live results will be lower and
   noisier — slippage, partial fills, and regime luck all bite.
2. **~−42% drawdown is steep.** That is the price of the strategy's return (26.1% gross /
   23.1% after-tax CAGR per `baseline_v0`); sizing can't reduce it much (the position cap
   binds), and the regime gate that *would* cut it also kills the return. A real client must
   be able to stomach a >40% peak-to-trough decline (−45.6% after-tax).
3. **High-variance / regime-dependent.** Bootstrap Sharpe 5th-percentile is 0.58 (below
   buy-and-hold in the worst ~5% of resampled paths). The *median* (1.23) clearly beats
   buy-and-hold, but this is a high-return, fat-right-tail book — not a smooth machine. The
   edge concentrates in momentum-friendly years (2017/2020/2021/2023 were +75% to +98%);
   choppy/reversal years are flat-to-modest.
4. **`min_hold = 10` vs the originally-specified 20.** The data strongly favours 10 (10 →
   33–36% CAGR; 20 → ~22%, the worst point in the sweep — both **optimistic-exit** figures;
   the gap, ~11pp, is the load-bearing number, and the exit-parity anchor at `min_hold=10` is
   `baseline_v0` = 26.1% gross). The strategy ships with 10; if a longer minimum hold is
   preferred for behavioural reasons, it costs ~11pp of CAGR — an explicit owner decision.
5. **Static fundamentals.** The Debt/Equity filter uses a manually-refreshed Screener
   snapshot; if it goes stale, the solvency screen is stale (low risk, but worth a periodic
   refresh).
6. **Single-name & single-regime risk.** The lean years are driven by individual blow-ups and
   per-stock regime misses rather than sector rotation — concentration in 15 names is real.

**Compliance framing:** outputs are *model-generated research signals / decision-support
output*. Nothing here is investment advice or a performance guarantee.

---

## 16. Operating procedures

- **Run live:** the GitHub Actions workflow `.github/workflows/cron-scanner.yml` runs it
  automatically at 4:15 PM IST on weekdays (schedule `"45 10 * * 1-5"`; runs from `main` only).
  The first run cold-starts the 600-day OHLCV cache (~3–5 min).
- **Run a research backtest locally:** `python diagnostics/run_long_horizon_tradelog.py`
  (uses the local cache); the canonical multi-year results are dispatched via the
  `cpcv-research.yml` GitHub Actions workflow on the corrected universe.
- **Change a parameter:** never hand-edit live. Re-run the offline derivation / walk-forward,
  then update **both** `models/long_horizon/config.json` and the `long_horizon/config.py`
  constants in one commit.
- **Monitor:** watch `results/signals_today.json` (today's book), `signals_history.json`
  (lifecycle / track record), and `portfolio_history.csv` (paper equity curve / drawdown).
- **Rollback:** there is no env-var rollback (v1 was deleted). To revert, restore the v1
  files from git history before commit `c0fbd1d` and re-point `render.yaml`.

---

## 17. Open decisions & roadmap

- [ ] **`min_hold` 10 vs 20** — pick the point (CAGR vs hold preference). Ships at 10.
- [ ] **Drawdown tolerance** — ~−42% as-is for max CAGR (`baseline_v0` = 26.1% gross), or
      de-lever (risk 1.5% → similar DD since the cap binds, at a lower CAGR; the previously
      quoted ~32% de-lever figure was optimistic-exit and needs re-confirmation on the
      exit-parity engine).
- [ ] **F&O-only universe** (circuit-free, even cleaner) — needs point-in-time F&O membership
      data.
- [ ] **AI sector-regime overlay** — currently shadow-only; could become a conviction
      boost/veto *if and only if* its forward scorecard proves skill (skeptical priors:
      price-based sector overlays were already killed).
- [x] **Productionised + live** (2026-06-25) — sole live strategy.
- [x] **Paper-trading wired** — clean ₹10L book accruing now.

---

## Appendix — glossary

- **ATR(63):** 63-day Average True Range — a volatility measure; the stop is a multiple of it.
- **ADV:** Average Daily Value (rupee turnover) — the liquidity measure for the universe and
  capacity caps.
- **Cross-sectional rank:** a stock's percentile vs all other eligible stocks *on the same
  day*.
- **PIT (point-in-time):** using only information that was actually available on the date in
  question — the discipline that prevents look-ahead and survivorship bias.
- **Walk-forward:** re-deriving parameters on past data and testing on the unseen next period,
  repeatedly — the gold-standard test that a strategy isn't curve-fit.
- **Favorable / adverse excursion:** the best / worst point a trade reaches during its life —
  the distributions the stop, target, and trailing values were derived from.
- **Calmar ratio:** CAGR divided by the absolute maximum drawdown — return per unit of
  worst-case pain.
