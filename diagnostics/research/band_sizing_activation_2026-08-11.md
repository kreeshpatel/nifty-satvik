# Band-conditional sizing is unreachable at the funding margin — 0.36 activations/year

**MEASUREMENT, DESCRIPTIVE ONLY. Zero trials. Zero screen-ledger rows** — activation counts and an
extension distribution, with **no outcome contrast and no R attached to anything**, which is the same
firewall `diag_eventsize_bound_0129.py` applies to its own mechanism section. Standing counts: read
them from `diagnostics/research/n_trials.json` and `diagnostics/research/label_screen_ledger.md`.

Reproduce: `python pipelines/diagnostics/bound_selectivity.py --validate`, then count
`marginal_pairs` whose best-unfunded name has `ext_vs_sma < 5`.

## Why this was measured before the bound was run

`selectivity_census_finding_2026-08-11.md` established that the near-SMA edge is real in money
(+4.83% of equity per trade below the weekly line against +0.22% at 5–10%) and that the binding
constraint is **price per unit of risk**, not rank: fixed risk over a tight stop demands ~39% of
equity per position against ~10% for an extended one. That pointed at **sizing** — a lever no killed
experiment touched, since 0104, the fill-priority tests, the pool filter and 0110 all acted on
selection, and 0130 priced only the *global* stop-width-independent version.

Running that bound costs a screen-ledger row. Before spending one, the free question: **how often
would the rule fire?**

## It fires twice in five and a half years

| | |
|---|--:|
| train weeks (2019-01-01 .. 2024-06-30) with a funding margin | **53** |
| of those, best UNFUNDED name is near-SMA (<5% ext) | **2** (3.8%) |
| **activations per year** | **0.36** |

For calibration, from the ledger's own record: **0119** failed the gate at ~2.7 activations/year
(15 swaps in 5.5y) and **0129** failed at **2.2/year**, with the finding stating plainly that *"2.2
activations a year cannot carry a rule, and cannot even measure one."*

**0.36/year is six times rarer than the rate already judged unmeasurable.** The bound is therefore
underpowered *by construction*, and spending a screen row to measure two events would be spending
programme multiplicity to learn nothing. **No screen row was appended and no bound was run.**

## Why it is so rare, and this is the part worth keeping

The extension of the best unfunded name at the funding margin:

| | |
|---|--:|
| median | **53.14%** |
| 25th percentile | 28.94% |
| 10th percentile | 17.97% |
| minimum | 0.37% |
| share below 5% ext | **3.8%** |
| share below 10% ext | 7.5% |

Against a touch44 population median of **8.72%**, the contenders at the margin are *six times more
extended than the typical signal*. That is not a coincidence — the contender is by definition the
**highest-CRS unfunded** name, and CRS and extension move together (`corr = 0.3425`; 97% of the >25%
band is top-5 by CRS against 28% below the line).

**So near-SMA names are not losing at the funding margin. They never reach it.** They are eliminated
far earlier, in the CRS ranking, and the margin is contested exclusively between names that are
already very extended.

This refines the census rather than contradicting it. The census measured "funded conditional on
being top-5" and found 0–2% against 57%, which is real. But the *marginal* decision — the one a
sizing rule could act on — is never between a near-SMA name and an extended one. It is between two
extended ones.

## Consequence: the plan changes

The bench's fourth component was built to price band-conditional sizing. It is built, validated
(it reproduces 0119's published −1.29 R/yr exactly through its own code path) and it **will not be
run on this rule**, because the activation count says the answer cannot be measured on this book.

That is the correct outcome of an activation bound and it cost nothing — which is the whole design
of the gate, now 4/4 FAIL with a fifth shape closed before it consumed a row.

**What survives.** The near-SMA edge remains real and remains unreachable, and every route that acts
*inside* this book — selection or sizing — now has a receipt against it. The one route with no
receipt is the one that does not contest this margin at all: **a separate sleeve with its own
capital**, where a near-SMA entry is not competing with an extended one for the same slot. That is
already registered as the Path-B pre-extension proposal for the 2026-10-01 review and is item 08 in
the binder.

## Caveats

- **Train years only.** The sealed slice (2024-07-01 .. 2026-06-30) is untouched; its one permitted
  opening was spent on 0116 S1.
- "Near-SMA" is frozen at **<5% ext**, the census band edge, chosen before this count rather than
  after. At <10% the activation rate is 7.5% of competitive weeks — 0.73/year — still far below the
  rate 0129 called unmeasurable.
- Activation counting says nothing about effect size, and deliberately so: attaching an outcome would
  have made this a screen.
