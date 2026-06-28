# 0070 — Systematic-crash exposure overlay (the road to −30%)

- **ID** — 0070
- **Registered** — 2026-06-26 (BEFORE the cloud run; question + arms + decision rule fixed first).
- **Parent / motivation** — 0069 established the binding constraint: the book's ~−45% drawdown IS the
  **COVID-2020 systematic (market-wide) crash** (every concentration/breadth arm's global MaxDD sits
  in 2020). Breadth dilutes it but COSTS 4-6pp CAGR (KILL); concentration keeps CAGR but doesn't help
  DD. The only CAGR-neutral DD lever found is the 0068 vol-target (DD ~−39 at neutral CAGR), which
  works *because* it actually de-grossed in COVID. So the road to −30 is **targeted market-state
  exposure management**, not sizing/diversification.
- **The KILL it must not repeat** — a BINARY index-200DMA dual-momentum gate was killed on this book
  (STRATEGY_FULL §11): it went to cash and stayed there for MONTHS during the V-shaped recovery,
  forfeiting the rebound and killing CAGR. Any regime/market-state design here MUST be **continuous**
  (partial de-gross, never zero) and **fast-re-engaging** (restore exposure within weeks of a bottom).
- **Hypothesis** — A continuous, fast-re-engaging market-state exposure scalar de-grosses the book
  through the COVID-style systematic crash and pushes the 2020 MaxDD below the 0068 vol-target's level
  (toward −30) at a SMALL CAGR give-back (≤ a few pp), because the de-gross is concentrated in genuine
  market-wide down-legs and re-engages before the recovery. Honest prior (from 0069): −35 may be a hard
  systematic floor for any *sizing* overlay; if even the aggressive arm floors ~−34, that is itself the
  finding (the last few pp need a defined-risk index hedge, deferred).
- **Mechanism (one engine hook, flag-gated, default OFF → golden byte-identical)** — a per-date
  exposure scalar in `[floor, 1]` computed TRAILING-ONLY from an equal-weight index of the universe,
  **LAGGED one trading day** (`_lh_overlay_core.lag_exposure` is the SINGLE lag point — a fill at date
  t's open may use only t-1's close, matching the vol_scalar convention), passed to
  `portfolio.simulate(exposure_map=...)` and multiplied into the sizing equity alongside the 0068
  vol_scalar (`equity * vol_scalar * exposure_t`; both only de-gross, so they compose). Signals live
  in `long_horizon/backtest/ohlc_panel.py` (all PIT-clean, pinned trailing-only by
  `tests/test_lh_overlay_core.py`).
- **Grid (5 NEW arms + OFF + the 0068 vol-target as the in-run reference to beat)** — frozen cfg:
  | arm | signal | params |
  |-----|--------|--------|
  | OFF | none | baseline |
  | VOL68_ref | 0068 book-vol (reference, counted under 0068) | target_vol 0.15, floor 0.40 |
  | SEMIDEV | index downside-semideviation | W=15, target_dvol 0.12, floor 0.40 |
  | SEMIDEV_AGGR | index downside-semideviation (aggressive) | W=10, target_dvol 0.10, floor 0.30 |
  | MKTDD | index peak-drawdown circuit-breaker | X=12%, Y=30%, floor 0.40 |
  | BREADTH_REG | continuous breadth + index-trend | breadth 20d / SMA50, floor 0.50 |
  | SEMIDEV_x_VOL68 | SEMIDEV stacked on the 0068 book-vol (product) | best-achievable probe |
- **Evaluation surface** — the same continuous single-curve, frozen-cfg, 2017+ run as 0068/0069
  (`_lh_overlay_core`), 2019+ reported separately. The overlay changes ONLY sizing (selection/exits
  unchanged), so the unseen-midcap split is N/A.
- **Decision rule — a FRONTIER, not one point.** HEADLINE: the per-arm (COVID-2020 DD, overall DD,
  CAGR give-back) table; the "most efficient" overlay = the single-signal arm with the SHALLOWEST
  COVID-2020 DD among those costing ≤ 3pp CAGR vs OFF. A win = an arm that pushes the 2020 floor below
  the 0068 vol-target's COVID DD by > 0.5pp at ≤ 3pp CAGR cost. The SHAPE gates (Calmar up / paired
  block-bootstrap dSharpe CI-low > −0.10 / MaxDD ≤ 0.90×OFF / ≥2-crash-spread) are ALSO applied to the
  best overlay arm for a formal PROMOTE. DSR REPORTED, NOT gated (the 0068 amendment). Judge on SHAPE.
