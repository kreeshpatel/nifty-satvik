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

## What this points to (for Phase D/E, measured — not adopted)
1. **Earlier-entry / RS re-timing** (#1) — the biggest, most-cited lever. Measure fresh.
2. **Earlier partial exit** (#2, the giveback fix) — measure 1.5R / faster-trail vs the 2R half.
3. **Data hygiene** (#3) — fix CSBBANK bad-tick + DCAL flat-print class (correctness, not alpha).
Each is a separate determinism-gated, decomposed measurement; AI findings are evidence, the portfolio
measurement is the verdict. Winners get the same forensic next (contrast), then `SYSTEM.md` synthesis.
