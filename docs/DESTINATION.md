# DESTINATION — Where the Long-Horizon Strategy Is Going

*Written 2026-06-27. Grounded in `long_horizon/STRATEGY_FULL.md`, `long_horizon/charter.md`,
`long_horizon/brain.md`, `models/long_horizon/config.json`, and the Phase-1 audit
(`long_horizon/audit/wiring_report.md`, `wiring_issues.md`, `PHASE1_FIXES.md`).*

> This document is the honest answer to "what does done look like?" It is not a roadmap
> (that is `long_horizon/charter.md` §Phased build). It is a statement of the shape of the
> finished product — what it IS and IS NOT, what "better" means and what the bar is, and
> what must be true before any real rupee enters the book.

---

## 1. What this strategy is — and is not

**What it is:**

A systematic, long-only, cross-sectional trend-momentum strategy for NSE large- and
mid-cap equities. It ranks a PIT-membership-masked, liquidity-filtered, solvency-filtered
universe by `sma200_slope_63` (the 63-session slope of each stock's 200-day moving
average) and holds the top 15. Exits are managed by an ATR-based stop, a fixed profit
target, a trailing stop, and a hard 63 trading-day time cap. Every parameter was derived
once from the pre-2017 training slice and frozen (`models/long_horizon/config.json → cfg`).

The edge is documented, mechanistically grounded (Jegadeesh–Titman intermediate-term
momentum; under-reaction and institutional flow accumulation; leverage removal of the
momentum-crash tail; liquidity filter that converts a fake 45% headline into an honest 30%),
and validated by a walk-forward that re-derives parameters per fold. The strategy is
**rules-based and fully inspectable** — there is no ML model, no daily re-optimisation, and
no uninspectable score. That is a deliberate design choice and a non-negotiable constraint
(see §4).

**What it is not:**

- A guaranteed-return machine. Research backtests overstate live returns. Live will be
  lower and noisier.
- A low-volatility book. The base carries **~−42% maximum drawdown** (honest reproducible
  anchor — `baseline_v0.json`, exit-parity-unified engine, 397-name solvent arm of the
  682-name corrected universe, 2017–2026: gross CAGR 26.1%, Sharpe 1.02, Calmar 0.62,
  ~152 trades/yr, WR 59.7%; after-tax STCG 20%: CAGR 23.1%, Sharpe 0.83, maxDD −45.6%).
  Previously reported as 30.3%/1.15 (optimistic-exit fill, `cpcv_long_horizon_final_682.json`);
  superseded by `baseline_v0` 2026-06-27 — the exit-parity unification costs ~4pp CAGR,
  and STCG a further ~3pp. That is the price of this return profile; the regime gate that
  would cut drawdown also kills return (tested four ways, killed — §11 of `STRATEGY_FULL.md`).
  A real client must be prepared to stomach a 40-plus-percent peak-to-trough decline.
- A smooth compounding machine. Bootstrap Sharpe 5th percentile is 0.58 — below buy-and-hold
  in the worst ~5% of resampled paths. The median (1.23) clearly beats buy-and-hold, but the
  edge concentrates in momentum-friendly years; choppy or reversal regimes are flat to modest.
- A strategy backed by live trade history. As of 2026-06-27, it has **never traded a single
  live rupee**. All performance numbers are research backtests. The paper book (₹10L clean
  start) is accruing now; real capital is gated.

---

## 2. The honest base — locked, never re-litigated

The base is a Titman-class trend signal on a clean universe. It is **locked**:

| Parameter | Value | Source |
|---|---|---|
| Signal | `sma200_slope_63` | `config.json → cfg.signal` |
| Selection | top 15 by cross-sectional percentile rank | `cfg.max_positions` |
| Stop | 3.67 × ATR(63), close-only | `cfg.stop_atr_mult` |
| Profit target | +22.52% | `cfg.target_pct` |
| Trailing arm | +4.00% | `cfg.trailing_activate_pct` |
| Trailing band | 4.27% below close-peak | `cfg.trailing_pct` |
| Min hold | 10 trading days (profit-taking suppressed; stop always active) | `cfg.min_hold_days` |
| Max hold | 63 trading days | `cfg.max_hold_days` |
| Risk per trade | 3.0% of equity ÷ stop distance | `cfg.risk_per_trade_pct` |
| Position cap | 15% of equity | `cfg.max_position_pct` |
| Capacity cap | 5% of 20-day rupee ADV | `cfg.max_adv_participation_pct` |

