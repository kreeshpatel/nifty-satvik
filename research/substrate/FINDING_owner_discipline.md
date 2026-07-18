# Finding — the owner's discipline config is FREE: entry/sizing rules cost nothing, only exit truncation kills

*Pre-registered in `research/preregistry_owner_discipline.md`, frozen before the run (R4). Trial
115 → 116. Run: `scripts/run_owner_discipline.py` (2026-07-16). Guards verified byte-identical first
(golden 1.1319/255 · live P2 1.0342/168).*

## The spec

`ext_cap=0.20` (skip any fill priced >20% above the signal-week 44w SMA) + `max_risk_pct=0.10`
(stop = max(week low, entry×0.90)) + `max_notional_pct=0.20` (no name >20% of sizing equity), on the
**unchanged live P2 exit**, 2% risk, all-grades.

Owner framing: *"i dont care even if it gave good returns, then our book is badly traded… max 20 percent
is fine, if more than 10 percent then our R is distorted."* A **risk-appetite** config with a pre-accepted
return cost — not an edge hunt.

## Result — the first non-disaster of the arc

| metric | BASE | SPEC | Δ | |
|---|---|---|---|---|
| Sharpe (full) | 1.03 | **1.11** | +0.07 | noise |
| **2022-26 slice** | **1.29** | **1.21** | **−0.08** | noise |
| CAGR | 21.2% | 21.6% | +0.44pp | noise |
| MaxDD | −34.8% | −33.6% | +1.23pp | noise |
| trades | 168 | 181 | +13 | |
| **median R** | 14.2% | **9.2%** | **−5.0pp** | **structural ✓** |
| **mean hold** | 20.5wk | **12.6wk** | **−7.8wk** | **structural ✓** |
| **notional/name** | 14% | **22%** | **+7.7pp** | **structural ✗** |
| move captured | +8.7% | +6.2% | −2.5pp | |

SPEC sits **+1.9σ of the random null** (0.74, sd 0.24).

## The honest read — "free", not "better"

The full-sample Sharpe (+0.07) and the 2022-26 slice (−0.08) **point in opposite directions**, which is
the signature of noise, not signal. This book is known to be chaotic under fill perturbation (G1 alone
0.47, G2 alone 0.42, G1+G2 together 0.97). At cumulative trial **116**, a +0.07 in-sample delta certifies
nothing and no DSR gate would pass it.

**The correct claim is that the discipline is approximately return-neutral** — which is precisely what the
owner pre-accepted, and considerably better than the expected −0.15 Sharpe.

What IS structural (arithmetic, not sampling):
- **median R 14.2% → 9.2%** — the R cap binds by construction.
- **mean hold 20.5wk → 12.6wk** — 2R at R=9.2% is an 18% move, not 28%. The named defect is fixed.
- **notional/name 14% → 22%** — `notional = risk% ÷ R%`. Guaranteed, and the real cost: the book now
  holds ~4-5 names instead of ~7. The 20% cap contained it; without it, worse.

Trade count *rose* (168→181) despite bigger positions, because shorter holds recycle capital faster.

## Root cause — why this survived when nine prior arms died

**The exit was left alone.** Every killed arm truncated the fat tail:

| arm | what it did to the exit | 22-26 |
|---|---|---|
| 60/40 + Rcap5 + cap20 | 2R/3R targets, no runners | 0.64 |
| 60/30/10 + small candle | 2R/3R + 10% runner | 0.50 |
| candle + live P2 exit | exit untouched, but **selection** gutted (MFE 15% vs 27%) | 0.37 |
| **this spec** | **exit untouched, selection barely touched** | **1.21** |

The unifying law of the whole arc, now stated positively: **the fat tail lives in the exit.** Entry and
sizing discipline is roughly free — you may cap R, cap extension, cap notional, and shorten holds without
paying for it. What you may **not** do is cut the right tail (fixed targets) or select against it
(small-candle filters, extension filters that remove the 69%-of-R buckets).

`ext_cap=0.20` is mild enough not to trigger the `EXT_IS_THE_ENGINE` failure: it trims only the fills
*priced* above +20%, while the 15-25% bucket (the book's largest R contributor, +56.0R) survives almost
intact.

## Recorded caveats (both pre-declared, both held)

1. **The owner's stated mechanism was inverted** — *"R … can create big positions"*. Notional is
   `risk% ÷ R%`, so a **wide** stop makes positions **small**. Capping R made the book **more**
   concentrated (14% → 22%), exactly as predicted. This is why `max_notional_pct=0.20` was added.
2. **`max_risk_pct` breaks the rule it enforces.** The rule says the stop is the signal-week low; the R
   cap lifts it to an arbitrary −10% line. `ext_cap` is the rule-faithful half (pure selection; stop stays
   the candle low). The owner chose both with the trade-off stated — a legitimate owner call, recorded.

## Verdict

**NOT a KILL and NOT a promote.** In-sample return-neutral; the discipline is delivered mechanically at a
concentration cost. **R11 stands: nothing ships in-sample automatically.** This is now an **owner
decision** on a cost/benefit table, not a research question — the research says "it's free, and here is
the concentration you buy with it".

## Next setup

If the owner adopts, the honest route is the one the P2 exit took: an owner-override adoption with the
override recorded (it fails no gate because it was never an edge claim), or the forward wall. The
**unspent** question this raises: if entry/sizing discipline is free and only exit truncation is fatal,
then the sizing layer (Phase 3) has more room than assumed — the arc has never tested a config that
*lowers* risk% to hold notional constant while capping R. That is the deconfounding arm
`FINDING_small_candle` declined to run, and it is now better motivated.
