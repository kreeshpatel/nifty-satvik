# LIVE OVERLAY & FROZEN-PARAM CHANGE PROTOCOL

**Status:** ENFORCEABLE. This is the governance contract for any change to (a) a
**frozen strategy parameter** in `models/long_horizon/config.json -> cfg`, or (b) a
**live overlay** in `models/long_horizon/config.json -> live_overlays`. No frozen
param or overlay changes outside this protocol. If a PR touches either block and does
not satisfy the steps below, the reviewer (the owner) rejects it on sight.

> Compliance framing: every artifact this protocol produces describes a
> **model-generated research signal / decision-support output**. Nothing here is
> investment advice or a performance guarantee. The headline numbers below are a
> **research backtest that has never traded a live rupee.**

---

## 0. The two kinds of change (read this first — the whole protocol hinges on it)

`models/long_horizon/config.json` has two blocks that look similar and are governed
**very differently**:

| | `cfg` (FROZEN) | `live_overlays` (LIVE OVERLAY) |
|---|---|---|
| What it is | The strategy the backtest measures and the cron trades | A paper-book-only de-grossing/risk modifier applied on top |
| Read by | `long_horizon.config.load_frozen_cfg()` — returns `.get("cfg", {})` **only** | `long_horizon_cron._live_vol_target()` — reads `.get("live_overlays", {})` |
| Touches the research backtest? | **YES** — it IS the backtest | **NO** — `load_frozen_cfg` never returns this block |
| Touches the golden master? | **YES** — `tests/test_long_horizon_golden.py` byte-compares the frozen-cfg harness | **NO** — overlay is invisible to the harness |
| Applied where, live | Entry/stop/target/sizing/exit math in `long_horizon_cron` + `signal_tracker` | Multiplies paper-portfolio sizing equity (`results/portfolio_history.csv`) via the shared `portfolio.vol_target_scalar` |
| Reversibility | Hard — re-derive offline, regenerate golden fixture | Soft — set `vol_target_annual=0` (or delete the block); next 4:15 PM IST scan is a no-op overlay |

**The load boundary is the safety mechanism.** `load_frozen_cfg()` (long_horizon/config.py
L155–189) does `json.loads(...).get("cfg", {})` — it structurally cannot see
`live_overlays`. That is why an overlay can ship to the live paper book **without
regenerating the golden master or moving any backtest baseline.** Do not break this
boundary. An overlay that needs to change `cfg` is not an overlay — it is a frozen-param
change and takes the heavier path in §6.

**Principle — the frozen cfg is NEVER hand-edited on the live path.** Frozen params are
derived once, offline, on the pre-2017 train slice and confirmed by the walk-forward
(`params_derived_through: 2017-01-01`,
provenance `long_horizon/results/cpcv_long_horizon_final_682.json`). They are not nudged
in production to chase live noise. Editing `cfg` by hand to "fix" a live result is the
single most dangerous thing anyone can do to this system; it silently desyncs the live
strategy from every backtest number we have ever quoted.

---

## 1. WHO may propose and approve

- **Propose:** anyone (the owner, or a research session of this agent). A proposal is a
  pre-registration (§2), not a code change.
- **Approve:** **the owner only.** No agent, cron, or automated job may promote a frozen-cfg
  change or a live overlay. The quarterly param-revalidation cron was **removed with v1
  (2026-06-25)** — there is deliberately no automated path that rewrites these params.
- **Implement (after owner approval):** the change is made by a normal PR that carries all
  the evidence and logging artifacts in §3. CI (golden master + 1814-test suite) must be
  green.

There is no emergency override that skips owner approval. The only thing anyone may do
without approval is **disable** a failing overlay (§4) — disabling is always allowed,
enabling never is.

---

## 2. Pre-registration (required before any test is run)

Hypothesis-first, results-second. Before touching the harness:

1. Write a pre-registration file under `research/preregistry/` (e.g.
   `00NN-<short-name>.md`) stating:
   - The exact param/overlay and its proposed value(s).
   - A one-sentence **mechanism** — why this should be edge, in plain English the operator
     can repeat. If you cannot, stop.
   - The success metric and the decision rule (the promotion bar, §5) **before** seeing the
     number.
   - The sub-periods and stress arms that will be run (§5).
