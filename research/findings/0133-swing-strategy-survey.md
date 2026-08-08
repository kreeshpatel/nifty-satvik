# 0133 — The finfluencer swing-strategy survey: nine tested, none survives

**Date:** 2026-08-06
**Class:** measurement / survey (screen row 18). **`n_trials` unchanged at 138.**
**Standing counts:** screens 18 · sealed opens 1 · n_trials 138.
**Verdict:** **NONE PROMOTABLE.** Nine SWING+POSITIVE strategies from an owner-supplied
finfluencer table were tested as complete systems on one uniform harness with a train/holdout
split. The apparent winner did not survive **specification uncertainty**, which is the new thing
this study found and the reason it is worth reading.

---

## 1. Design

Nine strategies, each implemented as a complete system (own entry, own stop, own exit, from
researched published rules), plus a **random-entry control**. Identical everything else: corrected
PIT Nifty-500 universe, 10 slots, 2% risk, 10% notional cap, 0.25%/leg, RS55 fill ranker,
signal-on-close → buy-next-open.

**TRAIN 2019-01-01..2023-12-31** (selection) · **HOLDOUT 2024-01-01..2026-06-30** (looked at once).

Spec provenance recorded per cell: SOURCED (published rules found) or RECONSTRUCTED (no usable
public spec; canonical reading, flagged).

## 2. The survey result

The random control returned **+9.12% CAGR / Sharpe 0.558 on train** and **−11.07% on holdout**.
Every number below is only meaningful against those.

| strategy | train CAGR | train Sh | holdout CAGR | holdout Sh | vs holdout null |
|---|---|---|---|---|---|
| Supertrend + Pivot (Ranade) | 16.03% | 0.972 | +12.80% | 0.696 | +23.9pp |
| 66 MA + Stoch (RECONSTRUCTED) | 7.11% | 0.438 | +12.34% | 0.632 | +23.4pp |
| Consolidation Breakout | **21.95%** | 1.222 | −5.06% | −0.258 | +6.0pp |
| Flag Breakout | 10.43% | 0.628 | −5.67% | −0.165 | +5.4pp |
| RSI Oversold *(killed 0020/22/24)* | −4.08% | −0.110 | −7.44% | −0.363 | +3.6pp |
| 5 Star RSI (Malkan) | **21.79%** | 1.223 | −8.04% | −0.303 | +3.0pp |
| RSI+MACD+Stoch (RECONSTRUCTED) | 11.68% | 0.770 | −8.59% | −0.468 | +2.5pp |
| *RANDOM CONTROL* | *9.12%* | *0.558* | *−11.07%* | *−0.539* | *0* |
| Triple Supertrend (Sundar) | 11.72% | 0.696 | −15.92% | −0.703 | −4.9pp |
| 44 MA *(daily proxy, see §6)* | −7.64% | −0.215 | −16.52% | −0.668 | −5.5pp |

**The two best train cells were the two worst out-of-sample.** Consolidation Breakout (21.95%,
Sharpe 1.222) and 5 Star RSI (21.79%, Sharpe 1.223) — precisely the pair a "best CAGR" selection
would have chosen — both went negative. **Three cells never beat the random control on train at
all** (Flag 10.43, Karan 11.68, Triple Supertrend 11.72 vs random 9.12), so their train numbers
were never evidence in the first place.

RSI Oversold is negative in both halves — an independent confirmation, on a different book and
timeframe, of the programme's existing triple-kill.

## 3. The apparent winner, dismantled

Supertrend+Pivot was the only cell both selectable on train and positive on holdout. Three
diagnostics then dismantled it.

**(a) The untouched window is weak — but see the CORRECTION below.** 2016-2018 was consumed by
neither train nor holdout:

| window | CAGR | Sharpe | MaxDD |
|---|---|---|---|
| 2016-2018 (never used; survivorship-optimistic) — **CONTAMINATED, see §3a-CORRECTION** | ~~−3.10%~~ | ~~−0.196~~ | ~~−30.9%~~ |
| 2019-2023 train | 16.03% | 0.972 | −23.5% |
| 2024-2026 holdout | 12.80% | 0.696 | −26.6% |
| **FULL 2016-2026 continuous** | **7.46%** | **0.518** | −35.0% |

