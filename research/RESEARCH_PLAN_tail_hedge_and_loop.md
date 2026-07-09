# Research Plan — Tail-Hedge Overlay + Research-Loop Engineering

*Drafted 2026-07-09. Status: **PLAN** (not a pre-registration, not a finding — no trial is
incremented by this document). Owner sign-off required before any run.*

This plan answers a specific ask: start a research phase using the newly-added **vibe-trading**
skill and "loop engineering," and target it at the current strategy. It is written to the house
discipline — **registry-first, adversarial, forward-wall-certified** — not as a green-field
idea list. Every direction below was cross-checked against `research/overlay_registry.md`,
`research/findings/`, `diagnostics/research/n_trials.json`, and `forward/prereg.md`.

---

## 0. The hard constraint (why most "research" here is not allowed)

- **The in-sample momentum program is CLOSED.** 112 cumulative arm-level trials
  (`n_trials.json`); the Deflated-Sharpe bar deflates with every new trial. Running trial #113
  on the single momentum sleeve **without a genuinely new lever is forbidden** — it cannot
  clear DSR and it taxes every other result.
- **The only certifier is the forward wall** (`forward/prereg.md`). No in-sample number promotes
  anything to live capital.
- **Already killed — do not re-propose:** the whole technical/chart zoo at 63d (RSI/MACD/Stoch/
  Williams/CCI/Bollinger/MFI/OBV — 0079/O-015, IC≈0), USD/macro rank tilt (0082/O-019),
  residual-momentum swap/blend (0077/0078), conviction sizing (0073/0020), regime entry gate
  (O-001), single-beta residual (O-002), sector selection (O-004), signal-level low-vol/quality
  blend (O-006/O-007), alt lookbacks (O-010/11/12), meta-labeling (0025). RSI-oversold is
  triple-killed (0020/0022/0024).

So a plan that respects the board has a **small** set of legal moves. This one picks the single
biggest legal move and builds the machinery to run it well.

---

## 1. Adversarial assessment of the vibe-trading skill

The skill is a broad finance toolkit (7 backtest engines, the 452-alpha **Alpha Zoo**, options
pricing, 29 swarm teams, the Shadow-Account loop, 18 data sources). Held to our bar:

| Capability | Verdict here | Why |
|---|---|---|
| Backtest engines (ChinaA / GlobalEquity / Crypto / Futures / Forex) | **NOT the backtest of record** | Data sources are HK/US/A-share/crypto (yfinance / stooq / akshare / OKX). **No PIT-clean NSE** with index-membership-as-of-date or our delisted backfill. Using it to *certify* would re-inject the survivorship bias finding 0025 measured. Our own pinned-dataset harness stays canonical. |
| **Alpha Zoo** (alpha101 / gtja191 / qlib158) | **Screen only, low priority, guarded** | These are largely the chart-indicator zoo we KILLED at 63d (0079/O-015). IC ≠ portfolio Sharpe (0079, O-019). At most a cheap external "have we missed a *non-technical* factor family" IC scan — never a ranker swap. |
| **Options pricing** (`analyze_options`: Black-Scholes + Greeks) + options skill | **ADOPT as tooling** | Directly serves the one legal new lever below (§2). Pricing a protective put / collar, its premium drag, and Greeks is exactly this module's job. Tooling, not a certifier. |
| Shadow-Account loop (journal → rules → backtest) | **Marginal** | Our strategy is systematic, not discretionary. One honest use: profile the owner's *executed* Kite fills vs the paper book (execution-quality / slippage diagnostic), not rule discovery. |
| Swarm teams / `start_research_goal` auditable goals | **Reference** | Parallels our pre-registration discipline; we already have that. Don't duplicate the ledger. |
| Market/fundamental data tools (US/HK/crypto) | **Out of scope** | Wrong market. Our data is NSE via the pinned cache + Kite owner app. |

**Bottom line:** vibe-trading enters this program as **options math + an external cross-check
oracle**, never as the engine that decides PROMOTE/KILL. A number it produces that *disagrees*
with our harness is a flag to investigate, not evidence.

**Installation is a gated step.** The tools are a pip package (`vibe-trading-ai`) + MCP server,
not yet wired into this repo. Installing + wiring `vibe-trading-mcp` is an external-network action
requiring owner go-ahead (§5). Nothing below blocks on it except the options-pricing convenience,
which we can also compute in-repo if preferred.

