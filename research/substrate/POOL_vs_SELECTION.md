# Pool quality vs selection skill — the first POSITIVE result (measurement, no trial)

**Run 2026-07-16.** Reproduce: `python scripts/diag_pool_filter.py 40`. Live config untouched.

## The question (owner's reframing)

The Monte-Carlo null proved CRS-rank sits at the 99-100th percentile — the **selection ceiling** is
reached. So instead of a better picker: **make the POOL good enough that even a random pick is fine** —
i.e. raise the null *floor* (0.67). This matters because the honest forward expectation spans **0.67 (no
selection skill persists) to 1.03 (full skill)**; raising the floor is real risk reduction.

## The target is real and OUT-OF-SAMPLE persistent (not fitted)

Touch-pool mean R by entry extension vs the signal-week SMA:

| bucket | train meanR | holdout meanR | note |
|---|---|---|---|
| <0% (below SMA) | +1.91 | +2.70 | best, but N=12/23 — cannot be manufactured |
| 0-5% | +0.72 | +0.55 | the core edge |
| **5-10%** | **+0.12** | **+0.19** | **worst in BOTH periods — 36% of the pool, 10% of the R** |
| 10-15% | +0.31 | +0.43 | |
| >15% | +0.41 | +0.62 | |

Dropping the 5-10% band lifts pool mean R by **+0.133 (train) / +0.154 (holdout)** — near-identical
across periods. **The structure is durable, not curve-fitted.**

## Result — the floor rises, but the ceiling breaks

| | random floor (Sharpe) | random floor (22-26) | CRS ceiling (22-26) | CRS DD |
|---|---|---|---|---|
| **A — all candidates (LIVE)** | 0.67 | 0.74 | **1.29** | −34.8% |
| **B — 5-10% band dropped** | **0.85 (+0.20)** | **0.84 (+0.10)** | **0.47 (−0.82)** | −50.1% |

**The owner's thesis is CONFIRMED for the floor: pool filtering raises the random-selection Sharpe
0.67 → 0.85.** Buying at random from the filtered pool is genuinely better.

**But it breaks CRS.** On the filtered pool CRS scores **0.47 — BELOW that pool's own random mean of
0.84** (~1.9σ). CRS flips from 100th-percentile skillful to actively harmful.

**Mechanism:** CRS ranks by relative strength, and high-RS names are the **more extended** ones. The
5-10% middle is therefore **CRS's hunting ground** — dead *on average*, but precisely where CRS's skill
extracts winners. Remove it and CRS is pushed into the weaker 10-15%+ tail. **Pool-level averages are NOT
what a skillful selector pulls out of that pool.**

## Decision framework (it is a HEDGE, not an upgrade)

| config | if CRS skill persists | if it does NOT |
|---|---|---|
| **Full pool + CRS (live today)** | **1.29** | 0.74 |
| Filtered pool, no CRS | 0.84 | **0.84** |
| Filtered pool + CRS | 0.47 | 0.47 — **never** |

**Recommendation: keep the full pool.** The Monte-Carlo showed CRS's 1.29 beats **all 100** random draws
(p<0.01) — strong evidence the skill is real. The filter only wins if CRS is a mirage.

**But it is now a quantified fallback:** if the forward wall shows CRS's edge decaying, the filtered pool
is the higher-floor fallback and we already know its number (0.84 vs 0.74).

## Caveats

- The band boundary (5-10%) was read off the in-sample bucket table; the *deadness* replicates OOS
  (train +0.12 / holdout +0.19), which is what licenses it — but the exact boundary is still a knob.
- Never combine the filter with CRS (0.47). The two are antagonistic by construction.
- Nothing shipped. The CRS-persistence question is answerable only on the forward wall.
