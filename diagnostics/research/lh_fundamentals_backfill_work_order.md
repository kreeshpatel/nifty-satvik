# Work order — fundamentals backfill for the recovered-delisted names (LH solvency gate)

**Status: SIGNED OFF AND EXECUTED 2026-07-29.** Probe passed, harvest banked, bracket resolved to a
point estimate. Outcome summary at the end of this file (§5); the binder's §1 stub carries the
decision items. Two of this order's premises were corrected before execution — see §5.

Original framing (retained for the record):

Counts at production: screens 11 · sealed opens 1 · n_trials 138 (this diagnostic spent none).

---

## 1. Why (the triggering measurement)

`scripts/run_corrected_anchor.py --bracket`, full window 2017-01-01..2026-06-30, four arms. Report:
`diagnostics/research/lh_solvency_bracket.json`.

| arm | Sharpe | CAGR % | MaxDD % | after-tax CAGR % |
|---|---|---|---|---|
| pinned | 0.667 | 15.47 | −46.3 | 12.34 |
| corrected AS-IS **(a)** — lower bound | 0.667 | 15.47 | −46.3 | 12.34 |
| corrected GATE-WAIVED **(b)** — naive upper bound | 0.869 | 21.30 | −45.3 | 16.85 |
| GATE-WAIVED, dedup **(c)** — honest upper bound | 0.691 | 15.88 | −47.5 | 12.26 |

- The pinned arm **reproduces `baseline_v1`** (0.667 / 15.47 / −46.3 vs the pinned anchor 0.667 /
  15.46 / −46.26) — the harness is validated against the anchor of record.
- **(a) == pinned exactly**, on the full window as on the smoke window. The corrected universe is a
  strict no-op for the LH book under the current gate: all 104 recovered names are dropped, and
  **only 2 of 104 have any fundamentals rows at all; only 1 has a non-null D/E.** The gate is not
  making an economic judgement about these names — it has no data to judge with.
- The pre-committed rule keys on the **(a)–(b) bracket: ΔSharpe +0.202**, with **197 of 1,373 trades
  (14%) and 788 name-weeks** from recovered names. That is an order of magnitude past the ±0.02 band
  and nowhere near a trivial book-entry count. **The flag does not close → this work order.**
- The decontaminated **(c) bracket is +0.024** — still outside ±0.02, so both readings agree on the
  outcome. (c) is reported as additional information; it was **not** used to re-adjudicate the rule.