2. Register it. A test run that was not pre-registered is hypothesis generation, not
   evidence, and cannot promote anything.

This mirrors the existing research discipline (`skills/sell-replace-logic/SKILL.md` §1,
and the v1-era holdout/pre-registry program) — it is not new ceremony, it is the house
rule applied to config changes.

---

## 3. Evidence required before approval

A frozen-cfg change OR a live overlay must carry **all** of the following in the PR before
the owner will look at it:

1. **Pre-registration** (§2) committed before the results.
2. **Walk-forward, re-derive per fold.** Not a single in-sample fit. Params/overlay are
   re-derived inside each fold so the reported number is out-of-sample. This is the same
   walk-forward that produced the ≥2019 ~32% CAGR / 1.31 Sharpe / 0-negative-year figure;
   any change is judged against that machinery, not a single-window backtest.
3. **The full promotion bar (§5), all seven gates, computed post-tax + post-cost.**
4. **Cost stress at 2× and 3× transaction cost.** The edge must survive realistic and
   pessimistic frictions; an effect that only exists at idealized cost is rejected.
5. **The 2022–2026 sub-period reported separately.** A change that helps 2017–2021 but
   hurts 2022–2026 is **REJECTED, not promoted** — the recent regime is the one we are
   about to trade.
6. **Block-bootstrap 95% CI on ΔSharpe** — must exclude zero.
7. **Turnover delta** — the increase must be ≤ 30%.
8. **For a FROZEN-cfg change only:** the regenerated golden fixture in the *same PR*
   (§6), with the diff explained.

If any artifact is missing the change is not eligible for approval. "It looked better in a
quick run" is not evidence on this codebase.

---

## 4. The promotion bar (quote-exact — do not paraphrase)

This is the canonical bar from `skills/sell-replace-logic/SKILL.md` and applies verbatim
to overlays and frozen-param changes:

**PROMOTE only if ALL of:**
- Post-tax post-cost **ΔSharpe ≥ +0.10**
- Post-tax post-cost **ΔCalmar ≥ +0.05**
- **2022–2026 sub-period shows positive ΔCAGR**
- **Walk-forward fold-pass rate ≥ 60%**
- **Bootstrap 95% CI on ΔSharpe excludes zero**
- **Turnover increase ≤ 30%**
- **Mechanism is explainable in one sentence to the operator**

**SHADOW** (log the signal / apply nothing) if **4–5** of the above hold.
**REJECT** otherwise, and log the reason in `research/overlay_registry.md`.

A "SHADOW" verdict means the overlay is computed and written to the analytics output for
the forward-wall record but **does not modify any live sizing**. Promotion to acting
status requires a fresh PR clearing all seven gates.

> Anchor metrics for every Δ: **baseline_v0** = gross CAGR 26.1% / Sharpe 1.02 / maxDD −41.9% /
> Calmar 0.62; after-tax (STCG 20%) CAGR 23.1% / Sharpe 0.83. Source: `research/baseline_v0.json`
> (supersedes the optimistic-exit 30.26%/1.15 from `cpcv_long_horizon_final_682.json`, 2026-06-27).
> **Do not anchor on the 34.67% / 1.248 re-derived variant** — it is not the live arm.

---

## 5. How a change is LOGGED

Three artifacts, every time, in the promoting PR. A change that is not logged in all three
is treated as un-reviewed and reverted:

1. **`research/config_CHANGELOG.md`** — append-only. One row per change:
   `date | block (cfg / live_overlays) | key | old → new | pre-reg id | PR | verdict`.
   This is the audit trail an owner (or a future session) reads to answer "why is this
   number what it is?"
2. **`research/overlay_registry.md`** — the verdict record with full reasoning: the
   hypothesis, the seven-gate scorecard, the sub-period split, the bootstrap CI, the
   failure modes considered, and the PROMOTE / SHADOW / REJECT call. REJECTED changes stay
   here forever so they are not relitigated (see §7).
3. **An ADR under `docs/decisions/`** (e.g. `docs/decisions/00NN-<name>.md`) — the durable
   decision record: context, the decision, the alternatives weighed, and the consequences
   (including what would make us reverse it). One ADR per promoted change.

