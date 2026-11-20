# EXPLORATORY — drawdown-switched beta hedge, and pre-extension breakouts as their own sleeve (2026-10-20)

**Tier 0 · EXPLORE** (`docs/PROCESS_TIERS.md`). No pre-registration, no screen row, no n_trials change.
Standing counts, read from the ledgers: **screens 23 · sealed opens 3 · n_trials 2** (unchanged).
Everything below is on the **train window, 2019-01-01..2024-06-30**; prices were cut at 2024-06-30 and the
cut asserted before the engine saw them; the sealed slice (2024-07-01..2026-06-30) was never loaded.
Nothing here is a threshold, a pass, or a live change. Both items are "suggests / worth testing" at most.

**Book.** Live configuration through `nq.lab.runs.replay(DEFAULT_CONFIG)`: manifest `LIVE BOOK`
(`is_live_book` true, `differs_on` empty, membership **pit**, config hash `fe1702d1…`, window
2019-01-01..2024-06-30, data vintage 2024-06-28). Reproduces the anchor: Sharpe 1.025, CAGR 20.5%,
MaxDD −40.1%, 77 trades.

**Deflation.** Deflated Sharpe = `nq.lab.runs.deflated_sharpe` (per-window basis, as the lab). It is
shown beside raw everywhere, with N = every variant evaluated in that script (Item 2: 13; Item 3: 20),
so it is a conservative within-note deflation, **not** the program n_trials. The control's own deflated
Sharpe is 0.28 (Item 2 basis) and 0.20 (Item 3 basis): at this N, a raw Sharpe near 1.0 is not
distinguishable from the best of N noise draws. Sub-periods are continuous slices of the one full run.

---

## Item 2 — drawdown-switched Nifty beta hedge (a bound; no engine change)

Script `pipelines/diagnostics/explore_hedge_overlay_20261020.py` → `diagnostics/research/explore/hedge_overlay_20261020.json`.

