# 0028 — CAGR bridge: decompose the locked-744 base's realized return into mechanism terms

- **ID:** 0028. Registered 2026-06-11, BEFORE any instrumented run.
- **Type:** measurement diagnostic (like 0021/0027) — **NOT a trial.** No candidate strategy
  is promoted or killed; the subject is the BASE's own realized return, decomposed. Per
  `n_trials.json` `_doc` ("Pure measurement diagnostics that make no trade decision … are NOT
  trials"), **`cumulative_n_trials` is unchanged (stays 43).** Precedent: 0021 (rank-IC),
  0027 (vol null).

## Question

The owner's standing intuition is "something is wrong with risk/sizing." The locked-744
yardstick (`locked_honest_base_744.json`) is ≥2019 mean Sharpe **0.968** / median **0.854**,
carried by 2020 (+2.72) and 2021 (+3.63) with three genuine negative folds — **2019 (−0.720),
2024 (−0.666), 2025 (−0.906)**. This measurement decomposes that realized return into
mechanism terms and asks: **is the felt risk/sizing problem real, and WHERE does it live —
in sizing/deployment (a construction lever) or in per-trade selection/regime (already studied
by 0027, which put 2024's picks at the 4th percentile of a vol-matched null)?**

It is a MEASUREMENT, not a remedy. Every lever it might point to is a future, separately
pre-registered trial.

## Subject (the exact object decomposed)

The locked-744 single-model recipe, re-run on the pinned, survivorship-correct, two-build-
deterministic cache (digest `64cda7c2db82…c671d0c`), fold grid pinned to the lock:

```
REPRODUCIBLE_MODE=1 python -m diagnostics.run_walk_forward \
  --start 2010-01-01 --end 2026-06-10 --initial-train-years 7 --step-months 12 \
  --embargo-days 45 --model-dir models/v1 --apply-bear-block
```

→ 10 folds (test 2017…2026-partial), flat risk (`apply_confidence_sizing` OFF — the locked
base ran flat), sweep_override OFF, executed one fold per process (`--only-fold`) for RAM
safety. **Reproduction gate (hard):** the merged per-fold `n_trades`/`win_rate` must match
the locked yardstick EXACTLY (2017:51, 2018:126, 2019:65, 2020:133, 2021:108, 2022:54,
2023:19, 2024:40, 2025:13, 2026:16); `sharpe`/`cagr` within |Δ| ≤ 0.10 (metric-definition
fixes AUD-033/034/035/036 may post-date the lock). Any trade-count mismatch → STOP, do not
analyze. Decomposition runs on instrumentation fields added additively to the engine behind a
byte-invariance gate (pre-existing trade/equity fields unchanged).

## Frozen definitions (immutable — no post-hoc freedom)

Per fold, from that fold's instrumented equity curve and trade list (each fold is an
independent simulation seeded at `initial_capital`; **never chain equity across folds**):

- **Geometric CAGR:** `CAGR_geo = (E_end / E_start)^(365.25 / max(days_span, 365.25)) − 1`,
  `days_span` = calendar days from first to last equity date.
- **Arithmetic annualized mean:** `μ_a = mean(r_t) × ppy`, where `r_t` = daily equity simple
  returns (the series seeded with `initial_capital` as day-0 equity, AUD-034 convention) and
  `ppy = len(r_t) / years_span` (AUD-036 observed-cadence convention).
- **Volatility drag:** `drag_exact = μ_a − CAGR_geo`, reported beside the classical
  approximation `0.5 · var(r_t) · ppy` (≈ σ²/2). Both reported; neither hidden.
- **Bridge identity (trade view):** `μ_a ≈ N · r̄ · s̄`, where N = trades in the fold-year,
  r̄ = mean per-trade `return_pct`/100 (net of ALL costs — brokerage, STT, slippage, impact),
  s̄ = mean position weight = `shares · entry / equity_at_entry`. The **residual**
  `μ_a − N·r̄·s̄` is ALWAYS reported (compounding + overlap + timing make it inexact).
- **Deployment:** `D_t = invested_t / equity_t` per day. Report mean, median, P10, P90,
  fraction of days at `D_t ≈ 0` (< 0.01), and mean concurrent open positions.
- **Realized risk per trade:** `realized_risk_pct = shares · (entry − stop) / equity_at_entry
  × 100`. The **intent** is `risk_per_trade = 3.5%`. Binding cap = the LAST sizing stage that
  strictly reduced share count, ∈ {`risk_budget` (none bound), `tail_gap`, `position_cap`,
  `adv`}. Report the realized-risk distribution and the binding-cap frequency table.
- **R-multiple:** `R = return_pct / stop_distance_pct`, with
  `stop_distance_pct = (entry − stop) / entry × 100`. Loser buckets (for `return_pct < 0`):
  `R ≤ −1.05` (gap-through-stop), `−1.05 < R ≤ −0.95` (clean stop), `−0.95 < R < 0`
  (bleed-out, exited above the stop).
- **Excursions:** MFE = `max_pct_during_hold` (existing). MAE on two bases, both tracked in
  the held-day loop from the first full day after the T+1-open fill (identical convention to
  MFE): `mae_close_pct` (policy-relevant — close-only stops) and `mae_low_pct` (pain-relevant
  — intraday low). "Were-ever-green" loser = a `return_pct < 0` trade with
  `max_pct_during_hold ≥ 2.0`.
- **Drawdown episodes:** maximal consecutive runs of `dd < 0` in the fold equity curve; record
  depth (min dd) and duration (days). A trade is "open during" an episode iff
  `entry_date ≤ episode_end AND exit_date ≥ episode_start` (ISO-string-safe compare).

## Frozen output tables (anything outside T1–T6 is labeled exploratory)

- **T1** — bridge terms per fold + pooled ≥2019: `CAGR_geo`, `μ_a`, `drag_exact`, σ²/2 approx,
  N, r̄ (with bootstrap CI), s̄, and the residual.
- **T2** — deployment distribution per fold + pooled ≥2019: mean/median/P10/P90 `D_t`, % days
  flat, mean open positions.
- **T3** — realized-risk distribution (mean/median/P10/P90 `realized_risk_pct`) + binding-cap
  frequency table + entry-skip counts per fold.
- **T4** — loss anatomy: R-multiple bucket counts, MAE/MFE (both bases) by `exit_reason`,
  were-ever-green loser count.
- **T5** — drawdown episodes for the three negative folds (2019/2024/2025): top-3 episodes,
  depth/duration, and the trades + sectors open during each.
- **T6** — **the localization contrast (the discriminating table):** every bridge + sizing +
  deployment term, positive folds {2020, 2021, 2022, 2023, 2026} vs negative folds {2019,
  2024, 2025}.

## Falsification framing (the null this measurement can confirm or break)

**H0 (sizing is NOT the problem):** caps and deployment are roughly CONSTANT background facts
across folds — they do not differ between positive and negative folds — and the negative folds
are explained by per-trade selection/regime softness (consistent with 0027 putting 2024's
picks at the 4th percentile of a vol-matched null). Under H0, T6 shows deployment and
realized-risk approximately FLAT across the positive/negative split, while r̄ (per-trade edge)
and the loss anatomy carry the difference.

**H1 (sizing/construction IS implicated):** T6 shows deployment or realized-risk materially
LOWER (or the binding-cap mix materially different) in the negative folds — i.e. the machine
under-deploys or mis-sizes exactly when it loses. T6 is the discriminating evidence; T2/T3/T5
are its mechanism.

This measurement cannot, by itself, "bless" a remedy — it can only locate the term that
separates good folds from bad. A result that points at H1 makes a portfolio-construction trial
the next n_trials candidate; a result that confirms H0 closes the sizing doubt and returns
focus to the strategic line (orthogonal data).

## Scope limits (stated so no result is over-read)

1. **Backtest object, not live.** Decomposes the YARDSTICK. Live sizing differs: AUD-012 (the
   locked base ran FLAT risk; live applies a 0.7–2.0× confidence multiplier), AUD-032 (the
   tail-loss gap cap is backtest-only), and live enforces no cash / `max_positions` /
   `max_signals_per_day` constraint. Findings about deployment/risk here describe the
   decision-bearing backtest, which every PROMOTE/KILL since 0020 is measured on — that is
   precisely why its mechanics matter — but they are NOT live-sizing claims.
2. **Within-run only (AUD-021).** Absolute levels move with cache vintage; this is a
   shares-of-a-whole decomposition WITHIN one reproduction-gated run. Structure (which term
   dominates, the positive/negative contrast) is the claim; absolute Sharpe/CAGR levels are
   not.
3. **Thin recent folds.** 2023 (19), 2024 (40), 2025 (13), 2026 (16) trades → per-fold numbers
   are descriptive; bootstrap CIs reported where n permits; no significance test is run on the
   contrast (this is measurement, not inference).
4. **No remedy is registered here.** Every lever this points to — lifting the position cap
   (≈ 0020 C_nocap, which was CI-straddled and parked "revisit on corrected universe"),
   conviction sizing (0020, inert under caps), exposure overlays (0013, KILLed), stop mechanics,
   a backtest RiskManager (AUD-030) — is a SEPARATE future pre-registered trial with its own
   n_trials increment.

## Pre-committed reading (decision branches — each changes the next action)

- **Deployment low + cash rarely the binding cap** → idle capital is structural → a
  portfolio-construction trial outranks new-data acquisition for the next slot.
- **Realized risk ≪ 3.5% with `position_cap` ~always binding** → mechanically explains a low
  CAGR-per-unit-Sharpe and sharpens the 0020 reframe (conviction sizing is inert *under the
  caps*, not uninformative).
- **Losers' MAE deep before the close-only stop fires** → stop mechanics becomes a trial
  candidate (close-only vs intraday).
- **DD episodes sector-correlated in 2019/2024/2025** → AUD-030 (no RiskManager in the
  backtest) becomes material rather than theoretical.
- **T6 flat across the split (H0 confirmed)** → "risk/sizing is fine" is CLOSED with evidence;
  the doubt cannot resurface without new evidence; full focus returns to orthogonal data.

No seed-hunting, no threshold moved after seeing a number; the table list and definitions above
are frozen at registration.

## Result

**Status: COMPLETE (2026-06-12).** Reproduction gate **PASS** — the instrumented
chunked run (one fold per process, `--only-fold`, REPRODUCIBLE_MODE=1, pinned-744 cache
digest `64cda7c2…`) matches `locked_honest_base_744.json` **exactly** on all 10 folds
(trades, win-rate, Sharpe, CAGR identical to 3dp). Evidence: `0028_armA.json` (merged),
`0028_cagr_bridge.json` (+ `.md` brief), per-fold `0028_trades/` + `0028_equity/`.
Byte-invariance of the instrumentation proven separately (`p8_bridge_invariance` PASS).

### Headline — the felt "risk/sizing problem" is REAL but is NOT what makes the bad folds bad

**T6 localization (the discriminating table):**

| term | positive folds {2020,2021,2022,2023,2026} | negative folds {2019,2024,2025} |
|---|---|---|
| CAGR_geo (mean) | **+47.8%** | **−9.8%** |
| **r̄ (per-trade, net)** | **+3.89%** | **−2.06%** |
| s̄ (position weight) | 0.1496 | 0.1490 |
| realized risk %/trade | 1.58% | **1.80%** |
| deployment (mean) | 0.310 | 0.200 |
| mean open positions | 2.12 | 1.35 |

**The only term that flips sign good→bad is r̄ (per-trade edge).** Sizing is flat across the
split — s̄ is identical (the 15% cap binds in every fold), and realized risk is if anything
*higher* in the bad years. **H0 confirmed: the negative folds are a SELECTION/regime problem
(negative per-trade expectancy), not a sizing/deployment bug.** This is consistent with 0027
(2024 picks at the 4th percentile of the vol-matched null). Sizing up would have amplified
bad-year losses symmetrically; the lower deployment in bad years is mildly *protective*.

### But the sizing audit surfaces two real, standing inefficiencies (not the cause of bad folds)

1. **The 3.5% risk-per-trade knob is inert.** `position_cap` is the binding constraint for
   ~95% of trades in every fold (2017: 49/51, 2018: 123/126, 2020: 127/133, 2021: 105/108,
   2024: 39/40). Pooled realized risk ≈ **1.67%/trade — half the 3.5% intent** — because the
   15% position cap clips the size before the risk budget ever bites. Tuning `risk_per_trade`
   does almost nothing on this universe.
2. **Chronic under-deployment / idle capital.** Pooled mean deployment **27%**; the 30-position
   cap **never binds** (`max_positions` skip = 0 in every fold) — at 15%/name the book tops out
   near ~6–7 names but averages ~2–3 because signals are sparse and cash fragments
   (`zero_shares_or_cash` is the dominant skip: 131 in 2018, 114 in 2020). Even the best years
   deploy only ~31–53%; thin years (2023, 2025) sit at 7–9% with 58–77% of days fully flat.
   Good-year CAGR is a levered-*down* image of the edge — the ceiling is partly a deployment
   ceiling.

### Volatility drag, loss anatomy, drawdown shape (T1/T4/T5)

- **Vol drag is not eroding the bad folds.** `drag_exact = μ_a − CAGR_geo` is ≈ 0 to +0.03 in
  every flat/negative fold; the large *negative* "drag" in 2020/2021 (−0.29/−0.31) is the
  convexity of compounding a >100% annual gain (CAGR_geo = exp(Σlog)−1 ≫ Σsimple), not a vol
  cost. The σ²/2 approximation is only meaningful in the small-return folds, where it is tiny.
- **Losers wander; they do not die fast at the stop.** Were-ever-green losers (up ≥2% before
  reversing) are the overwhelming majority: 2018 64/67, 2019 30/36, 2024 22/24, 2025 5/6.
  R-multiple buckets show bleed-out (−0.95<R<0) + gap-through (R≤−1.05) dominating clean stops.
  By exit reason, `time` exits bleed −6 to −7% (mae_low −11 to −14%) — pop-then-fade names held
  to the time stop. (`target`-exit MFE means are contaminated by a few split/penny outliers —
  the F5 OHLCV issue — so MFE *magnitude* is not cited; the were-ever-green count uses the
  robust ≥2% threshold.)
- **Drawdowns are slow year-long grinds, not sector-clustered crashes:** 2019 −25.9% over 145d
  (35 trades open), 2024 −13.3% over 208d (30), 2025 −9.5% over 245d (13). **Caveat:** the
  `sector` field came through blank in the trade export, so sector *concentration* (AUD-030) is
  **unresolved by this run**, not answered — flagged for a follow-up if pursued.
- **Accounting is clean:** Σ(per-trade pnl) ≈ Δequity every fold; open-position MTM gap ≤ 2.4%
  (AUD-033 fix holds), so the bridge numbers are trustworthy.

### Verdict and what it changes (no remedy is blessed here — each is a future trial)

- **CLOSED:** "the negative folds are a sizing bug." They are negative per-trade expectancy
  (selection/regime), not mis-sizing. The doubt cannot resurface without new evidence.
- **The CAGR ceiling is a deployment + offense ceiling, but lifting deployment is SYMMETRIC
  leverage** — it scales the negative folds as much as the positive ones (s̄ is regime-
  independent), so "deploy more / lift the 15% cap" is NOT free CAGR (it is ≈ 0020 C_nocap,
  which was CI-straddled and parked "revisit on corrected universe"). The validated path to
  higher CAGR without higher bad-year risk is **raising r̄ and signal frequency** (offense / new
  orthogonal inputs) — the strategic line — not a sizing change.
- Concrete future-trial candidates this measurement *locates* (each its own pre-registration +
  n_trials increment): (a) the inert `risk_per_trade` knob vs a position-cap/sizing redesign;
  (b) the time-stop bleed on were-ever-green faders; (c) deployment/leverage as an explicit
  pre-registered trial with the symmetric-risk caveat front-loaded.

### Scope (restated)
Backtest yardstick only (flat risk — AUD-012; tail cap backtest-only — AUD-032; no live cash/
max-positions/per-day enforcement). Within-run shares-of-a-whole decomposition; absolute levels
move with cache vintage (AUD-021) — structure (which term dominates) is the claim. Thin recent
folds (2023:19, 2025:13, 2026:16) are descriptive. **Measurement only — n_trials unchanged (43).**
