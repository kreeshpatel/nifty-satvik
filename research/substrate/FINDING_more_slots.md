# Finding — MORE SLOTS dilutes: every extra seat walks the book toward the random null

*Pre-registered `research/preregistry_more_slots.md`, frozen before the run (R4). n_trials 120→122.
Guards byte-identical (golden 1.1319/255 · live P2 1.0342/168).*

## Result — KILL, and INFORMATIVE (the mechanism check passed)

| arm | risk | notional/name | names | tr | Sharpe | CAGR | DD | **22-26** | win | skip_cash |
|---|---|---|---|---|---|---|---|---|---|---|
| BASE | 2.0% | 14.1% | ~7 | 168 | 1.03 | 21.2% | −34.8% | **1.29** | 54% | 19,728 |
| **SPEC** | 2.0% | **21.8%** | **~4-5** | 181 | 1.11 | 21.6% | −33.6% | **1.21** | 53% | 19,151 |
| S1 | **1.3%** | 13.0% | ~7 | 257 | 0.93 | 18.6% | −38.0% | **0.97** | 50% | 18,524 |
| S2 | **0.9%** | 9.2% | ~10 | 358 | 1.01 | 17.8% | −38.7% | **0.81** | 48% | 17,889 |

**Mechanism check (declared BEFORE the run): PASSED.** `skipped_cash` fell (19,151 → 18,524 → 17,889) and
trades rose (181 → 257 → 358). The lever did what it was built to do. **So this KILL is evidence about the
hypothesis** — unlike `FINDING_decouple.md`, where the mechanism failed and the KILL said nothing.

## The answer: dilution, monotonic, exactly as pre-declared

Within the SPEC family (only `risk_pct` varies — a clean comparison):

```
seats:   4-5  ->   7   ->  10        (random null = 0.74)
22-26:  1.21  -> 0.97  -> 0.81  ->  0.74
win%:     53  ->   50  ->   48
```

Every extra seat is filled by going **deeper down the CRS queue**, and CRS's skill is concentrated in the
top few names. The book walks straight down the runway toward the null. More trades, worse trades. This is
the `POOL_vs_SELECTION` / Monte-Carlo result (CRS at the 99-100th percentile of selection skill) showing up
as a **dose-response curve**: concentration is not incidental to CRS's edge, it *is* the edge.

## A correction to `FINDING_owner_discipline.md`

That finding called the SPEC's 22%-per-name concentration **"the real cost of the R cap"** and listed it as
structural ✗. **That was wrong, and this run inverts it.** Within the SPEC family fewer/bigger positions is
*better*: 4-5 names (1.21) > 7 (0.97) > 10 (0.81). The concentration is **load-bearing, not a cost**.
`max_notional_pct=0.20` should be understood as a **guardrail against runaway single-name risk**, not as a
mechanism that buys performance — and there is no diversification case for widening the book.

(Caveat on cross-family reads: S1 at 13.0% notional scores 0.97 while BASE at 14.1% scores 1.29. Similar
notional, very different books — the R cap and ext_cap change *which* trades exist and how many. Only the
within-SPEC comparison isolates slot count. Do not read "14% notional is worth 1.29" from this.)

## The cash-starvation thread is now CLOSED

`FINDING_cash_starvation` established the book abandons ~19k fills and takes ~2% of signals, and that the
CRS queue serves the *extended* version of a setup (MAXHEALTH: the +2.0%-ext window was worth **+3.00R**;
we took +19.4% ext for **−1.38R**). Two fixes existed:

1. **Reorder the queue** (near_sma fill-priority) — **KILLED at −0.80 Sharpe**; it displaces the
   CRS-strongest names, which *are* the runners.
2. **Add seats** (this finding) — **KILLED**; every seat dilutes toward the null.

**Both directions are now dead. The cash starvation is not a bug to fix — it is the selection working.**
The 19k skipped fills are the 98% of signals CRS is right to refuse. The MAXHEALTH +3.00R window is real
and unreachable: any mechanism that would have caught it also catches hundreds of worse ones.

## Verdict

**KILL both arms.** R11 — nothing ships. Live config FROZEN. `risk_pct` stays 2.0%.

## Next setup

The `tp_on_high` route I ranked first was **already REJECTED** (0.709 Sharpe / −49.7% DD,
`losers_analysis/FORENSIC_FINDINGS.md`) — caught only by a registry check I should have run before
recommending it. Recorded as a process failure: **registry-first is not optional**, and on the SPEC book
it would fire *more* often (2R = a 20% move at R=10%, vs 28% at R=14.2%) and truncate more.

What remains genuinely unspent is thin, and that is itself the finding: the faithful near-SMA-fire variant
of the owner's sequence (`FINDING_decouple.md` — the only hypothesis whose implementation never matched
its intent). Everything else on the entry, exit-truncation, selection, and sizing axes is dead. **The book
that survives every attack is the one already frozen**, plus the owner's discipline config, which remains
free and now looks *better* than recorded (its concentration is a feature).