---

## 2. The research questions (registry-cross-checked)

### RQ1 — Defined-risk tail-hedge overlay *(PRIMARY, genuinely new, registry-sanctioned)*

**Hypothesis.** A portfolio-level, defined-risk hedge (index protective put or put-spread /
collar on NIFTY, sized to a small annual premium budget) converts the strategy's fat left tail
into a bounded one — targeting a **dependable ≈ −30% max drawdown** without surrendering the
trend CAGR — where every *signal-side* lever has failed to.

**Why this is legal and new.** The registry explicitly reserves an `O-###` row for "the deferred
defined-risk tail hedge (vol-carry / options-backtester program) … the lever O-001/O-009/0069/0070
all point to as the only path to a dependable −30% DD" (`overlay_registry.md` §"future overlays").
No options/hedge backtester exists in the repo today — this is un-built, not relitigated. It is a
**portfolio overlay**, distinct from the §9 multi-sleeve fork (which needs a *base-Green* review
trigger and a second *certified sleeve*).

**Design space (fixed before running, per prereg discipline):**
- Instrument: NIFTY protective put vs put-spread vs zero-cost-ish collar (cap upside to fund the put).
- Moneyness: e.g. 5% / 10% / 15% OTM.
- Tenor + roll: monthly vs quarterly; roll at fixed calendar vs delta trigger.
- Budget: annual premium as % of NAV (e.g. 0.5% / 1.0% / 2.0%), OR event-triggered (only when
  drawdown / vol-target de-gross O-009 is already active).
- Trigger: always-on vs regime/vol-conditioned (note: an *always-on* put is a known CAGR drag; the
  research question is whether the DD relief is worth the drag **on our pinned return series**).

**How it is measured (canonical = our harness, NOT vibe-trading):**
- cfg-gated overlay so the golden master (`tests/test_stage2_golden.py`) stays **byte-identical
  when off** — the engine invariant.
- Backtest on the **pinned OHLCV** (`dataset-pin-20260701`) + a committed NIFTY options-premium
  series (data task — see risks). Report post-tax, post-cost ΔCAGR / ΔSharpe / ΔSortino / **ΔMaxDD**
  / ΔCalmar.
- **Continuous-slice** sub-period gate (never fresh-capital re-runs — the phantom-0.762 lesson),
  via `nq.runner.research.evaluate_overlay`.
- DSR-accounted at the correct cumulative trial count (increment `n_trials.json` **before** the run).
- vibe-trading `analyze_options` used to sanity-check premium/Greeks and as an **independent
  cross-check** of the drag estimate.

**Verdict rule (pre-committed, not retunable):** PROMOTE to a forward-wall shadow only if it
clears the DD-relief target **and** the CAGR give-up is inside the pre-registered tolerance under
the continuous-slice gate. **UNDERPOWERED / KILL is a first-class outcome** — if the honest read
is "DD helped but the drag eats it" or "cannot certify on this sample," that is recorded, not
retuned toward a pass.

**Chief risk = data.** A credible hedge backtest needs a PIT NIFTY options-premium history (or a
defensible BS-modelled premium with realistic IV). If we cannot source/model it honestly, the
result is a *modelled* estimate flagged as such — never presented as certified. This data task is
the real gate on RQ1 and is the first milestone.

### RQ2 — Earnings-event de-risking *(OPEN, data-gated, secondary)*

`overlay_registry.md` S5 is OPEN: exit low-conviction names with earnings inside the next 5 days,
re-enter after. It's registered but **unmeasured — it needs a PIT earnings calendar we don't have.**
Lower priority than RQ1; listed so the loop can pick it up **if** the calendar data lands.

### Explicitly OUT of scope (guardrail)
No momentum trial #113 without a new lever; no Alpha-Zoo chart-zoo ranker; no macro/USD tilt; no
residual-momentum; no RSI. If a "new idea" surfaces mid-program, it must name which of {new data,
new feature, new sub-period, new formulation} it brings **before** it earns a run.

---

## 3. Loop engineering — a disciplined research loop

"Loop engineering" = mechanize the house research cycle so a *bounded* parameter space (RQ1's
hedge grid) is explored **with the discipline baked in**, not bypassed. Built as a `Workflow`
(deterministic control flow, fan-out of independent arms), NOT an open-ended agent crank.

