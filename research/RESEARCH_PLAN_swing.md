# Research Plan — Weekly-Swing Book (swing-only, options declined)

*Drafted 2026-07-09. Status: **PLAN** (increments no trial). Owner directive this session:
**focus on swing trading, not options** — the tail-hedge lever is declined and removed. Supersedes
the prior tail-hedge draft of this file.*

Scope: the live forward-watch **`weekly-swing-0094-rank`** book (Bhanushali 6-step reconstruction
+ Nifty-50 CRS signals + CRS-ranked fills). Written to the house discipline — registry-first,
adversarial, forward-wall-certified.

---

## 1. Honest state of the swing book (verified 2026-07-09, not from memory)

- **Backtest is already on the CORRECTED universe** (`models/bhanushali_weekly/config.json`
  → `backtest.universe = "corrected (pinned + backfill + aliases)"`, 2017–2026): net **Sharpe 1.132
  / CAGR 24.7% / MaxDD −42.4% / win 59.2% / CI-low 0.474 / DSR 0.894**. Leakage-clean; ranked-fill
  ordering-probe verified (desc best, asc worst); sub-slices +1.17 / +1.05 / +1.19. **It is NOT
  survivorship-inflated** — the re-anchor worry does not apply here (checked; the backfill was
  already used).
- **In-sample work is CLOSED** (finding 0025 disposition: "no experiment remains that could change
  this verdict in-sample; the next knob is trial #2 of a search — forbidden"). The distinct
  practitioner/4×ATR variant (0025) came in at net +0.397 Sharpe / −12% DD — 0.003 under its
  pre-committed bar; recorded, not relitigated; Oct-1 decides it.
- **Forward-watch paper since 2026-07-04.** The book's real weakness is **not** Sharpe (1.13 is
  strong) — it is **DSR 0.894 < 0.95** (underpowered / multiple-testing) and the **−42% drawdown**.
- **The only certifier is the forward wall + the quarterly reviews** (`forward/prereg.md`); the
  Path-B swing sleeve is a registered PROPOSAL for the **2026-10-01** review (promote/kill
  pre-committed).

## 2. What is forbidden (so "research" here stays honest)

- **No no-new-lever trial.** Every in-sample trial deflates the DSR bar (cumulative n = 112). A
  trial that is not a genuinely new lever cannot clear DSR and taxes every other result.
- **No relitigating the KILL ledger** (regime entry gate O-001, RSI/MACD/chart-zoo 0079/O-015,
  residual-mom 0077/78, conviction sizing 0073/20, signal-level low-vol blend O-006/07, macro/USD
  0082) without declaring which of {new data, new feature, new sub-period, new formulation} is new.
- **No retune toward a pass.** Params are fixed in the pre-reg; UNDERPOWERED/KILL is a first-class
  outcome.
- **vibe-trading is cross-check only** — its data is not PIT-clean NSE, so it is never the backtest
  of record and never writes `n_trials` or a verdict. Our harness + pinned dataset stay canonical.

## 3. The two legitimate research tracks

### Track 1 — Certification machinery *(no trial, no-regret; "loop engineering" for swing)*

Build the operational loop that turns the accruing forward evidence into a **mechanical** Oct-1
decision, so the swing book is judged on pre-committed rules, not vibes:
- A **forward-wall processing loop** for the swing book: scheduled ingest of the paper ledger →
  gate checks (edge-intact / degraded / halt) → quarterly-review-readiness surfacing. The
  no-peeking companion to the daily monitor shipped today.
- The **Oct-1 promote/kill scorecard**: freeze the Path-B sleeve spec (the delisted backfill that
  gated it has landed), wire the pre-committed thresholds, and render a one-look "does it clear the
  bar" panel. Makes moving-the-goalposts structurally impossible.

This advances certification without spending a DSR-deflating trial. **Recommended first.**

### Track 2 — One genuinely-new swing lever, pre-registered *(costs one trial each)*

Active in-sample research is allowed **only** as a declared new lever, pre-registered, cfg-gated,
measured on the corrected universe with the continuous-slice sub-period gate and DSR accounting.
Target the book's real weakness — **DD / robustness**, not Sharpe. Registry-checked candidates
(each must confirm non-duplication before it runs):

| # | Lever | New because | Targets | Notes / risk |
|---|---|---|---|---|
| L1 | **Vol-target sizing ported to the swing book** | O-009 vol-target de-gross was PROMOTED for the *momentum base*; it has **not** been applied to this weekly book (which uses flat 2% risk). *New formulation.* | −42% DD | The most direct swing-native DD lever now that options are off the table. |
| L2 | **CRS denominator alternative** (Nifty-500-TRI or sector-relative RS) vs the N50 pick | Finding 0037 chose N50; the broader/sector denominator is untested here. *New formulation.* | Sharpe / robustness | May not move DD; judge on the continuous-slice gate, not IC. |
| L3 | **Swing-native entry-quality feature** (dip-depth / entry-confirm) into the CRS fill ranking | dip20_depth is a base shadow feature (Jaccard 0.04, CI excludes 0) but untested as a *swing fill-ranker*. *New feature.* | fill quality / DD | IC ≠ portfolio Sharpe (0079/O-019) — must clear as a *ranker*, not on IC. |

**Verdict rule (pre-committed, per lever):** PROMOTE to a forward-wall shadow only if it clears the
pre-registered bar under the continuous-slice gate; else record UNDERPOWERED/KILL. No retune.

## 4. Process (per Track-2 lever) — the disciplined loop

1. **Registry gate** — confirm the lever isn't a killed/near-identical idea (`overlay_registry.md`,
   findings, KILL ledger); if adjacent, declare the new {data/feature/sub-period/formulation}.
2. **Pre-register** — `diagnostics/research/preregistry/NNNN-*.md` (params fixed); increment
   `n_trials.json` **before** the run.
3. **Run** — cfg-gated overlay on the corrected universe via our harness; assert the golden master
   (`tests/test_stage2_golden.py`) stays byte-identical with the overlay OFF.
4. **Gate** — continuous-slice sub-period gate (`nq.runner.research.evaluate_overlay`, never
   fresh-capital) + DSR at the cumulative count + bootstrap CI.
5. **Record** — `research/findings/NNNN-*.md` (root-cause + next-setup) + an `overlay_registry.md`
   row. vibe-trading may cross-check a number; it never decides.

## 5. Non-goals / guardrails

- This doc is a PLAN — it increments nothing. A trial starts only after a written pre-reg.
- Engine invariant: any overlay cfg-gated; golden master byte-identical when off.
- Forward wall + Oct-1 review are the only paths to promotion; between reviews, log and leave alone.
- Options / derivatives hedges are **out of scope** per the owner's 2026-07-09 directive.

---

*Owner decision needed to start: (a) Track 1 machinery first (no trial), or (b) spend a
pre-registered trial on one Track-2 lever — and if so, which of L1 / L2 / L3.*
