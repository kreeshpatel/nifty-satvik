# Spec: two points of an after-tax frontier (independent re-derivation)

Re-derive two numbers from this spec and the files in `inputs/` only. Do NOT read anything under
`/home/user/nifty-satvik/pipelines/`, `/home/user/nifty-satvik/nq/`, `/home/user/nifty-satvik/diagnostics/`, or any
`.cache` folder. Write your own Python, in this directory. Use numpy 2.x `numpy.random.default_rng` for the bootstrap
(`source /home/user/nifty-satvik/.venv/bin/activate` gives the same numpy as the reference).

## Inputs (`inputs/`)

- **`daily.csv`**: one row per trading session, 2019-03-05..2024-06-28 (1,313 sessions). Columns:
  - `mom_nav`, `swing_nav`: the pre-tax NAVs of two trading books. These are the unit prices of the sleeves MOM and SW.
  - `mom_ret`, `swing_ret`: each book's daily return. Use them only for the volatility rule.
  - `index_px`: the index fund's unit price (IDX).
  - `arbitrage_real_px`: the arbitrage fund's unit price (ARB). It is net of expenses.
  - `liquid_real_px`: unused.
- **`momentum_trades.csv`**: realised trades of book MOM that exit inside the window. `pnl` is in rupees at the book's
  own scale. Each row is one exit, partial trims included.
- **`swing_ledger.csv`**: realised trades of book SW that exit inside the window, with `net_pnl` in rupees.
- **`open_positions_at_cut.csv`**: positions still open at the last session. Columns:
  - `sleeve`: MOM or SW;
  - `gain`: rupees at the book's own scale;
  - `days`: calendar days held at the last session.

## Instruments, costs, lots

- **Costs** are a fraction of the value traded:

  | instrument | buy | sell |
  |---|---|---|
  | MOM, SW | 0.2190% | 0.2040% |
  | IDX, ARB | 0.005% | 0.001% |

- **Lots.** A buy opens a lot (units, cost per unit = price, purchase date). A sell consumes lots first-in-first-out.
- **Cash** earns nothing.
- **Tax class.** Every instrument is equity for tax. A gain is long-term if (sale date − lot date) is > 365 calendar
  days, otherwise short-term.

## Run (₹20,00,000 cash at the first session)

**Each session, in order:**

1. **Pass-through** (MOM and SW only). For each book trade whose exit date maps to this session (an exit date that is
   not a session maps to the next session; exits after the last session are dropped):
   - Let u = units of that sleeve held now. If u > 0, book a realised gain of u × pnl (`net_pnl` for SW).
   - The gain is long-term if (exit_date − entry_date) calendar days are > 365, otherwise short-term.
   - Add pnl per unit to the cost basis of every open lot of that sleeve.
2. **Tax day.** If this is the last session on or before 31 March of a year, and not the final session, settle the
   period (rules below). The tax is paid from cash. Gains realised later that same session belong to the next period.
3. **Re-target.** NAV = cash + Σ units × price. Trade every instrument to its target, all sells first and then all
   buys. Cash is the residual.
4. **Record** the mark-to-market NAV (cash + Σ units × price) after trading.

**At the final session**, after steps 1–4:
1. Apply the open-position pass-through: for every row of `open_positions_at_cut.csv`, the same rule as step 1, with
   `gain` as pnl and `days` deciding the class (> 365 = long-term).
2. Sell every unit at that close, costs applying.
3. Settle the final period.

**Settlement** (net ST, LT; carried-forward losses cfST, cfLT):
- STloss = max(−ST, 0) + cfST; STgain = max(ST, 0)
- LTloss = max(−LT, 0) + cfLT; LTgain = max(LT, 0)
- Set off in this order, each step taking the smaller amount from both sides:
  1. LTloss against LTgain
  2. STloss against STgain
  3. remaining STloss against remaining LTgain
- tax = 20% × STgain + 12.5% × max(LTgain − 1,25,000, 0)
- Carry forward the leftover losses, and reset ST and LT to 0.

## The two books

**Point A — blend, target volatility 10%.**
- Daily re-target, every session: MOM = NAV × e × 0.70, SW = NAV × e × 0.30, ARB = NAV × (1 − e).
- r_t = 0.70 × mom_ret + 0.30 × swing_ret.
- vol_t = the sample standard deviation (ddof 1) of r over the 20 sessions ending at t−1, × √252.
- e_t = min(1, 0.10 / vol_t). e_t = 1 when vol_t is undefined (the first 20 sessions).

**Point B — static 65/35.**
- Re-target only at the first session and on each tax day (after the tax is paid): IDX = NAV × 0.65,
  ARB = NAV × 0.35.
- No pass-through: the book holds no sleeves.

## Metrics, for each point

- **After-tax CAGR** = (final cash / 20,00,000) ^ (365.25 / calendar days from first to last session) − 1, in %.
- **p95 drawdown.** Take the recorded daily NAV; weekly series = last value of each week ending Friday; weekly
  returns w = pct change, first dropped.
  - Bootstrap: T = len(w), h = 156, block b = 8, n = 10,000.
  - `rng = numpy.random.default_rng(20261118 + 1000*8 + 156)`.
  - `idx[:,0] = rng.integers(0, T, n)`; then `jump = rng.random((n, h)) < 1/8`; then `fresh = rng.integers(0, T, (n, h))`.
    Draw them in exactly that order.
  - For k = 1..h−1: `idx[:,k] = fresh[:,k]` if `jump[:,k]`, else `(idx[:,k−1] + 1) % T`.
  - Each path: NAV = [1, cumprod(1 + w[idx])]. Drawdown depth = max over the path of (1 − NAV / running max) × 100.
  - Report the 95th percentile (numpy default interpolation) of the n depths.
- **Excess Sharpe** of the daily NAV returns: (mean(r) − rf_d) / std(r, ddof 1) × √252, with rf_d = 1.065^(1/252) − 1.
- **Total tax paid.**

Write `RESULT.md` with these four numbers for each point. Also list any place where the spec was ambiguous and which
reading you chose.
