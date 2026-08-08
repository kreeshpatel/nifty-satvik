# 0132 — Daily Supertrend(10,3) + RS(14) + RSI(14)>60: NO TRIAL

**Date:** 2026-08-06
**Class:** Gate-0/1/2 measurement (screen row 17). **`n_trials` unchanged at 138.**
**Standing counts:** screens 17 · sealed opens 1 · n_trials 138.
**Verdict:** **NO TRIAL.** The entry carries no cross-sectional edge at the moment it fires; the
owner's exit rule truncates at a median of 8 days and costs consume 90% of a thin gross edge; and
the fill ranker that would carry the population into a capped book has *negative* rank-IC.

**Binds:** this new daily book only. It does **not** bind the live weekly swing book or the 63d
momentum book — and neither of those binds it (see §6).

---

## 1. What was proposed

Owner-supplied, from an external source, as a complete new strategy:

| | rule |
|---|---|
| **Entry** | daily timeframe; Supertrend green **and** RS of Nifty > 0 **and** RSI > 60 |
| **Exit** | any **two** of: Supertrend red · RS of Nifty < 0 · RSI < 60 |
| **Stop** | the Supertrend line, trailing (owner choice) |
| **Book** | live-swing sizing (2% risk) with `max_notional_pct` **0.10**, Nifty-500, fill by RS strength |

Indicator specifications taken verbatim from TradingView (support/solutions/43000634738):
Supertrend `atrLength=10, factor=3` on `hl2` with Wilder-RMA ATR and the documented band ratchet /
flip logic; RSI Wilder(14); RS(14) as the house CRS form `RS / SMA(RS,14) − 1 > 0` where
`RS = close / NIFTY-50 close`, length 14 per owner ("RS 14"). All three are trailing-only functions
of adjusted daily closes, so the construction is PIT-legal with nothing to truncation-test beyond
the OHLCV cache itself.

**Registry confrontation (Gate 0).** `Supertrend` had **zero occurrences** anywhere in the repo — a
genuinely new lever. `RSI` collides with O-005 (REJECT), O-015/0079 (IC≈0 at 63d) and the
triple-killed oversold thread (0020/0022/0024), but every one of those tested RSI as a *ranker* or
as *mean-reversion*; `RSI > 60` as a momentum confirm is opposite-signed and a different role, so
the collision rule permits it under **new formulation**. The RS leg is not new at all — a stronger
form of it is already the live swing book's fill ranker (0093/0094), and 0086 tested
RS-above-its-MA as an entry gate and found no improvement.

## 2. Coverage (Gate 1)

Corrected universe (pinned OHLCV + delisted backfill + alias map) masked to PIT Nifty-500
membership, ≥2019 only. **787 names · 918,560 member-days · 1,854 trading days · mean 495 eligible
names/day.** Warm-up drops 0.1%. No external join, no vendor timestamp, no seam.

Leg prevalence: Supertrend green **54.9%** · RSI>60 **24.8%** · RS>0 **47.2%** · all three **21.9%**.

**Slot pressure.** Fresh triples (condition true today, false yesterday): **39,102 signals, mean
21.5/day, median 19, p90 39, max 129** — against a book with roughly ten seats. The book would fund
well under 1% of its own signals, which makes the fill ranker, not the signal, the strategy. That is
the exact setup Law II governs.

## 3. The entry carries nothing at the moment it fires

Forward returns **date-demeaned** against the same-day cross-section of eligible members (a pooled
mean would confound the signal with the calendar, since the system fires in up-markets by
construction). 95% CIs.

| cohort | 5d | 10d | 21d | 63d |
|---|---|---|---|---|
| **TRIPLE, fresh cross — the actual entry** | −0.02 ± 0.05 | −0.00 ± 0.08 | **−0.00 ± 0.11** | +0.20 ± 0.20 |
| TRIPLE, all state-days | −0.03 ± 0.02 | +0.04 ± 0.03 | +0.17 ± 0.05 | +0.58 ± 0.09 |
| RSI>60 alone | −0.02 ± 0.02 | +0.04 ± 0.03 | +0.14 ± 0.05 | +0.54 ± 0.09 |
| Supertrend green alone | +0.02 ± 0.01 | +0.05 ± 0.02 | +0.06 ± 0.03 | +0.32 ± 0.06 |
| RS>0 alone | −0.03 ± 0.02 | +0.00 ± 0.02 | +0.03 ± 0.03 | +0.13 ± 0.06 |

(pp of excess return, date-demeaned)

Two things follow, and they are different things:

- **Being in the state pays a little; entering it pays nothing.** Every fresh-cross CI straddles
  zero out to 21 days. The state-level edge is concentrated in days *later* in the state's life,
  which is information you cannot trade at the entry.
