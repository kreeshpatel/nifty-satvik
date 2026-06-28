# Pre-registration 0063 — gate-loosening (min_confidence) — confound-controlled

**Date:** 2026-06-23
**Track:** B (model-internal entry-gate threshold) — CPCV-backtestable
**Status:** PRE-REGISTERED (frozen below); **BLOCKED on owner sign-off before the billed cloud run** — this trial re-opens a LOCKED decision (see §6 Governance).
**Holdout type:** paired CPCV portfolio metric on the locked honest base (de-leaked pinned-744 single-model), `REPRODUCIBLE_MODE=1`, embargoed.
**n_trials:** **+1** (the gate-loosening sweep is ONE registered alpha cell, scored at its loosest passing arm) → **55 → 56**. Bump BEFORE the run; log in `n_trials.json::_increment_log` + add a `families` entry. (The intermediate sweep points 0.91/0.90/0.89 are robustness/plateau samples of the same cell, not independent trials — the SHIP arm is whichever clears every gate, so the decision count is 1.) **DSR is scored at a RAISED local bar (>0.99) + a +3 band-retest penalty (effective n=59)** — this is the Nth probe of the same [0.88,0.92) cell (0026 / 0026b / 0056 / 0058-B); see §4 gate 4.

---

## 0. One-line summary

Does loosening the live entry gate `min_confidence` from **0.92 toward ~0.88–0.90** lift PORTFOLIO Sharpe/CAGR by deploying idle book into real-but-marginal-confidence edge — and does it do so via **genuine incremental-trade edge** rather than a **mechanical more-trades averaging artifact** or a **2021-only** effect? Pre-registered as a confound-controlled alpha trial with an analogue of 0026's "CI-low > 0 or don't take the extra trades" bar, at full 0058 rigor (per-fold wins, drop-2021, DSR-empirical, bad-year tail floor).

---

## 1. Hypothesis (precise) + exact arms

**Motivating observation (measurement, not assumption):** the 0058 2×2 decomposition isolated the GATE-LOOSENING component **B − A = +0.357 paired CPCV portfolio Sharpe, CAGR 16.5% → 33.3%** — the 14d model with the gate dropped to `min_confidence=0.88` / `min_predicted_return=5.0` vs the live-tight 0.92 / 8.0 — as real and statistically distinguishable. Separately, the 2026-06-22 deployment audit (0058/0059) established that the book is **chronically under-deployed (~20–27% deployed; the 30-slot cap NEVER binds; the binding constraint is SIGNAL SCARCITY at the tight gate, not slots)** and that the three *deployment-mechanism* levers (0046 ranker / 0047 trailing-off / 0042 EX-F) were KILLED on the portfolio metric ("deployment != alpha"). The remaining untested deployment route is the **gate threshold itself**.

**H1 (directional):** Lowering `min_confidence` from 0.92 toward ~0.88–0.90 admits real-but-marginal-confidence entries that, deployed into idle capital, raise paired CPCV portfolio Sharpe (CI-low > 0, point > the 0.3 noise floor) **AND** whose *incremental* (newly-admitted) trades carry after-cost per-trade expectancy with bootstrap CI-low > 0.

**H0 (null we must reject to ship):** The portfolio-Sharpe lift, if any, is a mechanical diversification/averaging artifact of trading ~2× as often (the incremental band trades are flat or negative per-trade after cost), **OR** the lift is carried by a single year (2021 bull-blowoff), **OR** the loosest arms degrade a worst-year / tail metric. Any of these → KILL.

**Critical confound flagged in advance (from the BAND/0026 report):** this trial moves a DIFFERENT knob and admits a DIFFERENT, STRICTLY-LARGER population than the 0026-killed `sweep_override`. The +0.80%/trade that 0026 measured was on the *sweep-conditioned* `band ∧ sweep_20d==1` subset and **MUST NOT** be cited as support here (wrong, narrower, momentum-filtered population). See §2.

### Arms (FROZEN)

A single-knob sweep of `min_confidence` on the **14d locked-base model** (`models/v1/config.json` `cfg_14d`), identical CPCV portfolio harness, identical native 14d exits, cost-inclusive, embargoed. **`min_predicted_return` is held at its live value 8.0 across ALL arms** — we deliberately do NOT bundle the two knobs the way 0058's `LOOSE` block did (which flipped 0.92/8.0 → 0.88/5.0 together and therefore could not separate the conf-gate from the return-floor). This trial isolates `min_confidence` alone.

| arm | model | min_confidence | min_predicted_return | exits | role |
|---|---|---|---|---|---|
| **G92 (base)** | 14d | **0.92** | 8.0 | native 14d | yardstick (== live config / locked honest base 14d arm) |
| G91 | 14d | 0.91 | 8.0 | native 14d | sweep / plateau sample |
| G90 | 14d | 0.90 | 8.0 | native 14d | sweep / plateau sample |
| G89 | 14d | 0.89 | 8.0 | native 14d | sweep / plateau sample |
| G88 | 14d | 0.88 | 8.0 | native 14d | loosest candidate |

