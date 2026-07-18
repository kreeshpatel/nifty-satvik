# 0094 Bhanushali weekly-swing — the complete system, traced to trade evidence

This is the synthesis of the AI per-trade forensic: 8 agents over all 104 losers + 4 agents over the 42
R≥2 winners of the frozen 0094 book (`scripts/run_bhanushali_weekly_rank.py`, Sharpe **1.132** / CAGR 24.7% /
MaxDD −42.4% / win 59.2% / 255 trades, corrected_universe, determinism-gated). Every rule below is tied to
named trades; every proposed exception was measured on the real engine, not asserted. Companion memory:
[FORENSIC_FINDINGS.md](FORENSIC_FINDINGS.md).

---

## Part 1 — The rules AS THEY ARE (the frozen 0094 signal)

**Universe.** NSE Nifty-500 large+mid, PIT membership, corrected (delisting-backfilled) universe (814 names).

**Signal (weekly bars, decided on the completed weekly close, executed next-Monday open):**
1. **Trend** — 44-week SMA rising: `slope_63 = SMA/SMA[13wk-ago] − 1 ≥ 0.03` (3% over 13 weeks).
2. **Pullback touch** — week's LOW into the band: `wlow ≤ wsma × 1.07` **AND** `wclose > wsma` (closed above).
3. **Quality green** — `close > open`, positive range, close in the upper half of the week's range.
4. **Relative strength** — `RS > SMA40(RS)`, `RS = close / Nifty50`.
   Top-ranked fills by CRS-distance fill first under the capital cap.

**Entry.** Next week's first daily open that prints inside `[signal_wlow, signal_whigh]`.
**Stop.** The signal week's low (initial risk).
**Sizing.** 2% equity risk per trade (`RISK=0.02`), ₹10L paper book.
**Exit.** Half booked at **+2R** (`tp2 = en + 2×(en−st)`), remainder trailed by `20-week-SMA × 0.96`
(4% trail), hard time cap at **13 weeks**.

**Reproduction gate.** Any change is cfg-gated; with defaults off the run is byte-identical (1.132 / 255).

---

## Part 2 — WHY trades win and lose (the AI forensic memory)

### The loss engine is ONE mechanism
**~100 of 104 losers are "false-touch blow-offs."** The signal-week LOW wicks the 7% band, but the week
**CLOSES 10–36% above the SMA (median ~22%)** — the rule fires on the week the stock *explodes up off the
SMA*, not on a quiet pullback. The next-week open therefore buys **9–40% extended** with a **6–28% stop**, so
any normal give-back becomes −0.5R to −5R. (CDSL +23.5% ext, BORORENEW +18%, DBL +24%, COHANCE +23%…)

### The winners fire on the SAME bar — extension is NOT the discriminator
9 of ~11 runners were also extended; several were textbook blow-offs with the same wide stops
(GMMPFAUDLR +38%/21%-stop → 2.73R, AUBANK +23.6%/14.7% → 2.51R, BAJFINANCE +20.6%/13.3% → 2.34R,
KALYANKJIL +25.6%/18.7% → 2.95R, GVT&D +26% → 2.15R). **`entry_ext_vs_SMA` and `risk_pct` cannot separate
winners from losers.** This is the mechanical reason every entry/stop/sizing filter tested rejects.

### What DOES separate them (in order of skill vs luck)
1. **Regime (mostly LUCK).** Runners cluster in the Mar–Oct 2020 COVID V and the 2021 bull; almost none in a
   flat/falling tape. GMM & VIPIND are pure survivorship. **GAEL is the tell:** the identical base-then-thrust
   setup in the weak Jan-2022 tape took −17.6% heat and barely scraped 2R. The tape supplies the fuel.
2. **A real pre-touch BASE / pullback into the rising SMA (the REPEATABLE part).** Every high-quality winner
   spent multiple weeks *basing on* or *declining into* the rising SMA before the signal (THYROCARE, DIVISLAB,
   PRESTIGE, HINDZINC, APLLTD, ALKYLAMINE, CENTURYPLY, MAZDOCK, BAJAJFINSV, RRKABEL, LINDEINDIA, J&KBANK).
   The best pierced BELOW the SMA and reclaimed at low extension (5.9–7.3%). Losers' "touch" was a **lone
   blow-off wick from far overhead with no base underneath.**
3. **Immediate follow-through / tight signal candle** (partly post-entry, but the tight-candle low-risk%
   subset is a pre-entry tell): PRESTIGE MAE −0.7, CENTURYPLY −1.2, HINDZINC −1.3/8.4%-risk, RRKABEL −0.5,
   IIFL −0.7/6.8%-risk.

### Three specific defects the AI found (python missed)
- **RS-lag late entry** — the `RS>SMA40(RS)`+slope gate certifies ONE CANDLE too late: a clean near-SMA green
  touch fired 1–3 weeks earlier at ~4–7% risk (DBL, CDSL, CANFINHOME, CHALET…~20 names) but was blocked
  because RS was still below its own SMA; RS clears only on the blow-off. The filter *selects the extended bar*.
- **2R-on-close miss** — the +2R half books only on the weekly CLOSE, not the intraweek HIGH. TRIVENI hit
  2R intraweek (H512 vs target 495) but closed below → the half never booked and +24.6% MFE round-tripped to
  −1R. Same class: TCI, TANLA.
- **Data bugs** — CSBBANK (bad-tick weekly low ₹274 between ₹340+ neighbours = phantom touch) and DCAL
  (~16 weeks of flat ₹300.9 OHLC poisoning the SMA/slope).

