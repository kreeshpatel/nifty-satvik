# Long-Horizon Strategy — Destination-Ordered Roadmap

> Grounded in the real repo as of 2026-06-27. Numbers come from files, not memory.
> Sources: `models/long_horizon/config.json`, `long_horizon/STRATEGY_FULL.md`,
> `long_horizon/audit/` (Phase-1 wiring audit), `long_horizon/brain.md`,
> `long_horizon/charter.md`, `docs/LIVE_OVERLAY_PROTOCOL.md`.
>
> **This is the master roadmap.** Other long-horizon program docs reference it. When a
> stage gate, promotion bar, or owner decision is restated elsewhere, this file is authoritative.

---

## Why this is reframed (read first)

The previous roadmap was a linear 8-phase research march (audit → must-fix → stages →
harness → conviction → hybrid → swing → methodology). That ordering optimised for "do the
research phases in sequence." It did not make the **destination** — *a corrected-universe,
conviction-layered, fully-validated model gating real capital for ~10 paying users* — the
organising principle.

This version is **destination-ordered**: every stage is a step on the single critical path to
the first real rupee, and the path is built so that *trust is established before trade*. The
re-org changes sequencing and emphasis, not the underlying engineering work or any frozen number.

| Old (linear research phases) | New (destination-ordered critical path) |
|---|---|
| P1 Audit & hardening → **DONE** | **Phase 1 — DONE** (unchanged: audit + safe hardening, golden master byte-identical) |
| P2 Must-fix before research | Folded into **Stage A** (reproduce baseline) + **Stage B** (corrected universe) |
| P3 Stage roadmap (A–E sub-stages) | Replaced by the six destination stages **A → F** below |
| P4 Statistical harness | **Stage A** (harness is the *first* thing built — trust before trade) |
| P5 Conviction model | **Stage C** (conviction *within* top-15 → drives the hybrid layers) |
| P6 Hybrid sizing/exit/risk | **Stage D** (conviction-driven, each layer separately gated) |
| P7 Swing research | **Deferred** (off critical path; revisit post paper-gate) |
| P8 Methodology ingestion | **Continuous** (governance / data-quality / rigor / monitoring) |
| (tail hedge / vol-carry second stream) | **Stage G** — the Sharpe↑/DD↓ end-stage (scheduled towards the end; off the *near-term* path, not indefinitely deferred) |

---

## Owner decisions (2026-06-27) — these set the shape

These three decisions are **locked** and drive every stage below. Do not relitigate without owner sign-off.

> **Decision 1 — Hold live until the conviction layer is in.**
> Real capital WAITS on the full research track. The frozen base does **not** go live on its
> own. Quality before speed. (The frozen base remains a fallback — see tradeoff 4 — but the
> default plan is to ship the conviction-layered system, not the bare base.)

> **Decision 2 — Model evolution = conviction-within-top-15 → sizing / exit / risk, ONLY.**
> The only sanctioned model-evolution axis is a conviction score *among the already-selected
> top-15 names*, feeding sizing, exit, and risk layers. The defined-risk **tail hedge** and the
> **vol-carry "second orthogonal stream"** are DEFERRED — off the near-term critical path,
> revisited only post-live.

> **Decision 3 — Fix the universe BEFORE live.**
> Widen to `current_members ∪ config.NIFTY_500`, include financials via a capital-adequacy
> proxy, **RE-DERIVE the frozen cfg on the corrected universe**, and accept a new (likely
> different) baseline. This is the sanctioned heavy-path re-derivation per
> `docs/LIVE_OVERLAY_PROTOCOL.md` — a deliberate, golden-master-regenerating change, not a live tweak.

---

## Honest tradeoffs (state them, don't hide them)

1. **The path to the first real rupee is materially longer.** Foundation re-derivation
   (Stage B) + conviction (Stage C) + hybrid layers (Stage D) + a **fresh ≥30-trade paper
   window** (Stage E) all precede live. This is the deliberate cost of Decision 1.