- Every arm shares the identical model (`cfg_14d`, 79 features, fwd_max_14d return head + hit_4pct_14d conf head), identical native 14d exits, identical costs (`BROKERAGE_PCT`, `STT_PCT` per `config.py`), identical CPCV grid. The ONLY thing that varies arm-to-arm is the one scalar `min_confidence`.
- The "incremental band" for any loosened arm Gx (x < 92) is the set of trades admitted by Gx but NOT by G92 — i.e. entries with confidence ∈ [0.0x, 0.92). This is the population whose standalone after-cost per-trade EV we gate on (§3, confound 1).

### Harness + window (FROZEN, inherited from 0058/0059)

- CPCV: `N_GROUPS=10`, `N_TEST_GROUPS=2` → C(10,2)=45 splits, `n_backtest_paths(10,2)` = **9 LdP paths**. Window **2015-01-01 → 2024-12-31**.
- Purge + embargo: `HORIZON_OBS=14`, `EMBARGO_OBS=14` (embargo ≥ horizon ⇒ LdP full two-sided purge; `cpcv.py` footgun guard stays silent).
- Per split: train `pm14` ONCE on purged train rows (`REPRODUCIBLE_MODE=1`), then run `engine.run(...)` for all 5 arm-configs per test group; store `daily_returns_from_equity_curve(res.equity_curve)` per (split, group). The equity-curve-always-exposed fix (0059 amendment, golden-master byte-identical) is in place so zero-trade folds annualize correctly.
- Path assembly: each of the 9 paths stitches one OOS daily-return series covering all 10 groups exactly once; per-path `sharpe(ser)` and `_cagr(ser)` (252-day annualization).
- `NOISE_FLOOR = 0.3`.

### What ships pre-run (research-only; golden-master untouched, no live/engine change)

`diagnostics/run_cpcv_gate_loosening.py` (a `min_confidence`-sweep adaptation of `run_cpcv_7d_2x2.py`, porting the per-group `blowups` loop, the `drop_2021`/`DROP_GROUP_PERIOD` machinery, a `fill_ratio` degeneracy guard, **and a new incremental-band per-trade after-cost EV + bootstrap-CI emitter** — these last items are the gaps the BASE/HARNESS report flagged as missing in `run_cpcv_deployment_readout.py`) + `.github/workflows/cpcv-gate-loosening.yml` + the n_trials 55→56 bump. No change to `config.py`, `models/v1/config.json`, the cron path, or any committed engine file.

---

## 2. Reconciliation with 0026 (head-on — the crux)

**This trial re-opens territory adjacent to a LOCKED decision. It must NOT be a loophole. Stated honestly:**

### 2.1 Same population as the 0026-killed band? — NO, a strict SUPERSET on a different knob.