**Construction.** Short Nifty notional = h × β × book equity. β = trailing-63d OLS slope of book vs Nifty
daily returns ending the **prior** day (floored at 0; hedge OFF until 63 returns exist). ON on day t only
if the Nifty **prior close** is ≥ X% below its trailing-252d high; OFF otherwise. Costs: 0.02% per side
on every change in hedge notional, plus roll 0.05%/month (0.05%/21 per day) on notional while on.
**Assumed, not modelled:** futures track spot (no basis, carry, dividend, or margin-funding drag), and the
hedge margin comes out of nowhere (the book's cash drag is ignored). Both flatter the hedge. X ∈ {5,10}
and h ∈ {0.5,1.0} are all stated; none is picked.

**Causal results (the honest ones).**

| variant | Sharpe raw | Sharpe deflated | CAGR | MaxDD | Calmar | worst year | time hedged | 2019-21 Sh / DD | 2022-24H1 Sh / DD |
|---|---|---|---|---|---|---|---|---|---|
| **unhedged** | 1.025 | 0.281 | 20.5% | −40.1% | 0.51 | 2022 −3.9% | 0% | 1.03 / −40.1% | 1.03 / −25.2% |
| X5 h0.5 | 0.961 | 0.217 | 16.8% | −32.5% | 0.52 | −10.3% | 34.8% | 1.02 / −32.5% | 0.88 / −25.2% |
| X5 h1.0 | 0.790 | 0.046 | 12.8% | −30.6% | 0.42 | −16.6% | 34.8% | 0.90 / −27.8% | 0.64 / −30.6% |
| X10 h0.5 | 1.013 | 0.270 | 18.6% | −34.3% | 0.54 | −6.9% | 12.6% | 1.03 / −34.3% | 0.99 / −24.4% |
| X10 h1.0 | 0.935 | 0.192 | 16.5% | −31.1% | 0.53 | −10.0% | 12.6% | 0.94 / −31.1% | 0.93 / −24.9% |

(The unhedged full-window −40.1% sits in 2019-21, COVID.)

**Clairvoyant ceilings (upper bounds, NOT achievable).** *Zero-lag* = same trigger but using the same-day
state (peeks one day). *Peak-to-trough* = hedged exactly from the peak to the trough of every Nifty
drawdown episode that reached X% (perfect timing of both ends).

| variant | zero-lag Sh / CAGR / DD | peak-to-trough Sh (defl) / CAGR / DD / Calmar | time hedged |
|---|---|---|---|
| X5 h0.5 | 1.307 / 23.9% / −28.8% | 1.490 (0.746) / 29.0% / −27.6% / 1.05 | 34.2% |
| X5 h1.0 | 1.517 / 27.0% / −19.8% | 1.924 (1.180) / 37.8% / −16.9% / 2.24 | 34.2% |
| X10 h0.5 | 1.193 / 22.6% / −29.7% | 1.354 (0.610) / 26.4% / −27.6% / 0.96 | 21.3% |
| X10 h1.0 | 1.304 / 24.5% / −22.7% | 1.646 (0.902) / 32.2% / −16.9% / 1.91 | 21.3% |

**Reading (exploratory).**

1. **The causal trigger buys drawdown depth with return, and Sharpe does not improve.** Every causal variant
   cuts MaxDD (−40.1% → −30.6% to −34.3%) and every one has lower or equal Sharpe and lower CAGR. The
   cheapest in Sharpe terms is X10 h0.5 (Sharpe −0.01, CAGR −1.9pp, MaxDD +5.8pp, hedged 12.6% of days),
   which is a risk dial, not an edge. The h=1.0 variants are worse than the unhedged book on worst year.
2. **Why it loses: bounces.** On hedge-ON days the book and the Nifty both had *positive* mean daily
   return (X5: book +0.100%/day, Nifty +0.110%/day; X10: book +0.235%, Nifty +0.168%). Being ≥5-10% under
   the 252d high is on average a rebound state in this window, and the book, which rebounds harder than the
   index, gives the gain away on the short leg. The hedge is right in the leg down and wrong in the leg up.
3. **The ceiling is large, so timing is the whole question.** With perfect peak-to-trough timing the
   hedge lifts Sharpe to 1.35-1.92 and cuts MaxDD to about −17%. The causal-to-clairvoyant gap (0.8-1.1
   Sharpe) is the price of not knowing the trough; a 252d-high trigger recovers none of it. Even the
   zero-lag ceiling (one day of foresight) gains 0.2-0.5 Sharpe, so the result is sensitive to a single
   day of signal delay: that is a warning about any trigger of this family, not a finding.
4. **Beta in drawdowns, against 0142's correction.** Rolling β averaged 0.66 over the window, **0.75**
   on hedge-ON days. Pooled OLS β of the book on the Nifty over ON days ex-COVID (2020-02-15..06-30
   removed) is 0.82 (X5, 390 days) and 0.91 (X10, 96 days), not 1.03. This is *not* a refutation of 0142
   (its beta/holdings-correlation definition was not reconstructed here, and 96 days is thin); it only
   says the hedge sized by trailing β is, if anything, over-hedged on average when the book's drawdown
   beta is below 1 and sub-1 betas are noisy at 63d.
5. **Sub-periods.** Hedge costs are small (turnover plus roll) next to the bounce effect; the damage is
   concentrated in 2022-24H1 for h=1.0 (Sharpe 0.64-0.93 vs 1.03).

**What would change the answer.** A different trigger. The cheapest next test, if the owner wants this
pursued, is a *breadth or volatility-state* trigger (not price-vs-high), judged against the peak-to-trough
ceiling above, which already tells us the prize (about +0.4 to +0.9 Sharpe, MaxDD to −17%) before any
trigger is tried. A trigger that recovers a third of that ceiling would be worth a pre-registered screen.

**Not a recommendation, whatever the result.** Acting on this means **F&O, a new instrument for a
cash-only book**: lot-size granularity at ₹10L (a Nifty future is far larger than a 0.5 × 0.66 × 10L
notional of about ₹3.3L), margin, MTM cash flow, and tax/compliance treatment. That is an owner decision
regardless. This is a **different mechanism from 0095** (book vol-targeting, KILL), which cut gross
exposure and redeployed the cash; this keeps the book whole and shorts an index against it.

---

## Item 3 — pre-extension breakouts as their own capital sleeve

Script `pipelines/diagnostics/explore_breakout_sleeve_20261020.py` → `diagnostics/research/explore/breakout_sleeve_20261020.json`.

**What STAGE4 (`scripts/diag_sleeves.py`) actually was.** Mechanism reused (filter a copy of P to a set of
setup origins, one engine run per sleeve, sum equity curves). But: it used **PIT membership** (so that is
not its defect), the **old P2 exit** (`no_time_cap, wk20_trail 4%, blowoff 2.5R`), **no Grade-A gate**,
`start=2017-01-01`, and `corrected_universe()` **uncut** (it saw the sealed slice). Its sub-periods were
continuous slices. So it is evidence about the P2-exit regime on an uncut window; for the live book it is
weak, and it is not the verdict that should close this.

**Construction here.** Live exit (config P), live discipline, live staleness, `LIVE_PREP`, PIT membership,
train-only. One wide P with `box_breakout`, `sr_pivot` (origin 3, the chart-validated pivot S/R breakout;
the older crude `sr_breakout` assigns no origin and is not used) and zoo origins 6 (cup/handle) and 8
(double bottom); touch signals are unchanged because every detector is additive. Sleeves filter that P to
an origin set. The Grade-A gate (top-5 by CRS distance per setup week) is applied **inside each sleeve**,
among that sleeve's own signals. **Seat cap N = `max_positions=N`**, sizing otherwise exactly live (2% risk,
10% max stop, 20% max notional); it is not a re-spread of notional. The touch-only control is
**byte-identical** to the lab replay (asserted). Splits are fixed at t0, not rebalanced.