**The loop, per arm:**
1. **Registry gate** — check the arm against `overlay_registry.md` / findings / KILL ledger.
   A near-identical killed arm is refused unless it declares a new {data/feature/sub-period/
   formulation}. (Prevents the loop from relitigating the dead.)
2. **Pre-register** — write `diagnostics/research/preregistry/NNNN-*.md` (Status PRE-REGISTERED)
   and increment `n_trials.json` **before** the run. Params are fixed here.
3. **Run** — cfg-gated overlay on the pinned dataset; assert golden-master byte-identity with the
   overlay OFF as a pre-flight.
4. **Gate** — continuous-slice sub-period gate + DSR at the cumulative count + bootstrap CI.
5. **Record** — emit `research/findings/NNNN-*.md` (root-cause readout + next-setup) and an
   `overlay_registry.md` row. UNDERPOWERED/KILL is a valid terminal state.

**Hard loop guardrails:**
- The loop may **only** run RQ1's pre-declared grid (and RQ2 if its data lands). It is **not**
  authorized to invent momentum-sleeve trials.
- Every arm cfg-gated → golden master byte-identical when off, always.
- The loop **cannot relax a threshold** or retune toward a pass; verdicts are mechanical.
- Forward wall stays the only certifier — the loop promotes at most to a *shadow* proposal for the
  next quarterly review, never to live capital.

**Second, operational loop (not a research-trial loop):** a **forward-wall processing loop** —
scheduled ingest of the 3-book wall log, gate checks, and quarterly-review-readiness surfacing.
This is the mechanical, no-peeking companion to `nq/paper/wall_cron.py`; it makes the discipline
("log and leave it alone between quarterly reviews") automatic. Distinct from the daily
weekly-monitor cron shipped today, which re-prices the *weekly-swing* forward-watch book.

---

## 4. Phasing & milestones

| Phase | Deliverable | Gate to advance |
|---|---|---|
| **P0 — Data honesty** | Committed NIFTY options-premium series (PIT) *or* a documented BS-modelled premium with realistic IV, clearly labelled MODELLED. | Owner accepts the data provenance. Without this, RQ1 is estimate-only. |
| **P1 — Overlay skeleton** | cfg-gated hedge overlay in the engine; golden-master byte-identical when off; one smoke arm end-to-end. | `tests/test_stage2_golden.py` passes; depgraph regenerated. |
| **P2 — Loop harness** | The §3 Workflow loop wired over RQ1's pre-declared grid, with the registry gate + prereg + DSR steps. | Dry-run on 1 arm reproduces a hand-run result byte-for-byte. |
| **P3 — Grid run** | Pre-registered sweep of the hedge grid; per-arm findings + registry rows; vibe-trading options cross-check attached. | All arms recorded (PROMOTE/UNDERPOWERED/KILL). |
| **P4 — Decision** | Owner review. If an arm PROMOTEs, it becomes a **forward-wall shadow proposal** for the next quarterly review — subject to the §1 two-shadow-book cap (a swap must be recorded). | Quarterly-review cadence (Jan/Apr/Jul/Oct). |

---

## 5. vibe-trading integration (gated on owner go-ahead)

1. `pip install vibe-trading-ai` (external network install — **needs owner OK**).
2. Wire `vibe-trading-mcp` so `analyze_options` / options skill / (optionally) `factor_analysis`
   are callable.
3. Use it for: (a) options premium/Greeks sanity + drag cross-check on RQ1; (b) a **one-off**,
   guarded external IC scan of any *non-technical* Alpha-Zoo factor family (screen, not a swap);
   (c) optionally, an execution-quality Shadow-Account profile of the owner's real Kite fills vs
   the paper book.
4. It never writes to `n_trials.json`, never issues a verdict, and never becomes the backtest of
   record.

---

## 6. Non-goals / discipline reminders

- This document is a **PLAN**, not a pre-registration — it increments nothing. The first trial
  starts only after P0 data honesty + a written pre-reg.
- No relitigating the KILL ledger without a declared new lever.
- Engine invariant is sacred: any overlay cfg-gated, golden master byte-identical when off.
- Forward wall is the only path to live capital; between quarterly reviews, log and leave it alone.

---

*Owner decision points: (a) approve the tail-hedge program as the phase's primary lever; (b)
approve the vibe-trading install/wire; (c) accept the P0 options-data provenance before RQ1 runs.*
