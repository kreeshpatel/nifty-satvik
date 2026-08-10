# The near-SMA edge is real in money, and the book cannot afford it

**MEASUREMENT. Zero trials. Zero screen-ledger rows** — reads `research/substrate/trades.parquet`
(uncapped ledger) and the committed capped export; never the banked label dataset. Standing counts:
read them from `diagnostics/research/n_trials.json` and `diagnostics/research/label_screen_ledger.md`.

Prompted by the owner's HINDALCO observation (signalled at 9.76% extension *after* an +8.74% week,
when the genuine touch was the week before).

Reproduce: `python pipelines/diagnostics/diag_selectivity_census.py --setup touch44`

## 1. The denominator concern is resolved, and it does NOT explain the gradient

`r_denominator_audit.json:305` warned the `<5% ext → +0.717R` core might be a stop-width artifact:
tighter stop → smaller 1R in rupees → bigger R for the same move. Two measurements close it.

| check | result |
|---|---|
| corr(R, % of equity) | **0.98959** |
| median equity-% per R | **2.103** against a fixed-risk expectation of **2.0** |
| median stop width below 10% ext | 5.155 / 5.810 / 5.562 — **not monotone** |

Per-trade risk in this substrate is fixed at 2% of equity, so R and money are proportional by
construction and R carries no denominator distortion at trade level. And within the sub-10% region —
where meanR swings from **+2.088 to +0.094** — stop width is essentially **flat**. The gradient is
not a denominator effect.

**So the near-SMA edge survives in money terms:** below the line is **+4.83% of equity per trade**
against **+0.22%** for the 5–10% band.

## 2. The full census, in both units

| band | N | win% | meanR | **eq%/trade** | stop width | **notional %** | **funded %** |
|---|--:|--:|--:|--:|--:|--:|--:|
| <0 (below line) | 39 | 61.5 | **2.088** | **4.826** | 5.16 | **38.80** | **0.0** |
| 0–5% | 379 | 50.4 | 0.576 | 1.213 | 5.81 | 34.42 | 0.5 |
| 5–10% | 615 | 39.7 | 0.094 | 0.218 | 5.56 | 35.96 | 1.3 |
| 10–15% | 457 | 43.3 | 0.325 | 0.719 | 7.48 | 26.73 | 6.1 |
| 15–20% | 155 | 43.2 | 0.292 | 0.690 | 11.12 | 17.98 | 11.6 |
| 20–25% | 37 | 45.9 | 0.415 | 0.943 | 15.39 | 12.99 | 27.0 |
| >25% | 38 | 42.1 | 0.093 | 0.229 | 19.36 | **10.33** | **55.3** |
| ALL | 1720 | 44.0 | 0.331 | 0.733 | 7.00 | 28.58 | — |

**Funded share runs almost exactly opposite to the edge.** The best band is funded **0.0%** of the
time; the weakest extended band is funded **55.3%**.

## 3. The mechanism, and it is not only the one on record

`EXT_IS_THE_ENGINE.md` attributes the near-SMA band's absence to selection alone: *"because CRS never
ranks them top."* That is real — but it is not the whole story.

| band | top-5 by CRS | funded | **funded GIVEN top-5** |
|---|--:|--:|--:|
| <0 | 28.2% | 0.0% | **0.0%** |
| 0–5% | 39.6% | 0.5% | **1.3%** |
| 5–10% | 65.7% | 1.3% | 2.0% |
| 10–15% | 79.6% | 6.1% | 7.7% |
| 15–20% | 82.6% | 11.6% | 14.1% |
| 20–25% | 97.3% | 27.0% | 27.8% |
| >25% | 97.4% | 55.3% | **56.8%** |

`corr(ext, CRS) = 0.3425` — positive, but far from identity.

**Conditional on already being top-5, the near-SMA bands are still funded 0–2% against 57%.**
Selection cannot explain that residual. The cash gate can, and the arithmetic is exact: per-trade
risk is fixed, so `shares = equity × RISK ÷ (entry − stop)`, and a tight stop therefore buys a
*large* position. A near-SMA entry demands **~39% of equity**; an extended one demands **~10%**.

**The book funds what it can afford, and what it can afford is the extended tail.** Two mechanisms
compound: near-SMA names are ranked lower *and*, when ranked highly, cost ~4× as much to hold.

This is consistent with — and puts a per-band number on — finding **0130**, which measured *"0 of
1,249 tightest-stop signals funded."*

## 4. What this does and does not license

**Does not.** It is not an argument for tightening `ext_cap`. That is finding **0104** (KILL: CAGR
27.2 → 18.9%, because freed cash redeploys into *more, weaker* trades), and the census is consistent
with 0104 rather than contradicting it — a filter changes *which* signals qualify, not what they
cost. Nor does it revive near-SMA fill priority (**−0.802**, proven worse) or pool pre-filtering
(POOL_vs_SELECTION: CRS collapses 1.29 → 0.47).

**Does.** It says the binding constraint on the best band is **price per unit of risk**, not rank.
That is a *sizing* question, and it is a different lever from every killed one, all of which acted on
selection. Finding **0130** already priced global stop-width-independent sizing at **−10.83% equity/yr**
(CI [−26.33, +4.74]), so the naive version is measured and negative. What has not been priced is a
*band-conditional* version — admitting near-SMA entries at reduced notional rather than at full
risk-based size.

**That is the next activation bound to run, and it is free.** It has not been run, and until it is,
this census establishes a mechanism and nothing more.

## Caveats

- **Population, not book.** These are uncapped-substrate per-trade figures. Law II is explicit that a
  population gradient need not survive to the funding margin — 0119, 0121, 0127 and 0129 are the
  receipts, and the gate stands at 4/4 FAIL.
- **N=39** in the `<0` band. Nine years produced thirty-nine of them.
- The top-5 figure is a **proxy**: ranked over the uncapped substrate's trades per ISO week, not over
  `grade_a_entries`' full `entry_win` population.
- **0126 Q2** already split the `<5%` band by hug and came back wrong-signed and underpowered
  (−0.536, CI [−1.493, +0.334]).
