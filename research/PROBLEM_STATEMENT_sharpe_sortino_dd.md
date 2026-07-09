# Research Problem Statement — Raising Sharpe/Sortino & Cutting Drawdown

> **How to use this file:** Paste everything inside the `====` fences below into a fresh
> Claude chat. It is written as a self-contained prompt: it assigns a role, gives the
> real baseline numbers, states the problem, lists hard constraints, tells the model what
> has *already* been tried (so it doesn't waste effort re-proposing dead ends), and
> specifies the exact deliverable format. Fill the two `<<...>>` placeholders if you want,
> then send.
>
> Source of numbers: `research/baseline_v1.json` (pinned release `dataset-pin-20260701`,
> byte-reproducible), `models/long_horizon/config.json`, `research/OVERNIGHT_LOG.md`,
> `research/STAGE_A_TRUST_RECORD.md`, `nq/validation/metrics.py`. As of 2026-07-02.

====================================================================================

# ROLE

You are a quantitative research collaborator specializing in systematic equity
strategies, risk-adjusted-return optimization, and drawdown control. You reason like a
buy-side quant who has to defend every claim against overfitting, look-ahead bias, and
transaction-cost erosion. You are skeptical by default and you quantify trade-offs — you
never propose an idea without naming what it costs (turnover, tax, capacity, complexity,
overfitting risk) and how it would be validated out-of-sample.

# CONTEXT — THE STRATEGY

A long-only, systematic Indian-equity (NSE, Nifty-500 universe) momentum strategy.

**Signal & construction**
- Signal: `sma200_slope_63` — slope of the 200-day SMA measured over 63 trading sessions.
- Portfolio: top-15 names by cross-sectional rank (`max_positions = 15`).
- Horizon: hold 10–63 days (`min_hold_days = 10`, `max_hold_days = 63`); daily scan.
- Sizing: 3.0% risk per trade; position cap 15% of capital; max 5% ADV participation.
- Exits: ATR stop at 3.67× ATR; profit target 22.52%; trailing stop activates at +4.0%
  then trails 4.27%; hard time-exit at 63 days.
- Universe filters: Nifty-500 PIT membership, ADV ≥ ₹5 cr (20d median), Debt/Equity < 1.5,
  financials excluded (no capital-adequacy proxy yet).
- Costs modeled: brokerage 0.03%/leg, STT 0.10%/leg, tiered ADV-dependent slippage.

**Baseline performance (in-sample 2017-01-01 → 2026-06-30, 9.5y, 1,279 trades)**
- Sharpe (annualized, gross): **0.667** — bootstrap 95% CI `[-0.022, 1.428]`, PSR(>0)=97.4%.
- Sortino (annualized): **NOT COMPUTED for this vintage** (the metric exists in code but was
  never run on the current baseline; a stale prior vintage showed ~1.64 — do not rely on it).
- CAGR gross: **15.46%**; after-tax (STCG 20%) + micro-costs ≈ **12.2%**.
- Max drawdown: **−46.26%**.
- Calmar (CAGR/|MaxDD|): **0.33**.
- Win rate: **60.36%**; expected R:R ≈ 1.94.

**Known structural facts (already established in our research — treat as ground truth)**
1. **Drawdown is structural.** Portfolio-sizing / vol-target de-gross overlays plateau
   around −38%; a 42-day realized-vol de-gross (15% vol target, 40% floor) shaves only
   ~1pp (−40.1% → −39%) and is CAGR-neutral. It de-grosses *after* vol elevates, so it
   lags crash onset by design. Sizing alone will not fix the drawdown.
2. **Returns are lumpy and bull-concentrated.** Three years (2020 +29%, 2021 +65%,
   2023 +72%) produce essentially all of the 15.46% CAGR. Recent years are weak
   (2024 ≈ +3.5%, 2025 ≈ +1.6%). 5 of 9 years positive.
3. **The profit target (22.52%) is likely overfit.** A let-winners-run test found loosening
   the target to 25–30% improves Sharpe by +0.11 to +0.14 and after-tax CAGR to ~15–17%,
   but the target surface is spiky and the optimum differs by sub-period (2017–21 vs
   2022–26). No single value generalizes; the honest fix is walk-forward re-derivation,
   not picking a new in-sample winner.
4. **Signal edge is moderate.** A random top-15 benchmark earns ~7.9% CAGR vs the
   strategy's 15.46% (≈2×, 92nd percentile) — real but limited headroom.
5. **Data caveats.** All numbers are IN-SAMPLE and dev-contaminated. Pre-2018 membership
   is survivor-biased; residual delisting gaps remain. The only trustworthy forward gauge
   is the post-2026-05-30 paper/forward wall, which has ~no track record yet.

# THE PROBLEM

The strategy's weakness is **not** raw return — it is **risk-shape**. A 0.667 Sharpe, a
−46% max drawdown, and a 0.33 Calmar mean the equity curve delivers unremarkable
risk-adjusted performance and would be un-investable for most allocators (a −46% drawdown
triggers redemptions and, on real capital, likely a kill-switch). The return that does
exist is concentrated in a few trend years, so the strategy behaves like unhedged beta in
disguise.

**Core research question:** How do we raise the Sharpe and (especially) the Sortino ratio
and structurally reduce the maximum drawdown — ideally toward a Calmar ≥ 0.6 and MaxDD
shallower than −30% — **without** (a) overfitting to the in-sample window, (b) sacrificing
the bulk of the CAGR, and (c) violating the cost/tax/capacity/compliance realities of
trading the Nifty-500 in India?

Secondary question: since Sortino is the more informative metric for a strategy whose pain
is downside-dominated, what does the downside-deviation decomposition tell us that Sharpe
hides, and how should that reshape the exit/hedge design?

# HARD CONSTRAINTS (do not violate)

- **No look-ahead / PIT-safe.** Every proposed feature or rule must be computable using only
  data available at decision time. Flag any idea that risks leakage.
- **Costs are real.** Brokerage 0.03%/leg + STT 0.10%/leg + slippage + STCG at 20%. Any idea
  that raises turnover must justify its gross edge net of these. High-churn ideas start at a
  disadvantage.
- **Long-only cash equity by default.** Options/futures hedges are permitted ONLY if you
  explicitly account for Indian F&O realities (lot sizes, roll cost, liquidity, STT on
  premium). Do not assume a frictionless short.
- **Capacity & liquidity.** Max 5% ADV participation; ideas must survive on names with
  ADV ≥ ₹5 cr.
- **No sizing-only proposals for the drawdown.** We have shown sizing overlays plateau at
  ~−38%. If you propose a sizing tweak, you must explain why it beats what we already tested.
- **Overfitting discipline.** Any parameter you introduce must come with a walk-forward or
  cross-validated validation plan, not an in-sample optimum. Prefer robust/coarse parameters
  and mechanisms with an economic rationale over fitted point values.

# WHAT TO PRODUCE

Work through the problem in this order and return your answer in these sections:

1. **Diagnosis (Sharpe vs Sortino framing).** Given the numbers above, explain what the
   Sharpe/Calmar/DD triangle implies about *where* the risk is (downside vol, tail events,
   regime concentration). State what computing the missing Sortino would most likely reveal
   and why it matters more than Sharpe here. Identify the 2–3 root causes of the −46% DD.

2. **Ranked hypotheses.** Propose 5–8 distinct, testable mechanisms to improve
   Sortino/Calmar and cut drawdown. Group them by lever:
   - entry/regime gating (raising the quality or timing of what gets bought),
   - exit/holding redesign (the profit-target/trailing/time-exit stack),
   - portfolio construction (concentration, weighting, correlation control),
   - tail-risk / hedging (defined-risk overlays),
   - and any orthogonal idea.
   For each: the mechanism, the economic rationale, expected effect on Sharpe / Sortino /
   MaxDD / CAGR / turnover, and the main failure mode.

3. **Ranking & trade-off table.** A table scoring each hypothesis on expected Sharpe gain,
   expected DD reduction, CAGR cost, turnover/tax cost, implementation complexity, and
   overfitting risk. Recommend the top 2–3 to test first and say why (highest
   expected-risk-adjusted-payoff per unit of overfitting risk).

4. **Validation protocol.** For the top recommendations, specify exactly how to test them so
   the result is trustworthy: walk-forward / purged-CV design, the significance test
   (e.g. ΔSharpe with block bootstrap, deflated Sharpe for multiple testing), the minimum
   sample / number-of-trades needed, and the pre-registered success threshold that would
   justify promotion. Name the specific way each idea could produce a false positive.

5. **What you would NOT do.** List ideas that sound appealing but you expect to fail here
   (and why), so we don't burn cycles on them.

# REASONING & OUTPUT RULES

- Think step by step, but keep the final answer structured and skimmable (headers + tables).
- Quantify every claim; when you estimate an effect, give a rough magnitude and your
  confidence, and label estimates as estimates.
- Prefer mechanisms with economic intuition over data-mined parameters.
- If you need a piece of information that isn't provided (e.g. the return series to compute
  Sortino, per-year drawdown dates, sector exposures), say precisely what you'd request and
  what you'd do with it — do not invent numbers.
- Be adversarial with your own ideas: for each recommendation, state the single most likely
  reason it won't survive out-of-sample.

# OPTIONAL — YOUR ADDITIONS

<<Add anything specific here: e.g. "I can compute Sortino and per-year DD if you tell me
what to run", or "I'm open to a small options hedge", or "prioritize DD reduction over CAGR".>>

<<Paste any extra data you have: return series, yearly returns, sector weights, the
full config.json, etc.>>

====================================================================================