### (a) Coverage

Per year on 2019-01-01..2024-06-30, **before** the Grade-A gate (all signals incl. non-members), and the
Grade-A signals that are PIT members, fillable (next open inside the signal-week range) and pre-extension
(open < 10% over the signal-week 44w SMA):

| origin | signals / yr | fillable / yr | pre-extension (<10%) share of fillable | <20% share | Grade-A fillable / yr | …of which <10% |
|---|---|---|---|---|---|---|
| touch44 (control) | 863 | 578 | **54.8%** | 95.0% | 138 | 21.7 |
| box | 850 | 577 | **0.09%** | 11.5% | 133 | 0.2 |
| sr_pivot | 105 | 66 | **0.8%** | 33.8% | 57 | 0.5 |
| cup_handle | 339 | 219 | 0.4% | 25.4% | 102 | 0.4 |
| double_bottom | 919 | 572 | 0.6% | 21.8% | 115 | 0.4 |

**Headline of the coverage check: "pre-extension breakout" is close to an empty set.** A box or S/R
breakout fires after the name has held above a rising 44w SMA for 8+ weeks (box) or cleared a prior
resistance, so its next open is almost never within 10% of the line (median open is +25% to +32% over the line for the four breakout families, against +9% for touch);
under a live 20% ext cap only 11-34% of fillable box/S-R signals even pass. The funnel 0123 names as its
re-open condition ("enter before the extension") is therefore largely a *touch-family* object in this
engine. The 10%-capped breakout sleeve below runs on **8 trades in 5.5 years**.

### (b)/(c) Sleeves and splits (Sharpe raw / deflated, N = 20)

Standalone sleeves, each on its own ₹10L:

| sleeve | trades | Sharpe | defl | CAGR | MaxDD | Calmar | worst yr | 2019-21 / 2022-24H1 Sh | corr with touch | top-2 share of gross gains |
|---|---|---|---|---|---|---|---|---|---|---|
| **touch-only (control)** | 77 | 1.025 | 0.195 | 20.5% | −40.1% | 0.51 | −3.9% | 1.03 / 1.03 | — | 23% |
| shared 5-seat touch+box+sr | 53 | 0.877 | 0.047 | 13.9% | −31.3% | 0.45 | +3.0% | 1.12 / 0.52 | 0.73 | 30% |
| box+sr, 5 seats | 32 | 0.857 | 0.028 | 8.3% | −15.1% | 0.55 | −2.3% | 0.88 / 0.83 | 0.52 | 36% |
| box+sr, 8 seats | 38 | 0.769 | −0.061 | 8.2% | −19.8% | 0.42 | −6.9% | 0.67 / 0.93 | 0.54 | 31% |
| box+sr+cup+dbl, 5 seats | 24 | 1.683 | 0.853 | 20.0% | −13.6% | 1.47 | +1.7% | 1.54 / 2.09 | 0.54 | 38% |
| box+sr+cup+dbl, 8 seats | 28 | 1.558 | 0.728 | 22.0% | −19.0% | 1.16 | +5.6% | 1.34 / 2.27 | 0.54 | 35% |
| box+sr, ext cap 10%, 5 or 8 seats | 8 | 0.445 | −0.384 | 1.9% | −7.1% | 0.27 | −2.4% | 0.26 / 1.01 | 0.36 | 100% |

Summed with touch (touch share first):

| combo | Sharpe | defl | CAGR | MaxDD | Calmar | worst yr | 2019-21 / 2022-24H1 Sh |
|---|---|---|---|---|---|---|---|
| touch alone (control) | 1.025 | 0.195 | 20.5% | −40.1% | 0.51 | −3.9% | 1.03 / 1.03 |
| 60/40 touch + box+sr (5 seats) | 1.075 | 0.246 | 16.3% | −29.6% | 0.55 | −1.7% | 1.08 / 1.07 |
| 50/50 touch + box+sr (5 seats) | 1.084 | 0.254 | 15.1% | −27.0% | 0.56 | −1.0% | 1.09 / 1.07 |
| 60/40 touch + box+sr (8 seats) | 1.045 | 0.215 | 16.2% | −31.8% | 0.51 | −2.2% | 1.02 / 1.08 |
| 50/50 touch + box+sr (8 seats) | 1.042 | 0.213 | 15.1% | −29.8% | 0.51 | −1.7% | 1.01 / 1.09 |
| 60/40 touch + zoo (5 seats) | 1.322 | 0.492 | 20.3% | −26.5% | 0.77 | −0.1% | 1.29 / 1.40 |
| 50/50 touch + zoo (5 seats) | 1.410 | 0.580 | 20.3% | −23.5% | 0.86 | +0.9% | 1.36 / 1.52 |
| 60/40 touch + zoo (8 seats) | 1.315 | 0.485 | 21.1% | −29.3% | 0.72 | −0.1% | 1.24 / 1.48 |
| 50/50 touch + zoo (8 seats) | 1.388 | 0.558 | 21.3% | −27.0% | 0.79 | +0.9% | 1.28 / 1.63 |
| 60/40 and 50/50 touch + box+sr ext-cap-10% | 1.034-1.035 | 0.204-0.206 | 12.9-14.6% | −24.0 to −27.3% | 0.54 | −3.4 to −3.5% | 0.99-1.01 / 1.07-1.08 |

("zoo" = box + sr_pivot + cup_handle + double_bottom.)

**Reading (exploratory).**

