# Finding 0105 — Intraday hard stop KILLs the swing book: the close-only stop is protective (the whipsaw > the recovery)

**Verdict:** **KILL** — keep the close-only weekly stop. Pre-reg
[0105](../../diagnostics/research/preregistry/0105-hardstop-swing.md); `scripts/run_0105_hardstop_swing.py`.
n_trials 132→133 (counted before the run).

## Result (frozen 0094, corrected universe 2017-2026)
| | Sharpe | CAGR | MaxDD | trades | win | expR |
|---|---|---|---|---|---|---|
| close-only stop (0094) | +1.132 | +24.7% | −42.4% | 255 | 59% | +0.48 |
| **intraday hard stop** | **+0.655** | **+12.4%** | **−53.3%** | 301 | 48% | +0.24 |
| Δ | **−0.477** [−0.84,−0.07] | −12.3pp | **−10.9pp (worse)** | +46 | −11pp | −0.24 |

Pre-committed bar **4/4 FAIL**. Stop exits 66 → **122** (114 hardstop + 8 gap). Byte-identical baseline.

## Root cause — the discriminant was one-sided; the whipsaw dominates
The best-vs-worst discriminant showed the stop touches only losers (66/66) and ~19.8R is "recoverable" from
intra-week blow-throughs. **But that only counted trades that ALREADY stopped out.** The daily hard stop
*also* catches the ~56 trades that dipped below the stop intra-week **but recovered by Friday and became
winners** under the close-only rule — and those intra-week recoveries **ARE the momentum edge** (the
deep-near-SMA entries that dip then rip). Killing them at −1R halved CAGR (24.7→12.4), collapsed the win
rate (59→48%), and — counterintuitively — **deepened the DD (−42→−53)**: more realized losses + the
0095/0104 cash-redeploy inversion (freed cash → 46 more, weaker fills).

## The teaching point
The "sloppy" close-only weekly stop that "routinely blows past 1R" is **not a bug — it is protective.** It
gives trades room to recover intra-week, and the edge lives precisely in those recoveries. The +19.8R
forensic estimate was real but the hidden whipsaw cost was ~3× larger. This is the fourth time the
cash-redeploy/edge-dilution mechanism has killed a "make it safer" lever (0095, 0104, and now the exit
side). **The exit/stop is NOT the free asymmetric lever it looked like.**

## What remains
Owner's live idea — WIDEN the stop slightly (more recovery room, the opposite of hard_stop) — is the one
exit lever still aligned with this lesson and has prior support (0025: 4×ATR geometry lifted the swing book
+0.40 Sharpe / −12% DD). Pre-register a single widened-stop arm (not a sweep) if pursued. Entry-side levers
are exhausted (body-frac null; ext_cap-tighten KILL 0104; hard-stop KILL 0105).