> Note: `research/` and `docs/decisions/` are the canonical homes for these. If they do
> not yet exist in the checkout, the promoting PR creates them — do not scatter the
> artifacts elsewhere.

`models/long_horizon/config.json` is itself the live source of truth, but the JSON is the
*state*, not the *justification*. The justification lives in the three artifacts above.
The `provenance` / `_note` fields inside the JSON must be updated in the same PR to point
at the pre-reg id (the existing `live_overlays._note` and `provenance` fields already do
this for 0068 — keep them current).

---

## 6. FROZEN-cfg change vs LIVE-OVERLAY change — the mechanical difference

### 6a. A FROZEN-cfg change (heavy path)
Changing anything in the `cfg` block changes the strategy the backtest measures **and** the
golden master.

- It must be **re-derived offline** on the train slice / walk-forward — never hand-typed to
  a value that "looks better" live.
- The **golden master fixture must be regenerated in the same PR** (the harness that
  `tests/test_long_horizon_golden.py` byte-compares is driven by `load_frozen_cfg()`; a new
  `cfg` makes the test go red until the fixture is intentionally rebuilt). Regenerate via
  the documented build command for the long-horizon golden fixture, commit the new
  baseline + the config change together, and explain the diff in the PR.
- `expected_portfolio_metrics` in config.json is updated to the new arm's numbers in the
  same PR.
- The full §3 evidence + §4 bar apply.

A red golden master on an *unrelated* PR means someone changed `cfg` (or gating/sizing/exit
math) without going through this path — that is the test doing its job. Do not "fix" it by
regenerating the fixture; find the unintended change.

### 6b. A LIVE-OVERLAY change (light path)
Changing `live_overlays` (e.g. the vol-target value, window, or floor) is **paper-book
only**:

- `load_frozen_cfg()` does not return this block, so the **research backtest baselines and
  the golden master are untouched** — no fixture regeneration.
- The §3 evidence + §4 bar **still apply** (an overlay must be validated on the backtest via
  its own pre-reg arm, e.g. 0068), but the validation runs as an explicit harness arm that
  *opts in* to the overlay, not as the default frozen path.
- The overlay is applied live by `long_horizon_cron._live_vol_target()` to the trailing
  paper-portfolio equity in `results/portfolio_history.csv` using the **shared**
  `portfolio.vol_target_scalar` — live and backtest use the identical formula and cannot
  drift. A malformed `live_overlays` block must never crash the scan (the loader degrades to
  scalar 1.0 — a no-op).

---

## 7. How an overlay is REMOVED if it fails forward

Overlays are paper-book-only and **soft-reversible** — that is their whole point. An overlay
is on probation on the forward wall from the day it ships.