**Expected performance (honest reproducible anchor — `baseline_v0.json`, exit-parity-unified
engine, 397-name solvent arm, 2017–2026):**

| | Gross | After-tax STCG 20% |
|---|---|---|
| CAGR | 26.1% | 23.1% |
| Sharpe | 1.02 | 0.83 |
| Max drawdown | −41.9% | −45.6% |
| Calmar | 0.62 | 0.51 |
| Trades/yr | ~152 | — |
| Win rate | 59.7% | — |

**The 23.1% after-tax figure is what a client actually nets** — gross is a pre-cost ceiling,
not a deliverable. Both numbers are research backtest (never traded live); live will be lower.

*Previously reported as ~30.3% CAGR / 1.15 Sharpe (optimistic-exit fill,
`cpcv_long_horizon_final_682.json`). That figure is superseded by `baseline_v0` as of
2026-06-27. The exit-parity unification (backtest now fills targets conservatively, matching
live behaviour) costs ~4pp CAGR over the full window; STCG is a further ~3pp/~0.18 Sharpe.
`STRATEGY_FULL.md §6` explicitly flagged this re-confirmation as pending; `baseline_v0` IS
that re-confirmation.*

*Walk-forward ≥2019 (~32% CAGR / 1.31 Sharpe, zero negative years) was also measured under
optimistic-exit and has NOT yet been re-confirmed on the exit-parity engine. Do NOT present
it as a current figure — it is pending re-confirmation on the Stage B corrected-universe run.*

**Anchor only on 26.1% gross / 23.1% after-tax.** The per-trade tradelog variant that re-derives
parameters on the full dataset reads 34.67% / 1.248; that is an in-sample, separately-derived
point, not the live-traded frozen-cfg number. Any internal comparison that uses 34.67% or the
superseded 30.3% as the base is misanchored (W-21 in the audit ledger).

**What has been tested and killed — do not relitigate without genuinely new evidence:**
market-regime / dual-momentum entry gate; residual/beta-stripped momentum; frog-in-the-pan;
sector-residual momentum and sector overlays for selection; all reversal/RSI/MACD/ROC
signals; signal-level low-volatility blending; heavier quality screens (earnings + ROE on
top of the debt filter); min_hold = 20 (the worst point in the hold sweep; ~22% CAGR vs
33–36% at min_hold = 10). Each was measured and has a root-cause readout. The discipline is:
a reversed result is a finding that constrains the next setup, not an invitation to try harder
versions of the same idea.

---

## 3. The research surface — what sits above the locked base

The Titman base is the floor. Everything above it is **the research surface**: overlays,
data improvements, and extensions that may or may not clear the strict promotion bar. The
research surface is the only thing that changes; the base never does.

### 3.1 What currently sits on the research surface

**Vol-target overlay (pre-reg 0068 — SHIPPED to paper 2026-06-26):**
De-grosses book sizing equity by `max(0.40, min(1.0, 0.15 / realized_42d_book_vol))`. Best-Calmar
arm (V2: vol_target_annual = 0.15, vol_window = 42, vol_floor = 0.40). In-backtest effect:
CAGR neutral, max drawdown improved approximately −45% → −39%. Configured in
`models/long_horizon/config.json → live_overlays` (outside the frozen `cfg` block, so the
research baselines and golden master are unaffected). Correctly quarantined: live uses a
shared `portfolio.vol_target_scalar` function; the backtest loads the same function; the
research backtest is untouched because `load_frozen_cfg()` drops `live_overlays`. This
overlay clears the CAGR-neutral bar but has not yet accrued 30 paper trades — it is
paper-validated, not live-validated.

