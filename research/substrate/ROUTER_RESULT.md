# Context-Router — RESULT: killed at the gates (measurement, no trial)

**Run 2026-07-16.** Spec: `research/CONTEXT_ROUTER_SPEC.md`. Plan + rules: the approved build plan
(risk register R1-R11). Reproduce: `python scripts/diag_router.py`. Nothing shipped; live config untouched.

## Gate 1 (A1) — FIRED: the entry-side router already exists

The zoo's `& ~wsig` masking **already assigns exactly one origin per name-week** in a fixed priority
order (touch → box → trend → sr → vcp → flag → cup → ascending → double_bottom). Verified: **32,369
entry windows, each with exactly ONE origin, zero overlaps, zero unassigned.**

| origin | 0 touch | 1 box | 2 trend | 3 sr | 4 vcp | 5 flag | 6 cup | 7 asc | 8 dbl |
|---|---|---|---|---|---|---|---|---|---|
| windows | 8518 | 6143 | 9143 | 379 | 181 | 80 | 1893 | 1197 | 4835 |

A one-state-per-name classifier would emit an **identical** entry set (**Jaccard = 1.0 > 0.90**) →
**A1 kill-gate fires.** Building a separate state classifier would have been "the zoo with extra
steps." *The gate saved the entire Layer-0/1 build.* Only ONE element of the spec was genuinely new:
**per-branch exits inside one shared-capital book.**

## Gate 4 (R3) — the router LOSES on the 2022-26 continuous slice

| config | trades | Sharpe | CAGR | MaxDD | Calmar | **22-26** |
|---|---|---|---|---|---|---|
| **A live touch (BASELINE)** | 168 | 1.03 | 21.2% | −34.8% | 0.61 | **1.29** |
| B all-7 shared, uniform P2 | 205 | 1.22 | 28.2% | −44.0% | 0.64 | 1.07 |
| B' good branches, uniform P2 | 204 | 1.11 | 25.2% | −40.1% | 0.63 | 0.94 |
| **R ROUTER — per-branch exits** | 201 | 0.98 | 20.5% | −39.2% | 0.52 | **0.71** |

**Router 0.71 vs baseline 1.29 → LOSES.** Per **R11** this is a FINDING; no retune, no goalpost move.

**Mechanism (the 4th sighting of per-trade ≠ portfolio):** box's let-run exit is genuinely better
**standalone** (22-26 1.08 vs 1.00) — it had its own Rs10L. Inside a **shared** book the same exit holds
positions **longer**, ties up capital, and **starves the better touch trades** (0.94 → 0.71). A
per-branch improvement validated in isolation becomes a portfolio negative under a binding cap.

## Gate 5 (A5) — did NOT fire, and it reframes the problem

Branch-pair return correlations: **0.61-0.79, all below 0.80** → genuine diversification IS available.

|  | touch | box | cup | asc | dbl |
|---|---|---|---|---|---|
| touch | 1.00 | 0.65 | 0.64 | 0.61 | 0.67 |
| box | | 1.00 | 0.69 | 0.72 | 0.79 |
| cup | | | 1.00 | 0.70 | 0.74 |
| asc | | | | 1.00 | 0.75 |
| dbl | | | | | 1.00 |

**Correlation was never the binding constraint.** The touch book **strictly dominates** every branch
(22-26: touch 1.29 > box 1.08 > cup 1.02 > dbl 0.94 > asc 0.64). Under a binding Rs10L cap, every rupee
diversified into a weaker branch is a rupee not in the best one. **Quality gap × capital scarcity**, not
correlation, is what kills every combination.

## Verdict

**Context-router KILLED.** The build stops at gate 4 (steps 6-8 were conditional on it holding). The
live touch-only book remains the best configuration tested across entry, exit, sizing, and routing.

## What the gates bought us

- **A1** killed a redundant classifier build in one command.
- **R1/R2/R6** held throughout (golden 1.1319/255; pure touch 1.0342/−34.8%/168; additivity exact) —
  the new `exit_by_origin` lever is inert when off.
- **R11** stopped a retune when the result disappointed.
- The engine gains a reusable, cfg-gated `exit_by_origin` lever (default None ⇒ byte-identical).