- **Expected failure modes** — (i) the de-gross fires too LATE (gap-down crash beats the trailing
  signal by a day) → COVID stays ~−38 and the arm only matches 0068; (ii) BREADTH_REG WHIPSAWS in
  choppy non-crash years (false de-gross) and bleeds CAGR; (iii) MKTDD re-grosses slowly if the index
  is slow to reclaim its peak (intermediate between semidev and the killed 200DMA); (iv) every arm
  hits the ~−35 systematic floor → the finding is "vol/market-state timing has a hard floor; only a
  defined-risk hedge reaches −30."
- **n_trials (cumulative)** — **73** (68 + 5 new arms). VOL68_ref not re-counted.
- **Status** — COMPLETE. Cloud run 28248413094 (2026-06-26, 397-name universe).
- **VERDICT — formal KILL (no single-signal arm clears all SHAPE gates), but a real, useful frontier.**
  Within-run (OFF: CAGR 26.1, overall/COVID DD −41.9):
    * **SEMIDEV_AGGR** (aggressive downside-semivol, W=10/target 0.10/floor 0.30) is the efficient
      frontier point: it cuts **COVID-2020 −41.9 → −31.4 (10.5pp) at ZERO CAGR cost** (26.21 vs 26.1),
      a GENUINE de-gross (covid deploy 92.0, −2.7pp), **beats the 0068 vol-target on COVID** (−31.4 vs
      −35.5), and has the BEST Sharpe (1.081). HOWEVER its OVERALL MaxDD is unchanged (−41.4) because
      a DIFFERENT drawdown — **2025 (−41.4)** — becomes binding: the short-window semivol caught COVID
      but NOT the slower 2025 grind. A COVID-specific win that does not generalize (exactly the
      skeptic's predicted failure; it improves only 2018+2020, fails the ≥2-of-3 spread on the year
      that matters).
    * **BREADTH_REG** is the most ROBUST: best Calmar (0.668 vs 0.623), shallowest OVERALL DD among
      single signals (−38.3), helps 2018 AND 2020 AND 2025 (−35.5 vs OFF −39.4), CAGR cost only 0.53pp,
      no calm-year whipsaw (deploy ~95% in 2021/2023/2024). It is the formal best arm — but KILLs on
      gate (b) (paired dSharpe CI-low −0.16 < −0.10) and gate (c) (−38.3 vs the −37.7 the 0.9×OFF bar
      needs — a NARROW miss).
    * The stack **SEMIDEV_x_VOL68** reaches the shallowest overall (−35.3) but at 5.45pp CAGR cost
      (over budget). MKTDD's COVID number is a partial lower-peak artifact (deploy only −0.9pp, flagged
      `covid_genuine_degross=false`). NO arm reaches −30 OVERALL.
- **Conclusion** — the CHEAP overlay program (sizing 0068/0069 + market-state 0070) has PLATEAUED at a
  ~−38 robust OVERALL floor. Market-state timing CAN cut a SPECIFIC crash hard and CAGR-free (COVID
  →−31 via aggressive semivol), but NO single signal catches every crash character (semivol misses the
  2025 grind; breadth misses none but only marginally), so the OVERALL MaxDD won't reliably reach −30.
  This is now EVIDENCE that the last leg to a dependable −30 needs the **defined-risk TAIL HEDGE**
  (always-on, crash-character-agnostic, CAGR-preserving) — the deferred vol-carry / options-backtester
  program — not another sizing/market-state lever.
- **CAVEAT (now material)** — the OFF COVID-2020 DD is −41.9 here vs −45.6 in 0068/0069: yfinance
  universe-REBUILD noise (the 2020 floor itself wandered 3.7pp across cloud builds). WITHIN-run lever
  deltas are clean (shared universe); cross-run ABSOLUTE floors are not. The crash-overlay comparisons
  should be re-run on a PINNED universe (committed OHLCV snapshot) before any promotion decision.

## How to run
```
gh workflow run cpcv-research.yml --ref <branch> -f runner=run_crash_overlay_long_horizon
```
Output: `diagnostics/cpcv_crash_overlay_long_horizon.json` + a printed per-arm table and the DD/CAGR
frontier (overall DD, COVID-2020 DD, COVID deployment, CAGR, CAGR-cost), the most-efficient overlay,
whether it beats the 0068 vol-target on COVID, and any arm reaching −30.
