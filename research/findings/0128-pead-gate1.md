# 0128 — PEAD Gate-1: the drift is REAL on our universe (+6.6% spread, 4/4 years) — and it is decaying, momentum-entangled, and absent in the liquid names we can actually trade

- **Status:** **MEASUREMENT.** 0 trials. No screen-ledger row (pre-reg §0.3 — the banked
  0116/0117 label set is never read). Sealed set and judge log untouched. No engine change.
- **Standing counts: screens 14 · sealed opens 1 · n_trials 138** — unchanged.
- **Verdict: gate FAILS as written (leg 4), and the failure is a partial-year artifact, not the
  famine leg 4 was designed to catch. Owner's call — see "The door" below.**
- **Date:** 2026-07-31. Pre-reg
  [`0128-pead-gate1.md`](../../diagnostics/research/preregistry/0128-pead-gate1.md).
- **Script:** `scripts/diag_pead_gate1_0128.py` → `diagnostics/research/pead_gate1_0128.{md,json}`.
- Takes up the **OPEN** registry row **SL-002** ("NSE PEAD sleeve — not yet measured").

## Coverage — no famine (the Weinstein lesson does not bite here)

58,871 NSE result events → 20,230 joinable to OHLCV → 14,672 PIT Nifty-500 members →
**12,186 usable** after ADV ≥ ₹5cr and the history requirement.

| year | 2019 | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 | 2026* |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| usable events | 1,083 | 1,360 | 1,738 | 1,773 | 1,810 | 1,948 | 1,985 | 489 |
| top decile | 110 | 138 | 175 | 178 | 183 | 195 | 200 | 49 |

*\*2026 is a stub: the data ends 2026-07 and every event needs 63 trading days after it, so H2-2026 is
structurally absent.*

Roughly **1,700–2,000 usable events/yr** — two orders of magnitude clear of the 22.5/yr that strained
Weinstein's CIs.

## The drift exists, and it is monotone

Market-adjusted drift (%) from **open(+2)** — sharing no bar with the ranking window — train 2019-22:

| decile | mean CAR(0,+1) | H=10 | H=21 | H=42 | **H=63** |
|---:|---:|---:|---:|---:|---:|
| 1 (worst) | −9.38 | −1.88 | −1.00 | −0.78 | **−2.91** |
| 5 | −1.07 | −0.51 | +0.17 | +0.95 | +0.58 |
| 8 | +2.49 | +0.25 | +1.19 | +2.29 | +2.87 |
| **10 (best)** | +9.99 | +0.90 | +2.37 | +3.55 | **+3.74** |

**Top-minus-bottom spread at H=63: +6.645% [+4.234, +9.173].** Train-year sign **4/4**
(2019 +6.7 · 2020 +2.0 · 2021 +9.6 · 2022 +7.3). Top decile net of ~0.26% round-trip: **+3.48%**.

**Legs 1–3 of the gate pass decisively.** On the existence question the answer is yes: post-earnings
drift is present on our universe in 2019+. That is a real result and it is the first thing in this
programme's premium search that has looked like this.

**Which is exactly when the leakage discipline applies** — *leaks inflate; a too-good result is
guilty until cleared*. Three things clear it partially and one caveat does not clear at all.

## §4 confound checks — the momentum one FIRES

