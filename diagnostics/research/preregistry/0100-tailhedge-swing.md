# Pre-registration 0100 — Options-OI-triggered defined-risk tail hedge on the weekly-swing book

**Status:** PRE-REGISTERED (written before any run; params fixed here and not retunable).
**Date:** 2026-07-26. **Owner-selected lever** — the registry's deferred "defined-risk tail hedge"
(overlay_registry line 159; O-009 companion conclusion: a dependable −30% DD needs the tail hedge,
NOT a regime gate). Owner chose the **coincident vol-stress trigger** and the **hedge (not sell-to-cash)**
shape after being shown that sell-to-cash is triple-killed (0090 regime, 0095 de-gross, O-001/A5).
**n_trials cost:** +1 (single arm, fixed params) → cumulative 129 → 130, incremented before the run.

## Overlay
A portfolio-level, **defined-risk NIFTY put-spread** bolted onto the frozen `weekly-swing-0094-rank`
book. It does **not** touch stock selection, sizing, or exits — the R94 engine is run unchanged and its
daily NAV curve is taken as-is; the hedge is an additive **sidecar** P&L on that NAV. So the engine
invariant is satisfied *by construction* (no engine/cfg edit → the 0094 run of record is byte-identical;
verified by asserting the book leg reproduces 0094's headline metrics + trade count).

Data: the new PIT-clean OI series `data/options_oi_pit.parquet`
(`nq.data.options_oi`, truncation-tested `tests/test_options_oi_pit.py`) + the raw per-strike bhavcopy
`data/_fo_oi_raw.parquet` for **actual** option premiums (no pricing model).

## Trigger — FIXED
- **Signal:** `atm_straddle_pct_z` (trailing-252d z of the front-monthly ATM straddle / spot = an
  OI-implied IV proxy). Trailing-only ⇒ lookahead-clean.
- **Arm** the hedge when `atm_straddle_pct_z > 2.0` (top ~4.7% of days, ~12/yr in bursts; validated to
  fire in every year's local stress, not just COVID — an absolute IV threshold is COVID-only).
- **Hold to the front-monthly expiry**, then **re-arm** for the next monthly iff the signal is still
  `> 2.0` on the roll date. Disarm (let it lapse) once the signal is ≤ 2.0 at a roll.
- Decision uses date-t EOD data, hedge established at t (next-session in live) — the same close→next
  cadence the book certifies on.

## Instrument & fills — FIXED
- **1-month front-monthly put-spread**, per hedge cycle:
  - Long put at `K1` = nearest listed strike ≤ spot_t (ATM).
  - Short put at `K2` = nearest listed strike ≤ 0.95 × spot_t (≈5% OTM) — defines the risk & cuts cost.
- **Entry debit** = actual bhavcopy PE close(K1) − PE close(K2) on the arm date (real market premium;
  because we arm *after* the vol spike this debit is honestly expensive — the realistic weakness, baked
  in, not modelled away). If either strike is untraded that day, use the nearest traded strike within
  ±1 tick-ladder; if unavailable, skip the cycle (logged).
- **Payoff at expiry** = defined-risk intrinsic `clip(K1 − S_E, 0, K1 − K2) − debit`, with `S_E` the
  front-future settle / spot on the expiry date.
- **Sizing:** protect the full book notional — `units = hedge_frac × NAV_t / spot_t`, `hedge_frac = 1.0`
  (the natural "hedge the book" choice; NOT tuned — a different fraction would be a hidden second trial).
  Cost debited from NAV at arm; payoff credited at expiry. Max loss per cycle = debit × units (~1–2% NAV).

## Hypothesis
Buying defined-risk downside convexity exactly when the options market is pricing stress caps the
left tail (2018/2020/2024/2025 down-legs) and cuts the book's −36%…−42% max drawdown, while keeping the
book **fully invested** so the recovery up-leg is retained (the exact thing sell-to-cash / regime gates
lose — 0090). Net: DD reduction at a bounded premium-drag CAGR cost.

## Predicted direction (before seeing results)
- **ΔMaxDD:** better (less negative) — the intended effect; strongest in COVID.
- **ΔCAGR:** negative — premium drag from cycles that expire worthless (arming *after* the spike means
  most non-COVID arms buy expensive protection into a recovery).
- **ΔSharpe:** ambiguous — positive iff the DD/vol reduction outweighs the drag; plausibly ≈ 0.

## Failure modes (≥2, named before running)
1. **Buys expensive protection after the spike.** z>2 is coincident, not leading, so the put-spread is
   bought at high IV; if the market V-bottoms (as it often does post-spike), the spread expires near
   worthless and the cumulative drag exceeds the DD benefit → net worse (the classic tail-hedge trap).
2. **Wrong-shape signal for the actual DD.** If the book's worst drawdowns are slow choppy grinds
   (2024–25 style) rather than sharp vol spikes, the IV trigger never arms into them → DD untouched
   while drag accrues (0090's lesson: a signal that doesn't match the loss mechanism can't fix it).
3. **Defined-risk cap too tight.** A 5%-wide spread caps payoff at (K1−K2); in a >20% crash (COVID) the
   spread maxes out early and under-hedges the deep tail → smaller DD relief than a naked put.

## Pre-committed verdict bar (DD-overlay class — fixed here, mirrors 0095)
Judged as a drawdown overlay (a hedge is not a Sharpe engine):
- **SHADOW (route to the forward wall)** iff ALL hold on the corrected universe, continuous-slice:
  1. **ΔMaxDD ≥ +3.0 pp** (absolute DD reduction),
  2. **ΔSharpe ≥ −0.05** (full-sample; not materially worse),
  3. **≥2022 continuous-slice Sharpe** not worse by more than 0.05 (the live-relevant regime),
  4. **ΔCAGR ≥ −2.0 pp** (bounded premium drag).
- **PROMOTE to a live hedge sleeve:** NOT available on in-sample evidence alone (the book is already
  UNDERPOWERED, DSR < 0.95). Live promotion is forward-wall only — logged as a WATCHED sidecar first.
- **KILL / UNDERPOWERED** otherwise. No retune, no re-run, no rounding a near-miss into a pass
  (the 0025 lesson: a 0.003 miss is a miss). `hedge_frac`, the 2.0 z-threshold, and the 5% width are
  fixed above; if the hedge needs different values to clear, that is itself the finding.

## Method
- Book leg: `run_bhanushali_weekly_rank` frozen 0094 config on the corrected universe (pinned + backfill
  + aliases), 2017–2026 — the same run as the 0094 record; assert byte-identical headline reproduction.
- Hedge leg: pure function of `data/options_oi_pit.parquet` (trigger) + `data/_fo_oi_raw.parquet`
  (premiums) + the front-future/spot path (payoff). Reproducible from the committed pipeline.
- Combine additively on the daily NAV; recompute Sharpe/CAGR/MaxDD/Calmar full-sample + `_slices`
  (continuous-slice, never fresh-capital).
- Report: ΔMaxDD/ΔSharpe/ΔCAGR/ΔCalmar, block-bootstrap ΔSharpe CI, DSR at cumulative 130, sample
  adequacy (n_independent ≈ 34 sixty-three-day windows), hedge-cycle ledger (arm date, debit, payoff, R).
- vibe-trading is NOT used (no PIT-NSE options); our harness is canonical.

## Registry cross-check (done before writing this)
- **Not** a regime entry gate (O-001/A5/0086/0090 — all KILL): the book stays fully invested; this adds
  convex protection, it does not sit out or de-gross the equity book.
- **Not** intra-book de-gross (0095 KILL — inverts on the cash-constrained book): the hedge is a NAV
  sidecar, it does not free cash into weaker fills.
- **Is** the explicitly-deferred "defined-risk tail hedge / options program" the registry names as the
  one remaining honest DD lever (line 159; O-009 companion 0070). New data (OI-implied IV), new
  instrument (put-spread), new axis (portfolio convexity) — clears the relitigation bar on all four.