### 7a. Kill switch (always allowed, no approval needed)
Set `vol_target_annual` (or the relevant overlay's enabling key) to `0` in
`models/long_horizon/config.json`, or delete the `live_overlays` block entirely. The loader
returns scalar `1.0` and the next **4:15 PM IST weekday scan** (GitHub Actions
`.github/workflows/cron-scanner.yml`, from `main` only) sizes with no overlay. No code
change, no PR ceremony, no fixture regeneration. **Disabling a failing overlay is always
permitted** — the asymmetry is deliberate: enabling needs the full bar, disabling is free.

### 7b. Forward-wall decay monitor (when to pull the switch)
An overlay that PROMOTED on backtest evidence is **rejected forward** and disabled if, over
the accumulating live paper record, any of these fire:
- The overlay's realized contribution turns the wrong sign vs its pre-registered thesis
  (e.g. a vol-target sold to *reduce* drawdown that instead degrades realized Calmar over a
  meaningful window).
- It materially raises realized turnover beyond its pre-registered ≤30% budget.
- It interacts badly with the frozen exits in a way the backtest did not show.

When the monitor fires: disable via 7a immediately, then log the forward verdict in
`research/overlay_registry.md` and append the reversal to `research/config_CHANGELOG.md`.
A re-enable later requires a fresh pre-reg + a full §3/§4 pass — a once-killed overlay is
not silently turned back on.

### 7c. Relationship to real capital
Overlays live on the **paper book only** until the pre-committed paper-trading gate is met
(≥ 30 paper trades / ~2 months reviewed before any real rupee). An overlay being "live"
means live on the paper path, not on real capital. The strategy is paper-ready, **not
real-capital-ready.**

---

## 8. BACKFILL — the one existing overlay (0068 portfolio vol-target)

The protocol above is applied retroactively to the only overlay currently shipped, so the
record is complete from day one.

**Overlay:** portfolio-level volatility target (de-grossing scalar on paper-book sizing equity).

| Field | Value | Source |
|---|---|---|
| `vol_target_annual` | `0.15` | `models/long_horizon/config.json -> live_overlays` |
| `vol_window` | `42` | same |
| `vol_floor` | `0.40` | same |
| Pre-registration | **0068, arm V2** (best-Calmar arm) | `live_overlays.provenance` |
| Shipped to paper | **2026-06-26** | `live_overlays._note` |
| Lives in | `models/long_horizon/config.json -> live_overlays` (NOT `cfg`) | config.json L25–31 |
| Applied by | `long_horizon_cron._live_vol_target()` → `portfolio.vol_target_scalar` on `results/portfolio_history.csv` | long_horizon_cron.py L187–216, L549–553 |
| Backtest / golden master impact | **NONE** — `load_frozen_cfg()` returns `cfg` only | long_horizon/config.py L155–189 |

**Evidence on file (0068):** arm V2 was selected as the best-Calmar arm of a pre-registered
sweep over `(target_vol, floor)`. In-backtest it is a **CAGR-neutral drawdown reduction**
(≈ −45% → −39% DD; the CAGR is preserved because the scalar de-grosses symmetrically rather
than timing the market — validated on the old optimistic-exit base 30.26%, since superseded by
baseline_v0 26.1% gross / 23.1% after-tax, 2026-06-27; re-confirmation on baseline_v0 pending). Follow-up **0070** confirmed that
sizing/market-state overlays plateau around −38% DD — a dependable −30% DD would require the
**deferred tail hedge**, not a richer vol-target. That plateau finding is itself the reason
no further overlay was stacked on top.

**Why it qualified as an overlay, not a frozen-cfg change:** it does not alter the
signal, the universe, the entry/stop/target math, or any `cfg` value — it only scales the
paper-book position sizing by a factor derived from the portfolio's own past equity (so it
is lookahead-clean, same convention as the backtest). It therefore correctly lives in
`live_overlays` and leaves the research backtest + golden master untouched.

**How to DISABLE it (no approval needed):** set `vol_target_annual` to `0` (or remove the
`live_overlays` block) in `models/long_horizon/config.json`. `_live_vol_target()` returns
scalar `1.0` and the next 4:15 PM IST scan sizes with no overlay. Log the reversal in
`research/config_CHANGELOG.md` + `research/overlay_registry.md`.

**Backfilled logging action (do once):** if not already present, add the 0068 promotion row
to `research/config_CHANGELOG.md`, ensure its verdict sits in `research/overlay_registry.md`,
and write the ADR `docs/decisions/0068-portfolio-vol-target.md`. The config.json
`provenance`/`_note` fields already carry the pre-reg pointer — keep them in sync on any
future edit.

---

## 9. Quick checklist (pin this)

Before merging ANY change to `cfg` or `live_overlays`:

- [ ] Owner approved (the only approver).
- [ ] Pre-registration committed *before* the results (`research/preregistry/`).
- [ ] Walk-forward, re-derive per fold (not single-window).
- [ ] All seven promotion-bar gates pass, post-tax + post-cost (§4).
- [ ] 2× and 3× cost stress survived.
- [ ] 2022–2026 sub-period reported separately and ΔCAGR ≥ 0 there.
- [ ] Bootstrap 95% CI on ΔSharpe excludes zero; turnover Δ ≤ 30%.
- [ ] Logged in `research/config_CHANGELOG.md` + `research/overlay_registry.md` + an ADR in `docs/decisions/`.
- [ ] `provenance`/`_note` in config.json updated to point at the pre-reg id.
- [ ] **If `cfg`:** golden fixture regenerated in the same PR; `expected_portfolio_metrics` updated; CI green.
- [ ] **If `live_overlays`:** confirmed `load_frozen_cfg()` is untouched and the golden master did NOT change.
