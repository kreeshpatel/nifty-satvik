# Finding 0107 — Swing × low-vol blend: the diversification free-lunch transfers to the live vehicle (per-year confirmed)

**Type:** MEASUREMENT — the frozen 0081 ERC recipe (quarterly inverse-vol) re-applied verbatim to the
swing-0094 × low-vol pair; **no new free params → no trial spent** (n_trials stays 134). Engine
`scripts/run_blend_hybrid.py`; returns `research/exports/blend_hybrid_returns.csv`. **Certification =
forward-wall only** (in-sample uncertifiable: low-vol is O-016; 0081 was UNDERPOWERED, DSR 0.315).

## Why this run
The 2026-07-26 sweep exhausted every entry (body-null; ext_cap 0104) and exit (hard_stop 0105; widen 0106)
lever — the swing book is a robust optimum you can't tinker better. The per-year lens then exposed the real
weakness: it's a **trend-year book that fades in chop** (2024 +9.9%, 2025 −14.1%). The only lever that
*addresses* chop-year weakness is structural — pair it with a book that earns in chop. This tests that on
the LIVE vehicle (0081 tested it on the momentum *base*, Sharpe 0.67).

## Result (common window 2017-09 .. 2026-06, corrected universe)
| book | Sharpe | CAGR | MaxDD |
|---|---|---|---|
| swing 0094 | 1.15 | 26.3% | −42.4% |
| low-vol | 1.06 | 14.5% | −32.6% |
| **BLEND (ERC)** | **1.23** | 18.7% | **−33.1%** |

corr **+0.54**; mean swing weight 0.37. **The blend Sharpe (1.23) beats BOTH sleeves** — the textbook
low-correlation diversification lift (risk-adjusted return rises, not just averages).

**Per-year — the blend has ZERO losing years (swing alone has 1):**
| yr | swing | low-vol | blend |
|---|---|---|---|
| 2020 | +11.4 | +33.1 | +25.0 |
| 2023 | +66.5 | +31.1 | +42.7 |
| 2024 | +9.9 | +28.9 | +21.3 |
| **2025** | **−14.1** | **+18.3** | **+5.6** |

The chop years that killed the swing book (2024/2025) are exactly where low-vol earns +29%/+18% — it
**rescues 2025 from −14% to +5.6%**. Mechanistic, not one-year luck.

## The honest trade-off (a risk-preference dial, not a strict upgrade)
The blend gives up CAGR (**26.3 → 18.7%**) — it dilutes the swing book's monster trend years (2022 +35→+8,
2023 +66→+43). So it is a *choice*: max CAGR + −42% DD + one losing year (100% swing) vs higher Sharpe +
−33% DD + no losing year (ERC blend). **The allocation weight IS the barbell dial — an owner risk decision.**
The Sharpe-*lift mechanism* is robust; the *absolute* 1.23/−33 is in-sample-optimistic.

## Verdict & routing
**Structural edge confirmed on the live vehicle; UNDERPOWERED to certify in-sample → FORWARD-WALL watched
book.** Registered in `forward/prereg_swing.md` as the `blend-hybrid` book alongside the live swing book;
certified on forward evidence at the quarterly review, never an in-sample config swap. This is the one lever
that survived the whole 2026-07-26 sweep, and the only one that fixes the chop-year fade — it doesn't tinker
with the momentum book, it pairs it with something that earns when momentum can't. Directly executes
`forward/action_plan.md` Tier-2.

## Open follow-ups
1. **Live infra:** the daily wall must compute a low-vol paper sleeve to log the blend forward (the swing
   paper book already runs; the low-vol sleeve cron is the missing piece).
2. **Weight choice:** ERC gives ~37% swing; the owner may prefer a higher swing weight (more CAGR, more DD).
   Fix the weight in the forward registration; do not tune it to the in-sample optimum.
