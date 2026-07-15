# AI per-trade forensic — 104 losers of the 0094 book (Phase B/C memory)

8 AI agents reasoned over every losing trade's chart packet (weekly bars + SMA + RS + earlier-entry
candidates), one trade at a time. This is the accumulated memory. Determinism-gated (1.132/255).

## Headline: the loss engine is ONE mechanism

**~100 of 104 losers are "false-touch blow-offs."** The signal-week LOW wicked into the 7% pullback band,
but the week **CLOSED 10–36% above the SMA (median ~22%)** — i.e. the rule fires on the *week the stock
explodes up off the SMA*, not on a quiet pullback. So the next-week open buys **9–40% extended** with a
**6–28% stop**, and any normal give-back or market wobble becomes a −0.5R to −5R loss.

## Dominant gaps (per-trade, AI-tagged)
| gap | ~count | what it is |
|---|--:|---|
| extended-entry / false-touch (chased the blow-off) | ~55 | bought the explosion week's open, reversed |
| **giveback** (ran +1.3 to +1.9R, never booked, round-tripped) | ~18 | the 2R half-book was unreachable on a wide stop |
| crash-cohort gap-through | ~12 | wide stop + market gap = multi-R (JSL −5.36, COVID-2020, AXISBANK, ATGL-Hindenburg) |
| time-bleed | ~8 | extended entry chopped to the 13-week cap flat/negative |
| whipsaw (first touch after a spent parabola) | ~5 | distribution bounce, not a trend leg |
| pure gap-through (clean entry, gap killed it) | ~2 | RRKABEL −1.96, AXISBANK — execution/sizing, not entry |
| **data-bug** | 2 | CSBBANK, DCAL — see below |

## The three ACTIONABLE mechanisms the AI found (new, specific, testable)

### 1. The RS/slope filter certifies ONE CANDLE TOO LATE — it blocks the good entry and admits the blow-off
Repeatedly (DBL, CANFINHOME, FINCABLES, GSFC, GSPL, HEG, BBTC, BHEL, KPITTECH, MFSL, LATENTVIEW, JYOTHYLAB,
LAXMIMACH, IRCON, TTKPRESTIG, JUBLPHARMA, PRSMJOHNSN, SIS…): a **clean near-SMA green touch fired 1–3 weeks
EARLIER** at ~4–7% risk, but was blocked because **RS was still below its 40-week SMA** (or slope <3%). RS/
slope crossed positive **only on the blow-off week** — so the filters *actively select the extended bar and
reject the pullback.* This is the mechanism behind the owner's "we entered late." **Lever: let the earlier
clean touch fire (re-time / relax the RS-vs-own-SMA gate, or take the FIRST touch when a name fires several
weeks running).** — Phase D experiment.

### 2. The 2R half-book is unreachable on extended entries → the giveback leak
Because the entry is extended, the stop is wide (12–24%), so 2R = +25–48% — **above the realized MFE.** Many
trades ran most of the way there and round-tripped: IPCALAB (MFE +17.8% vs 2R +18.6%), JKPAPER (+29% vs +35%),
KPITTECH, MFSL, UNOMINDA (+1.7R), UPL (+1.9R), ZENSAR×2 (+1.4/1.6R), BHEL (+21.8%), 3MINDIA, FINCABLES.
**Lever: an earlier partial (book at +1.5R, or a faster trail once MFE > 1.5R) salvages this whole cohort.**
— Phase E exit test.