- **RSI is the whole signal.** ST+RSI (+0.14/+0.58) is indistinguishable from RSI alone
  (+0.14/+0.54); RSI+RS (+0.17/+0.55) likewise. Supertrend and RS are near-redundant to RSI>60.
  The magnitude — half a percentage point over 63 days — is small enough to be exactly what
  O-015 meant by "IC≈0": real, and far too thin to survive a book.

## 4. The per-trade census — where the money actually goes

A flat mean entry edge does **not** settle a trend book, because trend books earn from asymmetric
truncation (cut at the line, hold the tail). So the rules were run as written, uncapped and
unranked — every fresh triple becomes a trade, entry at the next open, stop = the Supertrend line
as of the prior close (PIT), costs 0.25%/leg, 252-day backstop.

| | A — literal (intraday ST stop + 2-of-3 close rule) | B — rule-only (no intraday stop) |
|---|---|---|
| trades | 24,407 | 24,160 |
| win rate | 32.6% | 33.2% |
| **median hold** | **8 days** | **8 days** |
| median stop width | 10.6% | 10.6% |
| meanR gross | +0.060 | +0.071 |
| **meanR net** | **+0.006 ± 0.013** | **+0.018 ± 0.014** |
| median R net | −0.204 | −0.198 |
| p90 R | +0.82 | +0.86 |
| payoff | 2.12 | 2.15 |
| mean net return/trade | +0.08% | +0.23% |
| exit mix | rule 89% · stop 10% · maxhold 1% | rule 99% · maxhold 1% |
| **per-year sign** | **3/8 positive** | **3/8 positive** |

Both CIs straddle zero. At payoff 2.12 the breakeven win rate is 32.05%; the system delivers 32.6%.
**The strategy sits 0.55 percentage points of win rate away from being a coin flip**, and costs
consume 90% of gross expectancy (+0.060 → +0.006).

## 5. Root cause — the exit rule is an RSI(14) rule wearing a coat

This is the mechanism, and it is arithmetic rather than description.

Of all days on which the 2-of-3 exit condition is true, the leg `RSI<60` is one of the two on
**99.9%** of them (`RS<0` 80.1%, `ST red` 70.1%). Because RSI<60 is present in essentially every
exit, *"any two of three" is identically* **`RSI<60 AND (ST red OR RS<0)`**. And `RSI(14) < 60` is
true on **75.2% of all member-days** — it is the resting state of a stock, including a stock in a
perfectly healthy uptrend, because RSI(14) mean-reverts on every two-day pause.

So the binding clause of the exit is a near-permanent condition, and the trade closes at a **median
of 8 days**. A 3×ATR Supertrend stop is **10.6% wide**. An eight-day hold cannot travel 10.6% often
enough to pay for a 10.6% risk unit plus a 0.5% round trip. The tail never forms: **p90 is +0.82R**,
where a trend book needs multiples of R at p90 to survive a 33% win rate.

**Probe: is the 2-of-3 rule what truncates the tail?** Same entry, same intraday stop, exit only
when Supertrend flips red — 13,069 trades, win 36.4%, **median hold 23 days**, net meanR
**+0.148 ± 0.029** (CI excludes zero), p90 **+1.77**, mean net return/trade **+1.61%**. Removing the
owner's exit rule multiplies expectancy roughly 25×. **The exit rule, not the entry, is the value
destroyer** — but note the entry is still flat, so what the probe recovers is trend-following
geometry, not signal.

**Probe: does the RS(14) ranker rescue the population?** This is Law II's only escape hatch — a
capped book funds the top of the RS sort, so if that slice were better the null population would not
matter. It is not.

| RS(14) quintile at entry | n | net meanR |
|---|---|---|
| Q1 weak | 4,882 | +0.001 ± 0.039 |
| Q2 | 4,881 | +0.001 ± 0.024 |
| Q3 | 4,881 | +0.026 ± 0.028 |
| Q4 | 4,881 | +0.011 ± 0.024 |
| **Q5 strong** | 4,882 | **−0.009 ± 0.026** |
| **top 5% by RS** | 1,220 | **−0.017 ± 0.060** |

**rank-IC = −0.0227.** The ranker is wrong-signed: the strongest-RS names are the worst slice
(consistent with `EXT_IS_THE_ENGINE` — strongest RS is also most extended). A capped book fed by
this ranker would be **worse** than the null population it is drawn from. Law II gains a 9th
receipt, and this time the escape hatch is not merely absent but inverted.

## 6. Transferability

