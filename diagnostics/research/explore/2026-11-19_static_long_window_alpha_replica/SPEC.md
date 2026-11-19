# Spec: one static after-tax point and one alpha regression (independent re-derivation)

Re-derive the numbers below from this spec and `inputs/` only. Do NOT read anything under
`/home/user/nifty-satvik/pipelines/`, `/home/user/nifty-satvik/nq/`, `/home/user/nifty-satvik/diagnostics/` or any
`.cache` folder. Write your own Python in this directory. Use the repo venv
(`source /home/user/nifty-satvik/.venv/bin/activate`) for numpy and pandas; statsmodels is not installed, so write the
Newey-West estimator yourself.

## Part 1 — static 60/40 index/arbitrage, after tax, 2017-01-02..2026-06-30

**Input:** `inputs/step1_daily.csv`, one row per session, with columns:
- `index_px`: the index fund's unit price;
- `arbitrage_px`: the arbitrage fund's unit price.

**Instruments and costs.**
- Both instruments are mutual funds. Buy cost 0.005%, sell cost 0.001%, as a fraction of the value traded.
- Each buy opens a lot (units, cost per unit = price, date). Sells consume lots first-in-first-out.
- Cash earns nothing.

**Tax.**
- Both instruments are equity for tax. A gain is long-term if (sale date − lot date) is > 365 calendar days, otherwise
  short-term.
- Settlement of a period (net ST, LT; carried losses cfST, cfLT):
  - STloss = max(−ST, 0) + cfST; STgain = max(ST, 0)
  - LTloss = max(−LT, 0) + cfLT; LTgain = max(LT, 0)
  - Set off in this order, each step taking the smaller amount from both sides:
    1. LTloss against LTgain
    2. STloss against STgain
    3. remaining STloss against remaining LTgain
  - tax = 20% × STgain + 12.5% × max(LTgain − 1,25,000, 0)
  - Carry forward the leftover losses, and reset ST and LT.

**Run.** ₹20,00,000 cash at the first session. Each session, in order:
1. **Tax day.** If this is the last session on or before 31 March of a year, and not the final session, settle the
   period and pay the tax from cash. Gains realised later that same session belong to the next period.
2. **Re-target.** Only on the first session and on tax days. NAV = cash + Σ units × price; targets are
   index = NAV × 0.60 and arbitrage = NAV × 0.40. All sells first, then all buys; cash is the residual.
3. **Record** the mark-to-market NAV (cash + Σ units × price).

**At the final session**, after steps 1–3: sell every unit (costs apply), then settle the final period.

**Report.**
- **After-tax CAGR** = (final cash / 20,00,000) ^ (365.25 / calendar days first→last session) − 1, in %.
- **p95 156-week drawdown** of the recorded daily NAV:
  - Weekly series = the last value of each week ending Friday; w = pct change, first dropped.
  - T = len(w), h = 156, n = 10,000. `rng = numpy.random.default_rng(20261118 + 1000*8 + 156)`.
  - Draw in this order: `idx[:,0] = rng.integers(0, T, n)`; `jump = rng.random((n, h)) < 1/8`;
    `fresh = rng.integers(0, T, (n, h))`.
  - For k ≥ 1: `idx[:,k] = fresh[:,k]` where jump, else `(idx[:,k-1] + 1) % T`.
  - Path NAV = [1, cumprod(1 + w[idx])]; depth = max(1 − NAV / running max) × 100.
  - Report the 95th percentile.
- **Total tax paid.**

## Part 2 — alpha of the blend over the index fund, 2019-03..2024-06, weekly

**Input:** `inputs/step2_daily.csv`, with columns:
- `blend_net_nav`: the blend's pre-tax, net-of-cost daily NAV;
- `index_fund_px`: the index fund's price.

**Returns.** Weekly returns of each = the last value of each week ending Friday, pct change, first dropped. Align on
common weeks.

**Regression.** rf_w = 1.065^(1/52) − 1. Regress (blend − rf_w) on a constant and (index − rf_w) by OLS.

**Newey-West standard error of the intercept.**
- Bartlett weights w_l = 1 − l/(L+1), L = 8.
- S = Σ_t x_t x_t' e_t² + Σ_{l=1..L} w_l Σ_t (x_t e_t e_{t−l} x_{t−l}' + its transpose).
- V = (X'X)⁻¹ S (X'X)⁻¹, with no small-sample correction.

**Report.**
- alpha annualised = 52 × intercept, in %;
- beta;
- t = intercept / sqrt(V[0,0]);
- R²;
- n.
- The CAGR of a "beta-matched mix", whose weekly return is beta × index + (1 − beta) × rf_w: compound the weekly
  returns over the period, with years = (last week date − first week date + 7 days) / 365.25.

Write `RESULT.md` with these numbers, and list any ambiguity in the spec and the reading you chose.
