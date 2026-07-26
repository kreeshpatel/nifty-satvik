# Forward action plan — from research to real capital (a living, adversarial plan)

Built 2026-07-26 from three web-research streams (robustness/overfitting, survival/sizing, solo-trader
failure/passive-hurdle) + our own findings (0100-0103) + a risk-of-ruin measurement on our returns.
Every claim is sourced or reproducible. **Judged on drawdown-survival and forward/OOS evidence, not
in-sample Sharpe.** This is a framework the owner calibrates to their own numbers — not personalized
financial advice; the capital fraction and DD tolerance are the owner's to set.

## The reframe (why the plan is about structure, not signal)
The whole options/hedge/ML-switch arc (0100-0103) proved the drawdown is **idiosyncratic and can't be
hedged or timed away**. The web research says the same thing from the other side: at ~37 independent
windows with **zero live out-of-sample trades**, no in-sample work adds information, and the honest
benchmark is a **zero-effort factor ETF**, not the Nifty 50. So the leverage is in *how we size and
structure capital*, not another signal.

### The passive hurdle — the benchmark that must be beaten
| Passive option | Realized return | Tax/cost |
|---|---|---|
| Nifty200 Momentum-30 TRI | ~15.2% CAGR (UTI live) | LTCG 12.5%, deferred, ~0 churn |
| Nifty Alpha Low-Vol-30 | ~12.6% 5yr live (~19% since-2005 partly backtested) | same |
| Nifty 500 TRI | 14.85% 10yr | same |

Our in-sample **after-tax ~12-13% sits at or below all three.** The active book pays three haircuts the
ETF never does: overfit shrinkage, manual-execution decay, and a tax wall (~27 rotations/yr → ~all gains
**STCG 20.8% realized yearly** vs deferred **LTCG 12.5%**). Break-even bar: **~3-5%/yr gross alpha just to
match the ETF.** Large-N evidence (Barber-Odean; SEBI 2024: 93% of F&O traders lost money) says retail
*activity itself* is the destroyer. **Pre-committed benchmark = a factor ETF; burden of proof on the
active book.**

## The structure — a Taleb barbell (measured)
Don't tame the concentrated book (proven impossible) — **shrink it**. Majority in a safe/passive core, a
minority satellite in the active book, sized by drawdown budget.

From `scripts/diag_risk_of_ruin.py` on our momentum book (annRet 15.5%, vol 27.1%, hist DD −46%):
- **Bootstrap worst-case DD = −70%** (block-resampled) → plan against **−65 to −70%, not −46%.**
- Kelly leverage f* = 2.46x → half-Kelly 1.23x (full Kelly overbets an in-sample edge — never use it).
- **Satellite fraction = personal total-DD tolerance ÷ stressed book DD, then halved until forward-proven:**

| Tolerance (total capital) | Fraction | Start (halved) | Boot P(breach) |
|---|---|---|---|
| −10% | 14% | **7%** | 0.5% |
| −15% | 21% | **11%** | 0.5% |
| −20% | 28% | **14%** | 0.1% |
| −25% | 35% | **18%** | 0.5% |

Single-name catastrophe (Yes Bank ₹393→₹16, DHFL→0, Adani −60%) is bounded by
`satellite% × max_name_weight`: at 11% satellite + 15% name cap, a name→0 costs **~1.7% of total capital.**
Stops don't fill through gaps — the **position cap**, not a stop, is the defense.

---

## The doable list (what, why, how — prioritized)
Tags: **[M]** measurement (0 trials, safe) · **[D]** owner decision · **[B]** build.

### Tier 1 — before any real capital (cheap, decisive)
1. **[M] PBO/CSCV over the 131-trial history** — quantify how overfit the *program* is (DSR only fixes the
   threshold). *How:* CSCV on the trial return matrix; PBO = P(in-sample-best underperforms OOS median);
   `pypbo` or per Bailey-López de Prado. High PBO → trust every in-sample number less, size smaller.
