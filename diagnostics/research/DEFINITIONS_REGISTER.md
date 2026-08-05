# The Definitions Register — what the load-bearing numbers actually mean

**Class: VERIFICATION / SEMANTIC. Zero trials, zero screens. Counts frozen: screens 15 · sealed
opens 1 · n_trials 138.** Nothing here re-runs a result, re-adjudicates a verdict, or proposes a
hypothesis. The 2026Q3 audit proved the arithmetic; this asks what the arithmetic *means*.

**Scope is decision-weighted and terminal.** A metric earns a row only if it feeds an **Oct-1
decision** or a **standing law**. The register is complete when every metric quoted in
[`oct1_binder_decisions.md`](oct1_binder_decisions.md) has a row. Nothing else is in scope.

**How to read a row.** *"Would a reader wrongly assume"* is the operative column — every entry below
is a case where the honest number and the natural reading diverge. **Verdict** is one of:

- **CLEAN** — definition and natural reading agree; nothing to do.
- **PRESENTATION** — the number is right, the label misleads. **Fixed at source in this commit.**
- **DOOR** — a different defensible reading changes what a decision should be. Routed to the binder
  with **both readings**, unweighed.
- **PARKED** — noticed, unmeasured, and deliberately not analysed here (fishing guard).

---

## Index

| # | metric | convention in one line | verdict |
|---|---|---|---|
| 1 | **R** (R-multiple) | price outcome ÷ that trade's own stop width | **DOOR** (open, binder §6–8) |
| 2 | **"R" the symbol** | means three different things in committed text | **PRESENTATION** |
| 3 | **`risk_pct`** | means two different things in committed code | **PRESENTATION** |
| 4 | **trade count** | `total_trades` = **closed only**; open positions excluded | **PRESENTATION** |
| 5 | **win rate** | wins ÷ **closed** trades; open winners invisible | **DOOR** (young-book bias) |
| 6 | **CAGR** | two committed year-denominators → 24.7 vs 25.21 same book | **DOOR** |
| 7 | **MaxDD** | grid-dependent: −42.4% daily vs −33% monthly, same family | **DOOR** |
| 8 | **Sharpe** | rf = **0**, daily × √252 (also √12 monthly in 0113) | **DOOR** (on `KILL_SHARPE`) |
| 9 | **sleeve correlation** | Pearson on **daily** returns; frequency unstated in 0115 | **PARKED** |
| 10 | **alpha** | vs Nifty-500 TRI, rf = 0, daily regression × 252 | **CLEAN** |
| 11 | **±10R/yr floor** | a blended R unit, empirically derived in those units | **DOOR** (open, binder §8) |
| 12 | **"screen"** | a pre-registered *study*, not a statistical comparison | **CLEAN** (self-disclosed) |
| 13 | **DSR / n_trials** | deflates on **arm-level** cumulative 138 (family-level 77) | **CLEAN** |
| 14 | **worst year / losing years** | calendar years; partial first/last count as whole | **PRESENTATION** |
| 15 | **expectancy_R** | mean R over **closed** trades — inherits row 5 | **DOOR** (with row 5) |
| 16 | **PBO** | 46.2% over 924 combos, 17 configs, **monthly** matrix | **CLEAN** |
| 17 | **live rupee weight / recovery %** | defined in the R-denominator audit | **CLEAN** (cite) |
| 18 | **Calmar** | CAGR ÷ \|MaxDD\| — inherits rows 6 **and** 7 | **DOOR** (with 6, 7) |

---

## 1. R (the R-multiple) — **DOOR, already open**

- **Population:** every closed trade in the substrate / capped book.
- **Denominator:** that trade's **own** stop width, `(entry − stop) / entry`. Not a common unit.
- **Frequency:** per trade.
- **Code:** `scripts/build_substrate.py:97` (stop width) · audit `scripts/diag_r_denominator_audit.py`.
- **Wrongly assume:** that 1R is a constant quantity of money. It is, in the **uncapped** run of
  record (fixed 2% risk). It is **not** in the live book, where `max_notional_pct` binds on 53.4% of
  trades and the rupees behind 1R fall to a median 0.918×, p10 0.359×.
- **Violated in published use?** No use *violates* its definition — but several quote R across books
  with different sizing regimes without saying which. Fully worked in finding 0129 and binder §6–8.
- **Status:** door already open (binder §6, §7, §8). **Not re-opened here.**

## 2. The symbol "R" — three meanings — **PRESENTATION (fixed)**

