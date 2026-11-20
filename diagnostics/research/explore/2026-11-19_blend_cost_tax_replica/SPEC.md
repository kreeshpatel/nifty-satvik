# Spec: after-tax lot simulator for a 70/30 vol-targeted blend (independent re-derivation)

You are re-deriving numbers from this written spec and the three input files only. Do not read any code under
`/home/user/nifty-satvik/pipelines/` or `/home/user/nifty-satvik/nq/`, and do not read any file whose name begins with
`_pipeline` or ends in `blend_cost_tax.json`. Write your own implementation, in Python, in this directory.

## Inputs (`inputs/`)
- `daily.csv`: one row per trading session, 2019-03-05..2024-06-28 (1,313 sessions). Columns:
  - `mom_nav`, `swing_nav`: each book's pre-tax NAV in rupees. This is a sleeve unit's price.
  - `exposure_e_t`: the blend's equity exposure that session, between 0 and 1.
  - `liquid_px`: the liquid fund's price, net of its expense ratio.
  - `index_px`: unused here.
- `momentum_trades.csv`: realised trades of the momentum book ("0001") that exit in the window. `pnl` is in rupees
  at the book's own scale. Each row is one exit, including partial trims.
- `swing_ledger.csv`: realised trades of the swing book that exit in the window, with `net_pnl` in rupees. Trades
  still open at the end are already excluded.

## Instruments and costs
- `MOM` and `SW` are sleeve units, priced at `mom_nav` and `swing_nav`.
- `LIQ` is the liquid fund, priced at `liquid_px`.
- Trading costs, charged as a fraction of traded value:

  | instrument | buy | sell |
  |---|---|---|
  | MOM, SW | 0.2190% | 0.2040% |
  | LIQ | 0.005% | 0.001% |

- Each buy opens a lot: units, cost per unit and purchase date.
- Each sell consumes lots first-in-first-out.
- Cash earns nothing.

## The blend run
1. **Start.** Capital is ₹20,00,000 in cash at the first session.
2. **Each session, in this order:**
   1. **Pass-through.** For each book trade whose exit date maps to this session (an exit date that is not a
      session maps to the next session; exits after the last session are dropped):
      - Let u = units of that sleeve held now. If u > 0, a realised gain of u × pnl is booked.
      - It is long-term if the trade's (exit_date − entry_date) calendar days are > 365, otherwise short-term.
      - The cost basis of every open lot of that sleeve is raised by pnl per unit.
   2. **Tax day.** If this session is the last session on or before 31 March of a year, and it is not the final
      session of the window, settle that tax period (rules below). The tax is paid from cash.
   3. **Re-target.** NAV = cash + Σ units × price. The targets are:
      - MOM = NAV × e × 0.70
      - SW = NAV × e × 0.30
      - LIQ = NAV × (1 − e)

      Trade every instrument to its target, all sells first and then all buys. Cash is the residual.
3. **Gains from a sale.**
   - Each lot consumed realises units × (price − lot basis).
   - For MOM and SW, the gain is long-term if (sale date − lot date) is > 365 days, otherwise short-term.
   - Gains on LIQ are "slab".
   - Gains realised on a tax day after that day's settlement belong to the NEXT tax period.
4. **End of window.** At the final session, after the normal steps, sell every unit at that close (costs
   apply), then settle the final period.
5. **Settlement of a period** (net short-term ST, net long-term LT, slab SL; cfST and cfLT are carried-forward
   losses):
   - STloss = max(−ST, 0) + cfST; STgain = max(ST, 0)
   - LTloss = max(−LT, 0) + cfLT; LTgain = max(LT, 0)
   - Set off in this order, each step taking the smaller amount from both sides:
     1. LTloss against LTgain
     2. STloss against STgain
     3. remaining STloss against remaining LTgain
   - tax = 20% × STgain + 12.5% × max(LTgain − 1,25,000, 0) + 30% × max(SL, 0)
   - Carry forward the remaining STloss and LTloss.
   - Reset ST, LT and SL to 0.
6. **CAGR** = (final cash / 20,00,000) ^ (365.25 / calendar days from first to last session) − 1.

Run variants:
- **after-tax:** as above.
- **pre-tax:** settlement tax is always 0.
- **pre-tax, no costs:** as pre-tax, with every trading cost set to 0.

## What to report (write `RESULT.md` here, with numbers only from your own code)

**A. Anchors.** After-tax CAGR, pre-tax CAGR and no-cost pre-tax CAGR, in %, to 2 decimals.

**B. STCG/LTCG split (after-tax run).** Every realised gain event is one "exit": either one pass-through (one book
trade) or one lot consumed by a sale. Bucket each exit by holding days (0-30, 31-90, 91-180, 181-330, 331-364, 365+).
Report, for each source, bucket and class, the count and the sum of rupee gains. The sources are:
- pass-through
- wrapper unit sales during the run
- the terminal liquidation
- the liquid fund (slab)

Also report:
- the total tax per period, and in total
- per class over the whole run: count, gain and tax, where class tax = Σ over periods of that period's ST tax or
  LT tax
- the "331-364 ceiling": re-label every exit with 331-364 holding days as long-term, keep the same gains, recompute
  every period's tax with carry-forwards, and report the total tax difference

**C. Rebalance cost by trade size (pre-tax run).**
- **Trades.** Every instrument-session trade. Exclude the first session's purchases and the terminal liquidation.
- **size** = |trade value| / NAV of that session before trading.
- **Report:**
  - n, total cost, total turnover
  - size percentiles p10, p50, p90 and p99 (in % of NAV)
  - the share of total cost and of total turnover from trades of size < 0.5%, 0.5-1%, 1-2% and > 2%
  - for bands of 0.5%, 1% and 2%: the cost of the trades below the band

**D. Diagnostic (does not block anything).** An earlier independent replica of this simulator got 19.52% after-tax
CAGR where the reference pipeline gets 19.26%. Report your own after-tax CAGR. Then test which single modelling
choice moves the result by about +0.26pp. Change ONE thing at a time and report the after-tax CAGR of each variant:
1. pass-through gains booked on the session AFTER the exit date
2. tax settled on the first session of April instead of the last session on or before 31 March
3. same-day post-settlement sale gains assigned to the CURRENT period, not the next
4. no cost on the trades that fund a tax payment (approximate: no cost on tax-day trades)
5. LIFO instead of FIFO
6. no basis step-up on pass-through (lots keep their purchase basis)
7. the long-term threshold at ≥ 365 days instead of > 365
8. any other choice you think plausible

Name the component that closes the gap (costs, tax timing, lot ordering, or financial-year boundary), or say that
none does.