2. **[M] Active-vs-passive hurdle** — the book net of STCG+costs+execution-haircut vs Momentum-30 /
   Alpha-Low-Vol-30 TRI, 2017-2026. If it doesn't clear the ETF, the rational move is the ETF.
3. **[M] Risk-of-ruin / barbell fraction** — DONE (`scripts/diag_risk_of_ruin.py`); re-run on the *live
   vehicle's* returns once #7 is decided. Owner input: the personal DD tolerance.
4. **[M/B] Close the data debt** — re-anchor baseline_v1 on the corrected+backfilled universe (headline is
   survivorship-inflated; bias scales with hold length).
5. **[M] Cost/tax audit** — reconcile the backtester vs the FY25-26 NSE schedule; confirm STCG 20.8% (incl
   cess), correct STT sidedness. Fixes the yardstick #2 uses.
6. **[M] Parameter-plateau check** — sensitivity surface around 0094; ship the plateau/ensemble, not the
   argmax (the single-best-of-131 cell is the likeliest needle).

### Tier 2 — structure the capital
7. **[D] Decide the vehicle** — swing (0094) vs momentum base/blend. New argument: momentum's validated
   crash defense is **vol-scaling**, which the base has (O-009) but the swing book structurally rejects
   (0095 inverts). The base/blend is more defensible for size.
8. **[D/B] Build the barbell** — passive factor core + active satellite at the halved fraction from #3.
9. **[B] Route the momentum×low-vol blend (0081) to the forward wall** — the one diversifying edge that
   beat the base OOS (1.18 vs 0.86); the free lunch. Certify forward, never an in-sample config change.

### Tier 3 — the operating system (the human is the leak)
10. **[B] One-page recite-able live rulebook + prune accreted overrides** (P2/config-P/discipline caps).
    Complexity → abandonment under stress; cut back toward the clean tested core.
11. **[B] Deviation journal + fill reconciliation** — log modeled-vs-actual fill and every skipped signal;
    reconcile self-reported fills against contract notes (kills optimism bias + measures execution decay).
    **Automate the order so the "scary" (often best) momentum entries fire without discretion.**
12. **[D/B] Kill ladder (sign now, freeze):** 0→−25% normal; −25→−40% watch (verify character, check bugs);
    −42% (backtest max) → cut satellite ½; −55% (stressed) → hard halt to core; time-based → forced review.
    De-grossing locks in losses — survival tool, not profit tool. Thresholds only tighten.
13. **[B] Live edge-decay monitor** — rolling IC/Sharpe trend (factors decay ~58% post-pub; our
    midcap/non-US/illiquid pocket decays slowest, but monitor).

### Tier 4 — standing discipline
14. **Forward-wall-only certification.** No config change goes live on in-sample evidence; quarterly reviews
    only; no peeking between. Expect **lived DD > backtest DD**; a within-sample −46% is *in spec*, not a
    reason to abandon (DALBAR: the average investor lost 848bps in 2024 by capitulating).

## Recommended sequence
**#1, #2, #3 first** — the overfit number, the passive hurdle, the ruin/fraction — together answer *"deploy
real capital at all, and how much."* #4/#5 fix the yardstick they use. Then #7 (vehicle) → #8 (barbell) →
#10-12 (the operating layer) before the first rupee.

## Sources (key)
Deflated Sharpe / PBO / CSCV: Bailey-López de Prado. Momentum crashes: Daniel-Moskowitz (NBER w20439).
Edge decay: McLean-Pontiff; Jacobs-Müller (non-US persistence). Half-Kelly: MacLean-Ziemba-Blazenko (Mgmt
Sci 1992). Barbell: Taleb. Behavior gap: DALBAR QAIB 2024. Retail activity: Barber-Odean 2000; SEBI F&O
2024. India tax: Budget 2024 (STCG 20.8%, LTCG 12.5%). Single-name: Yes Bank / DHFL / Adani-Hindenburg.
Full sourced digests in the research-agent outputs; the OI/tail-hedge digest in
`.claude/skills/_ingested/options_oi_tailhedge.md`.