2. **The headline has already moved.** Stage A2 (cloud re-derivation on the frozen cfg, 397
   solvent names, corrected-682 universe, exit-parity-unified engine) produced **baseline_v0**
   (committed `research/baseline_v0.json`): **gross CAGR 26.1% / Sharpe 1.02 / maxDD −41.9% /
   Calmar 0.62; after-tax STCG 20%: CAGR 23.1% / Sharpe 0.83 / maxDD −45.6% / Calmar 0.51.**
   The previously reported 30.26% (optimistic-exit measurement, superseded 2026-06-27) and the
   ~32% / 1.31 walk-forward (same optimistic-exit, superseded) are historical provenance — do
   NOT present them as current expectations. The exit-parity unification cost ~4 pp CAGR;
   STRATEGY_FULL §6 said this was to be re-confirmed — baseline_v0 is that re-confirmation.
   Stage B's survivorship re-derivation (+284 delisted names → baseline_v1) will likely move
   the number further **down** (survivor-only data flatters returns). We anchor to the honest
   new number and update as each stage produces a new baseline.
3. **The paper-gate clock RESETS at Stage B.** The current paper book runs on the old base; the
   corrected re-derived base starts a *fresh* book. The ≥30-trade / ~2-month clock starts from zero.
4. **Stages C/D may mostly KILL** (the §11 history is a graveyard of plausible levers). Conviction
   must EARN its place through the promotion bar. If it cannot clear the bar, the corrected,
   re-derived **frozen base is still shippable** on its own — at which point Decision 1 is revisited
   with the owner.

---

## Cross-cutting requirements (every stage, every experiment)

These apply without exception to every backtest, research result, and live promotion decision:

| Requirement | Spec |
|---|---|
| Walk-forward type | Sliding-origin expanding windows; re-derive operating values per fold on the training slice only |
| OOS reserve | 18–24 months forward wall, fixed at the start of each stage; no peeks |
| Bootstrap | Block-bootstrap, block = 63 trading days, n = 5,000 resamples; report median + [5th, 95th] |
| Cost accounting | Post-tax, post-cost on every metric: brokerage 0.03% + STT 0.10% both legs + tiered ADV slippage + 5% ADV cap + stamp/exchange/SEBI/GST micro-costs (~3.5 bps, currently excluded — add before any promotion) |
| Promotion bar (7) | PROMOTE only when ALL hold: post-tax post-cost ΔSharpe ≥ +0.10, ΔCalmar ≥ +0.05, 2022–2026 sub-period positive ΔCAGR, walk-forward fold-pass ≥ 60%, bootstrap 95% CI on ΔSharpe excludes 0, turnover increase ≤ 30%, mechanism explainable in one sentence. SHADOW if 4–5 hold. REJECT otherwise. |
| Kill switch | Any single kill-criteria trigger (WR < 45% on 20 live trades, 30d realized Sharpe < 0, 5 consecutive zero-signal days) → immediate review |
| Decay monitor | `signal_analytics.json` IC vs rolling forward wall; degrade alert if 90d rolling IC < 0.02 |
| Verdicts | PROMOTE-CANDIDATE / UNDERPOWERED / KILL — all three are first-class outcomes; bare pass/fail is not a verdict |
| Stage-gate discipline | **STOP after each stage; owner reviews and confirms before the next stage starts.** No stage is concurrent with its successor. |

---

## Phase 1 — Audit & Safe Hardening

**Status: DONE (2026-06-27)**

**Commits:** `ab585c3` (audit docs + issue ledger), `b653f52` (safe Phase-1 wiring fixes).
**Test suite:** 1,814 passed, 8 skipped, 0 failed. **Golden master: byte-identical** (3 passed) —
no engine behaviour changed; the frozen `cfg` and `portfolio.simulate` outputs are bit-for-bit
unchanged.

### What was done