Per `transferability-of-verdicts`: this verdict was measured on **its own new daily book** and binds
only that. It does **not** transfer to the live weekly swing book or the 63d momentum book.
Symmetrically, the closed exit-geometry set (0105/0106/0109) and the five pre-entry walls were
measured on the 44-SMA touch funnel and do **not** bind this one — which is why the study was run
rather than refused.

## 7. Next setup

The one genuinely new, CI-clean object produced here is **the Supertrend line as a pure trailing
exit**: +0.148R net over 13,069 trades, median hold 23 days, p90 +1.77R. It is an **exit-geometry**
object, not an entry, and it comes with a warning stamped on it — **3/8 years positive**
(2020 +0.53, 2021 +0.39, 2023 +0.75; 2019, 2022, 2024, 2025, 2026 all negative). It is a
bull-regime engine, and Law VII territory at best.

If it is ever taken further it must be as exit geometry on a book **whose entry has independently
demonstrated edge**. This system's entry has none, so pairing the two here would only be measuring
the exit against noise.

## 8. Do not re-test unless

Re-open only on one of these, stated in a pre-registration:

1. **A different exit that is not a re-tune.** Changing the 2-of-3 thresholds (RSI 60→50, "any one",
   different periods) because they scored better on *this* census is refused relitigation — the
   census is now the thing you would be fitting to. A new exit must be motivated independently of
   these numbers.
2. **An entry whose fresh-cross date-demeaned 21d edge has a CI excluding zero.** That is the bar
   this entry failed, and it is the cheapest possible re-test.
3. **A fill ranker with demonstrated positive rank-IC on this funnel.** The RS ranker is −0.0227; a
   capped book cannot be proposed until something sorts these trades correctly.
4. **A different book shape** with its own capital and its own seat count — not a shared pool
   competing for the existing book's five seats (that path is closed by 0131's mechanism).

## 9. Reproduction and process disclosure

- `scripts/diag_supertrend_system.py` — coverage, leg prevalence, slot pressure, date-demeaned edge.
- `scripts/diag_supertrend_census.py` — the uncapped per-trade census, both stop readings, and the
  two probes. Emits `diagnostics/research/supertrend_census_{literal,ruleonly}.csv`.

- `scripts/diag_supertrend_portfolio.py` — the AmiBroker-equivalent portfolio backtest (slot cap,
  PositionScore ranker, sizing, compounding) and the retail→honest attribution waterfall.
- `scripts/diag_supertrend_bajaj.py` — the researched-spec attribution grid (addendum below).

**Process deviation, disclosed.** The screen-ledger standing rule is that a row is appended
*before* the screen runs. This arrived as an owner strategy paste and the Gate-0/1 measurement ran
as exploration before its screen nature was recognised; row 17 was therefore appended **after** the
run. The consequence is stated and enforced: **this study may be cited for its NO-TRIAL / null
conclusion, and may not be cited as a PASS for anything.** Two literal readings of the stop and two
labelled mechanism probes were run — no threshold, period, or parameter was searched.

---

# ADDENDUM (2026-08-06, same day) — the pasted rules were NOT the published strategy

The owner challenged the verdict against a remembered ~20% backtest and asked for an AmiBroker-style
portfolio test. Both parts of the challenge were substantially correct and are recorded here.

## A1. The §1–5 verdict was answering a per-trade question; the claim was about an equity curve

`scripts/diag_supertrend_portfolio.py` reproduces the disputed object directly — slot cap,
PositionScore ranker, position sizing, compounding. **Waterfall on the rules as pasted,** one
accounting knob at a time, retail → honest:

| step | CAGR | Sharpe | MaxDD | Δ CAGR |
|---|---|---|---|---|
| 1 RETAIL: survivor universe, 0.03%/leg, **2020-2023** | **+8.12%** | 0.436 | −54.3% | — |
| 2 + full period 2019-2026 | −3.93% | −0.037 | −55.6% | **−12.05pp** |
| 3 + honest costs 0.25%/leg | −12.01% | −0.385 | −72.2% | **−8.09pp** |
| 4 HONEST + survivorship-corrected PIT universe | −6.61% | −0.216 | −53.5% | **+5.40pp** |

Zero-cost upper bound on the honest panel: **−3.45%**. Even the maximally flattering configuration
(step 1) yields 8%, not 20% — so costs and survivorship alone cannot manufacture the claim, and the
**test window is the largest single knob at −12.05pp**.

**Recorded against interest:** the survivorship correction *helped* by +5.40pp here (step 3→4). The
corrected universe changes fill order and admits names the pinned cache lacks; the survivor-only
panel is not uniformly optimistic on this funnel. This cuts against the study's own narrative and is
reported for that reason.