Per-year, two years carry the entire record: **2017 +41.09%** and **2023 +44.13%**.

### §3a-CORRECTION (2026-08-06, same day) — the 2016 rows are junk and the −3.10% is wrong

A coverage audit run afterwards found the corrected universe carries **only ~21.6 eligible names in
2016**, against ~490 in every other year:

| year | mean eligible names |
|---|---|
| **2016** | **21.6** |
| 2017 | 466.5 |
| 2018-2025 | 489-500 |

The pinned OHLCV cache starts **2017-01-02**; the only 2016 bars come from the delisted-name
backfill, so every "2016" figure in this finding, in the deep dive and in the complementarity run is
computed on a ~21-name, mostly-delisted, wholly unrepresentative universe. **Those rows must be
discarded.**

**Consequence for the claim above.** The genuinely untouched window is effectively **2017-2018, not
2016-2018**. On that window Supertrend+Pivot returned **+41.1% then −28.3%**, i.e. roughly **+0.6%
CAGR — flat, not −3.10%.** The stated figure was wrong and made the strategy look worse than the
data supports.

**What survives the correction:** the qualitative point is unchanged and if anything cleaner — the
strategy was **flat across 2017-2018 and strong across 2019-2026**, so its apparent edge is still
confined to the window used for selection. What does NOT survive is the specific −3.10%, and any
argument resting on the untouched window being *negative* rather than *flat*.

**Also affected:** §6b's correlation matrix was computed over 2016-2026, so one of its 11 annual
observations is the junk year. The headline conclusion is robust to dropping it — it is driven by
2017/2021/2023 being 10/10 positive and 2018/2025 being 0/10, none of which involves 2016 — but the
exact ρ=0.678 should be read as approximate. §4's specification-family table (train and holdout
windows only) and finding 0134 (usable observations begin 2017-01-09) are **not** affected.

**Root cause, for the next session:** `corrected_universe()` silently spans a wider date range than
the pinned cache because the backfill reaches further back. Any study starting before 2017-01-02
must assert a minimum eligible-universe count per period, or it will silently compute on a handful
of delisted names.

**(b) The named indicator is inert.** Leave-one-out on train: all three legs 16.03% ·
**drop Supertrend 16.17%** (removing it *improves* the result) · drop EMA200 6.78% ·
drop pivot cross 2.61%. "Supertrend + Pivot" is an **EMA200 + pivot-breakout** system.

**(c) The parameter surface is chaotic, not a plateau.** Train CAGR over ATR-multiplier × target-R
spans 13.13% to 30.73% with no smooth structure and the published (2.0, 2.0) cell sitting mid-field
at 16.03%. Cost sensitivity is **non-monotone** (0.15%/leg → 15.49%, 0.25%/leg → 16.03%), and ADV
banding also raises CAGR above the unrestricted run. All three point the same way: **book-level
results here are composition-noise dominated**, so any single configuration's number is unstable.

Two findings do survive as useful, and both are negative-space results that save future work:
- **The stop and target are already well placed.** Target exits ran to only +2.20R median before
  reversing (trailing would harvest almost nothing), and winners took −0.40R median heat with p10 at
  −0.89R (tightening toward 1R would kill ~10% of winners). The two obvious "improvements" are
  closed before being spent on.
- **It is capacity-robust**: ADV 0-10cr 21.49% · 10-50cr 22.56% · 50cr+ 19.75%. It does not depend
  on illiquid names.

## 4. THE FINDING — specification uncertainty is a multiplicity axis

The published pivot rule is stated inconsistently across sources: "price must cross above a pivot
point" in one, and "the daily candle closes above the **R1** level", with pivots "based on the
**previous day's** high, low and close", in another, plus a stated conservative variant requiring
the candle to exceed the prior bar's high. The survey implemented **one** reading — the monthly
central pivot. Pricing all four:

| reading | 2016-18* | train | holdout |
|---|---|---|---|
| monthly central pivot P *(what the survey ran)* | −3.10% | **+16.03%** | **+12.80%** |
| daily central pivot P | +3.49% | −0.91% | −13.34% |
| **daily R1 — the SOURCED reading** | +6.76% | +4.96% | **−8.42%** |
| daily R1 + prior-high confirm | +0.12% | −3.76% | −8.65% |
| **family mean** | **+1.82%** | **+4.08%** | **−4.40%** |

**One reading of four works, and it is not the sourced one.** The readings disagree in *sign*
window by window with no consistency — monthly-P is the worst reading in 2016-18 and the best in
both later windows. A real mechanism would show through every reasonable reading of the same rule;
this shows through exactly one.

At the family mean the strategy's holdout is **−4.40%**, i.e. **+6.7pp over the −11.07% null** —
statistically indistinguishable from Consolidation Breakout (+6.0pp) and Flag Breakout (+5.4pp).
**Once specification uncertainty is priced, the survey's standout rejoins the pack.**

**Law (new, method class):** *Testing one reading of an ambiguously-specified external rule is a
hidden multiple comparison. The unit of evidence is the FAMILY of reasonable readings, not the
reading you implemented.* Where a published rule admits several faithful readings, price them all
and report the family; a result that survives only one reading is a specification lottery ticket.

