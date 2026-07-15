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

Still open (next loop pass): a **targeted first-touch preference** (the 4 cases — TATASPONGE, TRENT,
TRIVENI, TIMKEN26 — where the earlier fire PASSED all gates but the harness funded a later blow-off; a
fill-order fix, distinct from drop_rs which also admits noise). Plus the **data-hygiene fix** (CSBBANK/DCAL).

## What this points to (for Phase D/E, measured — not adopted)
1. **Earlier-entry / RS re-timing** (#1) — the biggest, most-cited lever. Measure fresh.
2. **Earlier partial exit** (#2, the giveback fix) — measure 1.5R / faster-trail vs the 2R half.
3. **Data hygiene** (#3) — fix CSBBANK bad-tick + DCAL flat-print class (correctness, not alpha).
Each is a separate determinism-gated, decomposed measurement; AI findings are evidence, the portfolio
measurement is the verdict. Winners get the same forensic next (contrast), then `SYSTEM.md` synthesis.