The full wiring audit (`long_horizon/audit/`) ran parallel auditors against the real data files
plus the live code, with every red/HIGH finding adversarially re-verified. Verdict: the core math
is honest and the exit decision layer is byte-identical between backtest and live (shared
`engine.exit_logic.decide_exit`). The risk was concentrated in **data plumbing and booking-layer
parity**, not in the signal or the math.

Safe hardening shipped that *did not* alter engine behaviour (observability, push durability,
parity, reproducibility): demerger quarantine guard (VEDL), 48-invisible-member observability,
drift-alert wiring, real gap-fill stop booking, kill-log durability, aging-from-fill correction,
fund-store path anchoring, logged feature-compute failures, 0-share BUY guard, persisted equity
curve, pyarrow pin. Full W-id ledger in `long_horizon/audit/wiring_issues.md` and
`long_horizon/audit/PHASE1_FIXES.md`.

### Also in place (the program OS)

- **Program OS + skills** — the long-horizon research operating system (pre-registration
  framework, HOLDOUT discipline, golden-master gate, charter/brain docs) is built and on `main`.
- **Governance protocol** — `docs/LIVE_OVERLAY_PROTOCOL.md` codifies the heavy-path
  re-derivation route (the sanctioned way to change the frozen cfg, used in Stage B).

The heavy-path items the audit flagged but **could not** fix safely (universe union, financials
D/E policy, CA-type-aware cleaner, kill-equity anchoring) are now **stages** below, not loose
TODOs — they require golden-master regeneration and/or new data and so belong on the gated path.

---

## The Destination-Ordered Roadmap (critical path to real capital)

Six stages, A → F. Each is self-contained, ends with an owner confirmation gate, and is **not**
concurrent with its successor. Stage A is the immediate next action.

```
A  Trustworthy ground   →  B  Corrected universe   →  C  Conviction model
   (harness reproduces       + re-derived base          (within top-15)
    the headline + KILLs)     (new baseline_v1)
                                                            │
F  Live capital   ←   E  Paper-revalidate   ←   D  Conviction-driven hybrid
   (kill switch +        (fresh ≥30 trades /        (sizing / exit / risk,
    decay monitor)        ~2 months, observe→enforce)  each layer gated)
```

---

### Stage A — Trustworthy ground

**Objective.** Before changing anything, prove the measurement apparatus reproduces the *current*
base. A research harness that cannot re-derive today's headline cannot be trusted to judge
tomorrow's lever. Trust before trade.

**Key work.**
- Build the statistical harness in `src/research/` — thin, reusable modules mirroring the v1
  `src/validation/` pattern: a backtest wrapper, sliding-origin walk-forward, block-bootstrap,
  power/MDE, pre-registration helpers, and a three-way verdict.
- Trigger the cloud `cpcv-research.yml` re-derivation of the **CURRENT** base (frozen cfg,
  `load_frozen_cfg()`) on the canonical corrected universe; persist the `equity_curve`.
- Commit `long_horizon/results/baseline_v0.json` (Sharpe, CAGR, DD, Calmar, trades/year,
  equity-curve hash) — the yardstick every later stage is measured against.

**Validation gate — COMPLETE (2026-06-27).** The cloud re-derivation (Stage A2) ran on the
frozen cfg, corrected-682 universe, 397 solvent names, exit-parity-unified engine and produced
`research/baseline_v0.json`:

| Metric | Gross | After-tax STCG 20% |
|---|---|---|
| CAGR | **26.1%** | **23.1%** |
| Sharpe | **1.02** | **0.83** |
| maxDD | **−41.9%** | **−45.6%** |
| Calmar | **0.62** | **0.51** |
| Trades/yr | ~152 (1 445 total) | — |
| WR | 59.7% | — |

The previously reported 30.26% CAGR / 1.15 Sharpe (optimistic-exit measurement) is SUPERSEDED
by baseline_v0 as of 2026-06-27. Exit-parity unification cost ~4 pp CAGR; after-tax STCG a
further ~3 pp / ~0.18 Sharpe. §11 KILLs re-verification is the remaining A-gate item; harness
is trusted on the reproduction axis. STOP for owner confirmation before Stage B.