| usage | meaning | example in committed text |
|---|---|---|
| `R`, `expR`, `meanR` | R-**multiple** (P&L ÷ risk) | `+0.494 meanR` |
| "median R 13.7→9.1%" | **stop width %** (`riskpct`) | `run_bhanushali_cron.py:80`; `run_owner_discipline.py:79` |
| `R/yr` | R-**multiples per year** | the ±10R floor |

- **Wrongly assume:** that "median R of 14%" is a 14× return. It is a 14%-wide stop.
- **Fix:** the two comment sites now say "median stop width". No behaviour touched.

## 3. `risk_pct` — two meanings in code — **PRESENTATION (fixed)**

| site | value | meaning |
|---|---|---|
| `scripts/build_substrate.py:97` | `(en − st) / en × 100` | **stop width** as % of entry |
| `scripts/run_bhanushali_weekly_rank.py:884` | `sh × (en − st) / sizing_eq × 100` | **% of equity risked** |
| `scripts/run_bhanushali_practitioner.py:225` | same as above | **% of equity risked** |

- **Wrongly assume:** that the substrate's `risk_pct` (median 9.06, max 74.8) is equity at risk. A
  74.8 would be an impossible position; it is a 74.8%-wide stop.
- **Violated in published use?** **No** — every consumer found uses the local meaning correctly. This
  is a latent trap, not a live error. Clarifying comments added at all three sites.

## 4. Trade count — `total_trades` means **closed** — **PRESENTATION (fixed)**

- **Population:** closed trades only. `n_closed = len(led)` — the closed ledger.
- **Code:** `scripts/run_bhanushali_cron.py:468, 497` · `nq/paper/book.py:198` (`len(self.trades)`;
  `self.trades` is appended **only on close**, lines 116/125).
- **The 4 / 5 / 0 puzzle, resolved:** `results/paper_portfolio_weekly.json` currently reads
  `total_trades: 4` with `n_positions: 5`. Both are correct and consistent: **4 closed + 5 still
  open = 9 positions taken since inception.** The 2026-07-24 archive reads `total_trades: 0` with 4
  positions — 0 closed, 4 open. Nothing is wrong; the key is misnamed.
- **Wrongly assume:** that the book has taken 4 trades in total, or that `total_trades` tracks the
  **≥30 closed** paper gate ambiguously.
- **Violated in published use?** **No, and the gate is safe by luck of naming**: the scorecard reads
  `total_closed` (`bhanushali_review_scorecard.py:68`), a correctly-named key, not `total_trades`.
- **Fix:** clarifying comments at both sites. **The key is NOT renamed** — it is a published field in
  `results/output_contracts.json`, and renaming it is a contract change, not a wording fix.

## 5. Win rate — closed-only denominator — **DOOR**

- **Definition:** `wins / n_closed × 100`, `wins = (led["R"] > 0).sum()` —
  `run_bhanushali_cron.py:469, 472`. (`R > 0` and `P&L > 0` coincide, so that part is not a
  divergence.)
- **Wrongly assume:** that it estimates the book's eventual hit rate. It **excludes open positions**,
  and on a trend book losers stop out fast while winners stay open for months — so a young book's
  win rate is **biased low by construction** and rises as winners mature.
- **Both readings:** *closed-only* (what is printed: 51–54%) vs *mark-to-market including opens*
  (unmeasured here). With 4 closed and 5 open, the printed rate rests on 4 observations.
- **Routed to the binder.** No re-computation attempted (out of scope).

## 6. CAGR — two committed year-denominators — **DOOR**

| site | `yrs` | same book publishes |
|---|---|---|
| `scripts/run_bhanushali_sixstep.py:220` (`_row`, the swing print) | `(last − first).days / 365.25` — **calendar years** | **24.7%** |
| `scripts/run_corrected_anchor.py:52` | `len(r) / 252` — **trading-bar years** | **25.21%** |
| `nq/validation/metrics.py:43` (canonical) | `n / 252` — **trading-bar years** | — |

- Both are applied to the **same book** (Sharpe 1.132, MaxDD −42.4 in
  `lh_solvency_bracket.json` and in the registry), which is why one book carries two CAGRs.
- **Wrongly assume:** that 24.7 and 25.21 are different books, different periods, or an error. They
  are the same equity curve under two year-denominators; bar-years are the shorter denominator, so
  they print the **higher** CAGR.
