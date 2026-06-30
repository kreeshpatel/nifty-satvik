# Overnight Autonomous Research Log — started 2026-07-01

> Owner is away. This is the running journal of every test run + decision taken in their absence, per
> the autonomous mandate: advance `docs/LOCK_PLAN.md`, record + **question** every result and dig
> deeper, take professional decisions without waiting, keep multi-agent work on a hybrid
> haiku/sonnet/opus tier to save tokens. **Morning briefing is at the bottom — read that first.**
> All numbers are pinned (`dataset-pin-20260701`, byte-reproducible) unless noted; every verdict is
> through the mechanized 7-gate `evaluate_overlay`.

## Standing decision rules (how I'm judging things while you sleep)
- **PROMOTE** only if `gate_pass=True` (all 7 auto-gates) AND a clean mechanism. None expected.
- **SHADOW** = positive but UNDERPOWERED (ΔSharpe CI straddles 0 / DSR<0.95) → log, touch no trade,
  flag for the forward wall. The let-winners-run lead is the live SHADOW candidate.
- **KILL** = ΔSharpe≤0 or fails the bar with a clear root cause → record + do-not-retest.
- Respect the §11 graveyard + the v1-don't-transfer rule (memory). Stay within the +6 n_trials budget
  (82→88 cap); batch correlated arms; measurements aren't trials.

---

## Test ledger

| # | Test | Run | Verdict | Decision |
|---|---|---|---|---|
| 0 | LOCK Step 1 — mechanize 7-gate bar (regression: A5 re-grades KILL identically, after-tax base ~12.76%) | local + commit bdabe59 | DONE | gates fail-closed; A5 fails 5/7 |
| 1 | **0071 let-winners-run** (B stop_only / C no_trailing / D no_target) — local --quick preview | local | B UNDERPOWERED (ΔSh +0.114, dCalmar +0.05, 2022-26 +9.6%, fold 75%, DSR 0.36); D UNDERPOWERED (+0.138); C KILL | awaiting cloud canonical → likely SHADOW |
| 1c | **0071** — cloud canonical (full 5000 samples) | run 28481282947 | **B stop_only UNDERPOWERED** (ΔSh +0.114, Sharpe 0.667→0.781, after-tax 12.76→14.87%); **D no_target UNDERPOWERED** (ΔSh +0.138, Sharpe→0.805, after-tax 12.76→**16.76%**); C no_trailing KILL | **SHADOW** the let-winners-run family (removing the target). Mechanism: target clips momentum winners + forces taxable churn. DIG DEEPER → target sweep (#2). |
| 2 | **Target sweep** (give-back curve): target_pct ∈ {15, 22.52(base), 30, 40, OFF} vs base — is OFF optimal or is a higher finite target better? EXPLORATORY (not a new trial). | _launching_ | _pending_ | _pending_ |

---

## MORNING BRIEFING (read first — filled as the night progresses)

**Headline so far:** the first non-KILL lead of the whole research arc — **removing the +22.52% profit
target ("let winners run") IMPROVES the 63d strategy** (ΔSharpe +0.11/+0.14, better Calmar + 2022-26 +
fold-pass), but lands **UNDERPOWERED**, so it's a SHADOW candidate, not a cfg change. This directly
vindicates your "don't trust short-term kills" rule: the v1 14d result (0047: let-winners-run is dead)
does NOT transfer to 63d. **The research edge to discuss in the morning is the EXIT structure**, not
conviction/sizing (both dead). Details + the deeper digging below as the loop runs.