**REUSE (do not rebuild).**
- `src/validation/{cpcv,overfitting,bootstrap,power,factor_metrics,null_test}.py` — CPCV folds,
  deflated Sharpe, block-bootstrap, MDE, IC/breadth, matched-permutation null.
- `long_horizon/backtest/portfolio.simulate` — the engine; harness wraps it, never reimplements it.
- The pre-registration framework (`long_horizon/preregistry/`, HOLDOUT discipline).
- Cloud workflow `cpcv-research.yml` (the re-derivation trigger).

---

### Stage B — Corrected universe + re-derived base

**Objective.** Execute Owner Decision 3: fix the universe *before* live, then re-derive and
re-freeze the cfg on the corrected universe, accepting the honest new baseline.

**Key work.**
- **B1 — Root CA-aware OHLCV cleaner.** Replace the "any ≥50% single-session drop = split"
  heuristic with a corporate-action classifier: cross-reference `yf.Ticker.actions` to separate
  a true split from a demerger (the VEDL lesson — back-adjustment fabricated +2.16 → +24.94
  slope). NaN `sma200_slope_63` for demerger names until clean post-event bars accumulate.
- **B2 — Universe union + entrants' data.** Widen
  `ds.stocks = sorted(current_members(membership, today) ∪ set(config.NIFTY_500))`; backfill PIT
  fundamentals + delisted OHLCV for the ~48 new entrants (today 0/48 have fundamentals coverage).
- **B3 — Financials capital-adequacy policy.** Banks + lending NBFCs (HDFCBANK, ICICIBANK, SBIN,
  BAJFINANCE) currently fall out because D/E = NaN from Screener Borrowings/net-worth. Replace the
  blanket D/E drop for Banking/NBFC GICS sectors with a **capital-adequacy proxy** (Tier-1 /
  CRAR-style), so financials are included on a leverage-appropriate basis.
- **B4 — Re-derive + re-freeze.** New pre-reg → walk-forward re-derivation of the cfg on the
  corrected universe → **regenerate the golden master** in the same PR → commit
  `baseline_v1.json` + the new `config.json`. **RESTART the paper book** (tradeoff 3).

**Validation gate.** The corrected-universe walk-forward holds (sliding-origin, ≥60% fold-pass,
positive 2022–2026 sub-period, bootstrap CI excludes 0 vs a null); the new headline is recorded
honestly even if it moved (tradeoff 2). Decision recorded as **ADR-0003**. Golden master
regenerated and green. STOP for owner confirmation.