**Direction note (important for the memo's methodology section).** Finding 0025 predicts survivorship
correction should *hurt*. Both waiver arms move the LH book *up*. The recovered set is not a set of
disasters: it mixes failures (JETAIRWAYS, MANPASAND, DHFL, RCOM, RNAVAL, GVKPIL, SREINFRA) with PSU
bank amalgamations (ALBK, ANDHRABANK, CORPBANK, DENABANK, ORIENTBANK, SYNDIBANK, VIJAYABANK) and
ordinary M&A/rename exits (LTI, MINDTREE, HEXAWARE, THYROCARE, ISEC, GSKCONS). Delisting is not a
synonym for failure, and the upper bound assumes *every* recovered name clears D/E < 1.5 — which is
precisely the assumption the highly-levered failures in the list would break. **The true value sits
inside the bracket, and the D/E data is exactly what decides where.** That is the whole case for the
backfill: not that the number is wrong, but that we currently cannot tell.

## 2. ~~The defect found underneath the flag~~ — **WITHDRAWN 2026-07-29, see §5**

> **This entire section is wrong and is retained only for the record.** The alias map holds 17
> entries, not 2 (the count read the container object). The byte-identical pairs are those aliases
> materialized deliberately. PIT membership windows are disjoint for 17/17, so no double-counting is
> possible, and no re-cut was performed. Do not act on anything below this line.

The corrected universe **double-counts 16 companies**. A duplicate screen (md5 of the rounded close
series) finds 16 groups where a "recovered" ticker is the **old symbol of a company still listed
under a new symbol already in the pinned universe**, with byte-identical price history:

`360ONE=IIFLWAM · ALIVUS=GLS · BAJAJCON=BAJAJCORP · CIEINDIA=MAHINDCIE · COHANCE=SUVENPHAR ·
EPL=ESSELPACK · ETERNAL=ZOMATO · INDUSTOWER=INFRATEL · NAVA=NBVENTURES · PCBL=PHILIPCARB ·
PGHL=MERCK · PVRINOX=PVR · RHIM=ORIENTREF · SAMMAANCAP=IBULHSGFIN · STLTECH=STRTECH`
plus `LMW=LAXMIMACH`, where **both** tickers sit on the recovered side.

17 of the 104 "recovered" tickers are duplicates; **87 are genuine.** `data/delisted_alias_map.json`
holds only 2 entries, so it is not performing this reconciliation.

Impact: under (b) these let one company occupy two of the same fifteen slots. Only 26 of 197 trades
(119 of 788 name-weeks) are duplicates, yet they carry **+0.178 of the +0.202** uplift — the
contamination is small in count and dominant in effect, because the duplicated names are the strong
ones. **This is why the naive upper bound must not be quoted on its own.**

Not fixed here: choosing which ticker survives a merge, and whether the corrected universe itself is
re-cut, is a governance-class call on the pin. Flagged for September.

## 3. The ask

### Scope
**87 genuinely-recovered names** (the 104 minus the 17 duplicates). The 17 duplicates need **alias
resolution, not fundamentals** — they already have coverage under their current symbol.

<details><summary>The 87 (from <code>lh_solvency_bracket.json</code>)</summary>

8KMILES, AKZOINDIA, ALBK, ALLCARGO, ANDHRABANK, AVANTIFEED, BCG, BHARATFIN, BHARATRAS, CAPF,
COFFEEDAY, CORPBANK, DCAL, DENABANK, DHANI, DHFL, EQUITAS, EROSMEDIA, EXCELCROP, FCONSUMER, FRETAIL,
GARFIBRES, GAYAPROJ, GDL, GEPIL, GET&D, GREENPLY, GSKCONS, GSPL, GUJFLUORO, GVKPIL, HCC, HCL-INSYS,
HEMIPROP, HEXAWARE, HSIL, IBVENTURES, INFIBEAM, INOXLEISUR, ISEC, ITDCEM, JAMNAAUTO, JCHAC,
JETAIRWAYS, JINDWORLD, JPASSOCIAT, JSLHISAR, KENNAMET, KIOCL, LAKSHVILAS, LTI, LTIM, MANPASAND,
MAXINDIA, MFL, MINDTREE, NIITLTD, ORIENTBANK, PEL, QUESS, RCOM, RELCAPITAL, RNAVAL, RUPA, RUSTOMJEE,
SEQUENT, SHANKARA, SOLARA, SPICEJET, SPTL, SREINFRA, STAR, SUVEN, SWANENERGY, SYNDIBANK, TATAMOTORS,
TATAMTRDVR, TATASPONGE, TATASTLBSL, TATASTLLP, TCNSBRANDS, THYROCARE, TIFIN, TMB, TV18BRDCST,
UJJIVAN, ZOMATO
</details>

### Minimal fields (the `value_quality_series` contract, unchanged)
Per name, one row per fiscal period-end, matching `data/fundamentals_pit_screener.pkl` exactly:

| field | why |
|---|---|
| `period_end` | the fiscal date the figures describe |
| **`debt_equity`** | **the gate itself** — the only strictly-required factor |
| `roe` | required: `solvent_universe_mask` re-admits a FINANCIAL with NaN D/E when ROE > 0, and 8 of the 87 are banks/NBFCs |
| `eps_ttm`, `book_value_ps` | carried for schema parity so the store stays one homogeneous object; not consumed by the gate |

**PIT rule (must not be relaxed):** index = `available_date` = `period_end + 90d`, dtype
`datetime64[us]`, matching the existing store. `value_quality_series` joins `merge_asof(direction=
"backward", allow_exact_matches=False)`, so a row is visible strictly *after* its availability date.
A backfill that back-dates availability would manufacture exactly the look-ahead that finding 0017
caught in the macro data.

### Candidate sources
1. **screener.in — recommended.** It is already the production source (`scripts/scrape_screener.py`
   → `fundamentals_pit_screener.pkl`, 654 names / 6,880 rows), so the schema, the 90-day availability
   convention, and the scraper all exist; the backfill is a re-run over a new symbol list, not new
   machinery. It retains pages for many delisted companies. **Risk: coverage is the open question,**
   which is why step 1 below is a coverage probe before any commitment. (Unrelated to the ad-hoc
   quarterly-variance screener pull deleted earlier on authenticity grounds — this is the pinned
   fundamentals path.)
2. **BSE/NSE annual-report archives** — authoritative and survives delisting, but PDF extraction per
   name-year; a fallback for gaps, not a primary route.
3. **Trendlyne / Tijori / Capitaline** — schema mismatch and licence cost; last resort.

### Effort
~1,050 rows (87 names × ~12, the store's median). Reusing the existing scraper: **one session,
roughly 2–3 hours**, dominated by rate-limited fetching and the PIT audit.
1. **Coverage probe first (~20 min):** try 10 names spanning the failure/merger/rename mix
   (JETAIRWAYS, DHFL, MANPASAND, ALBK, MINDTREE, HEXAWARE, THYROCARE, RELCAPITAL, TATAMTRDVR, LTI).
   If coverage is poor, stop and report rather than harvesting a biased partial set — a backfill that
   systematically misses the *failures* would bias the corrected anchor upward, the opposite of the
   correction's purpose.
2. Harvest the 87; write `data/fundamentals_pit_screener_backfill.pkl` (a separate object; the pinned
   store stays untouched until the owner accepts).
3. **PIT audit:** extend `tests/test_macro_pit.py`'s truncation pattern — assert no row is visible on
   or before its `available_date`, and that a truncated store reproduces truncated results.
4. Re-run `--bracket`; the three arms should converge, and the residual (a)→(c) gap becomes the
   *measured* solvency effect rather than a bound.

### What this does NOT authorize
No trials, no screens, no re-anchoring of the pin, no change to `nq/**`, no cron wiring. The harvest
produces data and an audit; the anchor decision stays September's, at quarterly-review class.

## 4. Also settled while the runs were warm

**Swing smoke-vs-full consistency — the sign flips, and the smoke window was unrepresentative.**

| window | pinned | corrected |
|---|---|---|
| smoke 2019–21 | 1.256 / 28.88 / −36.3 | 1.031 / 25.19 / −42.3 |
| **full 2017–26** | **0.830 / 15.91 / −35.0** | **1.132 / 25.21 / −42.4** |

On the truncated window the correction *hurt* the swing book (the 0025 direction); on the full window
it *helps* (+0.30 Sharpe). Do not carry the smoke reading forward — last session's note that the
swing side "shows the 0025 bias direction" holds only on 2019–21. The drawdown penalty is the one
consistent effect (−36 → −42 on both windows).

Separately: **corrected-universe swing = 1.132 Sharpe / 255 trades reproduces the live 0094 golden
master exactly**, confirming the live swing book already runs on the corrected universe. Only the LH
book is pinned to the survivor cache — which is why this conflation bites there and nowhere else.

---

## 5. EXECUTION OUTCOME (2026-07-29)

### Two premises corrected before harvesting
1. **The alias map was never incomplete.** It holds **17** entries, not 2 — the earlier count read
   the container object (`_readme` + `aliases`). `scripts/diag_alias_census.py` confirms with a
   constant-ratio scan: **17 pairs found, 17 already mapped, ZERO novel.**
2. **There is no double-counting.** PIT membership windows are **disjoint for 17/17** pairs, so one
   company can never occupy two of the fifteen slots. The byte-identical series are the mapped
   aliases materialized on purpose. **No re-cut was performed** — the swing census shows a naive
   re-cut would *cost* −0.158 Sharpe by deleting legitimate PIT history under the old name.

Consequently the §2 "defect" in this order is **withdrawn**, and the +0.178 it attributed to
contamination is re-explained: renamed-but-alive companies whose fundamentals sit under the successor
symbol, reachable by an **alias-aware join** rather than a harvest. 13 of the 17 needed no vendor
data at all.

### Probe (stop-clause)
First run reported 0/10 and a triggered stop-clause — that was a **probe bug** (it passed page HTML
to a parser expecting parsed P&L/balance-sheet frames), not vendor absence. Corrected, the probe
**PASSES**: failures 2/4 (JETAIRWAYS 11 periods, MANPASAND 2) vs others 4/6. Failure coverage is
comparable to the rest, so the harvest is not survivor-skewed and the stop-clause does not bind.

### Harvest (`scripts/harvest_fundamentals_backfill.py`, artifact `fundamentals_pit_backfill_20260729.pkl`)
- targets 90 = 86 non-alias recovered + 4 alias successors (ALIVUS, SAMMAANCAP, LMW, PGHL)
- **57/90 with usable rows · 52 with ≥1 D/E period · 621 periods recovered**
- **PIT check 57/57** satisfy `available_date >= period_end + 90d` (the script REFUSES to write on
  any violation)
- **failure-class names: 9/14 with D/E (64%)** — the survivor-skew the stop-clause guards against did
  not materialise
- vendor has nothing for 32 (20 no page, 12 empty) — these **remain gate-excluded** and the memo must
  say so: `8KMILES AKZOINDIA DHFL GEPIL GET&D GUJFLUORO HEXAWARE HSIL IBVENTURES INFIBEAM ITDCEM
  JCHAC LTI LTIM MFL RNAVAL SEQUENT SWANENERGY TATASPONGE TIFIN` (no page) and `BHARATFIN DENABANK
  GSKCONS HEMIPROP KIOCL LAKSHVILAS ORIENTBANK PGHL TATAMTRDVR TCNSBRANDS TMB VIJAYABANK` (empty)
- pin untouched; artifact is dated and sits under the repo's `/data/*` ignore

### The bracket, resolved (`--resolved`, report `lh_anchor_resolved.json`)
| arm (real gate, no waiver) | Sharpe | CAGR % | MaxDD % |
|---|---|---|---|
| pinned (`baseline_v1`) | 0.667 | 15.47 | −46.3 |
| corrected AS-IS | 0.667 | 15.47 | −46.3 |
| corrected + alias-aware | 0.662 | 15.14 | −45.2 |
| **corrected + alias + backfill** | **0.737** | **17.11** | **−49.6** |

**Point estimate ΔSharpe +0.070 · ΔCAGR +1.64pp · ΔMaxDD −3.3pp.** Bounds +0.202/+0.024 retired.
67 of 104 recovered names now carry D/E; **21 passed the gate, 46 were rejected on their real balance
sheets** — the conflation is resolved in the direction it was supposed to be. The correction is
**mixed-signed**: better Sharpe/CAGR, worse drawdown. Conditioned on 67/104 coverage.

### Open owner doors (September)
1. Re-anchor the pin to 0.737 / −49.6, or keep 0.667 / −46.3 with a stated caveat.
2. Whether the alias-aware fundamentals join graduates from harness-side composition
   (`run_corrected_anchor.resolved_store`) into `nq/**` — an engine change with its own golden gate.