## A2. The pasted images are a degraded version of the published strategy

Web research on the source (Vivek Bajaj / StockEdge "RS55") found **six** material differences from
the two pasted rule cards:

| # | pasted | published |
|---|---|---|
| 1 | "RS of Nifty > 0", read as CRS length 14 | **RS55** — 55-bar outperformance vs Nifty, zero-centred |
| 2 | RSI > 60 | **RSI > 50** |
| 3 | exit uses the same RS | exit uses **RS21**, a different period from entry's RS55 |
| 4 | (absent) | entry also requires **a breakout above the previous swing high** |
| 5 | (absent) | **"only works when Nifty is above its 200 DMA"** |
| 6 | "Timeframe: Daily" | **mother-daughter**: daily = filter, **2-hourly = trigger** |

Two further structural differences are stated by the sources: the strategy is applied to the **F&O
universe**, and it is described as **long the strongest / short the weakest** — not long-only.

## A3. Attribution grid on the corrected parameters

`scripts/diag_supertrend_bajaj.py`, honest panel, 2019-2026, 0.25%/leg, same book (10 slots, 2%
risk, 10% notional cap). Configurations fixed before running; components added in the order the
sources describe them, not searched.

| config | CAGR | Sharpe | MaxDD | trades | meanR |
|---|---|---|---|---|---|
| A as pasted (finding 0132) | −6.61% | −0.216 | −53.5% | 1,222 | +0.040 |
| B RS55, RSI>50, any-of exit (RS21) | +1.11% | 0.163 | −55.5% | 2,258 | +0.028 |
| C B + the 2-of-3 exit form | +4.46% | 0.310 | −45.1% | 784 | +0.094 |
| **D B but RSI>60** | **−12.64%** | −0.457 | −67.9% | 3,122 | +0.025 |
| E B + swing-high breakout (Donchian-20) | +1.65% | 0.189 | −54.3% | 991 | +0.059 |
| F E + Nifty>200DMA regime filter | +3.29% | 0.264 | **−35.7%** | 800 | +0.072 |
| **G F + the 2-of-3 exit = best daily reduction** | **+5.33%** | **0.362** | −35.8% | 469 | +0.109 |

**The RSI threshold is the single largest parameter: 60 vs 50 is worth ~14pp of CAGR (D vs B).** §5's
mechanism was right about *what* was breaking — an RSI leg that fires constantly — but the
programme's own §1 test hard-coded the wrong threshold, taken from the pasted card. The 200-DMA
regime filter is a genuine drawdown lever here (−54.3% → −35.7%), which is notable because O-001
killed regime gating **on the base book** — that verdict does not transfer to this funnel.

## A4. What this changes, and what it does not

**Changed:** §1–5's numbers describe the pasted rules, not the published strategy. The **NO TRIAL**
verdict stands — the best faithful daily reduction is CAGR **+5.33% / Sharpe 0.362** against
baseline_v1's **15.46% / 0.667**, so nothing here is promotable — but the *reason* is now "materially
worse than the incumbent", not "structurally broken", and that is a different and weaker claim than
§5 made. §5's mechanism and §3's flat entry edge were measured on the RSI-60 spec and should be
re-derived before being cited against the RS55 spec.

**Not testable here — stated as gaps, not dismissals:**
1. **The 2-hourly daughter timeframe.** Verified against `data/`: daily and weekly panels only, no
   intraday store. The published entry AND exit both trigger on 2H. This is a hard Gate-1 data
   block, and it is the single largest untested part of the strategy.
2. **Long-short.** Tested long-only.
3. **F&O universe** (~180–220 names) rather than Nifty-500.
4. **"Position buildup on every breakout"** — pyramiding is not modelled.

**Where the remembered ~20% most plausibly lives** (hypotheses, ranked by measured leverage, not
accusations): the 2020-2023 window (−12.05pp measured); near-zero costs (−8.09pp measured); total
return quoted as annual (step 1 is 1.37× over 4 years ≈ 37% cumulative); or a structure we cannot
reproduce — the 2H trigger, the long-short book, or the F&O universe.

**Cheapest way to settle it:** the backtest video references a published trade list. A trade list is
reproducible evidence; a headline number is not. With it, the divergence can be located in one pass
instead of inferred.

**Re-open condition, amended.** Condition 2 of §8 is superseded for the RS55 spec: that entry was
never tested at the fresh-cross level. Testing it is legitimate and is NOT relitigation — it is a
different entry. Conditions 1, 3 and 4 stand unchanged. Standing counts unchanged: **17 · 1 · 138**
(the addendum spends no new screen — it corrects the specification of screen 17, on the same funnel).