- **Violated in published use?** No site violates *its own* definition. The risk is **cross-document
  comparison**, and one comparison class is genuinely exposed: any **book-vs-benchmark** CAGR gap is
  only valid if both sides use the same denominator. (Finding 0114 is *not* an instance — it
  compares monthly book returns to monthly ETF NAVs on one convention, and says so.)
- **Both readings routed to the binder.** No number is restated here.

## 7. MaxDD — grid-dependent — **DOOR**

- **Definition:** `(eq / eq.cummax() − 1).min()` everywhere — the formula is uniform. **The grid is
  not.**
- **Code:** `run_bhanushali_sixstep.py:233` (daily) · `bhanushali_review_scorecard.py:65` (daily) ·
  `nq/validation/metrics.py:35`.
- **The same book family publishes −42.4% on a daily grid and −33% at monthly granularity**
  (finding 0114, which labels its grid explicitly). A coarser grid can only ever **understate** a
  drawdown, because it cannot see the troughs between sample points.
- **Wrongly assume:** that −33% and −42.4% describe different risk, or that the book improved.
- **Live consequence, stated not weighed:** the **§4 mechanical −50% halt**
  (`bhanushali_review_scorecard.py:36`, `HALT_MAXDD = -0.50`) reads the same curve. It currently
  evaluates on a **daily** grid — the conservative choice, and correct — but nothing in the code
  *states* that the grid is load-bearing for a risk control.
- **Routed to the binder** with both readings.

## 8. Sharpe — rf = 0, and three frequencies — **DOOR (on the kill gate only)**

- **Definition:** `mean / std × √periods`, **population std (ddof = 0)**, and **no risk-free
  subtraction anywhere** — `nq/validation/metrics.py:19-24`.
- **Frequencies in committed use:** daily × **√252** (`sixstep.py:232`,
  `bhanushali_review_scorecard.py:61`, `metrics.py`) · monthly × **√12** (`diag_pbo_cscv.py:55-57`,
  because its matrix is monthly). Both are internally correct.
- **The naming trap, resolved:** `results/portfolio_history_weekly.csv` is a **DAILY** series
  (verified: median row gap 1.0 day) — the `_weekly` suffix names the **book**, not the sampling
  frequency. **`√252` there is correct.** A maintainer "fixing" it to `√52` to match the filename
  would inflate the forward Sharpe by ≈2.2×. Session 2's annualization audit independently confirmed
  every load-bearing sleeve Sharpe reproduces under daily × √252 and that **no** book matches a mixed
  convention.
- **Wrongly assume:** (a) that Sharpe is excess-of-risk-free — it is not; with an Indian rf of
  ~6–7%, a zero-rf Sharpe **overstates** risk-adjusted excess return in **level** terms; (b) that
  0113's monthly-based 1.239 is directly comparable in level to the daily-based 1.132.
- **Where rf = 0 cancels and where it does not.** For **ΔSharpe** comparisons — how the programme
  almost always uses it — rf cancels and nothing is affected. It does **not** cancel in an
  **absolute** gate, and there is exactly one: **`KILL_SHARPE = 0.0`**
  (`bhanushali_review_scorecard.py:35`) reads "kill if the book underperforms **cash at 0%**", not
  "underperforms the risk-free rate". Under an excess-return reading the same gate would sit near
  Sharpe ≈ 0.25–0.30.
- **Routed to the binder** with both readings. **No verdict is re-adjudicated** — every KILL on the
  record was decided on ΔSharpe, CI, or slice tests, none of which move.

## 9. Sleeve correlation — daily Pearson — **PARKED**

- **Definition:** `np.corrcoef(rA, rD)` on **daily** return series — `diag_sleeve_rigor.py:96`.
- **Wrongly assume:** that the published ρ (0.54 in 0081, 0.57 in 0083, 0.57–0.64 in 0115) is at the
  decision or holding horizon. It is daily, and none of those findings state the frequency.
- **Violated in published use?** No — the number is what the code computes. But 0115's KILL rests on
  a "not orthogonal" reading of 0.57–0.64, and **whether that is frequency-robust is unmeasured**.
- **PARKED, deliberately.** Measuring it means re-running series → out of scope, and re-adjudicating
  0115 is explicitly forbidden. Logged in the parking lot.

## 10. Alpha — **CLEAN**

- Benchmark **Nifty-500 TRI**; `daily r_book = α + β·r_bench`, α annualised ×252; **rf = ZERO,
  disclosed at source**: *"with an Indian RF of ~6-7%, a zero-RF alpha OVERSTATES true excess
  return."* Population caveat also disclosed: the sole-ranker sleeve panels, **not** the capped ₹10L
  book of record. Source: `session2_alpha_decomposition.json`.