### 2b. The +2R half-book is checked on the WEEKLY CLOSE, not the intraweek high — banked gains are missed
**TRIVENI 2024-08-19** (the agents' "single most fixable defect"): the entry week's HIGH hit ₹512, ABOVE the
+2R target (~₹495) — 2R was reached intraweek — but the half-exit fires only when the weekly **close** ≥ 2R,
and the max close was ~₹480, so **the half never booked and a +24.6% MFE round-tripped to −1R.** Same class:
TCI, TANLA. **Lever: book the +2R half when the weekly HIGH crosses 2R (a resting limit), not the close.**
This is a pure capture-what-we-earn fix, not a "make it safer" filter. — Phase E exit test.

### 3. Data-integrity bugs (python missed these)
- **CSBBANK 2021-07-26**: the signal-week weekly low of ₹274 sits between neighbours that lowed ₹340+ and the
  same bar opened ₹347 — a **bad-tick low** that manufactured a phantom touch (entry was 35% over SMA).
- **DCAL 2017-10-04**: ~16 consecutive weeks of **identical flat ₹300.9 OHLC** (illiquid/carried prints)
  poisoned the 44-SMA and slope → false trend + false touch.
**Lever: validate the weekly low against daily bars; flag dead/flat OHLC runs.** — data hygiene fix.

## Secondary levers the cohort points to
- **Crash/regime**: COVID-2020 (JSL/CANFINHOME/AARTIIND/HONAUT/RATNAMANI/SFL/VBL/GODREJPROP), AXISBANK-2018,
  ATGL-Hindenburg — wide stop + index gap = the −2R to −5R tail. A vol/regime veto or crash-day de-gross.
- **Deep sub-SMA wick → oversized stop**: signal weeks with huge range (VBL low −11%, ZFCVINDIA −12%, BLS −5%)
  set 20–26% stops. A max-range / max-stop guard.
- **Quality/solvency floor**: RELCAPITAL (insolvent ~₹10), RPOWER (spent ₹40 parabola), JETAIRWAYS (bankrupt),
  MANPASAND (accounting fraud) — a price/solvency floor pre-empts the worst.
- **Parabolic-slope tell**: slope >20%/13wk marks a *topping* vertical name whose pullbacks are deep and
  bounces fail (BSE, JYOTHYLAB, ZENSAR, HEG) — down-weight, don't chase.

## Earlier-entry availability (the owner's core question)
A cleaner 1–2-week-earlier near-SMA entry **existed but was skipped in roughly half the losers** — almost
always blocked by the RS-vs-own-SMA gate or the slope gate (occasionally the green-week rule on a red
pullback bar). In the other half the name was chronically extended / in a downtrend and no clean pullback
existed. **So "enter earlier" is real, and its lever is the RS/slope timing (#1), not a new filter.**

## Phase D results (measured on the capped book, pinned, determinism-gated)
| lever | Sharpe | CAGR | MaxDD | verdict |
|---|--:|--:|--:|---|
| base 0094 | 1.132 | 24.7% | −42.4% | — |
| **tp_on_high** (book +2R half on intraweek HIGH, resting limit) | 0.709 | 13.3% | −49.7% | **REJECT** — fixes TRIVENI (−1.0→+1.2R) per-trade but truncates the runners; classic per-trade≠portfolio |
| **drop_rs** (let the RS-blocked earlier touches fire) | 1.095 | 23.8% | −38.9% | **~NEUTRAL** — RS gate does little; ~flat return, 3.5pp shallower DD, but win 59→53% (admits weaker signals). NOT the CAGR boost the stories implied |
| **first_touch** (keep the first fire of a run, skip the later blow-off) | 0.863 | 17.8% | −39.5% | **REJECT** — −0.27 Sharpe / −6.9pp CAGR; the later "blow-off" fire is often the momentum winner, so skipping it removes runners |

**Consistent verdict across all 3 levers:** the AI-found patterns (false-touch blow-off, RS-lag, giveback)
are genuinely present *per trade*, but every fix trades **return for drawdown** — the extended/blow-off
entries and the fat-tail runners are the **same trades**. drop_rs is the only ~neutral one (better DD,
flat return). This reproduces, from a fresh bottom-up loser forensic, the per-trade≠portfolio wall.

Still open (next loop pass): a **targeted first-touch preference** (the 4 cases — TATASPONGE, TRENT,
TRIVENI, TIMKEN26 — where the earlier fire PASSED all gates but the harness funded a later blow-off; a
fill-order fix, distinct from drop_rs which also admits noise). Plus the **data-hygiene fix** (CSBBANK/DCAL).

## WINNER forensic — 42 R≥2 runners, 4 AI agents (the contrast)
Same method, run on the winners to find what separates them from the false-touch losers. The verdict is
blunt and consistent across all 4 batches:

**At the entry bar, most winners are INDISTINGUISHABLE from the losers.** 9 of every ~11 runners were also
extended (>10% over SMA); several were textbook blow-offs with the SAME wide stops that defined the losing
cohort — GMMPFAUDLR (+38% over SMA, 21% stop, 2.73R), AUBANK (+23.6%, 14.7% stop, 2.51R), BAJFINANCE
(+20.6%, 13.3% stop, 2.34R), KALYANKJIL (+25.6%, 18.7% stop, 2.95R), GVT&D (+26%, 2.15R). **Extension and
stop-width do NOT separate winners from losers.** This is why every entry-filter lever rejects.

Three things actually separate them, in order of skill-vs-luck:
1. **Regime dominates (mostly LUCK).** The runners cluster hard in the Mar–Oct 2020 COVID V and the 2021
   bull; almost none fire in a flat/falling tape. GMM & VIPIND are pure survivorship — mechanically identical
   to losers, saved only by the tape. **GAEL is the tell:** the same base-then-thrust setup in the weak
   Jan-2022 tape took −17.6% first-2wk heat and barely scraped 2R. The market, not the entry bar, supplies
   the fuel.
2. **A real pre-touch BASE / pullback into the rising SMA (the REPEATABLE part).** Every high-quality winner
   spent multiple weeks *basing on* or *genuinely declining into* the rising SMA before the signal (repeated
   touch-weeks, or several consecutive down-weeks toward the line): THYROCARE, DIVISLAB, PRESTIGE, HINDZINC,
   APLLTD, ALKYLAMINE, TEAMLEASE, CENTURYPLY, MAZDOCK, BAJAJFINSV, RELCAPITAL, RRKABEL, LINDEINDIA, J&KBANK.
   The losers' "touch" was a **lone blow-off wick descending from far overhead** with NO base underneath. The
   best variants (THYROCARE, DIVISLAB, SUVEN, HAVELLS, WELCORP) actually pierced BELOW the SMA and reclaimed,
   at low extension (5.9–7.3%).
3. **Immediate follow-through / tight signal candle.** Cleanest winners never gave back the entry gain
   (PRESTIGE MAE −0.7, CENTURYPLY −1.2, HINDZINC −1.3, RRKABEL −0.5, IIFL −0.7) and had tight signal candles →
   low risk% (HINDZINC 8.4%, PRESTIGE 8.1%, SAIL 6.4%, IIFL 6.8%). MAE is partly *outcome* not predictor —
   but the tight-candle/low-risk% subset is a genuine PRE-entry quality tell.

**Synthesis — why the wall is the wall:** discriminator #1 is unforecastable, #3 is mostly post-entry, and #2
(base quality) is a chart-pattern the current 4-rule signal does not measure. The false-touch blow-off and
the fat-tail runner are the *same bar* unless you can see the base beneath it. That is the one remaining
testable, non-relitigated lever → the pre-touch base filter below.

## Phase D result 2 — early-MAE cut (test discriminator #3: cut deep-early-drawdown trades)
| lever | Sharpe | CAGR | MaxDD | verdict |
|---|--:|--:|--:|---|
| early_cut 8% / 2wk | 0.588 | 10.8% | −42.9% | REJECT |
| early_cut 10% / 2wk | 0.676 | 13.1% | −47.5% | REJECT |
| early_cut 12% / 2wk | 0.854 | 16.9% | −39.8% | REJECT |
| early_cut 12% / 3wk | 1.032 | 22.1% | −41.2% | REJECT (−0.10 Sharpe, −2.6pp CAGR) |

**Verdict:** cutting deep first-2wk drawdown spares NO net edge — the runners that took −7% to −17% heat and
held (ALKYLAMINE −6.3, APLLTD −12.3, GAEL −17.6, KEC −13.8, GODFRYPHLP −15, KALYANKJIL −9.3, J&KBANK −10.8)
are cut by the same rule that cuts the losers. Confirms discriminator #3 is post-entry / non-separable: the
early heat of a survivor and a stop-out look identical until they resolve. per-trade≠portfolio, 4th time.

## PHASE 1 — ENTRY refinement (owner's staged program: entry → exit → sizing)
Owner directive 2026-07-15: refine the ENTRY first (base indicator = 44-SMA); define WHEN to buy relative to
the SMA (near-SMA / percentile distance), goal = enter EARLY / lower-extension instead of chasing the blow-off.

### The per-trade truth — bucket the 255 base trades by entry extension vs signal-week SMA
| entry ext vs SMA | n | mean R | win% | sumR |
|---|--:|--:|--:|--:|
| 0–5% | 3 | 0.85 | 67% | 2.5 |
| **5–10%** | 20 | **1.12** | **90%** | 22.3 |
| 10–15% | 72 | 0.60 | 65% | 43.5 |
| 15–20% | 62 | 0.60 | 58% | 37.2 |
| **20–25%** | 45 | **0.045** | **47%** | 2.0 |
| >25% | 53 | 0.28 | 51% | 15.1 |

**Near-SMA (<10% ext): n=23, meanR 1.08, win 87%. Extended (≥10%): n=232, meanR 0.42, win 56%.** The owner's
intuition is CORRECT per-trade — naturally-near-SMA entries are far higher quality — BUT only ~9% of fires
are naturally near the line, and the 20%+ blow-offs are near-dead money (47–51% win, ~0 R). Median entry ext
is 17.6%; even R≥2 runners have median ext 15.6% (the fuel comes from extension), losers 19.5%.

### Lever E1 — near-SMA LIMIT entry (rest a buy at SMA×(1+band), fill on a pullback). REJECT — and instructive
| arm | Sharpe | CAGR | MaxDD | win% | tr |
|---|--:|--:|--:|--:|--:|
| base | 1.132 | 24.7% | −42.4% | 59% | 255 |
| band 5% non-strict | 0.261 | 3.2% | −61.2% | 47% | 221 |
| band 5% STRICT (skip if no pullback) | 0.345 | 4.8% | −39.0% | **41%** | 145 |
| band 3% STRICT | 0.033 | −0.9% | −43.3% | **41%** | 126 |

**You cannot MANUFACTURE a near-SMA fill.** Resting a limit at the SMA forces *extended* names to come back to
the line — and the ones that do are the failing ones (falling knives), so win rate collapses 59→41%. The
naturally-near-SMA winners (bucket above) fired the signal *while already* near the line; they are a different
population than "extended name dragged back by a limit." This mechanically explains why "enter near the SMA"
as a pullback rule is the anti-edge in a trend-momentum book: the thrust AWAY from the SMA is the signal.

### Lever E2 — fill-time EXTENSION CAP (skip fills whose open > cap% over SMA; drop the dead blow-off tail)
PIT-safe (the open is observed before the buy). Determinism-gated (off ⇒ 1.132/255).
| cap | Sharpe | ΔSh | CAGR | MaxDD | Calmar | win% | tr |
|---|--:|--:|--:|--:|--:|--:|--:|
| base | 1.132 | — | 24.7% | −42.4% | 0.58 | 59% | 255 |
| 12% | 0.529 | −0.60 | 9.2% | −42.0% | 0.22 | 46% | 202 |
| 15% | 0.969 | −0.16 | 19.5% | −37.9% | 0.52 | 54% | 208 |
| 18% | 0.917 | −0.22 | 18.6% | **−32.5%** | 0.57 | 52% | 217 |
| 20% | 0.941 | −0.19 | 18.9% | −37.3% | 0.51 | 56% | 220 |
| **22%** | 0.983 | −0.15 | 19.9% | **−32.4%** | **0.61** | 54% | 235 |
| 25% | 0.662 | −0.47 | 12.3% | −35.4% | 0.35 | 55% | 239 |

**Verdict: REJECT on Sharpe (every arm below base), but cap 18–22% is a real DEFENSIVE variant** — DD −42→−32
(≈10pp shallower), Calmar 0.58→0.61, at a CAGR cost 24.7→~20%. Same return↔drawdown trade as drop_rs and the
A-only swing decision — NOT a return edge. cap 12% over-cuts (kills the 90%-win 5–10% *and* the solid 10–20%
buckets → win 46%). The fat-tail runners live in the extended buckets too (>25% bucket meanR 0.28, +15 sumR),
so capping trims CAGR alongside DD. This is the 7th independent lever to hit the per-trade≠portfolio wall.

### Lever E3 — near-SMA FILL PRIORITY (fund the closest-to-SMA candidate first under the capital cap)
The 5–10% bucket wins 90%; currently fills go strongest-CRS-first (which funds the extended names first). Does
preferring near-SMA fills — WITHOUT dropping trades or forcing pullbacks — raise quality? Determinism-gated.
| arm | Sharpe | ΔSh | CAGR | MaxDD | win% | tr |
|---|--:|--:|--:|--:|--:|--:|
| base (crs priority) | 1.132 | — | 24.7% | −42.4% | 59% | 255 |
| near_sma priority | 0.330 | −0.80 | 4.8% | −49.5% | 47% | 240 |
| near_sma + ext_cap 22% | 0.780 | −0.35 | 15.7% | −39.7% | 51% | 227 |
**REJECT, and the deepest confirmation yet:** even *prioritizing* the high-quality near-SMA fires (no pullback
forced, no trades dropped) collapses to −0.80 Sharpe — because under the capital cap it **displaces the
CRS-strongest extended names, which are the runners.** The momentum leaders fund the fat tail; any capital
reallocated toward "quality/near-SMA" starves it. The CRS-strongest-first fill order is load-bearing.

### PHASE-1 ENTRY — FINAL VERDICT (8 levers, entry space exhausted)
The owner's "buy near the SMA / enter early" is **correct per-trade** (near-SMA fires win 87% at 1.08R) but
**portfolio-negative every way it can be implemented:**
- **Force it** (near-SMA limit): drags extended names back to the line, fills the failing ones → win 59→41%.
- **Select it** (ext_cap): defensive-only — DD −42→−32, but −Sharpe/−CAGR (trims the fat tail with the dregs).
- **Prioritise it** (near_sma fill order): displaces the CRS-leaders that fund the runners → −0.80 Sharpe.
- **Enter earlier in time** (drop_rs ~neutral, first_touch reject): the later "blow-off" fire IS the winner.

**The extended entry IS the edge** — extension = momentum fuel; the median R≥2 runner enters 15.6% over the SMA,
and the CRS-strongest-first fill order concentrates the fat tail. The base 0094 entry is near-optimal for
return; it cannot be refined upward. **Only shippable entry change = a DEFENSIVE cap (ext_cap ~20%)** — a
robust DD reducer (−10pp DD, holds in both continuous-slice sub-periods: 2022-26 −34→−27, 2017-21 −42→−32),
Sharpe cost −0.15 → a forward-wall candidate (owner decision), analogous to the A-only swing variant. NOT a
config change (fails the +0.10 Sharpe bar). This is the 8th independent lever to hit per-trade≠portfolio.

### Lever E4 — FLAT-BASE / DARVAS-BOX BREAKOUT (owner's GAIL case — an ADDITIVE setup, not a filter)
The owner flagged GAIL 2023: a stock that NEVER pulled back to touch the SMA — it consolidated in a tight
range ABOVE the rising line (~108–133) and let the SMA rise INTO it (a TIME correction), then broke out
+50%. The touch rule (`low<=SMA*1.07`) is blind to it — GAIL's base held 8–19% above the SMA and the low
only grazed the band on one week (filtered by green/RS). **GAIL was never traded.** New cfg-gated ADDITIVE
signal `box_breakout`: a tight base (range<=box_tight) that held ABOVE the SMA for box_len weeks in an
uptrend, then a GREEN close above the box high → buy, stop at the box low. Determinism-gated (off ⇒ 1.132/255).

| arm | Sharpe | ΔSh | CAGR | MaxDD | Calmar | win% | tr | new |
|---|--:|--:|--:|--:|--:|--:|--:|--:|
| base | 1.132 | — | 24.7% | −42.4% | 0.58 | 59% | 255 | — |
| **box 12wk/35%** | 1.073 | −0.06 | 22.2% | **−33.8%** | **0.66** | **59%** | 411 | +156 |
| box 6wk/25% | 0.984 | −0.15 | 21.7% | −34.0% | 0.64 | 58% | 371 | +116 |

**This is the best-behaving lever found — the ONLY one that ADDS trades while HOLDING win rate (59%) and
IMPROVING Calmar (0.58→0.66, DD −42→−34).** And it captures GAIL: the uncapped signal set books
**GAIL 2023-11-07 @ ₹111 = +4.76R** (the exact breakout the owner circled), plus 2023-08-03 +0.18R. Every
other lever traded return for DD or cut trades; this adds a genuinely new *setup class* (time-correction
base breakouts — the MAZDOCK/BAJFINANCE/HINDPETRO/RRKABEL winner archetype the forensic named).

**The catch — NOT sub-period robust (fails the continuous-slice gate):** box12/35 is a big win in the
trending 2017–21 era (Sharpe 1.08→1.47, DD −42→−31) but DEGRADES the choppy 2022–26 era (Sharpe 1.18→0.65) —
base breakouts fail more in chop, and +156 signals crowd the 15-slot capital cap. So the flattering
full-sample Calmar is carried by the bull years. **Verdict: a real, valuable NEW setup (solves the owner's
GAIL gap) but regime-sensitive → forward-wall candidate WITH a choppy-regime guard / separate sleeve sizing,
NOT a blind cfg flip.** The right home is a Phase-3 sizing sleeve (size the box book separately so it doesn't
starve the touch book), or a regime gate — both owner decisions. New cfg lever: `box_breakout/box_len/box_tight`.

### Lever E5 — SWING SETUP LIBRARY (owner's VBL case + "trend/breakout/S-R, all the patterns")
Owner (via VBL 2021-24, another leader that rode ABOVE the SMA and never touched — base traded it 4× and
missed the ₹85→₹650 ride) wants a LIBRARY of swing setups, not just the 44-touch. Built + measured additively,
all determinism-gated (off ⇒ 1.132/255):

| setup | Sharpe | CAGR | DD | Calmar | win% | tr | 22-26 | 17-21 |
|---|--:|--:|--:|--:|--:|--:|--:|--:|
| base (pullback-to-44SMA) | 1.132 | 24.7% | −42.4% | 0.58 | 59% | 255 | 1.18 | 1.08 |
| **#2 box breakout** (E4) | 1.073 | 22.2% | −33.8% | 0.66 | 59% | 411 | 0.65 | 1.46 |
| #3 trend-continuation (pullback to 20wk) | 0.841 | 18.5% | −38.9% | 0.48 | **51%** | 281 | 0.68 | 0.98 |
| #2+#3 combined | 0.870 | 18.0% | −38.3% | 0.47 | 54% | 393 | — | — |

**Verdict: the box breakout is the ONLY additive setup that holds quality; loose trend-continuation REJECTS.**
Trend-continuation catches VBL moves (2018-04 +2.45R, 2021-05 +1.65R) but floods weak signals (2020-01 −4.58R,
several −1R) → win 59→51%. The discriminator is STRUCTURE: the box demands a tight base + a defined stop at
the box low (quality filter); a plain pullback-to-20wk has neither → the near-SMA falling-knife failure again.
Adding #3 to #2 drags box down (1.073→0.870). VBL IS captured by both, but only the box keeps portfolio quality.

**PHASE-1 ENTRY — FULL LIBRARY VERDICT:** of the classic swing patterns, only TWO survive as portfolio-worthy —
the base pullback-touch and the flat-base/box breakout. The box is the keeper (captures GAIL+VBL, holds win%,
better Calmar) but is regime-sensitive (great 2017-21, weak 2022-26) and crowds the 15-slot cap → its home is
a **Phase-3 sleeve** (own capital bucket) routed to the forward wall, NOT a cfg flip. Loose patterns (trend-
continuation, and by extension plain S/R / flag) add weak signals and dilute — pattern-count is not the edge,
structure + defined risk is. Reversal/oversold stays triple-killed (0020/0022/0024). New cfg: `trend_pullback/tp_band`.

### Lever E6 — SUPPORT/RESISTANCE BREAKOUT (setup #4) — LOOKED GREAT, KILLED BY AUDIT
Tested-resistance breakout (prior swing high hit ≥2×, price under it, then a green close above in an uptrend;
stop = 12-wk base low). Determinism-gated (off ⇒ 1.132/255). Raw sweep looked spectacular:
| arm | Sharpe | CAGR | DD | Calmar | win% | tr | 22-26 | 17-21 |
|---|--:|--:|--:|--:|--:|--:|--:|--:|
| base | 1.132 | 24.7% | −42.4% | 0.58 | 59% | 255 | 1.18 | 1.08 |
| sr 12/3% | 1.099 | 24.6% | −34.3% | 0.72 | 58% | 552 | 0.86 | 1.32 |
| **box+sr** | **1.381** | **32.4%** | **−29.2%** | **1.11** | 60% | 541 | 0.93 | 1.79 |

**The box+sr 1.381 / Calmar 1.11 is a MIRAGE — killed by the reproduce-before-trust audit** (a result better
than base is guilty until cleared; construction is PIT-clean — no lookahead — so the flattery is structural):
1. **Absurd stops:** SR risk% median **33%**, max **87.5%** (stop at the 12-wk base low, far below a breakout
   entry). A 33% stop almost never triggers → the 58–60% "win rate" is ILLUSORY (wins on any drift), meanR tiny.
2. **Edge is DEAD recently:** SR-book meanR by year — 2017 1.18, 2020 0.30, 2021 0.23, 2023 0.59, but
   **2024 0.03 / 2025 0.01 / 2026 0.01** (win 40–51%). The full-sample number averages over a fat bull middle;
   no edge in the last 3 years. 2022-26 slice 0.93 < base 1.18 — it DEGRADES the recent, decision-relevant regime.
3. **A different strategy, not a refinement:** 523 of 552 trades are brand-new wide-stop breakout bets, and
   this is ~arm #15 of the session's setup search → the deflated-Sharpe bar is high and this fails the
   sub-period gate outright. **KILL.** (Distinct from #2 box: the box's tight-range + box-low stop keeps stops
   sane and quality real; dropping the tightness constraint here is exactly what let the wide-stop junk in.)

**FINAL Phase-1 setup-library verdict:** of the classic swing patterns, only the base pullback-touch (#1) and
the flat-base box breakout (#2) survive; trend-continuation (#3) dilutes and S/R breakout (#4) is a
bull-amplifier mirage. Pattern-count is emphatically NOT the edge — structure + a SANE defined stop is. The
box is the one keeper (captures GAIL+VBL, real tight stops, holds win%), regime-sensitive → Phase-3 sleeve /
forward wall. Everything looser is the near-SMA/wide-stop failure in a new costume.

### E7 — CHART-VALIDATION corrects the record (owner: "read the actual charts, never kill blind")
Owner pushed back: the box/S/R detectors were built from OHLCV heuristics that were NEVER visually checked, so
neither the box's "regime-sensitivity" nor the S/R "kill" could be trusted. Built `scripts/render_chart.py`
(weekly candles + SMA44/20 + the detector's overlays) and READ the charts. Two verdicts changed:

**Box breakout — the loose detector was momentum-chasing junk; the TIGHT one is real.** Rendering GAIL showed
`box_tight=0.35` firing 7× UP the trend (drawing "boxes" over rising 12-wk windows → "close>box-high" = just a
new high; 20-27% stops). Tightening to a real flat base (`box_len≈8, box_tight≈0.15`) fires only on genuine
consolidations (GAIL's ₹92-103 and the circled ₹105-120 base; VBL's ₹93-107 launch base). Portfolio: the tight
box is **regime-BALANCED** (box8/15%: Sh 1.098, 22-26 **1.07** / 17-21 **1.11**, DD −38, win 56%) whereas the
loose box was carried by the bull (17-21 1.46 / 22-26 0.65). Same headline Sharpe, but now honest and robust —
the loose version's flattering Calmar 0.66 was a bull-market momentum artifact. **The tight box is the keeper.**

**S/R breakout — the "KILL" (E6) was on a BROKEN detector.** Rendering showed the "resistance" was the rising
trailing 12-wk high (not a tested horizontal level) and the stop was the 12-wk low (→33%). Rebuilt properly:
resistance = ≥2 PIVOT HIGHS clustered within 3% (price rejected there repeatedly), green close above, stop 6%
below the level (broken resistance=support). Visually correct on GAIL (level ₹113-118, the 3× rejection the
owner circled). Portfolio with the CORRECT detector (median risk now **13%**, not 33%): **Sh 0.810, win 52%,
22-26 0.87** — honest but BELOW base. So E6's 1.381 was pure wide-stop illusion (stops that never trigger
inflate win rate AND return); the real S/R breakout is a genuine-but-mediocre setup, not an edge. Not a
wrongful kill anymore, not a keeper either.

**Durable lesson:** a detector's portfolio number is meaningless until you SEE that it marks what a human sees
(reproduce-before-trust, extended to chart geometry). `render_chart.py` is now the standing tool for validating
any pattern detector before trusting its backtest. New cfg: `sr_pivot/sr_piv_len/sr_piv_band/sr_piv_stop`.
Corrected setup-library verdict: base pullback + TIGHT box breakout are the two keepers; loose box, trend-
continuation, and (properly-detected) S/R all fall short. The box → Phase-3 sleeve / forward wall.

### E8 — BOX DETECTOR validation gallery (owner: "see it on many stocks first")
`scripts/render_gallery.py` rendered the tight box (8wk/15%) on box-driven WINNERS + LOSERS + known MISSES
(195 box-new trades total). Read the charts; systematic assessment:
| chart | seen | class |
|---|---|---|
| KEI +4.05R | tight ₹1500-1700 base → clean mid-trend breakout → ₹2700 | correct, textbook |
| MCX −2.72R | correct ₹205-225 base + breakout, then COVID gap through stop (later ran to ₹330) | correct, macro-killed |
| ASTRAL −1.69R | REAL box but broke out at the CYCLE TOP after a 3× run → bull trap | correct, late-cycle fail |
| MAZDOCK (miss) | real base but an Apr-22 spike widened the 8wk range >15% → rejected (touch caught it +7.32R) | tightness too fragile |

**Verdict from SEEING (not inferring):** the tight box draws GENUINE consolidations — no loser was a *false*
box. Its losses are the SAME failure modes as the base rule (macro crashes, late-cycle exhaustion breakouts),
not detector error → explains why it lands at ~base quality, not a plateau-breaker. Its MISSES come from one
fixable flaw: a lone prior spike inflates the range test. Two chart-revealed tuning directions (each fixes a
SEEN failure, not param-fishing): (1) **robust/trimmed range** so a single spike doesn't block a real base
(recovers MAZDOCK-type); (2) **late-cycle guard** (don't buy a breakout already stretched far above a longer
MA / near a multi-year high) to avoid ASTRAL-type tops. Tools now standing: `render_chart.py` (single) +
`render_gallery.py` (batch winners/losers/misses). Detector-validation-before-backtest is the workflow.

### E9 — the two chart-revealed box tunings, IMPLEMENTED + TESTED → both REJECTED (and why)
Acted on E8's two directions. Seeing + numeric diagnosis + portfolio measurement killed both:
- **Trimmed/close-range** (fix the MAZDOCK "miss"): the numeric diagnostic showed MAZDOCK never was a box miss —
  its base **dipped BELOW the 44-SMA in Jun-2022** (close ₹117.6 vs SMA ₹127), so the "held above SMA" gate
  correctly excluded it; it's a PULLBACK, caught by the touch rule (+7.32R). Using close-range instead just
  loosens the tightness test → +105 trades, Sh 1.098→1.029, 22-26 1.07→0.87 (the loose-box dilution again). REJECT.
- **Late-cycle run-up guard** (fix the ASTRAL top): rendering showed a 52-wk run-up>150% guard removes the WRONG
  fire — it killed ASTRAL's Aug-2021 (early-cycle, ~winner) and KEPT the Jan-2022 top (its steepest year ended
  Aug-21, not Jan-22). Portfolio: Sh 1.098→0.980. A cycle top is not separable from a valid breakout by 1-yr
  run-up. REJECT.

**Verdict: the plain tight box (box_len=8, box_tight=0.15, hi-lo range, held-above-SMA) is already the best
version — both "obvious" fixes make it worse.** Not every failure has a fix "around it": MAZDOCK is correctly a
touch trade; the ASTRAL/MCX losses are the irreducible late-cycle/macro risks the base rule also carries. This
is the value of see→diagnose→measure over assume: the refinements looked right on the failure charts and were
wrong on the data. New cfg (`box_close_range`, `box_maxrunup`) kept default-off (byte-identical 1.132/255),
recorded as tested-and-rejected. The box stands as-is → Phase-3 sleeve / forward wall.

### E10 — METHOD CORRECTION (owner): judge ENTRIES per-trade (uncapped), NOT the ₹10L portfolio
Owner, mid-Phase-1: the ₹10L / 15-slot cap is a Phase-3 SIZING question; judging entries by the capped
portfolio Sharpe conflates "good entry?" with "was capital free when it fired?". Adding a setup floods the cap
→ good signals skipped for cash → the portfolio number punishes the ENTRY for a SIZING problem. Correct lens =
per-trade expectancy on the UNCAPPED signal set (every signal fills, R capital-independent).

**PER-TRADE EXPECTANCY (uncapped) — overturns the portfolio-based verdicts:**
| setup | N | win% | meanR | medR | PF |
|---|--:|--:|--:|--:|--:|
| TOUCH (base) | 3045 | 46% | +0.159 | **−0.34** | 1.17 |
| **BOX breakout (8/15)** | 655 | 58% | **+0.279** | +0.24 | **1.70** |
| **S/R pivot** | 985 | 50% | **+0.293** | +0.03 | 1.45 |

**The base touch is the WEAKEST entry per-trade** (46% win, median trade LOSES −0.34R, carried by its 20% R≥2
fat tail). The **box (+0.279, PF 1.70) and S/R (+0.293) are markedly BETTER entries** — ~2× the base's
expectancy, median trade a winner. The capped portfolio Sharpe ranked them backwards because the 15-slot cap
starved them — a SIZING artifact, not entry quality. **This overturns E4/E6/E7: the box is not merely
"additive/regime-sensitive," it is a higher-expectancy entry; the S/R pivot is not "mediocre 0.81," it is the
HIGHEST-expectancy entry.** (Prior capped verdicts stand as portfolio/sizing facts, not entry-quality facts.)
Box per-trade meanR by year is positive most years (2021 +0.47, 2023 +0.91) but ~0 in 2024-26 — the entry edge
has faded recently, like everything. **Phase-1 conclusion (corrected): base pullback + box + S/R pivot are all
real, positive-expectancy entries; box & S/R are BETTER than the base touch per-trade. Harvesting them is a
Phase-3 sizing job (slots/sleeves), not an entry-rejection.** All Phase-1 setup evaluation henceforth = uncapped
per-trade expectancy; the ₹10L portfolio is not computed until sizing.

### E11 — THE HIGH-EXPECTANCY CORES (per-trade), and the DEEP NEAR-SMA TOUCH edge (the session headline)
Per-trade expectancy by entry-extension-vs-SMA bucket (uncapped), per setup — locates each entry's edge:
- **TOUCH:** the edge is the DEEP near-SMA touch. ext<5%: N=648, meanR **+1.004**, PF 2.49 (~6× the full-rule
  +0.159). The 5–10% band is a TRAP: N=1092 (largest bucket), meanR **−0.521**, PF 0.65. 10–20% ~+0.32.
- **BOX & S/R:** the edge is in the EXTENDED breakouts (they break out above a base ABOVE the SMA, so high ext
  is normal). Both peak at 20–25% / >25% ext (meanR ~+0.35, PF ~1.9); both weak in the 10–15% zone.

**The deep near-SMA touch (<5% ext) is the strongest, cleanest edge of the whole study — validated 3 ways:**
| CRS-rank tier | near-SMA (<5%) meanR | rest meanR |
|---|--:|--:|
| lowCRS | +0.511 | −0.638 |
| midCRS | +1.338 | +0.157 |
| hiCRS | **+1.603** | +0.190 |

1. **Rank-orthogonal:** near-SMA adds +0.9…+1.4R on top of CRS rank in EVERY tier — even the losing lowCRS tier
   (−0.64) turns POSITIVE (+0.51) when the touch is deep near-SMA. deep-near-SMA × hiCRS = **+1.6R**.
2. **Regime-persistent:** meanR by year +0.37/+3.74/+1.84/+0.63/+1.56/… incl. **+0.92 (2025), +0.95 (2026)**
   on N=231 recent — still working where the box/others faded. Only 2024 negative.
3. **Large sample:** N=648, win 50%, meanR +1.004.

**Interpretation:** the base touch rule's edge IS its deep-near-SMA subset (the genuine pullback/undercut-reclaim
— DIVISLAB/THYROCARE archetype); the 5–10% band and blow-offs are dilution. CAVEAT (unchanged): you cannot
MANUFACTURE near-SMA entries with a limit (falling knives, E1) — but you CAN select/overweight the signals that
naturally fill <5% above the SMA (PIT-safe: the open is observed pre-fill). On the portfolio lens this "rejected"
(cap artifact, E2); on the correct per-trade lens it is the core edge. **Phase-1 hands Phase-3 three ranked
cores: (1) deep-near-SMA touch [+1.0R, best], (2) box breakout extended [+0.3, PF 1.9], (3) S/R extended
[+0.3] — Phase-3 sizing overweights the deep-near-SMA×hiCRS touches (+1.6R) and sizes down the −0.52R 5–10% band.**

## PHASE 2 — EXIT (per-trade lens). Characterization + the giveback-ratchet (first genuine improvement)
### Exit characterization (capped 255 book of record) — where R leaks
| exit | N | % | meanR | meanMFE | capture |
|---|--:|--:|--:|--:|--:|
| time cap (13wk) | 164 | 64% | +1.02 | 2.06R | 49% |
| stop | 66 | 26% | −1.32 | 0.50R | — |
| trail | 19 | 7% | +1.88 | 4.10R | 46% |

Overall we capture only **27%** of the average trade's MFE (0.48R kept vs 1.81R MFE). Structural cause: **the
trail activates only AFTER the 2R half books** — a trade that runs to ~1.8R MFE but never hits 2R has NO trail,
only the stop and the 13wk clock → it rides the cap and gives it back. Giveback quantified: 116 trades reached
≥1.5R MFE, 22% finished <1R (mean giveback 1.54R); of 80 that touched ≥2R intraweek, 26% never booked the half
(the 2R-on-close miss / TRIVENI).

### Exit variants — every BLUNT fix cuts the runners (per-trade meanR)
base +0.481 | trail-before-2R +0.185 (win 59→42%) | tp_on_high +0.322 | lock 2.0→1.0 +0.410 | cap-26wk +0.477.
The base exit's low MFE-capture is the PRICE of letting the fat tail run (19 trail-runners at 4.1R MFE + the
dip-then-recover survivors). Extending the cap is per-trade-neutral → the 13wk clock isn't costing us.

### ★ THE GIVEBACK RATCHET — lock 1.5R once MFE ≥ 2.5R (first genuine improvement of the session)
Surgical MFE-conditional lock-in: raise the stop to en+1.5R only after intraweek MFE reaches 2.5R.
| setting | meanR | Sharpe | 22-26 | 17-21 | win% | PF |
|---|--:|--:|--:|--:|--:|--:|
| base | +0.481 | 1.132 | 1.18 | 1.08 | 59% | 2.20 |
| 2.5R→1.5R | +0.500 | 1.168 | 1.19 | 1.13 | 60% | 2.24 |
| **2.75R→1.5R** | +0.500 | **1.173** | 1.18 | **1.16** | 60% | 2.24 |
| 2.75R→1.75R | +0.497 | 1.170 | 1.18 | 1.15 | — | — |

**Improves every metric (meanR, win%, PF, Sharpe) AND both sub-periods, with DD unchanged (−42.4).** A stable
PLATEAU (2.5-2.75R → 1.5-1.75R all ~+0.500 / Sh ~1.17), not a spike → not overfit. Works where tp_on_high
failed because it RAISES THE STOP but lets the position run — a runner that hits 2.5R and continues to 5R still
captures 5R (the lock never triggers); it bites ONLY when a trade peaks at 2.5R+ then reverses (exactly the
giveback leak). Determinism-gated (`lockin_mfe=0` off ⇒ 1.132/255). **Honest size: SMALL (+0.04 Sharpe /
+0.02R) — below the +0.10 promotion bar → forward-wall / next-version candidate, NOT a blind cfg flip.** But
it's real, robust, mechanism-sound — the giveback fix the forensic (§2/§2b) pointed at, finally landing. New
cfg: `lockin_mfe/lockin_at` (+ tested-neutral `trail_always/trail_after/cap_weeks`).

## PHASE 2 — AI EXIT FORENSIC (5 agents, 95 giveback + 66 stop-out trades) + the AI-derived exit
Agents reasoned over each trade's weekly hold-path (entry→exit + 8 weeks after) to judge the exit. Ranked leaks:
1. **The 13-week TIME CAP is the #1 capture loss** — ~55-60% of "giveback" trades were EXIT_OK_KEPT_RUNNING: the
   cap severed a still-trending winner that ran 4-27R AFTER exit (ALKYLAMINE +2R-half → 27.6R, MAZDOCK → 16.6R,
   NAUKRI → 5.1R, GUJGAS → 4.8R, DIVISLAB → 6.8R). They peaked ON the exit week, close above a rising 20-SMA.
2. **The +2R half-book caps the monsters** (same names — half sold at 2R while the runner went 8-27R).
3. **The true giveback-with-a-tell leak lives almost entirely in TRAIL exits** (~19-35%): the x0.96 20-SMA trail
   is too loose. Tell = a blow-off week closing in its lower third, then 1-2 LOWER weekly closes/highs, while
   still far above the trail. But the trail is ALSO too tight for single-wick shakeouts (IBVENTURES→8.9R,
   RHIM→7.45R, VIPIND→5.3R resumed after being stopped) → cut on a CLOSE break, not a wick.
4. **Loss side mostly irreducible:** only 25% of stop-outs cuttable (median +0.5R); 60%+ gaps/immediate-fails
   where the 20-SMA sits far below the stop and never fires first. Soft-stop only as a confirmed-break exit on
   aged/fading positions, never blanket (whipsaws recoveries) — confirms the mechanical soft-stop REJECT.

### AI-derived exit (hold-while-trending + lower-close tell) — the per-trade≠portfolio split, on the exit
| exit | meanR | win% | PF | Sharpe | tr |
|---|--:|--:|--:|--:|--:|
| base | +0.481 | 59% | 2.20 | 1.132 | 255 |
| no_cap + lh3@2R (lower-close tell) | **+0.622** | 51% | 2.06 | 0.786 | 160 |
| lock-in 2.75→1.5 (keeps cap) | +0.500 | 60% | 2.24 | **1.173** | 254 |

**Removing the cap is a big PER-TRADE win (+0.481→+0.622, +29%) — the AI was right the cap cuts winners — but
the capped Sharpe DROPS (1.13→0.79) because trends held to their end occupy a slot ~2× longer (only 160 trades
complete vs 255). That's a CAPITAL-EFFICIENCY cost = a Phase-3 sizing problem, not an exit failure.** Two honest
results: (a) the lock-in ratchet is the clean adopt-now (better per-trade AND Sharpe, no holding-period cost);
(b) cap-removal + lower-close tell captures more R but needs Phase-3 sizing to pay for the longer holds. New cfg
(all off ⇒ 1.132/255): `lh_arm_r/lh_n/no_time_cap/trendhold_pct` + earlier `lockin_mfe/lockin_at`. NEXT: run the
exit on the FIXED Phase-1 entry (deep near-SMA touch + box + S/R), not the pre-decided 255 (owner directive).

### EXIT on the FIXED Phase-1 entry (owner directive) — surfaces the FILTER-vs-SIZING truth
Reproduced the fixed entry = deep near-SMA touch (ext_cap 0.05, TOUCH-ONLY via origin-aware fill) + box(8/15)
+ sr_pivot, and re-ran the exit on that book (252 trades). Determinism preserved (all off ⇒ 1.132/255).
| exit | meanR | win% | Sharpe | 22-26 | 17-21 |
|---|--:|--:|--:|--:|--:|
| base exit | +0.310 | 56% | 0.764 | 0.72 | 0.79 |
| + lock 2.75→1.5 | +0.341 | 56% | 0.897 | 0.61 | 1.18 |
| + no_cap + lh3@2R | +0.414 | 49% | 0.572 | 0.49 | 0.63 |

**Key finding: the fixed-entry book is WORSE on the capped book (Sh 0.764 vs base 1.132) — and it's a real
result, not a bug.** The deep-near-SMA edge (E11) was measured UNCAPPED (per-signal); on the CAPPED book the
CRS-rank fill ALREADY cherry-picks good touches (incl. strong EXTENDED ones that win), so hard-filtering to
<5% ext (ext_cap) DROPS CRS-strong winners → the book degrades. **This proves E11's own caveat: the deep-
near-SMA edge is a Phase-3 SIZING overlay (overweight the good ones), NOT an entry FILTER — wiring it as a hard
gate is the wrong tool.** So the "fixed entry" for exit-testing is better taken as the setup LIBRARY (touch +
box + S/R) with the near-SMA emphasis deferred to sizing. **The EXIT conclusion is robust across both books:
the lock-in ratchet (2.75→1.5) is the clean improvement (lifts meanR/PF/Sharpe on the fixed book too:
0.764→0.897); cap-removal is per-trade-up / capital-costly everywhere.** New cfg: `ext_cap_touch_only` +
origin-tagged entry_win (0=touch,1=box,2=trend,3=sr) — the foundation Phase-3 sizing needs to weight setups.

**PHASE-2 EXIT VERDICT:** adopt the **lock-in giveback ratchet (MFE≥2.5R → lock 1.5R)** as the exit refinement
— robust, small (+0.04 Sharpe), improves per-trade AND Sharpe on every book, mechanism-sound → forward-wall/
next-version. The bigger capture (cap-removal, +0.14R/trade) is real but a Phase-3 sizing tradeoff (longer
holds). Loss side is irreducible (soft-stop rejected 3×). Exit is characterized; the deep-near-SMA and
cap-removal both route to Phase-3 sizing.

## What this points to (for Phase D/E, measured — not adopted)
1. **Earlier-entry / RS re-timing** (#1) — the biggest, most-cited lever. Measure fresh.
2. **Earlier partial exit** (#2, the giveback fix) — measure 1.5R / faster-trail vs the 2R half.
3. **Data hygiene** (#3) — fix CSBBANK bad-tick + DCAL flat-print class (correctness, not alpha).
Each is a separate determinism-gated, decomposed measurement; AI findings are evidence, the portfolio
measurement is the verdict. Winners get the same forensic next (contrast), then `SYSTEM.md` synthesis.
