# 0021 — Base selection quality: is the technical selector soft, and why?

- **ID:** 0021 (research/diagnostic). Prompted by the owner: "if the selection engine doesn't
  use technicals well and gives bad trades, then news / other features after selection are
  pointless — they just shorten the list. The main base is very soft; we must make it strong."
- **Registered:** 2026-06-09 (BEFORE the directional run; question + method fixed first).
- **Type:** measurement (rank-IC), no trades/sizing → isolates SELECTION from weighting/exits.
  RELATIVE (ML vs naive) comparisons cancel common-mode survivorship → local read trustworthy.

## Question

The base is the 79-feature LightGBM. Is its stock SELECTION soft because **(a) the model
under-extracts the technical signal** (ML ≈ naive single-technicals → a real lever: build a
stronger selector), or because **(b) technicals are only weakly predictive of direction** (ML
>> naive but still thin live → a ceiling: orthogonal/non-technical signals are the only path),
or **(c) the model overfits** (ML < naive → simplify)?

## Method

Per fold (walk-forward, strong model: 9-yr train, 2019–2025 test, embargo-45), train the
locked-base model, predict on the test slice, and compute the spearman rank-IC of each signal
vs the realized forward target across each day's cross-section (`factor_metrics.
information_coefficient` + `ic_summary`). Signals = model `predicted_return` + naive
single-technicals (return_20d, return_5d, rsi_14, adx_14, bb_pct, ema_21_above_50). Two
targets, because they measure DIFFERENT things:
- `fwd_max_14d` — MAX excursion over 14d ≈ a **volatility** proxy (how much it moves).
- `fwd_return_14d` — close-to-close **directional** return (does it go UP) — the alpha that
  actually trades.

## Result

### Target = fwd_max_14d (excursion ≈ vol) — `selection_quality_local.json`

| signal | IC-IR | mean IC | t | regime (BEAR/CHOPPY/BULL) |
|---|---|---|---|---|
| **MODEL (_pred)** | **1.848** | **0.244** | 76.9 | 1.61 / 1.69 / 2.04 |
| adx_14 | 0.331 | 0.028 | 13.8 | 0.38 / 0.24 / 0.39 |
| ema_21_above_50 | 0.194 | 0.023 | 8.1 | — |
| return_20d | 0.132 | 0.018 | 5.5 | −0.57 / −0.08 / 0.43 |
| rsi_14 / bb_pct / return_5d | ≤0.08 | ~0 | — | — |

**The model's IC-IR vs fwd_max is enormous (1.85) — but this is a RED HERRING.** fwd_max is
the max excursion ≈ volatility; the model (trained to predict fwd_max) is excellent at ranking
"which stocks will MOVE a lot," NOT "which will go UP and be profitable." This is exactly why
a 0.24 IC coexists with a ~49% win rate and thin Sharpe — you can't trade the peak; exits/stops
set the P&L. The honest selection-alpha test is the DIRECTIONAL target below.

### Target = fwd_return_14d (directional) — `selection_quality_directional.json` — DECISIVE

| signal | IC-IR | mean IC | t | regime (BEAR/CHOPPY/BULL) |
|---|---|---|---|---|
| **MODEL (_pred)** | **0.024** | **0.0044** | **1.01** | 0.20 / −0.01 / 0.01 |
| return_20d | −0.089 | −0.011 | −3.7 | −0.26 / −0.18 / 0.01 |
| return_5d | −0.175 | −0.019 | −7.3 | −0.47 / −0.18 / −0.10 |
| rsi_14 | −0.121 | −0.014 | −5.0 | — |
| bb_pct | −0.118 | −0.013 | −4.9 | — |
| adx_14 / ema_21>50 | ~0 | ~0 | — | — |

**VERDICT: the base technical-selector has NO directional alpha (IC-IR 0.024, mean IC 0.004,
t=1.01 ≈ ZERO).** The model ranks VOLATILITY (fwd_max IC 1.85), not direction. Naive price
technicals are NEGATIVELY directional at 14d (return_5d −0.18, return_20d −0.09, rsi −0.12) —
short-term REVERSAL dominates momentum. So:

- The system's thin live edge (~49% WR, Sharpe ~0.45–0.8) is **NOT directional stock-picking**
  — it is a **vol-selection + asymmetric-payoff (convexity)** structure: pick high-excursion
  names, ride a +4%-target/ATR-stop where fat-tailed winners outweigh the slight majority of
  small losses. WR≈49% (coin-flip on direction) is exactly what IC≈0 predicts.
- This is option **(b)/ceiling** for technicals: not "the model under-extracts" (it beats the
  *negative* naive signals by being vol-neutral) — but technicals **carry no positive
  directional signal at 14d** in this large-cap universe. Adding technical features can't
  create directional alpha that isn't there (corroborates the 0004/0002/0010 feature kills).
- **Implication for the program:** a downstream filter/sleeve only helps if it adds
  *directional* IC the base lacks (news/flows/events, or a horizon/structure where direction is
  predictable). A pure list-shortener with no directional IC is near-pointless on this base —
  the owner's instinct confirmed. The validated existing edge is the vol/convexity structure,
  which is real but thin.

### Horizon scan (run bghmo833h, `selection_quality_horizons.json`) — CEILING confirmed

MODEL directional IC-IR by horizon: 7d −0.012, 14d +0.024, 21d +0.045, **30d +0.066** (best);
fwd_max_14d 1.85 (vol). Directional IC is ≈0 at EVERY horizon — a slight positive drift with
longer horizon (short-term reversal → weak long-term momentum) but even the best (30d, 0.066)
is negligible (tradeable wants IC-IR ≳ 0.3–0.5). **No horizon gives price-technicals meaningful
directional alpha.**

## CONCLUSION (definitive)

The base technical-selector is at its **directional ceiling**: ~0 directional IC at all
horizons (7–30d). Its only real skill is volatility-ranking (fwd_max IC 1.85). The engine is a
**vol-selection + asymmetric-payoff (convexity) harvester**, NOT a directional stock-picker;
the thin live edge is structural (WR≈49% coin-flip on direction + winners > losers), and that
is the honest ceiling. **You cannot make the *technical* base directionally strong — the signal
isn't there** (efficient large-caps; short-term reversal, no momentum, at these horizons). This
is WHY 0004/0002/0010 (technical-feature additions) all failed, and why a downstream
list-shortener with no directional IC is near-pointless.

**Implications for "make the base strong" (the strategic answer):**
1. **Non-technical DIRECTIONAL signals** are the only alpha path — flows/events/sentiment with
   directional IC the price-technicals lack. This is exactly the breadth program, REFRAMED:
   every sleeve must be judged on *directional* IC, not just "is it orthogonal." (Value/0018
   KILLed — ep is a 126d slow factor, not 14d directional.)
2. **Better harvest the vol/convexity edge** — largely tested (0016 optimizer, 0013 exposure,
   0007 calibration, 0020 sizing all neutral/killed) → little headroom.
3. **Accept the thin edge** + prove it on the forward wall + invest in product (the 0012 STOP
   posture).
4. **Reversal factor** (the only positive-directional technical: return_5d reversed ≈ +0.17
   IC-IR, but mean IC ~0.019 = tiny, high-turnover, cost-prohibitive; 0014 MR already KILLed it)
   — NOT pursued; the IC is too small to survive costs.

### Confidence-head refinement (run bshnfgo8d, `selection_quality_conf.json`) — a LEAD

0021's "no directional alpha" used the RETURN head (predicted_return, trained on fwd_max=vol).
But the live gate selects on the CONFIDENCE head (P(hit +4% in 14d)). Its directional IC:

| target | return-head IC-IR | **conf-head IC-IR** | best naive |
|---|---|---|---|
| fwd_return_14d | 0.024 | **0.107** | −0.004 |
| fwd_return_30d | 0.066 | **0.142** | 0.029 |

**The GATE is NOT directionally blind** — the confidence head carries **weak-but-positive
directional IC (~0.11 @14d, ~0.14 @30d)**, 4-5x the return head, clearly above the negative/
zero naive technicals. So the model's thin directional skill lives in the conf/gate head, and
it is **~30% stronger at 30d than 14d.** This is consistent with ~49% WR + thin positive Sharpe
(IC-IR 0.11 is real but small — tradeable wants 0.3-0.5).

**LEAD (→ 0022):** the directional signal is strongest at 30d but the live exits cut winners
at +3-5%. Does letting winners run harvest the 30d edge? **Tested → NO (run_exit_ablation.py,
`exit_ablation_local.json`, strong model 2019-2025):**

| arm | med Sharpe | med CAGR | WR | maxDD |
|---|---|---|---|---|
| base (tight exits) | +0.824 | +15.8% | 50% | −13.5% |
| let_run (no trailing/partial, raw target) | +0.486 | +6.3% | 46% | −14.4% |
| let_mid (delay trailing +8%) | +0.952 | +17.9% | 49% | −13.5% |

let_run is WORSE (median Sharpe 0.49 vs 0.82; CAGR 6.3% vs 15.8%) — letting winners run fully
HURTS; the early exits are PROTECTIVE. let_run−base paired CI [−0.41, +0.44] (includes 0);
let_mid is marginally higher but also within noise (7 folds). **Confirms the vol/convexity
thesis: the edge captures the short EXCURSION, not a sustained 30d directional move; the weak
conf-head 30d signal (IC 0.14) is NOT profitably harvestable by holding for direction.** (Also
confirms the TRUE base ≈ medSharpe 0.82 / CAGR 15.8% with a properly-trained model — matches the
locked 0.81; the weighting-ablation's 0.08 was a short-train-window artifact, as caveated.)

## FINAL CONCLUSION (0020/0021/0022 — comprehensive)

- **Weighting/sizing = NEUTRAL** (0020): confidence-sizing is a no-op; not the bottleneck.
- **Base = a short-excursion VOL/CONVEXITY harvester** with WEAK directional skill: return head
  ranks vol (IC 1.85, ~0 directional); conf/gate head has thin directional IC (0.11-0.14, best
  at 30d) — real but too small to hold for. The thin edge (medSharpe ~0.82, WR ~50%) is
  protective early exits on high-vol names, NOT directional stock-picking.
- **Exits ≈ optimal** (0022): letting winners run hurts; tight exits lock the excursion.
- **"Make the base strong":** you CANNOT make the *technical* base directionally strong — the
  signal isn't there (return head 0, conf head 0.14, naive negative) and isn't harvestable by
  holding longer. The only material levers: **(a) NON-technical DIRECTIONAL signals** with
  cross-sectional directional IC the technicals lack (the breadth program, REFRAMED to require
  directional IC — value/0018 already failed this bar); **(b) accept the thin vol/convexity
  edge + prove it on the forward wall + invest in product.** No cheap technical lever remains.
  This is the definitive (negative) map; the next investment decision (build a non-technical
  directional sleeve vs accept+ship) is the owner's.