1. **Box + S/R alone is a weaker book than touch, with a shallow drawdown.** Sharpe 0.77-0.86 against
   1.025, CAGR 8% against 20.5%, MaxDD −15 to −20% against −40%. It is diversifying (daily-return
   correlation 0.52-0.54 with touch, against 0.73 for the shared-book variant, which is mostly touch
   trades). Giving it more seats (8) is *worse*, not better: more small positions, lower Sharpe and
   CAGR, the dilution of 0131 reproduced inside the sleeve.
2. **Summed with touch, box+S/R is a drawdown dial, not an edge.** 60/40 or 50/50 lifts raw Sharpe by
   +0.05 to +0.06 (1.075 / 1.084), well inside noise, cuts MaxDD by 8.3-13.1pp, and costs 4-5pp of CAGR
   because half the capital earns 8%. Calmar +0.04 to +0.05. Deflated Sharpe 0.25 vs 0.195.
3. **Adding cup/handle and double-bottom changes the picture**, and it is the only arm with a notable
   number: the 5-seat zoo sleeve alone reads Sharpe 1.68, MaxDD −13.6%, CAGR 20% (matches touch's CAGR at a
   third of its drawdown), and 50/50 with touch reads **Sharpe 1.41 (deflated 0.58), CAGR 20.3%, MaxDD
   −23.5%, both sub-periods ≥1.36**. **Caution that dominates the reading:** that sleeve is **24-28
   trades in 5.5 years**; its two largest trades are 35-38% of gross gains (ALKYLAMINE entered
   2020-03-13, +₹4.3L on ₹10L; VBL 2022-05-19 +₹3.3L), with per-trade R wildly inflated by
   near-zero stops on some COVID-low entries (DEEPAKNTR 2020-03-13: stop 0.5% below entry, R 218), so mean R is meaningless and the NAV is carried by a
   handful of 5-8x names. n=24 cannot certify a Sharpe of 1.68. It is a *lead*, not a result.
4. **The mechanism applies here as predicted** (program-laws II: 0131's dilution applies only inside shared
   seats): the shared 5-seat touch+box+sr book is worse than touch alone (0.877 vs 1.025, CAGR 13.9%),
   while the same signals in their own capital reach a combined 1.08-1.41. Separating capital does remove the
   cannibalisation; what it cannot do is create a standalone breakout edge: box+S/R alone is below
   touch on Sharpe and CAGR.
5. **Pre-extension (program-laws I).** The sleeve that would test the 0123 re-open ("buy before the
   extension") has 8 trades in 5.5 years: **UNDERPOWERED**, not a no. Sharpe 0.445 on 8 trades is
   uninformative either way. Whether pre-extension breakouts exist at all is a *signal definition* issue:
   with these detectors they almost never fire near the line.
6. Not run: breakout sleeves without the Grade-A gate, other splits, rebalancing, and a joint sleeve with
   a different ext cap (e.g. 15%). The cheapest test that would change the picture is the **zoo sleeve on
   a longer or independent sample** (it cannot be extended here without touching the sealed slice) or a
   **per-trade R / %-of-equity comparison on the uncapped ledger**, which is how the zoo's edge was first
   shown (0131), and is not a capped-NAV question.

---

## Provenance and checks

- Manifests: both scripts assert `is_live_book` and `membership == "pit"`; the touch-only sleeve NAV is
  byte-identical to the lab replay. Data vintage 2024-06-28.
- Tests run before pushing, all passing (93): `tests/test_lab_runs.py`, `tests/test_replay_parity.py`,
  `tests/test_stage2_golden.py`, `tests/test_r94_golden.py`, `tests/test_standing_counts.py`. No `nq/**`
  or `config.py` edit, so the dependency map was not regenerated.
- Hedge assumptions that flatter the result: futures track spot, no carry/basis/dividend, no margin drag,
  no lot-size granularity. Sleeve assumptions: capital splits not rebalanced; cost impact scales with
  sleeve capital (small at ₹10L).
- Both results remain EXPLORATORY: not for a threshold, not a live change. Promotion goes up one tier
  (a tier-2 bound or tier-3 trial) before it can touch the book.