**AI sector-regime analyst (shadow only):**
Runs weekly, writes a forward scorecard, touches no trade. The price-based sector overlay
family was killed (`STRATEGY_FULL.md §11`). The AI narrative overlay is orthogonal —
forward-only, not backtestable — and is correctly kept in shadow. It can become a conviction
modulator *only if* its forward scorecard proves skill over a meaningful sample, against
skeptical priors.

**Drawdown tail hedge (deferred):**
Pre-regs 0069 and 0070 showed that sizing / market-state overlays plateau at approximately
−38% overall drawdown — a specific crash like COVID can be cut to −31% with a bespoke
signal, but no single signal generalises across crash types. A dependable −30% floor needs a
structurally-orthogonal instrument: defined-risk options tail-hedging (the deferred
vol-carry / options-backtester program). Not on the current research surface.

**Data improvements (Task-8, cloud-gated):**
The 48 current index members invisible to the live scan (AUD-007; confirmed 48 by Phase-1
audit) cannot be added until they have PIT fundamentals coverage in
`data/fundamentals_pit_screener.pkl`. The CA-type-aware OHLCV cleaner (W-01 root fix,
replacing the heuristic that mis-classified VEDL's demerger as a split) requires a golden
master regeneration and a cloud re-derivation. Both are sequenced to the cloud backtest gate.

### 3.2 What the research surface is NOT for

It is not for re-litigating the base signal, the universe definition, or the solvency
filter. Those are locked by the data and by the kill history. It is not for adding
uninspectable complexity — every overlay must be explainable in one sentence and must expose
its mechanism to forward validation (§3.3). It is not for chasing CAGR — the promotion bar
is risk-adjusted return improvement, not raw return.

### 3.3 The promotion bar (non-negotiable)

An overlay promotes from shadow to live paper **only if ALL of the following hold**
(from `skills/sell-replace-logic/SKILL.md`, the pre-committed bar):

| Gate | Threshold |
|---|---|
| Post-tax post-cost ΔSharpe | ≥ +0.10 |
| ΔCalmar | ≥ +0.05 |
| 2022–2026 sub-period ΔCAGR | positive |
| Walk-forward fold-pass rate | ≥ 60% |
| Bootstrap 95% CI on ΔSharpe | excludes 0 |
| Turnover increase | ≤ 30% |
| Mechanism | explainable in one sentence |

Shadow (not promote, not kill) if 4–5 gates hold. Kill otherwise, with a root-cause readout.

A PROMOTE is never a live change. It authorises a flag-gated shadow run and forward-wall
accrual. The live book changes only after paper evidence accumulates.

---

## 4. Non-negotiable constraints

These are the properties that must hold in every state of the system — in paper, in live,
in every research run, and in every overlay that is ever added.

**Rules-based clarity preserved.** The selection signal, entry, exit, and sizing are fully
inspectable rules derivable from the frozen config. If an overlay cannot be explained in one
sentence and cannot be reproduced by a third party from the config and the OHLCV data, it
does not ship. ML components are permitted only above the rule layer and only if they
demonstrably improve the transparent rule baseline — and they must be separately pre-registered
and gated.

**Correctness > reproducibility > maintainability.** In that order. A backtest number that
cannot be reproduced from a clean clone is not a number (W-07 in the audit ledger, the
reason `equity_curve` is now persisted). A live fill that cannot be traced to the exit logic
is not a trade (W-05: gap-down stops now fill at the real open, not optimistically at the
stop). The golden master (`tests/test_long_horizon_golden.py`) is the enforcement mechanism
— any behavior-changing fix must regenerate it.

**Point-in-time discipline throughout.** Features use only data available at the signal date.
PIT membership mask is applied every run. Fundamentals use the ~90-day-lagged Screener store
with a strict `merge_asof(backward, allow_exact_matches=False)`. There is no exception; a
claimed feature that cannot be reconstructed point-in-time is forward-only (documented as
such, excluded from the backtest, and validated only on the forward wall).

**Forward-only for what cannot be reconstructed PIT.** The AI sector analyst, any news
sentiment score, and any real-time alternative data source fall here. They may inform live
overlays with explicit forward-skill gates; they never enter the backtest. Conflating a
PIT-backtestable feature with a forward-only feature is the single most reliable way to
fabricate an edge.

**The paper gate before real capital.** At minimum 30 closed paper trades and approximately
2 months of live operation must be reviewed — fill realism, hit rates relative to backtest
expectations, drawdown path — before any real rupee enters the book. This is pre-committed
and cannot be shortened by a good run. The paper broker (₹10L clean slate from 2026-06-25)
is the gate mechanism. The strategy is paper-ready; it is not real-capital-ready.

**No re-entry on the same day as an exit.** Enforced by the backtest and the live tracker:
exit on day *t*, earliest re-entry at *t+1* open. This is not an optional behavioural
preference; it is part of the strategy contract.

**Kill verdicts are permanent without new evidence.** A tested-and-killed overlay (see §2
and `STRATEGY_FULL.md §11`) does not get re-tested because someone thought of a slightly
different version. It gets re-registered under a new pre-registration with genuinely new
data, a new hypothesis, or a structural reason why the prior kill does not apply.

---

## 5. The path from here to real capital

The current state (as of 2026-06-27, post Phase-1 hardening):

- Live scanner running: GitHub Actions `cron-scanner.yml`, weekdays 4:15 PM IST.
- Paper broker accruing: clean ₹10L book, signals published to `results/signals_today.json`.
- Phase-1 wiring fixes shipped (commits `ab585c3`, `b653f52`): 1814 tests pass, golden master
  byte-identical, demerger quarantine live (VEDL blocked), gap-down stop fills corrected,
  alert webhook wired (pending owner secret configuration), aging parity fixed.
- Open (data-gated, not behavior-altering): W-02 universe union (48 invisible current members;
  deferred to Task-8 PIT fundamentals expansion), W-01 root CA-type fix (deferred to cloud
  re-derivation + golden master regeneration), W-04 financials D/E policy decision (62 banks
  + NBFCs silently excluded; needs an explicit owner policy decision, not code).

**What must happen before real capital:**

1. **Accrue ≥ 30 paper trades** (~2 months at current pace). Review: fill rates vs indicative
   entries, win rate vs expected 63%, drawdown path vs −40% budget, any sector / single-name
   concentration flags.
2. **Cloud re-derivation** (`cpcv-research.yml` on the expanded universe) must re-confirm the
   `baseline_v0` anchor (26.1% gross / 1.02 Sharpe) on the current, W-01-and-W-02-corrected
   data; the corrected result becomes `baseline_v1`. The local cache is survivor-only and
   cannot substitute. (The prior 30.3% headline is superseded; do not use it as the
   re-confirmation target.)
3. **Reproducibility artifact** (`diagnostics/run_long_horizon_tradelog.py` with the
   persisted `equity_curve`) must produce a byte-verifiable baseline that any future session
   can reproduce from a clean clone.
4. **AUD-007 observability** is already live (divergence logged in `cron_health` each run);
   the divergence is stable and documented; the universe-union fix ships with Task-8.
5. **Owner decision on financials exclusion** (W-04): explicitly acknowledge that HDFCBANK,
   ICICIBANK, SBIN, and ~60 other deposit-taking banks and NBFCs are excluded by the D/E filter
   (their D/E is NaN in the Screener store), not by leverage concern. This is a data coverage
   gap, not a strategy decision. Decide: special-case the sector, or keep the exclusion and
   document it loudly.

None of these are engineering surprises — they are known, measured, and sequenced. The
strategy's correctness is not in question; the path is about evidence accumulation, not
debugging.

---

## 6. What "done" looks like

Done is NOT a date or a feature list. Done is a state:

**The base never changes.** `models/long_horizon/config.json → cfg` is frozen; no cron
re-derives it; no research branch proposes modifying it without a full re-derivation from
scratch on updated data, a new pre-registration, and a walk-forward gate.

**Every overlay above the base has a clear paper trail.** Pre-registration document,
measured delta, bootstrap CI, mechanism sentence, verdict (PROMOTE / SHADOW / KILL), and
the date it was wired or killed. Nothing on the research surface exists without a
pre-registration.

**The live book has passed the paper gate.** At least 30 closed paper trades reviewed;
fill realism confirmed; drawdown path within the budgeted −40%; no structural parity defect
between the paper ledger and the backtest.

**The reproducibility gate passes.** A clean clone can reproduce the headline within
statistical tolerance from the committed artifacts and the cloud CPCV run. The golden master
is current. The equity curve is a committed artifact, not a derived ephemeral.

**The owner has explicitly accepted the risk profile.** Gross ~26% CAGR / ~−42% drawdown /
after-tax ~23% CAGR / high-variance / regime-dependent. Not as a disclaimer, but as a real
capital decision: "I am willing to watch this book decline 40-plus percent before the up-year
that recovers it." The 2018 fold was −6.6% (mild); but the bootstrap 5th-percentile Sharpe is
0.58, below buy-and-hold. A bad draw is not a bug — it is a known property of the strategy.

**Compliance framing is consistent throughout.** Every published signal carries the framing
from `STRATEGY_FULL.md §15`: *model-generated research signal / decision-support output* — not
advice, not a guarantee.

Done is not the absence of open research questions. There will always be open questions
(Task-8 data, the deferred F&O-only universe, the tail hedge program, the AI analyst forward
wall). Done is the state where every live component has been through the gate, every number is
traceable to a reproducible artifact, and the owner is consciously running real capital against
a strategy they understand, not hoping for the best.

---

## 7. What will make the strategy worse (do not do these things)

- **Add an uninspectable score.** An ML ranker, a news sentiment gate, or any signal that
  cannot be verified from the OHLCV data and the frozen config introduces a surface that can
  over-fit silently and break without warning. The rules-based clarity is load-bearing.

- **Override the paper gate.** Early live trading "while the paper track record accrues" is
  not a shortcut; it is a different experiment with no baseline. The 30-trade gate exists
  because the backtest cannot capture fill realism, partial-fill behaviour, or the emotional
  discipline required to hold a 15-stock book through a −15% paper drawdown.

- **Re-litigate killed experiments.** The dual-momentum regime gate, sector overlays, and
  RSI/MACD signals were killed with measured root-cause readouts. Trying a "slightly different
  version" without new data or a new structural argument is probability-of-false-discovery,
  not discovery.

- **Anchor on the re-derived number.** The 34.67% / 1.248 figure comes from a run that
  re-derives parameters on the full dataset and then measures in-sample. The live strategy's
  honest frozen-cfg anchor is `baseline_v0`: 26.1% gross / 23.1% after-tax / Sharpe 1.02
  (the prior 30.3% / 1.15 was the optimistic-exit figure, superseded 2026-06-27). Any
  comparison that uses 34.67% or the superseded 30.3% as the baseline inflates the apparent
  contribution of an overlay by 4–8pp of CAGR.

- **Treat the paper book as live.** The paper broker books entries at the next open with
  realistic slippage; but it assumes fills, does not model exchange queues, and does not
  account for days when the stock is in a circuit or suspended. Real fills will be worse on
  the tail. The paper track record is a necessary but not sufficient condition for live
  deployment.

- **Add parameters without the promotion bar.** A plausible-sounding overlay that improves
  the in-sample Sharpe by 0.05 is not an improvement; it is a risk of over-fit. Every
  parameter added to the system costs a degree of freedom in future validation. The
  promotion bar (§3.3) is calibrated to reject the over-fit zone.

---

## Owner decisions & path to capital (2026-06-27 reframe)

*This section records three explicit owner decisions made 2026-06-27, the destination-ordered
critical path they imply, and four honest tradeoffs that follow from them. It supersedes the
earlier linear phase-march framing while remaining consistent with the locked base (§2), the
promotion bar (§3.3), the non-negotiable constraints (§4), and the paper gate (§5). See also
`docs/ROADMAP.md` and the ADR log (ADR-0003, ADR-0004).*

---

### Decision 1 — Hold live until the conviction layer is in

Real capital waits on the **full research track** (Stages A–E below). The frozen base
as it stands does NOT go live on its own, even if the paper gate clock has ticked past
30 trades on the current book. The rationale: the base is an honest, reproducible signal,
but the universe is known-correctable (W-01 CA-type fix, W-02 missing 48 members, W-04
financials exclusion) and a conviction layer exists that may materially improve the
risk-adjusted return profile. Deploying real capital against a universe that the team
has already identified as incorrect, then re-deriving mid-live, is operationally worse
than waiting. Quality before speed.

---

### Decision 2 — Model evolution is conviction-within-top-15, nothing more

The only permitted evolution of the strategy before live is **conviction scoring that
modulates sizing, exit aggressiveness, and risk caps within the existing 15-slot top-K
selection** (Stage C/D below). Specifically:

- **Permitted:** z-score blend / logistic / ranked conviction model on PIT-safe features;
  quintile-scaled sizing (mean-preserved, 15% cap still binds at top); quintile-dependent
  exit widths (Q1 tighter, Q5 wider); soft sector / correlation caps informed by conviction.
- **Not permitted (near-term):** replacing the `sma200_slope_63` base signal; adding ML
  ranking that is uninspectable; expanding to a different universe definition beyond the
  W-01/W-02/W-04 corrections.
- **Explicitly deferred (off critical path):** the defined-risk tail hedge program (pre-regs
  0069/0070); the vol-carry / options second stream (the structurally-orthogonal premium
  program). Both remain parked. Revisit only after the conviction-layered strategy has
  accrued real capital history.

The vol-target overlay (pre-reg 0068, already in `live_overlays`) is the sole exception:
it was pre-registered, backtest-validated, and CAGR-neutral — it ships with the paper book
under the existing quarantine structure.

---

### Decision 3 — Fix the universe before live; re-derive; reset the paper clock

The three open universe defects (W-01, W-02, W-04 from the Phase-1 audit) are **prerequisites
for live**, not post-live clean-up items:

- **W-01:** CA-type-aware OHLCV cleaner (demerger vs split — the VEDL lesson); requires
  golden master regeneration and cloud re-derivation.
- **W-02:** Universe union = `current_members ∪ config.NIFTY_500`, covering the 48 current
  index members invisible to the live scan due to missing PIT fundamentals.
- **W-04:** Financials capital-adequacy proxy: include banks / NBFCs via a tier-1-ratio or
  CET1-equivalent filter rather than the D/E filter that silently excludes ~62 deposit-taking
  names (HDFCBANK, ICICIBANK, SBIN, etc.). This is a data-coverage gap, not a deliberate
  strategy decision. Owner has sanctioned an explicit proxy policy.

After all three are addressed, **re-derive the frozen cfg** from scratch on the corrected
universe: new pre-registration → walk-forward → regenerate golden master → commit
`baseline_v1.json` + a new `config.json`. This is the sanctioned heavy-path re-derivation
documented in `docs/LIVE_OVERLAY_PROTOCOL.md` as ADR-0003.

**The paper book clock resets at Stage B.** The current paper book (₹10L, running since
2026-06-25) is on the old base (uncorrected universe). It accumulates useful fill-realism
and behavioral data, but the 30-trade paper gate for Stage E counts only from the new
corrected-universe paper book opened after Stage B ships.

---

### Destination-ordered critical path: Stages A → F

The path is ordered by what must be true before the next stage starts. It is not a time
estimate; it is a dependency chain.

**Stage A — Trustworthy statistical harness**

Build `src/research/` as the shared computation engine for all subsequent research stages.
Reuse existing validated modules: `src/validation/{cpcv, overfitting, bootstrap, power,
factor_metrics, null_test}`, `long_horizon/backtest/portfolio.simulate`, and the pre-reg
framework under `long_horizon/research/preregistry/`.

Gate: the harness reproduces the **26.1% CAGR / 1.02 Sharpe** anchor (from
`baseline_v0.json` — the exit-parity-unified result on the 397-name solvent arm) within ≤ 1pp
via the `cpcv-research.yml` cloud run (the original 30.26% / 1.15 from
`cpcv_long_horizon_final_682.json` was the optimistic-exit figure; `baseline_v0` is the
current honest anchor), AND the harness replicates the §11 KILLs
(at minimum: regime gate, dual-momentum gate, sector overlay — the three largest). A result
that can't reproduce its own documented kills cannot be trusted to gate conviction.

**Stage B — Corrected universe + re-derived base**

Four sub-steps, in order:

- **B1:** Root CA-type-aware OHLCV cleaner (split vs demerger via `yf actions`; fixes the
  VEDL mis-classification that produced a fabricated price series).
- **B2:** Universe union: add the 48 current index members with PIT fundamentals coverage
  from `data/fundamentals_pit_screener.pkl`; pull delisted OHLCV for new entrants where
  available.
- **B3:** Financials capital-adequacy policy: define and implement the D/E-replacement
  proxy; confirm that HDFCBANK, ICICIBANK, SBIN, and peers now enter the eligible universe.
- **B4:** Re-derive frozen cfg on the corrected universe: new pre-registration → cloud
  walk-forward → regenerate golden master → commit `baseline_v1.json` + new `config.json`.
  Open and fund the fresh paper book (₹10L clean start). ADR-0003 gates this.

Gate: corrected-universe walk-forward produces a non-negative Sharpe in every post-2019
fold; the golden master passes byte-identically on the new config; the new baseline is
committed and its headline (whatever number comes out of the corrected universe — it will
very likely differ from both the superseded 30.3% and the current 26.1%) is locked as the
new anchor. Do not anchor to 30.3% or 26.1% after B4; anchor to the honest new
`baseline_v1` number.

**Stage C — Conviction model (within top-15)**

Design and validate a conviction score that says "among the 15 names already selected by
rank, which are higher- vs lower-quality entries right now?" The model form must be
inspectable: z-score blend of PIT-safe features, logistic regression, or quantile ranking.
No uninspectable ML. Validate via the Stage A harness: conviction-stratified top-15 vs
rank-only baseline on the corrected-universe walk-forward.

Output: `conviction_score` and `conviction_quintile` in `signals_today.json`, computed at
scan time. Gate: the conviction model earns pre-registration and must clear the promotion
bar (§3.3) before Stage D begins. If conviction cannot clear the bar after a pre-specified
number of attempts, the corrected frozen base (Stage B output) is shippable on its own —
then revisit Decision 1 (the hold-live condition).

**Stage D — Conviction-driven hybrid layers (separately gated)**

Each layer is promoted or killed independently against the §3.3 bar:

- **D1 — Sizing:** quintile-scaled position weight (mean-preserved so aggregate exposure
  is unchanged; 15% cap still binds at the top). Q1 receives a smaller initial allocation;
  Q5 receives a larger one.
- **D2 — Exit:** conviction-aware stop/target width. Q1 (lowest conviction): tighter stop,
  earlier exit. Q5 (highest conviction): wider target, more room to run.
- **D3 — Risk caps:** soft sector concentration and pairwise-correlation caps informed by
  the conviction quintile distribution. No hard exclusions — soft de-grossing only.
- **D4 — Sell-and-replace logic (S1–S7 / R1–R4):** conviction-driven re-evaluation at
  rebalance events. Whether a slot is freed for a higher-conviction entrant, or held for
  the existing name, is governed by the pre-registered S/R rules from
  `skills/sell-replace-logic/SKILL.md`.

Each D sub-layer is pre-registered, measured, and gated before wiring to the paper book.
None of D1–D4 goes to paper until Stage C produces a passing conviction score.

**Stage E — Paper-revalidate the full conviction-layered system**

Run the complete conviction-layered strategy (corrected universe + re-derived base +
passing conviction model + whichever D layers cleared the bar) on the fresh paper book
opened at Stage B. The gate: ≥ 30 closed paper trades, approximately 2 months of operation,
reviewed for fill realism, hit rate vs backtest expectation, drawdown path vs the
corrected-universe budget (which may differ from −40%), no structural parity defect.

Flip kill-criteria from `observe` → `enforce`. This is the pre-committed real-capital gate:
it cannot be shortened by a good run, and it cannot be bypassed because the backtest looked
clean.

**Stage F — Live capital**

Real rupees enter only after Stage E passes. Activation requires:

- Kill switch armed: WR < 45% / 20 live trades → halt; 30-day realized Sharpe < 0 →
  halt; 5 consecutive zero-signal days → halt.
- Decay monitor live: 90-day rolling signal IC < 0.02 → review (not auto-halt, but a
  mandatory pre-registered review decision).
- Compliance framing consistent throughout: every published signal carries the
  `STRATEGY_FULL.md §15` framing (*model-generated research signal / decision-support
  output* — not advice, not a guarantee).

**Continuous (all stages)**

- **Governance:** every research step follows the `LIVE_OVERLAY_PROTOCOL.md` loop:
  pre-registration → harness validation → result registry → ADR entry → ship or kill.
  Nothing wires to the live path without a pre-registration. See ADR-0003 (universe
  re-derivation) and ADR-0004 (conviction layer) for the two primary active decisions.
- **Data quality:** the OHLCV cleaner, PIT fundamentals, and the AUD-007 divergence log
  must be reviewed on every data change before a research result is trusted.
- **Backtest rigor:** no number is trusted until it can be reproduced from a clean clone.
  The `equity_curve` persistence, the golden master, and the Stage A harness exist
  specifically to enforce this.
- **Monitoring:** the kill-criteria system (WR, Sharpe, signal volume) runs in `observe`
  mode through Stage E; the nightly cron health report covers scanner parity and data
  freshness.

---

### Four honest tradeoffs

These are known costs of the Decision 1–3 choices. They are not surprises; they are the
price of the quality-before-speed stance.

**Tradeoff 1 — The path to first real rupee is materially longer.**

The previous framing implied live capital could follow a ~2-month paper window. The
corrected path requires: Stage B foundation re-derivation (W-01/W-02/W-04 all three) +
Stage C conviction pre-registration and validation + Stage D layer gating + Stage E fresh
paper window (≥ 30 trades, ~2 months minimum) — ALL before Stage F. The total additional
elapsed time is meaningful. The ~10 paying users are aware that the strategy has never
traded a live rupee; they have paper track record, not live. The delay is real and should
be communicated explicitly.

**Tradeoff 2 — The headline may move, possibly down.**

After Stage B corrects the universe (W-01 demerger fix, W-02 48 new entrants, W-03/W-04
financials inclusion), the re-derived frozen cfg will produce a different backtest headline.
The current anchor is already the honest baseline_v0 (26.1% gross / 23.1% after-tax), which
is lower than the previously-reported 30.3% (optimistic-exit, superseded 2026-06-27). Stage B
survivorship corrections and new entrants have historically compressed research backtests
further — the Stage B number (`baseline_v1`) may well be lower still. We do not pre-anchor to
any specific figure surviving Stage B. Whatever number comes out of Stage B is the new honest
baseline; it is locked and never re-litigated upward.

**Tradeoff 3 — The paper-gate clock resets at Stage B.**

The current paper book (running since 2026-06-25) accumulates useful behavioral data —
fill realism, indicative hit rates, drawdown path — but its 30-trade count does NOT
count toward the Stage E gate. Stage E requires ≥ 30 trades on the corrected-universe,
conviction-layered book opened after Stage B ships. The current book is not wasted; it
is an input to fill-realism calibration and an early behavioral check. But it is not the
gate-counting book.

**Tradeoff 4 — Stages C/D may mostly kill; the corrected base is the fallback.**

The §11 kill history demonstrates that well-motivated overlays frequently fail the
promotion bar. Conviction may be no different: if Stage C cannot produce a pre-registered
conviction score that clears the §3.3 bar after a pre-specified attempt budget, the
corrected frozen base (Stage B output) is shippable on its own — it is a valid,
documented, rules-based strategy. In that case Decision 1 (hold-live-until-conviction)
is revisited: the owner decides whether to live-launch the base alone and layer conviction
post-live, or to continue paper until conviction clears. This decision point is not a
failure of the program — it is the program working as designed.