- **Nothing to fix — this is the house standard for how a metric should be published.**

## 11. The ±10R/yr floor — **DOOR, already open**

Unit is the blended R of rows 1–2; derived empirically from composition noise on this book **in
these units**, so it is internally consistent with every bound measured against it. Fully treated in
binder §8, including the invalid-comparison trap (deflating a bound while leaving the floor
undeflated). **Not re-opened here.**

## 12. "Screen" as a countable act — **CLEAN (self-disclosed)**

- **Definition:** one **pre-registered study** appended to `label_screen_ledger.md` before it runs —
  **not** one statistical comparison. Current count **15**.
- **Wrongly assume:** that screens = 15 means 15 hypothesis tests. The ledger itself states rows 1–6
  spanned **~25 feature-target comparisons**, so the comparison count is ≥34.
- **Violated in published use?** No — and the ledger carries its own multiplicity note plus a dated
  bookkeeping correction (row 12 appended retroactively 2026-07-31). It also does **not** feed DSR;
  `n_trials` does. Exemplary; no action.

## 13. DSR / `n_trials` — **CLEAN**

Deflates on **`cumulative_n_trials = 138`**, counted **arm-level** ("each multi-arm ablation
contributes its arm count"); the less-conservative **family-level 77** is recorded as the stated
alternative. **Wrongly assume:** that deflation is per-study. It is cumulative and permanent.
`n_trials.json` documents both, plus the full increment log. No action.

## 14. Worst year / losing years — **PRESENTATION (fixed)**

Calendar-year buckets compounded from daily returns (`run_corrected_anchor.py:53-54`). A **partial**
first or last year counts as a whole entry in "losing years" and can appear as `2017: 0.0` (no
trades yet) or as a full-looking figure from a two-month stub. **Wrongly assume:** that "0 losing
years" spans ten complete years. Clarifying comment added.

## 15. `expectancy_R` — **DOOR (with row 5)**

`avg_r` = mean R over **closed** trades (`run_bhanushali_cron.py:474`), read by the **promote gate**
(`PROMOTE_EXPECTANCY_R = 0.10`, both legs required with MaxDD > −25%). Inherits row 5's closed-only
bias **and** row 1's denominator heterogeneity. Currently rests on **4 closed trades**. Routed with
row 5.

## 16. PBO — **CLEAN**

46.2% over **C(12,6) = 924** IS/OOS combinations across **17** cfg-gated configs on a **monthly**
matrix (`diag_pbo_cscv.py`). **Wrongly assume:** that its 1.239 → 0.843 Sharpes are comparable in
level to daily-based figures — they are monthly. **The ~0.68 IS→OOS haircut is a *ratio*, so it is
frequency-invariant and transfers**; the levels do not. No action.

## 17. Live rupee weight / recovery % — **CLEAN (cite)**

Both defined, with their caveats, in `r_denominator_audit.{md,json}`: the weight factor is
`min(2%, 20% × stop_frac) / 2%`; the 37.1% vs 10.6% recovery split carries its own written
**mechanical caveat** (a narrow stop needs a smaller reversal to recover). Cite, do not restate.

## 18. Calmar — **DOOR (with rows 6 and 7)**

`CAGR / |MaxDD|` (`nq/validation/metrics.py:53`) — a **ratio of two grid-dependent quantities**, so
it compounds row 6's year-denominator and row 7's drawdown grid. A Calmar quoted from a monthly-grid
DD and a bar-year CAGR is not comparable to one from a daily-grid DD and calendar-year CAGR. Routed
with rows 6 and 7.

---

## Terminal condition

Every metric quoted in `oct1_binder_decisions.md` now has a row: Sharpe (8), CAGR (6), MaxDD (7),
Calmar (18), DSR (13), R and R/yr (1, 2, 11), stop width (3), win rate (5), expectancy_R (15), trade
counts (4), PBO (16), rupee weight and recovery % (17), correlation (9), alpha (10), and the
screens/sealed-opens/n_trials counts (12, 13). **The register is complete and closed. It is not to
be extended without a fresh decision-weighted scope.**

**Outcome: 5 PRESENTATION fixes applied at source (comment-only, zero behaviour change) · 6 DOORs
routed to the binder with both readings · 1 PARKED · 6 CLEAN.** No verdict was re-adjudicated, no
result was re-run, no hypothesis was generated. Counts unchanged: **screens 15 · sealed opens 1 ·
n_trials 138.**