**Momentum (pre-reg §4.1: "if the spread lives only in the high-momentum tercile, it is momentum
wearing an earnings costume → KILL, not a discovery"):**

| trailing-63d momentum tercile | spread (H=63) | 95% CI |
|---|---:|---|
| low | +3.17 | **[−1.04, +7.51]** — straddles zero |
| mid | +5.87 | [+2.26, +9.38] |
| high | **+9.93** | [+5.40, +14.52] |

Monotonically increasing in momentum, and **not significant among low-momentum names**. This is not
the pure form the pre-reg named as an outright KILL (the mid tercile is significant), but it is the
substance of it: **the effect is not established independent of momentum**, and momentum is already
the house signal. A PEAD sleeve built on this would carry a large momentum loading — which attacks
precisely the 0115 limb it needed to clear.

**Liquidity (pre-reg §4.2: "if it survives only in the bottom tercile, it is not tradable at this
book's size"):**

| ADV tercile | spread (H=63) | 95% CI |
|---|---:|---|
| low | +6.69 | [+2.22, +11.38] |
| mid | +8.78 | [+4.79, +12.90] |
| **high** | **+3.64** | **[−0.30, +7.61]** — straddles zero |

**The effect is not significant in the most liquid third** — the names this book actually trades at
size. This is the textbook small-cap concentration of PEAD, and it is the tradability problem in its
usual place.

## Decay — the literature's dispute, answered for our window

| | train 2019-22 | out-of-window 2023-26 |
|---|---:|---:|
| top-minus-bottom spread (H=63) | **+6.645** | **+2.822** [+0.74, +4.86] |

Per-year: 6.7 · 2.0 · 9.6 · 7.3 ‖ 4.4 · 2.2 · 2.5 · 0.5. **Still positive and still CI-clean out of
window, but under half the train magnitude, with a visible downtrend.**

This is consistent with the decay side of the contested Indian literature (significant 2002-2017 in
Sen/SCIRP; null 2014-2018 in the EconStor/NSE study). **It does not adjudicate either paper** — our
calendar starts 2019, after both windows, exactly as the pre-reg recorded in advance.

## The door — the gate fails, and I am not retuning it

The pre-committed gate (§3) requires all four legs. **Legs 1, 2, 3 PASS. Leg 4 FAILS:** the floor was
"≥150 top-decile events/yr" and the minimum across years is **49** — which is **2026, a stub year**
that is structurally half-length because the data ends 2026-07 and every event needs 63 trading days
after it.

**Mechanically the gate says FAIL, so this study reports FAIL.** I am not amending the threshold or
dropping the stub year to produce a pass — that is precisely the retune the laws forbid, and a gate
that can be adjusted after seeing the result is not a gate.

**But reporting the bare FAIL would be equally dishonest**, because leg 4 exists to catch famine and
there is no famine: every complete year carries 110–200 top-decile events. Leg 4 failed on a
construction detail the pre-registration did not anticipate.

**This is therefore an owner's call, and it is a governance-shaped one:**

- **Accept the close.** SL-002 moves OPEN → closed-on-a-technicality, and the last untested premium
  family shuts with the substantive result on record. Defensible: the confounds are unflattering
  enough that the substantive case is weak anyway.
- **Or amend leg 4 by a dated pre-reg amendment — written and committed BEFORE any Phase-2 number
  exists** — to read "≥150 top-decile events per *complete* year". That is a legitimate amendment
  only because it is made against a construction artifact, its direction was fixed before Phase 2
  ran, and it is recorded. It would not change legs 1–3, which already passed.

**My recommendation: accept the close.** Not because of leg 4 — because of the confounds. The
substantive case for a PEAD sleeve is that it is a *different return source* (0115's requirement),
and the momentum tercile table says it is substantially the *same* return source, while the ADV table
says the part we could trade at size is not significant. A sleeve that is momentum-loaded and
liquidity-fragile fails 0115's low-correlation limb on the evidence already in hand, before Phase 2
spends anything.

## Limitations that bound the claim

1. **Survivorship in the horizon requirement.** Every event needs 63 trading days of subsequent data,
   so events within 63 days of a name's data end are dropped. Names that stopped trading are
   under-represented, which biases the drift **upward**. The corrected universe's delisted backfill
   mitigates but does not eliminate this. **The +6.6% is an optimistic estimate.**
2. **The surprise proxy is not analyst surprise** (pre-reg §0.2). This measures drift conditional on
   a large *announcement reaction*, not on an earnings *surprise*. It is a weaker and different claim,
   and any Phase 2 inherits it.
3. **`ann_ts` is the intimation timestamp, not the results-release time** (pre-reg §1). The brief's
   "announcement+1 if after-close, decided per event" is **not implementable on this data**. The
   conservative CAR(0,+1) / enter-at-open(+2) convention forgoes day +1's drift to stay leakage-free
   regardless of release time.
4. **Market-adjusted, not beta-adjusted.** No beta estimation; a systematic beta tilt across deciles
   would inflate the spread. Not measured here.

## Reproduce

    python scripts/diag_pead_gate1_0128.py

## Do NOT re-test unless

New data resolves one of the two substantive confounds: an **estimate-based surprise** (SUE) that
separates surprise from announcement reaction, or evidence that the momentum entanglement and
liquidity fragility do not hold on a **forward** sample. Re-running this gate with a different horizon
set, a different decile count, or a different market proxy is relitigation and is refused — the
effect's existence is not in doubt; its *usability* is what failed.