**REUSE.** Stage-A harness (all of it); `data/data_store.py::clean_ohlcv_for_features` (extend,
don't replace); `fundamentals_pit_screener.pkl` store; `docs/LIVE_OVERLAY_PROTOCOL.md`
(this *is* the sanctioned heavy-path re-derivation); `diagnostics.build_golden_fixture`.

---

### Stage C — Conviction model (within top-15)

**Objective.** Execute Owner Decision 2's first half: a **conviction score among the already-selected
top-15 names**, lifting per-trade expectancy without changing the universe selection or exit logic.

**Key work.**
- New module `src/research/conviction.py`. PIT-safe features only (rolling, no lookahead — every
  feature follows the `_compute_stock_features` discipline).
- Model form is **inspectable**: z-score blend / logistic / ranked composite. **NO uninspectable
  ML** — a conviction score must be explainable in one sentence (promotion-bar criterion 7).
- Output `conviction_score` + `conviction_quintile` per held name; write both into
  `signals_today.json` (additive — does not change which names are selected, only annotates them).

**Validation gate.** Through the Stage-A harness: **conviction-top-15 vs rank-only** must clear
the 7-criterion promotion bar on `baseline_v1`. Pre-registered before any cloud run. UNDERPOWERED
and KILL are acceptable outcomes (tradeoff 4). STOP for owner confirmation.

**REUSE.** Stage-A harness; `src/validation/factor_metrics.py` (IC/IR of the conviction score);
`src/validation/null_test.py` (matched-permutation null — the AUD-022 lesson: IC verdicts need a
matched null); the pre-registration framework. Candidate hypotheses (low-vol blend, quality/fraud
filter, PEAD) are catalogued in `long_horizon/brain.md` — each enters as its own pre-reg.

---

### Stage D — Conviction-driven hybrid layers

**Objective.** Execute Owner Decision 2's second half: let the Stage-C conviction *drive* sizing,
exit, and risk — each layer promotion-bar-gated **separately**.

**Key work (each is its own pre-reg + gate).**
- **Sizing** — quintile-scaled, **mean-preserved** (don't lift average risk; redistribute it),
  with the 15% position cap still binding. Higher conviction → larger within-cap weight.
- **Exit** — Q1 (low-conviction) tighter stop/target; Q5 (high-conviction) wider, to let the
  best names run within the 63-day cap.
- **Risk** — soft sector / correlation caps (soft, not the hard sector caps that were KILLED for
  hurting lean years).
- **Sell-replace (S1–S7 / R1–R4)** — capital-reallocation rules: fill a freed slot with the
  current top-ranked non-held name. **Sector EXIT / ROTATION (S4 / R3) are NOT pre-killed** —
  they are distinct tests from the §11 sector-*selection* overlay KILLs.

**Validation gate.** Each layer separately clears the 7-criterion promotion bar on `baseline_v1`
through the harness; turnover stays ≤ +30%; mean risk is preserved. A layer that fails is dropped,
not forced. STOP for owner confirmation after the hybrid set is assembled.

**REUSE.** Stage-A harness; the shared sizing/exit kernels (`base_risk_qty`,
`engine.exit_logic.decide_exit`, `portfolio.simulate`) — extend behind flags, never fork;
golden-master gate on any kernel change.

> **KILLED — do not re-open** (`STRATEGY_FULL.md §11`): regime / dual-momentum entry gate,
> residual/beta-stripped momentum, frog-in-the-pan, sector-residual + sector **selection**
> overlays, RSI/MACD/ROC reversal, signal-level low-vol blend, earnings+ROE over-filter,
> min_hold = 20 (the worst point in the sweep). Hard sector-exposure caps (hurt lean years).
> *Sector EXIT/ROTATION (S4/R3) are a different test and are NOT pre-killed.*

---

### Stage E — Paper-revalidate the full system

**Objective.** The pre-committed real-capital gate. Validate the *complete* corrected,
conviction-layered system in paper before any real rupee.

**Key work.**
- Run the full Stage-B + C + D system on the **fresh** paper book (the Stage-B restart).
- Accumulate **≥ 30 paper trades over ~2 months**; review outcomes against `baseline_v1`.
- Flip the kill-criteria from **observe → enforce**.

**Validation gate.** ≥30 trades / ~2 months reviewed; live paper metrics consistent with
`baseline_v1` (no regime-shift surprise, kill switch not tripped); kill-criteria in enforce mode.
This is **the** gate to Stage F. STOP for owner confirmation.

**REUSE.** `signal_tracker.py` lifecycle; `results/portfolio_history.csv` + `paper_equity.py`
ledger; `signal_analytics.json` IC tracking; the existing kill-criteria machinery (observe→enforce flip).

---

### Stage F — Live capital

**Objective.** First real rupee, under continuous protection.

**Key work.**
- **Kill switch** armed: WR < 45% on 20 live trades, 30d realized Sharpe < 0, OR 5 consecutive
  zero-signal days → immediate halt + review.
- **Decay monitor** armed: 90d rolling IC < 0.02 on the forward wall → degrade alert.
- Real-capital sizing within the frozen (Stage-B re-derived) cfg caps.

**Validation gate.** Kill switch + decay monitor both live and tested; owner authorises real
capital explicitly. Continuous monitoring (below) runs indefinitely.

**REUSE.** Kill-criteria machinery (now in enforce mode from Stage E); decay monitor against
`signal_analytics.json`; `portfolio_history.csv` for the live equity curve.

---

### Stage G — Structural risk profile (Sharpe ↑ / drawdown ↓) — *towards the end*

**Objective.** Resolve the **low Sharpe + deep drawdown** that the base carries (baseline_v0:
gross Sharpe 1.02 / −41.9% DD; after-tax 0.83 / −45.6%). This is the dedicated end-of-project
risk-profile stage — the lever set that Stages C/D (conviction) and the live vol-target do **not**
fully reach. Added per owner (2026-06-27): the deep DD/Sharpe fix must be *in the plan*, scheduled,
not vaguely deferred.

**Key work (the actual levers, ordered by evidence).**
- **Defined-risk tail hedge** (Nifty puts in DD regimes) — per 0070, the *only* lever that takes
  DD to a dependable **−30%** without killing CAGR (the regime-gate trap; sizing/market-state
  overlays plateau ~−38%). Needs its own options/vol-carry backtester + PIT F&O data foundation.
- **Vol-carry second stream** (IV > realized) — an *orthogonal* Sharpe source (a different premium,
  not another momentum signal), so portfolio composition finally pays. Optional, heavier.
- **De-leverage trade-offs** — risk 3% → ~1.5% buys a smoother curve at a CAGR cost; quantify the
  honest frontier.

**Why "towards the end."** It is sequenced *after* (a) Stages C/D reveal how much Sharpe/DD the
conviction work already recovers — so we size this stage to the *residual* gap, not a guess — and
(b) Stage F establishes a real live-risk baseline. It is the **gate to SCALING** real capital: first
live runs on the conviction-layered base with the kill-switch + live vol-target managing a ~−40% DD
operationally; Stage G is what earns a dependable −30% before the book is scaled up.

**Validation gate.** Any tail-hedge/vol-carry arm must pass the 7-criterion promotion bar
(post-tax post-cost) AND demonstrably cut DD *without* killing CAGR, on its own backtester +
data foundation, pre-registered. Honest expectation: conviction lifts Sharpe; only this stage
moves DD structurally below ~−38%.

**STOP for owner confirmation before starting — not now (owner deferred the active work).**

---

## Continuous (runs alongside every stage)

Not a stage — standing disciplines that never stop:

| Track | What it enforces | Anchor |
|---|---|---|
| **Governance** | Every change follows pre-reg → harness → registry → ADR → ship. The frozen cfg only changes via the heavy path. | `docs/LIVE_OVERLAY_PROTOCOL.md`, `long_horizon/preregistry/` |
| **Data-quality** | On any data change (universe, OHLCV cleaner, fundamentals): re-run coverage + CA asserts before trusting a number. | B1 cleaner, panel-coverage assert |
| **Backtest-rigor** | No number is trusted before it passes the cross-cutting requirements table (walk-forward, OOS reserve, bootstrap, post-tax-post-cost). | Stage-A harness |
| **Monitoring** | Cron health, drift alerts, push-durability, decay IC — all on every live run. | `cron_health`, `signal_analytics.json` |
| **n_trials / DSR** | Cumulative trial count tracked; deflated-Sharpe threshold rises with every experiment. | `src/validation/overfitting.py::deflated_sharpe_ratio` |
| **Golden-master gate** | Any change to `decide_exit`, `base_risk_qty`, or `portfolio.simulate` regenerates the golden master *in the same PR*. | `diagnostics.build_golden_fixture` |

---

## Deferred (off the near-term critical path)

Explicitly NOT on the path to first live capital. Revisited only when the owner re-opens them.

| Deferred item | Why deferred | Revisit when |
|---|---|---|
| **Tail hedge (defined-risk options)** | Owner Decision 2: off the *near-term* critical path. NOT deferred indefinitely — now scheduled as **Stage G** (the Sharpe↑/DD↓ end-stage), the dependable −30% DD lever. | **Stage G** (towards the end; gates scaling) |
| **Vol-carry "second orthogonal stream"** | Owner Decision 2: a second return stream is a separate program, not model-evolution-within-top-15. Now an optional arm of **Stage G**. | **Stage G** (towards the end) |
| **Swing research (5–14 day)** | Separate horizon, separate charter, separate baseline. Zero interaction with the 63-day scanner. | Post paper-gate (Stage E cleared) |

> **One live overlay is already on the paper book and stays** — pre-reg **0068** vol-target
> (`vol_target_annual` 0.15 / `vol_window` 42 / `vol_floor` 0.40), applied to the paper-portfolio
> sizing equity only, in `config.json::live_overlays`. It is **NOT** part of the frozen `cfg`
> block, so the research baselines and golden master are unaffected. CAGR-neutral DD reduction
> (~−45 → −39 in-backtest). This is the *only* overlay live; the tail hedge above is what would
> take DD to a dependable −30.

---

## Frozen facts (confirm against `models/long_horizon/config.json` — do not invent)

**Frozen `cfg` (UNCHANGED by this reframe; re-derived only at Stage B):**

| Param | Value |
|---|---|
| `signal` | `sma200_slope_63` |
| `gate_quantile` | 0.5 |
| `stop_atr_mult` | 3.67 |
| `target_pct` | 22.52 |
| `trailing_activate_pct` / `trailing_pct` | 4.0 / 4.27 |
| `min_hold_days` / `max_hold_days` | 10 / 63 |
| `risk_per_trade_pct` | 3.0 |
| `max_position_pct` | 15.0 |
| `max_adv_participation_pct` | 5.0 |
| `max_positions` | 15 |

**Headline — HONEST BASELINE_V0 (frozen-cfg arm, Stage A2 result, 2026-06-27):**
**Gross: 26.1% CAGR / 1.02 Sharpe / −41.9% DD / Calmar 0.62 / ~152 trades/yr / WR 59.7%**
**After-tax STCG 20%: 23.1% CAGR / 0.83 Sharpe / −45.6% DD / Calmar 0.51**
Source: `research/baseline_v0.json` — corrected-682 universe, 397 solvent names,
exit-parity-unified engine. This is the yardstick every later stage is measured against.

*Previously reported (optimistic-exit, superseded 2026-06-27):* 30.26% CAGR / 1.15 Sharpe /
−40% DD / Calmar 0.76 / ~154 trades/yr. Not a target to defend — retained for provenance only.
NOT the 34.67% re-derived variant. Anchor to baseline_v0 until Stage B produces `baseline_v1`.

**Walk-forward (re-derive per fold) ≥ 2019 — PENDING RE-CONFIRMATION:** the ~32% CAGR /
1.31 Sharpe / 0 negative years figure was measured with the same optimistic-exit as the old
headline. It is NOT a current figure — treat as historical provenance (superseded 2026-06-27).
A corrected walk-forward on the exit-parity-unified engine is pending (CPCV run post Stage A
§11 KILLs verification).

**§11 KILLs:** regime / dual-momentum gate, residual/beta-stripped momentum, frog-in-the-pan,
sector-residual + sector SELECTION overlays, RSI/MACD/ROC reversal, signal-level low-vol blend,
earnings+ROE over-filter, min_hold = 20 (worst point). *Sector EXIT/ROTATION (S4/R3) are a
different test — not pre-killed.*

**Promotion bar (7):** post-tax post-cost ΔSharpe ≥ +0.10, ΔCalmar ≥ +0.05, 2022–26 positive,
fold-pass ≥ 60%, bootstrap CI excludes 0, turnover ≤ +30%, mechanism explainable.

---

## Decision log (locked choices, do not relitigate)

| Decision | Value | Rationale | Source |
|---|---|---|---|
| Signal | `sma200_slope_63` | Highest IC at 63d; robust across bootstrap and walk-forward folds | `long_horizon/brain.md` |
| min_hold | 10 trading days | 10 → 33–36% CAGR; 20 → ~22%, the worst point in the sweep | `STRATEGY_FULL.md §11` |
| Market-regime gate | OFF | All 4 arms (entry_trend, exit_trend, breadth, dual-momentum) hurt CAGR or whipsawed | `long_horizon/brain.md §REGIME GATE = KILL` |
| D/E threshold | 0 ≤ D/E < 1.5 | Threshold-robust; solvency fix removed distressed-pump names (35.5 → 30.3 CAGR, optimistic-exit era; baseline_v0 solvent arm = 26.1% under exit-parity-unified engine) | `long_horizon/brain.md §SOLVENCY-CORRECTED` |
| Drawdown tolerance | ~−40% accepted | The regime gate that cuts DD kills the CAGR; vol-target gets ~−39% CAGR-neutrally; dependable −30 needs the deferred tail hedge | `STRATEGY_FULL.md §15` |
| Params frozen | Yes — re-derived only at Stage B (heavy path) | Derived once on pre-2017 train slice; confirmed stable across folds; corrected-universe re-derivation is the one sanctioned change | `models/long_horizon/config.json`, `docs/LIVE_OVERLAY_PROTOCOL.md` |
| Owner Decision 1 | Hold live until conviction layer is in | Quality before speed; real capital waits on the full track | §Owner decisions |
| Owner Decision 2 | Model evolution = conviction-within-top-15 → sizing/exit/risk only | Tail hedge + vol-carry deferred off the critical path | §Owner decisions |
| Owner Decision 3 | Fix the universe before live (union + financials proxy + re-derive) | Sanctioned heavy-path re-derivation; accept the honest new baseline | §Owner decisions |

---

## Status summary

| Stage | Title | Status |
|---|---|---|
| Phase 1 | Audit & Safe Hardening | **DONE** (2026-06-27; commits `ab585c3`, `b653f52`; golden master byte-identical) |
| A | Trustworthy ground (harness + reproduce baseline + KILLs) | **IN PROGRESS** — A2 cloud re-derivation COMPLETE (baseline_v0: gross 26.1%/1.02 Sharpe, after-tax 23.1%/0.83); §11 KILLs re-verification pending; gated on owner sign-off |
| B | Corrected universe + re-derived base (`baseline_v1`, ADR-0003) | NOT STARTED — blocked on A |
| C | Conviction model (within top-15) | NOT STARTED — blocked on B |
| D | Conviction-driven hybrid (sizing / exit / risk) | NOT STARTED — blocked on C |
| E | Paper-revalidate full system (≥30 trades, observe→enforce) | NOT STARTED — blocked on D |
| F | Live capital (kill switch + decay monitor) | NOT STARTED — the pre-committed real-capital gate |
| — | Continuous (governance / data / rigor / monitoring) | ONGOING — parallel to every stage |
| — | Deferred (tail hedge / vol-carry / swing) | OFF CRITICAL PATH — revisit post-live |

---

## Immediate next action

**Stage A — §11 KILLs re-verification (A2 cloud re-derivation is DONE).**

Stage A2 is complete: the harness ran on the frozen cfg + corrected-682 universe +
exit-parity-unified engine and established **baseline_v0** (`research/baseline_v0.json`):
- Gross: **26.1% CAGR / 1.02 Sharpe / −41.9% DD / Calmar 0.62 / ~152 trades/yr / WR 59.7%**
- After-tax STCG 20%: **23.1% CAGR / 0.83 Sharpe / −45.6% DD / Calmar 0.51**

The previously reported 30.26% / 1.15 headline (optimistic-exit, superseded 2026-06-27) is
HISTORICAL PROVENANCE ONLY. Exit-parity unification cost ~4 pp CAGR; after-tax a further ~3 pp.

**Remaining A-gate item:**
1. Re-run killed §11 levers through the harness against baseline_v0; confirm all still KILL.

Then STOP for owner confirmation before Stage B.

**Stage B reminder:** the survivorship re-derivation (+284 delisted names → baseline_v1)
will likely move the baseline further DOWN — survivor-only data flatters returns. Accept the
honest new number.