---

## Part 3 — Every proposed fix, MEASURED (the per-trade≠portfolio wall)

Grouped by the owner's staged program. **ENTRY levers are the current phase.**

**ENTRY (Phase 1) — the buy trigger vs the 44-SMA**
| lever | what it encodes | Sharpe | CAGR | MaxDD | verdict |
|---|---|--:|--:|--:|---|
| **base 0094** (chase next open) | — | 1.132 | 24.7% | −42.4% | — |
| near-SMA LIMIT, strict (band 5%) | rest a buy at the SMA, fill on pullback | 0.345 | 4.8% | −39.0% | **REJECT** — win 59→41%, catches falling knives |
| ext_cap 12% | drop fills >12% over SMA | 0.529 | 9.2% | −42.0% | REJECT (over-cuts the good buckets) |
| ext_cap 22% | drop only the dead ≥22% blow-off tail | 0.983 | 19.9% | **−32.4%** | REJECT on Sharpe; **defensive** (−10pp DD, Calmar 0.61) → wall |
| near_sma fill-priority | fund closest-to-SMA candidate first | 0.330 | 4.8% | −49.5% | **REJECT** — displaces the CRS-leaders that fund runners |
| drop_rs | let RS-blocked earlier touches fire | 1.095 | 23.8% | −38.9% | ~NEUTRAL (better DD, win 59→53%) |
| first_touch | keep first fire, skip later blow-off | 0.863 | 17.8% | −39.5% | REJECT (the later fire IS the winner) |
| base_min (pre-touch base) | require a base near SMA before touch | 0.815 | 15.4% | −53.5% | REJECT (DD WORSE) |

_Per-trade truth: near-SMA fires (<10% ext) win **87%** at 1.08R vs extended (≥10%) 56%/0.42R — but only ~9%
of fires are naturally near the line, and the ≥20% blow-offs are dead money (47–51% win, ~0R). The owner's
near-SMA instinct is right per-trade, but (a) it's unmanufacturable — a pullback limit drags extended names
back to the line and fills the failing ones (win 59→41%); (b) as a selection cap it's defensive-only. The
extended entry IS the edge (median R≥2 runner enters 15.6% over the SMA — extension = momentum fuel)._

**EXIT (Phase 2, blocked) / SIZING (Phase 3, blocked)**
| lever | what it encodes | Sharpe | CAGR | MaxDD | verdict |
|---|---|--:|--:|--:|---|
| tp_on_high | book +2R half on intraweek HIGH | 0.709 | 13.3% | −49.7% | REJECT (truncates runners) |
| early_cut 12%/3wk | cut deep first-2wk drawdown | 1.032 | 22.1% | −41.2% | REJECT (cuts survivors too) |

_base_min swept K∈{2,3,4}, L∈{6,8,10,12}, band∈{8,10,12}% — **every arm rejects**, best only 0.815, and
several make drawdown WORSE (K4/L12 → −60.8%). Requiring a pre-touch base does not isolate the winning
subset; it just thins the book, and because regime (not the bar) drives the outcome, thinning drops fat-tail
runners faster than losers._

**Consistent verdict (8 levers, per-trade≠portfolio wall):** the AI-found patterns are genuinely present
*per trade*, but every entry/exit/base fix trades return for drawdown because the extended blow-off entries and
the fat-tail runners are the **same trades**. **Phase-1 entry is exhausted:** the owner's "buy near the SMA" is
right per-trade (near-SMA fires win 87%) but portfolio-negative every way — forced (limit → 41% win), selected
(cap → defensive-only), or prioritised (fill order → displaces the CRS-leaders, −0.80). The extended entry IS
the edge; the CRS-strongest-first fill order is load-bearing. **This independently re-derives, bottom-up from AI
reasoning over every trade, the program's standing conclusion: the entry bar cannot separate winners from
losers — regime does, unforecastable in-sample. 0094 is a plateau; the forward wall is the only certifier.**
Only shippable entry artifact: a DEFENSIVE ext_cap ~20% (−10pp DD, robust across slices) → wall, owner decision.

---

## Part 4 — The exception / false-entry rules the evidence supports (candidate, for the forward wall)

These are the *characterization* rules the forensic supports — none is adopted into the frozen cfg; each is a
forward-wall candidate or a correctness fix. **The portfolio measurement is the verdict, not the story.**

1. **Base-context preference** — prefer a touch with a visible multi-week base at the rising SMA; down-weight
   a lone wide-range blow-off from far overhead. (measured as `base_min` — Part 3.)
2. **Data hygiene (correctness, not alpha)** — reject a weekly "touch" whose low sits far below the same bar's
   open/close AND both neighbour weeks' lows (bad-tick, CSBBANK); flag dead/flat OHLC runs before they feed
   the SMA (DCAL). To implement + verify next.
3. **Regime is the dominant driver** — the biggest tail losses are crash-cohort gap-throughs (COVID-2020,
   AXISBANK-2018, ATGL-Hindenburg); the biggest wins are regime-carried. This is why the forward wall (not an
   in-sample filter) is the only honest certifier.

---

## Provenance
Base of record: 0094 frozen. Forensic: 2026-07-15, session `df0ba614`. All levers determinism-gated
(off ⇒ 1.132/255). n_trials incremented per pre-reg discipline. This doc is characterization + measured
levers; nothing here changes the frozen cfg. The forward wall (`forward/prereg_swing.md`) certifies.