- **0026 killed `sweep_override`**, a TEST-side *conditional re-admit*: it re-admits watchlist signals with confidence ∈ **[0.88, 0.92) AND `sweep_20d == 1`** (a breakout-volume filter). On the corrected 744 universe its swept subset was n=106 = 21% of base admits, EV **+0.80%/trade, WR 56.6%, bootstrap CI95 [−1.23, +2.77] straddles zero**. The pre-committed rule was KEEP iff (swept per-trade CI-low > 0) AND (per-fold Sharpe Δ ≥ 0); CI-low FAILED → **DISABLE** (PR #103, 2026-06-10), even though the portfolio-level signal was mildly positive (+0.28 Sharpe). The honest lesson: 106 trades cannot separate +0.8% from zero, and the disable-default rule was committed precisely for that case.
- **0063 moves `min_confidence`**, the gate threshold itself, admitting the **UNCONDITIONAL** [0.0x, 0.92) band — every entry in that confidence range, sweep or no sweep. The gate-loosening population **strictly CONTAINS** the sweep_override population (they overlap exactly on `band ∧ sweep`) plus all the non-sweep band trades.
- Consequence, stated plainly: **0026's +0.80% CANNOT be borrowed as support here.** It was measured on the sweep-momentum-filtered slice, which is plausibly the *better-EV* part of the band; the unconditional band 0063 admits includes the non-sweep trades that, on the 2026-04-22 survivor cache, averaged the −0.46%/trade "structurally negative-EV, parasitic in 4/6 years" picture that originally moved the gate 0.88→0.92. The gate-loosening cell's own band-EV on the corrected universe has **never been measured** — that is exactly what confound-1 below is for.

### 2.2 Legitimate new correlated cell, or goalpost-moving on a locked decision? — Legitimate, on three independent axes; with the discipline that bites both ways.

Per the house **correlated-cell rule** ("a KILL kills one cell, not the hypothesis"):

1. **Different knob.** Gate threshold (`min_confidence`) vs a conditional TEST-side override (`sweep_override`, `band ∧ sweep_20d==1`).
2. **Different population.** Unconditional superset vs sweep-conditioned subset.
3. **Different evidentiary regime.** 0026 was a *parity/correctness* measurement with a disable-by-default rule and **no DSR by design** ("can't prove it helps = don't take the extra trades"). 0063 is an *alpha trial* with DSR at the inflated n_trials. 0026 never measured, and does not claim to kill, the gate cell; the 0058 B−A signal (+0.357 Sharpe) is alpha-relevant evidence 0026 never evaluated.

**Where the correlation bites (and the discipline we adopt because of it):**

- The two cells share the `band ∧ sweep` trades. 0026's KILL legitimately does NOT extend to the gate cell — **but the converse holds too: 0063 may NOT cite 0026's mildly-positive +0.80%/+0.28-Sharpe as evidence.** Treated as a known correlation, not support.
- **0063 adopts an analogue of 0026's "CI-low > 0 or don't take the extra trades" bar**, applied to the population 0063 actually admits: the *incremental band trades' after-cost per-trade EV bootstrap CI-low must be > 0* (§3, confound 1). If the extra trades cannot be shown to have positive EV in their own right, we do not take them — exactly 0026's discipline, transported to the correct (unconditional, superset) population.

### 2.3 The live 0.92 lock (binding right now).

`min_confidence = 0.92` was **"Locked for 90 days regardless of live noise"** as of 2026-04-22 (CLAUDE.md) → lock runs to **≈2026-07-21** (today is 2026-06-23). A *research/backtest* trial of `min_confidence` does NOT violate the lock (the lock governs LIVE config; house discipline already separates a candidate measurement from a live flip, and everything here is owner-gated, "promote NOTHING yet"). But a **live** flip of `min_confidence` before ≈2026-07-21 would contradict the standing lock — so even a PASS authorizes only research → owner sign-off → flag-gated wiring → shadow, never an in-lock live change (§6). The pre-committed 0026b revisit ("≥100 forward-wall band observations") is a separate `sweep_override` trigger and is NOT consumed or pre-empted by this trial.

---

## 3. Confounds — each with a PRE-COMMITTED test

### Confound 1 — the ~2× trades artifact (more-trades/averaging vs genuine per-trade edge)

Loosening 0.92→0.88 roughly **doubles fills** (the owner's "~2×"; 0058 stored both arms' counts in `arm_trades`). A portfolio-Sharpe lift can be a **mechanical diversification/averaging artifact** even if the marginal trades are flat or negative — adding more uncorrelated draws of a near-zero-EV bet can raise portfolio Sharpe by lowering variance per unit return while the *incremental* trades add no alpha.

**PRE-COMMITTED test (decomposition + 0026-analogue bar):**
- Emit, for every loosened arm Gx, the **incremental band trades** = trades admitted by Gx but NOT by G92 (confidence ∈ [0.0x, 0.92)). Compute their **after-cost per-trade expectancy** (net of `BROKERAGE_PCT` both legs + `STT_PCT` sell side, per `config.py`) and a **bootstrap 95% CI** (≥10k resamples, same machinery class as 0026's swept-trade CI).
- **GATE (mandatory, ships-blocking): the incremental-band after-cost per-trade EV bootstrap CI-low must be > 0** for the arm that ships. This is the direct analogue of 0026's "CI-low > 0 or don't take the extra trades," applied to 0063's correct (unconditional) population. A portfolio-Sharpe lift with incremental-band CI-low ≤ 0 is treated as an averaging artifact → that arm cannot ship.
- Additionally emit `mean_open_positions` and `mean_deploy_frac` per arm (the deployment columns) so the lift can be attributed: if Sharpe rises while incremental-EV CI straddles 0 and deploy_frac rises, the lever is *deployment-mechanical*, not alpha. **Such an arm is KILLED for ship (gate 3), full stop** — the deployment-mechanical decomposition is RECORDED for the research ledger, but there is **no "report as a deployment lever" soft-promote path** (that narrative escape is exactly what let prior deployment knobs linger; a flat-incremental-EV arm does not ship).

### Confound 2 — 2021-dependence (single bull-blowoff year carrying the edge)

The locked base's 2021 fold is **+3.625 Sharpe / CAGR +106%** — the bull-blowoff fold. 0058's own B−A was on the same window where 2021 carried ~41% of the 7d gross edge. A portfolio lift that lives in 2021 is not a deployable edge.

**PRE-COMMITTED test:**
- **Per-year decomposition:** emit each arm's paired dSharpe and dCAGR resolved by year (map CPCV group → calendar year via `_group_period(g)`; the 2021 mapping `DROP_GROUP_PERIOD = ("2021-01-01","2022-01-31")` is already wired in `run_cpcv_7d_2x2.py` and is ported here).
- **Drop-2021 robustness:** recompute the paired (Gx − G92) dSharpe with the 2021 group EXCLUDED (`drop_2021=True` in `_path_metrics`). **The lift must survive: drop-2021 paired dSharpe CI-low still > 0.**
- **Drop-single-best-year robustness:** also recompute dropping whichever single year contributes the most to the lift. **No single calendar year may account for more than 50% of the total paired dSharpe lift.** If one year carries >50%, the edge is year-concentrated → KILL.
- **Drop-{2020, 2021} JOINT robustness (the load-bearing guard):** the base has **TWO** blow-off bull folds — 2020 (+2.722 Sharpe / +104% CAGR) and 2021 (+3.625 / +106%). Gate-loosening = deployment-into-idle-book, which mechanically pays most in runaway bull tape, and the single-year guards above **miss the 2020+2021 PAIR** (split the bull edge across two years → each is <50% AND drop-2021-alone leaves 2020 intact). PRE-COMMIT: recompute the paired (Gx − G92) dSharpe with **BOTH** the 2020 and 2021 groups excluded (extend `DROP_GROUP_PERIOD` to a list). **The lift must survive: drop-{2020,2021} paired dSharpe group-bootstrap CI-low still > 0.**
- **Non-bull incremental-EV gate (edge, not beta):** the incremental-band after-cost per-trade EV **bootstrap CI-low must be > 0 RESTRICTED to the non-bull folds (2019, 2022, 2024, 2025).** If the marginal trades only pay in 2020–21, the gate is buying market beta / good-tape deployment, not standalone edge → KILL. (Directly tests the lean-year-sector-audit finding that overlays "help only 2021 bull, HURT all 3 lean years.")
- **No single REGIME > 50%:** tighten the single-year rule to a regime cluster — no bull-blowoff cluster (2020 ∪ 2021, or any contiguous strong-tape run) may account for > 50% of the total paired dSharpe lift.

### Confound 3 — bad-year / tail floor (lean-years + tail-safety discipline)

The honest base is negative in **3/8 folds (2019, 2024, 2025)**; lean years are single-name / per-stock-regime risk, and the system serves ~10 paying users for real financial decisions. Loosening the gate must not buy mean-Sharpe by worsening the tail.

**PRE-COMMITTED test (block-ship even if mean Sharpe improves):** no loosening arm that ships may, vs G92 base:
- worsen the **worst-year Sharpe** (the most-negative per-year Sharpe across folds),
- worsen the **worst-year CAGR**,
- worsen **portfolio max drawdown** (deepest across the 9 paths), or
- worsen the **worst single-name realized loss** (most-negative single-trade after-cost return).

If ANY of these four tail metrics degrades for an arm, that arm is **blocked from shipping regardless of mean-Sharpe improvement.** (Tail worsening blocks ship; it does not by itself KILL a strictly-better-tail looser arm.)

---

## 4. Pre-committed PASS/KILL gate (ALL must hold to ship)

Scored against the locked honest base (`locked_honest_base_744.json`, mean_sharpe_2019plus 0.968 / median 0.854, 3 negative folds; digest `64cda7c2`) on the FROZEN harness. **An arm ships ONLY if ALL of the following hold for that arm:**

1. **Portfolio Sharpe lift, real (GROUP-LEVEL bootstrap CI — NOT the normal-approx `_ci`):** paired (Gx − G92) dSharpe **CI-low > 0 AND point > 0.3** (NOISE_FLOOR), where the CI is a **paired block bootstrap that resamples the 10 calendar GROUPS with replacement** (re-stitch the 9 LdP paths from the resampled groups, recompute the paired dSharpe each resample, ≥10k resamples). The inherited `mean ± z·pstdev/√9` parametric CI (the 0058 `_ci`) is **FORBIDDEN as the primary gate** — the 9 LdP paths share the same C(10,2) folds and are strongly positively correlated, so `pstdev/√9` understates the SE and "CI-low>0" fires too easily (the underpowered-fold-scalar-CI footgun). [primary metric]
2. **Per-fold robustness:** Gx wins paired per-path Sharpe vs G92 in **≥ 7 of the 9 CPCV paths** (the 0011 precedent bar; 6/9 is near coin-flip once path-correlation is accounted for — sign-test p≈0.25 — so the bar is the stricter 7/9). Requires dumping the per-path vectors (one-line emitter change from the 0058 runner, which today persists only aggregates).
3. **Incremental-band per-trade edge (the 0026 analogue — the EXISTENCE gate):** incremental-band after-cost per-trade EV **bootstrap CI-low > 0** (§3 confound 1), bootstrapped on the **engine's realized after-cost trade returns (`res.trade_log` net returns** — brokerage both legs + STT sell per `config.py`, NOT a re-derived/idealized approximation), ≥10k resamples, trade-level resampling. A portfolio-Sharpe lift WITHOUT this **KILLS that arm — no "but the portfolio Sharpe was positive" override** (the magnitude metric may never stand in for the existence gate; §8.5).
4. **DSR (band-retest bar RAISED):** `deflated_sharpe_ratio` > **0.99** (NOT the usual 0.95), computed with **EMPIRICAL** skew/kurtosis of Gx's pooled daily returns (NOT normal 0/3 — the flaw 0051 was caught on), `n_observations`=9 paths, `sharpe_variance`=pstdev² of per-path Sharpes, at **`cumulative_n_trials = 56 + band_retest_penalty`, `band_retest_penalty = 3`** (frozen now → effective n = 59). Rationale: this is the **Nth probe of THIS EXACT [0.88,0.92) cell** — 0026 (`sweep_override` DISABLE), the pending 0026b, 0056 (regime-conditional gate, KILL), and 0058's B arm all probed the gate-relax direction. Selective-reporting bias here is **band-specific, not program-uniform**, so BOTH the local bar is raised (0.99) AND the effective trial budget is penalized (+3) — a nominal lift clearing 0.95 at n=56 is exactly the "luck from many tries on one cell" the house DSR rule warns against.
5. **Non-degeneracy:** trivially satisfied for loosened arms (`n_trades_Gx ≥ n_trades_G92` by construction since loosening only admits), but emit `fill_ratio` for completeness and sanity (loosening that does NOT raise trade count would indicate a wiring bug → investigate, do not ship).
6. **Plateau / monotonicity sanity (not a single lucky point):** the dSharpe-vs-min_confidence curve across {0.92, 0.91, 0.90, 0.89, 0.88} must be **broadly monotone / plateau-shaped, not a single-arm spike.** Concretely: the SHIP arm's neighbor (the next-tighter arm) must also show paired dSharpe CI-low > 0, OR the SHIP arm must be a clear plateau (its lift within noise of the loosest arm). A lone interior spike with both neighbors at/below zero is treated as overfitting to one threshold → KILL the spike (do not ship it; a tighter neighbor that itself passes all gates may ship instead).
7. **Year/regime robustness (confound 2 — ship-blocking):** the paired dSharpe **group-bootstrap CI-low stays > 0 with 2021 dropped AND with {2020, 2021} JOINTLY dropped**; no single calendar year and no bull-blowoff regime cluster carries > 50% of the lift; and the incremental-band per-trade EV **CI-low > 0 restricted to the non-bull folds (2019/2022/2024/2025)**. KILL on any miss (a lift that lives only in bull tape is beta, not all-weather edge).
8. **Bad-year / tail floor (block-ship):** none of the four tail metrics in §3 confound 3 worsens vs G92.
9. **Skeptic-agent clearance:** overfit-skeptic + backtest-validator both clear (the 0058/0051 gate that overturned a naive promote).

**KILL on ANY miss.** Record the full sweep + decomposition regardless (it tells us whether the lever is "loosen the gate" or whether the 0058 B−A was itself a 2021/averaging artifact).

**Which arm ships if PASS:** the **LOOSEST** `min_confidence` arm that clears EVERY gate above (1–9). E.g. if G90 and G91 pass all gates but G89/G88 fail the incremental-band CI or the tail floor, **ship G90.** If only G91 passes, ship G91. If no arm clears every gate, **ship nothing** (KILL — the live 0.92 stands).

**Correlated-cell rule:** a KILL of one arm kills that arm/threshold, not the hypothesis; a tighter passing arm may still ship. But the hypothesis as a whole is KILLED if the loosest passing point is G92 itself (no arm beats base on every gate).

---

## 5. Interpretation guide (pre-stated)

- **Lift + incremental-band CI-low > 0 + drop-2021 survives + tail floor holds + plateau:** genuine marginal-confidence edge being deployed into idle book → proceed toward owner sign-off + shadow at the loosest passing arm. The system was leaving real edge on the table by gating at 0.92.
- **Lift but incremental-band CI straddles 0 (deploy_frac up, EV flat):** the Sharpe rise is a **deployment/averaging artifact → KILL for ship, full stop** (gate 3, no override from the portfolio number). The deployment-mechanical decomposition is recorded for the ledger; it is NOT a "deployment lever" to be promoted — the magnitude metric may never stand in for the existence gate (§8.5).
- **Lift concentrated in 2021 / one year (>50%):** year-dependent, not deployable → KILL. Confirms the owner's stated "genuine-edge-vs-just-more-trades" and missing-drop-bad-year confounds were the right things to fear.
- **Loosest arms improve mean Sharpe but worsen a tail metric:** KILL the offending arms on the tail floor; a tighter arm that improves mean AND holds the tail may still ship. Tail safety is non-negotiable for paying users.
- **No arm beats G92 on every gate:** the 0058 B−A +0.357 was a bundled (also moved `min_predicted_return`) and/or averaging and/or 2021 effect; the disciplined 0.92 gate is protective → live config stands, lock honored to ≈2026-07-21.

---

## 6. Governance (re-opening a locked decision — owner-gated, compliance-safe)

This trial **re-opens a LOCKED decision** (`min_confidence = 0.92`, locked 2026-04-22 for 90 days "regardless of live noise," running to ≈2026-07-21) and probes territory adjacent to the 2026-06-10 0026 `sweep_override` DISABLE. Two hard governance gates:

1. **Owner sign-off BEFORE the billed cloud run.** This is a research measurement, but it re-opens a standing lock and consumes a billed CPCV matrix run. It does NOT dispatch until the owner explicitly approves the frozen design above. "Promote NOTHING yet" stands — this pre-registration is a request to *measure*, not a decision to change anything.
2. **A PASS authorizes ONLY a research finding → a separate, golden-master-safe, flag-gated wiring change → a shadow period — never a direct live change**, and never an in-lock live flip:
   - Any wiring of a loosened `min_confidence` into the live path must be **flag-gated** (a new `min_confidence` value behind config, defaulting to the live 0.92) and must pass the **golden-master byte-invariance test** (`tests/integration/test_golden_master.py`) — if the change alters gating output, the baseline is regenerated intentionally in the same PR (`python -m diagnostics.build_golden_fixture`).
   - It then runs in **shadow** (scored on the forward wall, not blocking live signals) before any flip touches the decision-support output the ~10 paying users see.
   - A LIVE flip of `min_confidence` must wait until after the 0.92 lock expires (≈2026-07-21) OR an explicit owner override of the lock — whichever the owner chooses, in writing.

**Compliance-safe framing:** this trial evaluates a candidate change to a model-generated, decision-support entry threshold. It makes no claim about and offers no guarantee of live outcomes; it authorizes a research measurement only. Nothing here changes the recommendations served to users until it has cleared the gate, owner sign-off, golden-master safety, and a shadow period.

---

## 7. Provenance / cross-references

- **Lever source:** 0058 `gate_BvA` (B − A = +0.357 paired CPCV portfolio Sharpe, CAGR 16.5%→33.3%) in `diagnostics/run_cpcv_7d_2x2.py`; pre-reg `diagnostics/research/preregistry/0058-7d-horizon-clean-2x2.md`. NOTE: 0058's B − A bundled BOTH `min_confidence` AND `min_predicted_return` (its `LOOSE = {0.88, 5.0}`); **0063 isolates `min_confidence` alone** (holds `min_predicted_return=8.0`), so 0063's lift is a clean single-knob measurement and may be SMALLER than B−A's bundled number.
- **Deployment context:** 0059 `diagnostics/run_cpcv_deployment_readout.py` + `0059-deployment-metric-reaudit.md` (chronic under-deployment; deployment-mechanism levers KILLED; "deployment != alpha"; the interpretation guard adopted in §3/§5).
- **0026 reconciliation:** `diagnostics/research/preregistry/0026-sweep-override-parity.md`; CLAUDE.md lines 305–306, 409. The 0026b revisit trigger (≥100 forward-wall band obs) is a separate `sweep_override` cell, untouched by this trial.
- **Honest base:** `diagnostics/research/locked_honest_base_744.json` (LOCKED 2026-06-10, digest `64cda7c2`); per-fold 2021 = +3.625 / +106% (the drop-year target).
- **DSR machinery:** `src/validation/overfitting.py` (`deflated_sharpe_ratio`, `expected_max_sharpe`, `cumulative_n_trials`); n_trials registry `diagnostics/research/n_trials.json`.
- **CPCV machinery:** `src/validation/cpcv.py` (`cpcv_splits`, `cpcv_paths`, `make_groups`, `n_backtest_paths`, purge+embargo); `src/validation/composition.py` (`daily_returns_from_equity_curve`, `sharpe`).
- **Gate-rule precedent:** 0011 (`0011-triple-barrier-win-label.md`) per-fold Sharpe-wins ≥ ~7/9 bar (mapped to ≥6/9 here); 0058 frozen 6-point rule (the template for §4).

---

## 8. Skeptic's dissent — the case that re-opening is a MISTAKE (filed against this trial)

*Written by the domain skeptic defending the 0026 KILL. The author of §§1–7 owns the trial; this section is the standing objection it must answer. Pre-committed so the dissent cannot be softened post-hoc. Its core claim: **even if the billed run returns a clean positive +0.357-class portfolio-Sharpe lift, that number is not sufficient evidence to re-open the gate**, and several of the gates in §4 may pass on artifacts that the dissent names in advance.*

### 8.1 What 0026's per-trade EV CI knows that a CPCV portfolio-Sharpe decomp structurally cannot

0026's primary metric was the **pooled after-cost per-trade return of the admitted trades, with a bootstrap CI** — a *direct, units-of-the-decision* measurement: "when we take this specific extra trade, what does the user net?" It answered +0.80%/trade, CI [−1.23, +2.77], n=106, and the disable-default rule fired because **106 trades cannot separate +0.8% from zero.** That is the honest power statement for this population.

A paired CPCV **portfolio-Sharpe** decomp answers a *different and weaker* question: "does the daily-return *series* of the loosened book have a higher risk-adjusted slope?" Portfolio Sharpe is a ratio of a path's mean daily return to its daily volatility. It can rise for reasons that have **nothing to do with the admitted trades being good**:

1. **Variance-denominator reduction (the averaging artifact).** Adding ~2× more positions of near-zero-EV bets that are imperfectly correlated lowers the *denominator* (portfolio daily vol) faster than it lowers the *numerator* (mean daily return). Sharpe = mean/vol rises even though every incremental trade is a coin-flip-or-worse after cost. This is mechanical diversification, not edge. The per-trade EV CI is **immune** to this: it never divides by portfolio variance, so it cannot be flattered by adding draws.
2. **Calendar in-fill / deployment timing.** On a chronically ~27%-deployed book (0028/0048/0059), the tight gate leaves long *flat stretches* — days with zero open positions contribute zero return and zero variance but still count in the 252-day annualization. Loosening fills those days. If the fill happens to land in good-tape windows (and the gate's own confidence signal is correlated with tape), the path's annualized Sharpe rises purely because **idle calendar got converted to deployed calendar at favorable moments** — a property of *when capital was idle*, not of whether the marginal trade had standalone edge. The per-trade EV CI strips the calendar out entirely; it asks only about the trades themselves.
3. **Path-stitching smoothing.** The 9 LdP paths each stitch 10 groups; more trades per group means smoother stitched series and lower per-path Sharpe dispersion, which *also* feeds DSR favorably (lower `sharpe_variance` → easier DSR > 0.95). A portfolio-Sharpe-plus-DSR gate can therefore be co-flattered by the same trade-count inflation it is supposed to discipline.

**The asymmetry that matters:** 0026's CI said "I cannot prove these trades are good." A +0.357 portfolio Sharpe says "the series looks better." **These are not in contradiction, and the second does not rescue the first** — a better-looking series built from individually-unprovable trades is exactly the deployment/averaging artifact §3-confound-1 was written to catch. The dissent's position: the portfolio number is the *seductive* metric precisely because it can be true while the decision-level metric (per-trade EV) is null.

### 8.2 Could the lift be REAL at the portfolio level while the band trades are individually negative-EV? — Yes, and that is the modal outcome the dissent predicts.

This is not a hypothetical. It is the explicit finding pattern of the deployment family this trial descends from: 0046 (ranker), 0047 (trailing-off), 0042 (EX-F) were **KILLED on the portfolio metric** with the standing house verdict *"deployment != alpha"* (0059, `run_cpcv_deployment_readout.py` docstring lines 31–34: "A candidate that is Sharpe-flat but CAGR-up via deployment is reported as such (deployment lever, not alpha) — NOT auto-promoted"). The gate threshold is just *another deployment knob* — the one deployment route 0059 left untested — and there is no prior reason it should behave differently from the three deployment knobs that already failed.

Concretely, the dissent's predicted decomposition: G88 lifts paired portfolio Sharpe (numerator-up from a little real edge in the sweep-conditioned slice + denominator-down from diversification + idle-calendar in-fill) **while** the incremental-band after-cost per-trade EV CI straddles or sits below zero — *because the unconditional [0.88, 0.92) band 0063 admits is a strict superset of the 0026 band, and the part 0063 adds over 0026 is precisely the NON-sweep trades that the 2026-04-22 survivor-cache measured at −0.46%/trade, "structurally negative-EV, parasitic in 4/6 years."* 0026 already measured the *better* (momentum-filtered) half of this band and still could not clear CI-low > 0. The half 0063 adds on top is the half that originally MOVED the gate to 0.92. There is no version of this where the unconditional band's standalone EV is *stronger* than the sweep-conditioned subset's — it can only be diluted.

**What shipping that actually does to the ~10 live users:** it converts a confidence-gated, ~27%-deployed book into a ~2×-turnover book where **each user takes roughly twice as many trades, each one slightly worse after cost.** Every incremental trade pays `BROKERAGE_PCT` both legs + `STT_PCT` on the sell — a guaranteed deterministic drag — in exchange for an expectancy whose CI includes zero. The portfolio-Sharpe number is a *fund-level* abstraction; the *user-level* experience is "the bot now tells me to buy more marginal-confidence names, and the average one loses a little." For a paid decision-support product, shipping more-trades-each-slightly-worse on the strength of a ratio that can rise without per-trade edge is the precise failure 0026's disable-default rule existed to prevent. **The per-user cost is concrete and paid every trade; the portfolio-Sharpe benefit is a path-statistic that may be an artifact.**

### 8.3 Is this just re-learning the 2021 bull deployment? — High prior, and the confound-2 guard is necessary but not obviously sufficient.

The lever's entire motivating number (0058 B−A, CAGR 16.5%→33.3%) was measured on a window where **2021 is +3.625 Sharpe / +106% CAGR** and 0058's own write-up records that **2021 carried ~41% of the 7d gross edge.** Gate-loosening's mechanism *is* deployment-into-idle-book; the year with the most idle-book-to-good-tape upside is, definitionally, the runaway bull. The dissent's prior: a large chunk of +0.357 is 2021 in-fill.

§3-confound-2 (drop-2021, drop-single-best-year, no-year->50%) is the right instinct, but the dissent flags two ways it can under-bite:
- **CPCV group→year mapping is many-to-one and leaky at the seams.** `DROP_GROUP_PERIOD = ("2021-01-01","2022-01-31")` drops a *group window*, not clean calendar 2021; with `EMBARGO_OBS=14` the bull-blowoff's influence bleeds into adjacent groups' train/test seams. "Drop-2021" removes the group, not necessarily all of 2021's deployment tailwind.
- **The >50% rule is a single-year concentration test; it does not catch a two-year bull cluster.** If 2021 *and* 2023 (both strong tape) together carry the lift at, say, 35% + 30%, no single year trips the 50% bar, yet the edge is still "good-tape deployment," not all-weather alpha. The dissent requests — and this is a pre-committed amendment ask — that the drop-2021 arm ALSO be reported with the bad-years (2019/2024/2025) shown *separately*, so the reviewer can see whether the lift is *negative or flat in every lean year* (which would confirm "this only deploys well in bull tape" — exactly the lean-year sector-audit finding that price-sector overlays "help only 2021 bull, HURT all 3 lean years"). A lift that is bull-tape-only is a market-beta timing bet dressed as an alpha gate, and it should KILL even if it survives the literal drop-2021 line.

### 8.4 The governance objection, independent of any number.

`min_confidence = 0.92` is **LOCKED to ≈2026-07-21 "regardless of live noise"** (CLAUDE.md, the 2026-04-22 decision). The lock was not a casual default — it was set *because the 0.88–0.92 band was identified as structurally negative-EV* and the lock exists specifically to stop the band being re-litigated on short-horizon noise. Filing a trial to re-open it **29 days before the lock expires**, on the strength of a backtest number, is — even granting the doc's careful "research ≠ live flip" framing — pattern-matching to exactly the impulse the lock was meant to resist. The disciplined action is **to wait out the lock and let the pre-committed 0026b forward-wall trigger (≥100 live band observations) accumulate**, because forward-wall live data is the one evidence class that is immune to every artifact in §8.1. Re-opening now spends a billed cloud run and owner attention to *maybe* front-run a trigger that will answer the question with better data in a few weeks anyway. The opportunity cost is real: this run's n_trials bump (→56) also deflates every *other* live candidate's DSR.

### 8.5 The ONE measurement that settles standalone edge — and whether the draft pre-commits to it.

**The single decisive measurement is the one in §3, confound 1 / §4, gate 3: the after-cost per-trade expectancy of the INCREMENTAL band (trades admitted by the loosened arm but NOT by G92 — i.e. confidence strictly in [0.0x, 0.92)), with a bootstrap 95% CI, and the ship-blocking requirement that its CI-low > 0.** This is the *only* metric on the list that asks the 0026 question on the 0063 population: "do the extra trades, in their own right, net positive after cost?" Portfolio Sharpe, drop-2021, DSR, plateau, tail-floor — every other gate can pass on a deployment/averaging artifact; this one cannot, because it never touches portfolio variance or calendar and isolates exactly the trades loosening adds.

**Does the draft pre-commit to it? — YES, and that is the trial's single strongest feature.** §3-confound-1 and §4-gate-3 make incremental-band CI-low > 0 a *mandatory, ship-blocking* gate, explicitly framed as "the direct analogue of 0026's 'CI-low > 0 or don't take the extra trades,' applied to 0063's correct (unconditional) population," and §5 commits that "Lift but incremental-band CI straddles 0 → KILL for ship purposes." The dissent's residual warnings, stated for the record so they cannot be waived at scoring time:
1. **Power.** 0026 had n=106 on the *sweep-conditioned* slice and still straddled zero. The unconditional incremental band will be larger (more trades) but also *diluted* with the −0.46% non-sweep half — the dissent's prior is that this CI will again straddle zero, and if it does, the rule must fire to KILL with no re-roll, exactly as 0026 did. **No "but the portfolio Sharpe was positive" override.** The doc says this; the dissent is on record holding it to it.
2. **The bootstrap must be on the SAME after-cost trade-return units as 0026** (net of `BROKERAGE_PCT` both legs + `STT_PCT` sell side), ≥10k resamples, not a t-approximation — fat tails inflate naive CIs the wrong way (the same class of flaw that produced the normal-DSR 0.952→0.87 correction in 0051/0058).
3. **If incremental-band CI-low > 0 AND drop-bad-years holds AND tail-floor holds — only THEN is the portfolio-Sharpe lift admissible as the thing that sizes the prize.** Portfolio Sharpe is the *magnitude* metric; the incremental-band CI is the *existence* gate. The draft orders them correctly. The dissent's whole position reduces to: **do not let a passing existence-gate be inferred from a passing magnitude-metric — they are independent, and only the existence gate defends the user.**

### 8.6 Skeptic's bottom line

Re-opening is defensible *only* as a measurement, *only* with §4-gate-3 enforced literally and asymmetrically, *only* with the bad-year decomposition strengthened per §8.3, and *only* with owner sign-off that accepts the lock is being probed 29 days early at a billed-run + DSR-deflation cost. The expected outcome, on the dissent's prior, is **KILL at gate 3** (incremental-band CI straddles zero, exactly as 0026) with a recorded "portfolio Sharpe rose but it was deployment, not alpha" — i.e. the same verdict as the other three deployment knobs, and a re-confirmation that the 0.92 lock is protective. If that is the outcome, the disciplined read is not "we were unlucky" but "the per-trade EV CI was right the first time, and forward-wall live data (0026b), not another backtest, is the instrument that should reopen this." The trial may proceed; it must not be allowed to ship on the magnitude metric alone.
