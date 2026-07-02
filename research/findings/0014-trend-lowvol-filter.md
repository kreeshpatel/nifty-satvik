# 0014 — Trend × low-vol filter (0080): the strongest in-sample hybrid — and still uncertifiable

- **Status:** **KILL by the pre-committed bar (uncertifiable)** — but the strongest in-sample overlay of the arc, and the third signpost to the low-vol / multi-sleeve lever. Forward-wall watch candidate; do NOT change the frozen cfg.
- **Date:** 2026-07-02. Pre-registration: [`diagnostics/research/preregistry/0080-trend-lowvol-filter.md`](../../diagnostics/research/preregistry/0080-trend-lowvol-filter.md).
- **Type:** TRIAL (2 fixed-cutoff arms; cumulative_n_trials 95 → 97).
- **Anchor:** pinned `baseline_v1`. Script `scripts/run_lowvol_filter.py`; raw `research/exports/lowvol_filter_0080.json`.

## Hypothesis
High realized-vol trend names are "junk-rally" momentum that reverses hard in a rotation; dropping them
before ranking by the slope improves the shape at modest CAGR cost. This is a conditional FILTER, distinct
from O-006 (low-vol signal-blend) and O-016 (low-vol sole ranker).

## Result (base: Sharpe 0.667 / Sortino 0.836 / CAGR 15.5 / DD −46.3 / 22-26 Sh 0.570 / 22-26 DD −46.3)
| filter | Sharpe | Sortino | CAGR | DD | 22-26 Sh | 22-26 DD | ΔSharpe [CI] | DSR | fold |
|---|---|---|---|---|---|---|---|---|---|
| **keep ≤ 50% vol** | 0.889 | 1.103 | 17.2 | −33.5 | 0.988 | −31.4 | +0.222 [−0.36, +0.76] | 0.35 | 0.50 |
| keep ≤ 33% vol | 0.871 | 1.086 | 14.6 | −37.8 | 1.035 | −23.9 | +0.204 [−0.34, +0.68] | 0.33 | 0.50 |

The filter improves **every axis at once** — CAGR *higher* (17.2 vs 15.5), Sortino 0.84→1.10, DD −46.3→
−33.5, 2022-26 DD to −23.9. The best in-sample overlay profile in the whole program.

## Verdict
**KILL by the bar.** ΔSharpe +0.22 but **CI [−0.36, +0.76] straddles 0**, DSR 0.35 ≪ 0.95, fold-pass 0.50
< 0.60. Kill criterion (i) ΔSharpe CI-low ≤ 0 fires. Uncertifiable at ~34 windows — the same wall that
stopped 0076/0077/0078/0079's low-vol arm.

## Root-cause readout (REQUIRED)
The mechanism is real: dropping the high-vol names keeps the *cleaner* trends (better Sharpe even though
Sharpe is vol-normalized — so it's not only the lower-vol-lower-DD effect) and avoids the volatile
junk-rally reversers, lifting return AND cutting DD. **But two honesty checks temper it:** (a) part of the
DD improvement is *mechanical* — a book restricted to low-vol names has a structurally shallower drawdown
regardless of skill; (b) the Sharpe gain, while positive on the point estimate, is **not consistent**
(fold-pass 0.50 — half the years) and its CI straddles 0, so it cannot be distinguished from luck at this
sample. This is the identical profile to every strong-looking lever this session: real mechanism, in-sample
lift, uncertifiable.

**The deeper read:** 0080 (filter) + O-016 (low-vol sole ranker) + the 0079 IC screen (rvol has real
negative IC) are three independent signposts to the **same lever — low-vol**. 0080 is its *best* form
(retains the trend CAGR while cutting DD). That the low-vol lever keeps recurring, always strong and always
uncertifiable in-sample, is precisely the case for it as a **separate defensive sleeve** certified on the
forward wall — not a frozen-cfg filter promoted off an in-sample run.

## Next setup
- **Forward-wall watch candidate** — arguably stronger than veto-0.1 (it improves more axes), but the
  pre-reg's two-shadow cap (base/veto/drift) is full → it waits, or displaces a shadow via a §7 swap, or
  feeds the multi-sleeve build.
- **The low-vol / multi-sleeve fork (forward/prereg §9)** is now triply-motivated. When the base clears the
  12-month review Green, the defensive low-vol sleeve is the justified build — and 0080 is the evidence for
  *how* to construct its momentum leg (trend, low-vol-filtered).
- Do NOT retune the cutoff or promote to cfg in-sample. The two values are fixed; a third is a new trial.