This is the third time in one session that an external strategy's published spec differed
materially from the pasted/assumed one (0132's RS55-vs-RS14 and RSI-50-vs-60 being the first two),
which is what motivated looking here at all.

## 5. Hybridisation made it worse — a fresh Law III receipt

On the survivor, with overlays that had each shown an independent drawdown benefit earlier:

| variant | train CAGR | holdout* CAGR | holdout* MaxDD |
|---|---|---|---|
| base (survivor, unchanged) | 16.03% | +12.80% | −26.6% |
| + Nifty>200DMA regime | 9.28% | +9.81% | **−14.2%** |
| + RS55>0 | 14.37% | −4.59% | −38.9% |
| + both | 8.92% | −3.31% | −21.0% |

Every overlay subtracted return. The RS55 filter cost **−17.39pp** of holdout CAGR — the third
wrong-signed relative-strength result of the session (0132's rank-IC −0.0227 and its inverted
top-quintile being the first two). Only the regime filter bought anything real, and it bought
**Law VII's trade**: −12.4pp of drawdown for ~3pp of CAGR. Not a promotion; an owner risk
preference.

## 6. Caveats stated against the study's own conclusions

- **The 44 MA cell does NOT indict the live book.** The table's "44 MA" was implemented as a
  *daily* 44-SMA pullback. The live swing book is the **44-WEEK** SMA on weekly bars with the whole
  0093/0094 apparatus. Different instrument; the 3-day median hold shows the daily proxy simply
  churns. No inference about the live book is licensed by this row.
- **66 MA + Stochastic beat its train result out of sample** (7.11% → 12.34%) but ranked *below the
  random control* on train, so it was never selectable. Its holdout success is unselectable luck,
  not a result — and its spec is RECONSTRUCTED, since no public rule set was found.
- **11 of the table's 22 POSITIVE strategies are intraday** and were not tested at all: the repo
  holds daily and weekly bars only. That is a coverage gap, not a verdict.
- **Two specs (66 MA + Stochastic, RSI+MACD+Stochastic) are RECONSTRUCTED**, so their cells test the
  canonical reading, not a verified published rule. By §4's own law, both are single readings of an
  unspecified rule and should be read as such.
- **Every window is now spent** — train and holdout by the survey, 2016-2018 by the deep dive. No
  unused history remains for this family.

## 6b. There is nothing to switch to — and "bad years" are not bad market years

The owner asked whether bad years could be detected and a different system substituted in them.
Rather than restate the regime-switch kills (O-001, 0056, 0086, 0090, **0103: switch not learnable
OOS, static blend dominates**), the prior question was measured: *do these nine strategies actually
have different good and bad years?*

**Annual-return correlation across the nine, continuous 2016-2026: mean pairwise +0.678, median
+0.692, min +0.296, max +0.938. ZERO of 45 pairs are negatively correlated.** The years are
all-or-nothing: **2017, 2021 and 2023 were 10/10 positive; 2018 and 2025 were 0/10.**

**The decisive detail — the premise is inverted:**

| year | strategies positive | Nifty-50 |
|---|---|---|
| 2018 | **0/10** | **+3.2%** |
| 2025 | **0/10** | **+10.5%** |
| 2026 | **5/10** | **−8.7%** (the only down year) |

**Every strategy lost money in two years when the index rose, and half of them made money in the
one year the index fell.** Conditioning on market direction is therefore not merely unhelpful here,
it is wrong-signed for this purpose: a "go defensive when the market is negative" rule would have
gated the book OUT of 2026 (when half the strategies worked) and left it fully exposed through 2018
and 2025 (when none did). Per-strategy correlation to the Nifty's annual return is +0.49 to +0.80 —
positive on average, and useless at exactly the years that matter.

**The static blend — the form 0103 says beats a learned switch — buys almost nothing.** Equal
weight across all nine, rebalanced annually, zero fitted parameters: **CAGR +4.77%, 6/11 positive
years, worst year −24.23%**. At ρ≈0.68 there is no diversification to harvest; the blend's worst
year is barely better than its components'.

**Law:** *These nine strategies are one bet wearing nine costumes.* Long-only momentum/breakout
entries on one universe share a single risk factor, and it is **trend persistence, not index
direction** — which is why the good years (2017/2021/2023 broad trending rallies) and the bad years
(2018/2025 trend-break years) do not line up with the index at all. A rotation between them cannot
exist, and the only lever the structure actually offers is **exposure** (cash), at Law VII's price:
the Nifty>200DMA gate bought −12.4pp of drawdown for ~3pp of CAGR, and even that is a poor proxy
because it reads direction rather than persistence.

**On collision:** any future proposal to switch, rotate, or regime-gate *between* strategies in this
family is answered by the correlation matrix, not by re-measurement. A proposal must first
demonstrate a candidate with **negative or near-zero annual correlation** to this set — none of the
nine qualifies, and neither does the random control (+0.664 to the index).

## 7. Next setup

Nothing here is promotable and nothing further should be tested in-sample on this family; the
history is used up. If the owner wants to pursue any of it, the only instrument that can still
generate unbiased evidence is the **forward wall** (`forward/prereg.md`), which is built,
hash-chained and costs nothing but time.

The strongest genuinely-open leads from this arc are structural, not parametric: the **intraday
half of the table** (needs an intraday store) and the **Bajaj 2-hourly daughter timeframe**
(0132 §A4) — both blocked on the same missing data, and both untested rather than disproven.

## 8. Do not re-test unless

1. **A different reading of an already-priced rule** — refused unless it is documented in a source
   and priced as part of the family per §4, never adopted alone.
2. **An intraday bar store exists**, which unblocks 11 untested strategies and the Bajaj daughter
   timeframe. This is the highest-value unlock in the arc.
3. **Forward evidence** accumulates on a logged book.
4. **A fresh, never-touched holdout** — a different market or a genuinely new period.

Re-running any cell here with tuned parameters against these windows is refused relitigation: the
windows are spent, and §3(c) shows the parameter neighbourhood is noise.

## 9. Reproduction

- `scripts/diag_swing_strategy_survey.py` — the nine-cell survey + random control, train/holdout.
- `scripts/diag_swing_hybrid.py` — the hybrid overlays on the survivor.
- `scripts/diag_ranade_deepdive.py` — three windows, trade anatomy, MFE/MAE, leg decomposition,
  robustness surface, cost sensitivity, capacity. Emits `ranade_trades_2016_2026.csv`.
- `scripts/diag_ranade_pivot_variants.py` — the four-reading specification family of §4.

**Process disclosure.** Screen row 18 was appended after the runs (same deviation as row 17, same
consequence: citable for its null, never for a pass). The survey's train/holdout split, the random
control, and the spec-provenance labels were all fixed before running. One amendment was made
before any output was read — the RSI+MACD+Stochastic cell was moved to the canonical oversold-
pullback form on new source evidence, and the superseded run's output was discarded unread.
