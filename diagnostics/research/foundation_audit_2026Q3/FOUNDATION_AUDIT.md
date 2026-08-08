# Foundation audit — the input, not the code

**Date:** 2026-08-06 · **Class: VERIFICATION.** Zero trials, zero screens, zero new hypotheses.
**Counts frozen at start and at every commit: screens 15 · sealed opens 1 · n_trials 138.**
Sealed 2024H2+ not opened. Judge log not read.

**Deliverable status: binder input.** Nothing here is corrected, retuned or re-adjudicated. Two
findings could move a published number; both stop at the owner's door with both readings, per the
standing guard.

| Layer | Question | Verdict |
|---|---|---|
| **1 — price truth** | Does the pin report what NSE published? | **CLEAN** |
| **2 — corporate actions** | Is every event adjusted, correctly scaled, on the right date? | **CLEAN** on the census · **1 arithmetic defect** · **1 convention conflict → owner** |
| **2b — series continuity** | Is every discontinuity in the series a real event? | **DEFECT — 7 fabricated price steps, 2 of them new** |
| **3 — atomic trade** | Does one published trade rebuild from raw bars? | **CLEAN — 10/10 fields exact** |

---

## Why this audit exists, and what only it could find

Every number the programme publishes rests on `data/ohlcv.pkl` (pin `dataset-pin-20260701`, sha
`f8625a8f…`), and until now nothing had tested that file against the exchange. The blind
adversarial replication could not: it was handed the same pickle, so any error in the data was
inherited by both sides of the comparison rather than caught by it. Below exchange-published prices
there is nothing left to appeal to, which is what makes this the bottom of the stack.

The audit reaches three sources NSE publishes and this repo had never joined against:

1. **Daily cash bhavcopy**, both URL families (pre-2024 archive and post-2024 UDiFF), for 30
   trading days — one per quarter, 2019Q1 through 2026Q2 — plus every session needed by layers 2
   and 3. Every symbol in the pinned universe that the exchange listed that day is compared, so
   within each sampled date the coverage is a **census, not a draw**: 710 of 710 pinned symbols
   appear, 17,801 name-days.
2. **The corporate-action record** (`/api/corporates-corporateActions`), which enumerates every
   split, bonus and demerger with its ex-date. This makes layer 2 a census of *events* rather than
   a scan for events large enough to notice.
3. **ISIN**, which survives a ticker rename. A ticker-only join reports "no exchange data" for
   every company that changed its NSE symbol — exactly the names most likely to carry a defect, and
   silently. The ISIN fallback recovered **ten** identities: CENTURYTEX→ABREL, TATAMOTORS→TMPV,
   RUCHI→PATANJALI, JUBILANT→JUBLPHARMA, MOTHERSUMI→MOTHERSON, GMRINFRA→GMRAIRPORT,
   MINDAIND→UNOMINDA, FAIRCHEM→PRIVISCL, SUVENPHAR→COHANCE, AMIORG→ACUTAAS. Where these overlap
   the repo's own `data/delisted_alias_map.json` they agree with it, which is a free check on both.
   One recovered pair (KPIT↔BSOFT, the 2019 Birlasoft demerger) is a rename *by scheme of
   arrangement* rather than a pure rename; ISIN continuity is weaker evidence there and it is
   flagged rather than relied on.

Producers, all committed and re-runnable: `scripts/audit_foundation_bhavcopy_2026Q3.py`,
`audit_foundation_prices_2026Q3.py`, `audit_foundation_corpactions_2026Q3.py`,
`audit_foundation_seam_2026Q3.py`, `audit_foundation_atomic_trade_2026Q3.py`. The extracted exchange
rows are committed beside them — every session this audit's published figures depend on — so those
figures re-derive without the network. Rows outside that set were dropped to keep the evidence
proportionate, so a *new* question re-fetches; the scripts do that automatically and idempotently.

---

## Layer 1 — price truth: **CLEAN**

**Sample.** 30 dates × 710 symbols = **17,801 name-days**, 2019-02-15 to 2026-05-15. Zero sampled
name-days where the exchange listed a name the pin lacked.

**The central result is a negative one, and it is the strongest single number in this audit:**

> Across 17,801 name-days, the pinned close is **above** the exchange's raw close on **zero**
> occasions (tolerance 1 basis point).

An adjusted series may sit below raw — adjustments only ever remove value going backwards — but it
can never sit above it. Not one exception in seventeen thousand observations rules out the entire
class of defect in which prices are inflated, mis-scaled upward, or carried from a different
instrument. Anything that made the book look better than reality would have shown here.

**What the pin actually is.** 611 of 710 symbols are vendor-adjusted at their first sampled date;
99 are raw. Median implied factor 0.9816. Exact-to-the-paise agreement on all four of O/H/L/C
occurs on 20.5% of name-days — and that low figure is *expected*, not a failure: exact agreement
happens only where no dividend or split has been declared since, so it is a measure of how recently
each name last had a corporate action, not of price truth.

**Volume is separately confirmed and separately informative.** 14,689 of 17,801 volume readings
match the exchange exactly (82.5%). The 15.8% that differ are not noise: their ratio has a median
of exactly **2.0**, a 75th percentile of exactly **5.0** and a 95th of exactly **10.0**, and the
mismatch rate falls monotonically from 29.1% in 2019 to 1.2% in 2026. Those are split factors, and
that decay is the signature of volume back-adjusted for every subsequent split. Volume is
correct — and, as layer 2b shows, it is correct in a place where price is not.

**Per-symbol reconciliation.** A symbol reconciles when its implied factor is never materially
above 1 and never falls as time advances. **703 of 710 reconcile. Seven do not**, and those seven
are the whole of layer 2b.

*Recorded correction:* an earlier pass of this script also required the factor to equal 1 on the
last sampled date and reported 116 unreconciled names. That criterion was wrong rather than strict —
the last sample is 2026-05-15 while the pin closes 2026-06-29, so any name going ex-dividend in
between correctly sits below raw. A false positive in an audit is as damaging as a missed defect.

**What this layer can and cannot rule out.** It rules out, at quarterly resolution across the full
universe: inflated prices, wrong-instrument contamination, and any adjustment path that is not
monotone. It **cannot** see a corporate action that is unadjusted on *both* sides of its ex-date,
because such a series agrees with raw everywhere and is still discontinuous. That blind spot is not
a limitation of the sample size; it is structural, and it is why layer 2 exists.

---

## Layer 2 — corporate actions: **CLEAN on the census, one defect, one convention conflict**

### The method, and an assumption that failed

The first version of this layer used `PREVCLOSE(ex) / CLOSE(ex−1)` as "the exchange's own
adjustment receipt", on the belief that NSE republishes the previous close on the post-event scale.
**It does not.** ADANIPOWER's 5:1 split (ex 2025-09-22) prints `prevclose = 709.40` against a close
of `170.25`. Every event accordingly returned a factor of exactly 1.0, which would have read as
"the exchange never adjusts anything" and silently turned the audit into a null instrument that
passed everything. It is recorded because an audit that hides its wrong turns is worth less than
one that shows them.

The replacement assumes nothing. Write the pin as `pickle(t) = raw(t) × adj(t)`. Both sides are
observable, so `adj(t)` is measurable on any session. An event of factor `f` must divide every bar
*before* its ex-date by `f` and leave the rest alone, so

    f_implied = adj(ex) / adj(ex−1)

and a correct series has `f_implied == f`. One quantity answers all three parts of the question:
**adjusted**, **correctly scaled**, and **on the right date**.

### Pass A — the census: every event NSE published

234 corporate actions in the pinned universe, 2019-01-01 to 2026-07-01, grouped into 227 event-days
(a bonus and a split declared on the same ex-date are one price step, so their factors multiply —
judging them separately convicted BAJAJFINSV, BAJFINANCE, EASEMYTRIP, 360ONE, CGCL and NAZARA
falsely in an earlier pass).

| Resolution | n | Meaning |
|---|---:|---|
| `CORRECTLY_ADJUSTED` | **187** | implied factor equals the exchange's stated ratio, on the ex-date |
| `CONVENTION_DEMERGER_BACKADJUSTED` | **22** | vendor back-adjusted a value-leaving event → **owner** |
| `LEFT_UNADJUSTED_AS_INTENDED` | **15** | demerger left as an honest discontinuity, per repo convention |
| `DEFECT_MISSCALED` | **1** | HGS 2022-02-22 |
| `NO_EXCHANGE_DATA` | 2 | ACUTAAS 2025-04-25, LICI 2026-05-29 — unresolved, not passed |

Splits and bonuses therefore resolve **187 exact out of 188**; the 37 demergers split 15 / 22 on
convention (below).

**The one arithmetic defect.** HGS, ex 2022-02-22, "Bonus 2:1" → expected factor 2.0, implied
**2.0207** — off by 1.03%. HGS holds no trade in the run of record and no position in the live
book. Recorded, not corrected.

**The convention conflict — this is an owner decision, not an error.** For 22 demergers the vendor
back-adjusted the pre-ex history (RELIANCE ×1.083 for the Jio Financial spin-off, ITC ×1.039,
SIEMENS ×1.704, EDELWEISS ×1.850, NMDC ×1.301 and 17 others). That is the *total-return* convention:
the spun-off shares are treated as a distribution the holder received. It is arithmetically
defensible and it **contradicts this repo's committed convention**, which
`data/corporate_actions_demergers.csv` states plainly — back-adjusting a demerger "FABRICATES a
soaring trend slope (e.g. VEDL: raw sma200_slope_63 2.16 → 24.94)".

Both readings, neither weighed:

- *The vendor is right.* The holder did receive value; a continuous total-return series is the
  correct input to a momentum signal, and the 22 names are internally consistent.
- *The repo is right.* The listed entity genuinely shrank; smoothing the discontinuity invents
  trend the listed company never had, which is precisely the VEDL failure the CSV was written for.

What makes it an owner item rather than a footnote is that **the pin does both**. VEDL, ABFRL,
RAYMOND, SKFINDIA and 11 others are left as −55% to −65% cliffs while RELIANCE and ITC are smoothed.
Whichever convention is chosen, the pin is currently not applying it uniformly, and the four-row
reference CSV covers four of the 37 demergers in the window.

### Pass B — the complement: is every discontinuity a real event?

Pass A only ever looks at real ex-dates, so it cannot see a jump that no event explains. Pass B
scans the pin for every single-session move beyond −40% / +60% and resolves each against the
exchange. **18 found.**

| Resolution | n |
|---|---:|
| `GENUINE_MOVE` / `GENUINE_MOVE_ON_CA_DATE` | 7 |
| `DEFECT_UNEXPLAINED_JUMP` | **9** |
| `NO_EXCHANGE_DATA` | 2 |

**On the provenance of this list.** The blind session's own extreme-move list is *not in this
repo* — `SESSION4_BLIND_REPLICATION.md` records findings F1–F4 only and states plainly that the raw
report was never filed here. This audit therefore did not work from a checklist: it enumerated every
single-session move beyond −40% / +60% in the pin independently and resolved all 18. The three names
the owner quoted (ABFRL, RAYMOND, VEDL) are among them. That is a stronger position than checking
someone else's list, but it means this audit cannot certify that its 18 *are* their eight, and it
does not claim to.

The seven genuine ones reproduce the exchange to four decimal places: **VEDL −64.90% (exchange
−64.90%), ABFRL −66.59% (−66.59%), RAYMOND −64.76% (−64.76%), SKFINDIA −54.75% (−54.75%), TMPV
−40.15% (−40.15%, recovered via ISIN), ABREL −55.36% (−55.36%, via ISIN), YESBANK −56.11%
(−56.11%)**. All are **genuine moves, correctly left alone**. None is a defect.

Of the nine defects, **four are INDIAMART** (2019-10-27 +104%, 2019-10-29 −51%, 2020-11-14 +99%,
2020-11-17 −51%) — the Diwali Muhurat sessions, where the pin carries a doubled bar that reverts
two days later. The repo already knows: `run_bhanushali_sixstep.ERRATUM_BARS` names exactly
`("INDIAMART","2019-10-27")` and `("INDIAMART","2020-11-14")`. **The `drop_erratum` flag defaults to
False, so those bars are in the run of record.** Known, pre-declared, gated off — recorded here as
independent rediscovery, which is a useful validation of the instrument. Two more (CDSL 2017-07-03,
J&KBANK 2017-02-27) sit in the pre-2019 warm-up head the programme does not trade.

The two `NO_EXCHANGE_DATA` rows are PATANJALI 2020-01-27 and ALOKINDS 2020-02-19. PATANJALI's ISIN
resolves the event session (as RUCHI) but not the session before it — the correct answer for a
post-insolvency relisting, where there *is* no prior session on the same basis. Reported as
unresolved rather than assumed benign.

The remaining three are the subject of layer 2b.

---

## Layer 2b — series continuity: **DEFECT**

### What was found

Seven names carry an implied adjustment factor that **falls** as time advances. No correct
adjustment can do that. Each fall was localised to the exact session by bisection against the
exchange:

| Name | Seam session | Step | Series return that day | Exchange return | Fabricated |
|---|---|---:|---:|---:|---:|
| GPIL | **2024-01-01** | ×5.00 | −79.50% | +2.48% | −82.0pp |
| CGCL | **2024-01-01** | ×4.00 | −74.83% | +0.68% | −75.5pp |
| MOTILALOFS | **2024-01-01** | ×4.00 | −74.61% | +1.55% | −76.2pp |
| CONCOR | **2025-01-01** | ×1.25 | −20.88% | −1.10% | −19.8pp |
| TRENT | **2026-01-01** | ×1.50 | −33.05% | +0.43% | −33.5pp |
| MAHLIFE | 2025-05-14 | ×1.0884 | −4.83% | +3.59% | −8.4pp |
| UPL | 2024-11-18 | ×1.0425 | −2.05% | +2.11% | −4.2pp |

**Five of seven land on 1 January**, with clean rational factors. That is a mechanism, not a
coincidence, so the class was closed rather than sampled: `adj` was probed on the last session of
each year and the first of the next, for **every one of the 710 names across every year boundary
2018–2026**. It returns exactly these five and no others. **The January-boundary class is complete.**

### The mechanism, corroborated by a second field

The pin's history is assembled from blocks of different adjustment vintage. Within a block the
adjustment is correct; across the boundary it is not. CGCL is the clearest case: its real split+bonus
(factor 4) has ex-date 2024-03-05 and pass A resolves it `CORRECTLY_ADJUSTED`. The bars from
2024-01-01 to 2024-03-04 duly carry the ÷4. **The bars before 2024-01-01 do not** — so the split
adjustment was applied to a trailing window of the history instead of all of it, and the boundary
of that window prints as a −74.8% crash on a day the stock rose 0.68%.

Volume settles it independently. Inside each seam segment the volume ratio moves in lockstep with
the price factor — CGCL price 0.2496 / volume 4.0, GPIL 0.1977 / 5.0, MOTILALOFS 0.2461 / 4.0,
CONCOR 0.7864 / 1.25. Two independently stored fields agreeing rules out a price-only artifact: the
segment is genuinely a correctly-adjusted block sitting next to an unadjusted one.

### Why the repo's own guards could not see it

Every corporate-action detector in this repo is a threshold on move size: `_CORP_ACTION_MOVE = 0.50`
in the momentum cleaner, `≥50%` in the M6 demerger scan, `<−45%` in the `DATA_BUG_unadjusted_splits`
scan. A vintage seam produces a step of *whatever the pending corporate action happens to be*.

- **GPIL, CGCL, MOTILALOFS** (−75% to −80%) clear every threshold and are already on the record.
- **CONCOR (−20.9%), TRENT (−33.1%), MAHLIFE (−4.8%), UPL (−2.1%) clear none of them.** They were
  invisible to every scan this repo has ever run, and they are invisible to the momentum path's
  cleaner too — which means the momentum engine does not repair them either.

**This is the finding.** Not "three more unadjusted splits", but: *the defect class is not
size-bounded, and every existing guard is.*

### Both readings — the two items that stop here

**(a) The backtest reading — bounded and small.**
Four trades in the run of record's substrate are open across a seam, together **−23.89 R = −1.28%
of the book's 1,868.62 R**:

| Trade | R | Status |
|---|---:|---|
| CGCL 2023-10-30 → 2024-01-08 | −17.325 | already on the record (`DATA_BUG_unadjusted_splits.md`) |
| GPIL 2023-12-18 → 2024-01-08 | −3.807 | already on the record |
| MOTILALOFS 2023-10-16 → 2024-01-08 | −1.320 | already on the record |
| **CONCOR 2024-01-08 → 2025-01-06** | **−1.438** | **NEW — below every existing detector threshold** |

The three known figures reproduce the committed ones exactly, which validates the measurement. The
increment this audit adds to the *backtest* is one trade and −1.438R. That is small, and saying so
plainly is part of the finding.

**(b) The live reading — active now, and it flips a live gate.**
TRENT's seam is 2026-01-01. Its pre-seam bars sit 1.5× too high, and the 44-week window still
contains 17 of them. Measured today:

| | 44-week SMA | close / SMA | `close_above_sma` |
|---|---:|---:|---|
| **as pinned** | 3,445.78 | 0.9456 | **False** |
| seam-corrected | 2,852.29 | 1.1423 | **True** |

TRENT is a **top-decile-by-R name** (+20.76R historically). As pinned, it is excluded from the live
swing universe by a data artifact, and it stays excluded until the seam leaves the 44-week window
around **2026-11-06**. The pin is also the live cache — `run_bhanushali_cron._refresh_ohlcv` merges
into this same file with no cleaning step — so this is not a backtest curiosity.

Both readings are stated; neither is weighed. **No correction is applied.** Repairing the seam
changes historical bars and therefore re-anchors the determinism guard (1.1319 / 255) and every
pinned assertion downstream — a pin re-anchor is quarterly-review/governance class per CLAUDE.md,
not a session action. It also lands in the same decision as the existing survivorship re-anchor
(finding 0025) and the demerger-convention item above, which argues for deciding them together.

---

## Layer 3 — atomic trade: **CLEAN, 10 of 10 fields exact**

**The trade, selected mechanically.** The run of record was regenerated (`Sharpe 1.1319`, closed
ledger 249) and the trade chosen as the one whose R is closest to the **median R of the closed
ledger**, restricted to the inter-decile band — middling by construction, neither a winner whose
arithmetic flatters the engine nor a disaster dominated by one exit rule. The rule is recomputed at
run time, so it cannot drift into a hand-picked example.

> **VGUARD · entry 2019-07-29 · exit 2019-10-29 · R = 0.305 · reason `time`**
> (ledger median R = 0.3050; inter-decile band [−1.245, +2.424])

**Price truth over the trade's life.** All 70 sessions from ten bars before the signal week to the
exit were pulled from the exchange. Exact-to-raw agreement is **0 of 70 — and that is the correct
answer**: the series is dividend-adjusted, so it sits below raw by a near-constant factor. What must
hold is that the factor is *constant across the trade*, because a constant cancels out of every
ratio the engine forms. It is: `adj` ranges 0.971048 → 0.974300, a 0.335% spread whose only step is
on **2019-07-16, thirteen days before entry**; inside the holding period it is constant to six
decimal places. Maximum daily return gap vs the exchange: 0.0034.

### The worked example — what each engine field means

| # | Field | Value | How it is produced |
|---:|---|---:|---|
| 1 | signal-week low → `stop0` | **210.06** | lowest low of the signal week (2019-07-22…26); the stop is this, not an ATR |
| 2 | signal-week high | 233.45 | upper bound of the fill-eligible range |
| 3 | `rank` (CRS) | 0.0864 | cross-sectional strength; sets fill priority under the cash cap |
| 4 | `entry` | **227.01** | the **open** of the first entry-window session with `lo < open < hi` |
| 5 | `risk0` (per share) | 16.95 | `entry − stop0` — the R denominator, fixed at entry, never re-based |
| 6 | `tp2` | 260.92 | `entry + 2 × risk0` — the half-booking trigger, never reached here |
| 7 | sizing equity | 1,644,799.97 | book equity at the **end of the previous book session** (not the ticker's) |
| 8 | `shares` | 1,940.44 | `sizing_eq × 2% / risk0` — risk-based, fractional, uncapped in this config |
| 9 | risk as % of equity | 2.0000 | the engine asserts this invariant on every fill |
| 10 | cost leg (in) | 0.003500 | 0.13% STT+brokerage + 0.22% MID_CAP slippage; no impact term (ADV ₹13.3cr) |
| 11 | `cash_out` | 442,045.83 | `shares × entry × (1 + cost_leg)` — cash actually leaves the book |
| 12 | weekly ladder | 13 weeks | every weekly close tested: stop (≤210.06) never hit, `tp2` never hit |
| 13 | `held_weeks` / reason | 13 / `time` | `CAP_WEEKS = 13` weekly closes with no other trigger |
| 14 | exit trigger close | 2019-10-27 | the decision is taken at a **weekly close** |
| 15 | `exit_date` / `exit_px` | 2019-10-29 / **232.18** | filled at the **next session's open** — decision and fill are different days |
| 16 | `R` | **0.305** | `(exit_px − entry) / risk0` = 5.1638 / 16.9518 |
| 17 | `proceeds` | 448,947.28 | `shares × exit_px × (1 − cost_leg)` |
| 18 | `net_pnl` | **6,901.45** | `proceeds − cash_out`; identity residual **0.00000000** |
| 19 | `stt_paid` | **891.03** | 0.1% on both legs' gross — a subset of the cost legs, not additional |
| 20 | equity contribution | +0.4196% | of equity at fill; the daily curve delta is **not** this number |

**Every one of the ten independently re-derived fields matches the engine's ledger exactly** —
entry, stop, rank, exit session, exit price, exit reason, weeks held, R, net P&L and STT.

**R survives rebuilding from raw exchange prices.** Recomputed entirely from NSE's unadjusted
bars — entry open 233.00, exit open 238.30, signal-week low 215.60 — R = **0.3046**, against
**0.3046** on the pinned series. Difference **0.0000**. The constant adjustment cancels exactly, as
it must.

**Two definitional points the exercise settled.**

*`trades` counts resolved positions, not closed trades.* Called with `return_state=True` the open
book is left unrealised and `trades == 249 == the closed ledger`; the determinism guard calls it
without `return_state`, which realises the 6 still-open positions as reason `eos` and reports
**255** — on the same equity curve and the same Sharpe 1.1319. Neither figure is wrong; they count
different things. This is the same closed-vs-open distinction `DEFINITIONS_REGISTER` §4 records for
the paper book's `total_trades`.

*Restating a constant is only evidence while it still equals the engine's.* This script restates
the cost model as literals rather than importing it. The first run therefore disagreed on net P&L
by ₹1,069 on a ₹6,901 trade, while price, dates, shares, R and STT all matched exactly — the audit
had written MID_CAP slippage as 10bp and SMALL_CAP as 20bp, plausible round numbers, against the
true 22bp and 40bp. A version that imported the constant would have agreed with the engine and
proved nothing. The script now asserts its literals against `nq.engine.portfolio.SLIPPAGE`, the ADV
tier thresholds, `STT_BROK`, `STT_PCT`, `RISK` and `CAP_WEEKS`, so drift on either side fails loudly.

---

## What this audit can and cannot rule out

**Ruled out.** Prices above the exchange's, anywhere in the pinned universe at quarterly resolution
(0 of 17,801). Wrong-instrument contamination. Non-monotone adjustment paths outside the seven named
names. Unhandled splits and bonuses (187 of 188 exact; one off by 1%). Mis-dated adjustments. Any
January-boundary vintage seam (census-complete, 5 found). Arithmetic error in the engine's
trade→ledger→equity path, on a middling trade, to the paise.

**Not ruled out, and stated as open bounds.**

1. **Intra-quarter seams away from a year boundary.** The quarterly sample detects a seam only when
   it is not cancelled by a real corporate action inside the same inter-sample window. MAHLIFE and
   UPL show this class exists off the year boundary. Closing it needs `adj` on every session, i.e.
   the full daily bhavcopy — roughly 1,850 sessions, mechanical and inexpensive, but not run here.
2. **Corporate actions before 2019-01-01.** The census starts at 2019 in line with the programme's
   trust boundary; the 2017–2018 warm-up head is unaudited, and two of the nine unexplained jumps
   sit in it.
3. **Rights issues generally.** MAHLIFE (×1.088) and UPL (×1.043) are rights-issue factors. Rights
   are not in the split/bonus/demerger census, so their handling is only sampled, not enumerated.
4. **One trade is one trade.** Layer 3 proves the arithmetic path on a `time`-exit trade. The `stop`,
   `trail`, `half` and `eos` branches are pinned by the golden master but were not hand-computed here.

---

## Items that stop at the owner's door

Neither is corrected, and neither is weighed.

**F-1 · The vintage seam.** 7 fabricated price steps; the January-boundary class is complete at 5.
Backtest exposure −23.89R = −1.28% of book R across 4 trades, of which **CONCOR (−1.438R) is new**.
Live exposure: **TRENT's 44-week gate reads False as pinned and True corrected**, and stays wrong
until ~2026-11-06, on a top-decile-by-R name. Repair re-anchors the determinism guard and every
pinned assertion — governance class. Naturally decided together with the survivorship re-anchor
(0025).

**F-2 · Demerger convention.** The pin back-adjusts 22 demergers and leaves 15 as cliffs. Either
convention is defensible; applying both is not. The committed reference covers 4 of 37 events.

**Recorded, no door.** HGS bonus mis-scaled by 1.03% (no trade, no position). INDIAMART's four
Muhurat bars (already pre-declared as `ERRATUM_BARS`, drop gated off by default). Two pre-2019
jumps in the untrusted head.

---

## Cross-references

- Evidence: `layer1_prices.json` · `layer2_corpactions.json` · `layer2b_seams.json` ·
  `layer3_atomic_trade.json` · `bhavcopy_sample.parquet` · `bhavcopy_events.parquet` ·
  `corpactions_raw.parquet`
- `research/substrate/DATA_BUG_unadjusted_splits.md` — the prior, threshold-bounded statement of
  the same class
- `diagnostics/research/m6_demerger_scan.md` — the ≥50% detector this audit shows is size-bounded
- `diagnostics/research/DEFINITIONS_REGISTER.md` — §4 closed-vs-open trade counts
- `diagnostics/research/verification_audit_2026Q3/INDEX.md` — the parent audit and its guards

---

# Addendum — 2026-08-06, same day: the cause is upstream, and the guard found two more

Added when the monotonicity guard (item 1 below) was built and run. The findings above stand as
measured; three statements in them are **corrected or refined**, and the corrections matter more
than the original wording did. Nothing in the layer verdicts changes.

## C-1 · The seams are the VENDOR's, not this repo's assembly — this is the important correction

The body above inferred a "vintage seam" from *how the cache was assembled*: a trailing block
carrying an adjustment the earlier block does not. The shape of that description is right and the
attribution was wrong.

**A fresh, single-call download from the vendor reproduces all 13 seams exactly** — same sessions,
same factors, including the two INDIAMART Muhurat bars. The pin is byte-faithful to what the vendor
serves (pin/fresh ratio constant to 4dp for every seam name). So:

- This repo did not create them, and no change to how the cache is stitched removes them.
- **Rebuilding the cache does not heal them.** The live cron's monthly clean rebuild — whose stated
  purpose is exactly to put the whole cache "on one adjustment basis" — provides **no protection
  against this class**, because a clean rebuild faithfully reproduces the vendor's discontinuity.
- Every downstream consumer of the vendor inherits it, which is why the guard is worth more than a
  one-off repair.

The mechanism is now named per event rather than guessed. The vendor applies a corporate action's
adjustment only from **1 January of the ex-date's year** onward, leaving earlier history unadjusted:

| Name | Corporate action | Ex-date | Adjustment applied from | Fabricated step |
|---|---|---|---|---|
| TRENT | Bonus 1:2 (factor 1.50) | 2026-06-04 | 2026-01-01 | −33.05% |
| CONCOR | Bonus 1:4 (factor 1.25) | 2025-07-04 | 2025-01-01 | −20.88% |
| CGCL | split+bonus (factor 4) | 2024-03-05 | 2024-01-01 | −74.83% |
| GPIL | factor 5 | 2024 | 2024-01-01 | −79.50% |
| MOTILALOFS | factor 4 | 2024 | 2024-01-01 | −74.61% |

This is why layer 2 pass A resolved these same events `CORRECTLY_ADJUSTED`: the step **at the
ex-date is right**. The defect is a second, spurious step at the year boundary. Both are true at
once, and only the complement pass could see the second one.

It affects a **minority** of events — 5 of the 188 splits/bonuses in the census leave a year-boundary
seam — so this is a pattern, not a universal vendor rule, and no model of vendor behaviour should be
built on it. That is precisely the argument for a guard rather than a correction formula.

## C-2 · "Zero above raw" holds at the resolution it was measured, and one exception exists at higher resolution

The body's strongest claim — the pinned close is above the exchange's raw close on **zero** of
17,801 name-days — is correct **on the 30-date quarterly grid**. The guard's reference is denser
(519 dates, 51,053 name-days, adding both sides of every year boundary and every corporate-action
session). On that grid there are **2 name-days above raw**: one in the pre-2019 warm-up head
(J&KBANK, adj 1.95), and **one inside the trusted period — HBLENGINE 2024-12-23, adj 1.0297**.

Two in 51,053 (0.004%) does not overturn the CLEAN verdict for layer 1, and the exception is the
same HBLENGINE anomaly named below rather than a separate defect. The claim is restated at its
true resolution because the original was quoted as an absolute.

## C-3 · Two seams the audit's quarterly grid could not see

The denser probe grid found two monotonicity violations the 30-date sample missed. Neither is
explained by any corporate action in the NSE record, and neither has been localised to its exact
session:

| Name | Window | Step | Cache vs exchange on the session | Status |
|---|---|---:|---|---|
| **HBLENGINE** | 2024-12-23 → 2024-12-24 | ×1.0336 | cache **−0.65%**, exchange **+2.68%** | **OPEN — inside the trusted period** |
| TRENT | 2019-03-06 → 2019-03-18 | ×1.0214 | cache +10.56%, exchange +12.93% | OPEN |

HBLENGINE is the consequential one: it sits inside the period the programme trades, and the nearest
corporate actions (dividends of Re 0.50 and Re 1) are two orders of magnitude too small to explain
a 3.36% step. Both are carried in the guard's register marked `OPEN-undiagnosed` so they are not
mistaken for settled, and both reproduce in a fresh vendor pull.

This is the audit's own limit #1 closing on itself: the body stated that intra-quarter seams away
from a year boundary were sampled rather than enumerated. Denser probing found two immediately.

## C-4 · The live-exposure sentence was right, for the wrong reason

The body said TRENT's gate is wrong live "and the pin is also the live cache". That reasoning was
wrong: `data/ohlcv.pkl` is gitignored and is **two different artifacts** — the pinned release on a
research machine, and a monthly-rebuilt actions-cache instance on the cron runner.

The conclusion survives C-1 intact, and is now confirmed directly rather than inferred. The live
weekly panel of 2026-07-31 prints TRENT `sma44 = 3248.73`, `close_above_sma = False`. A fresh
single-vintage pull reproduces `sma44 = 3248.88` — a 0.005% match — and the seam-corrected series
gives `sma44 = 2809.84`, `close/sma = 1.0698`, **`close_above_sma = True`**.

**Scope, stated precisely:** only TRENT has a seam inside the current 44-week window. CONCOR's
(2025-01-01), HBLENGINE's (2024-12-24), UPL's and the 2024 seams have all aged out; MAHLIFE is not
in the live 500-name universe. **TRENT is the only live-affected name today, and it stays affected
until roughly 2026-11-06.** None of the five open positions (DELHIVERY, INDUSINDBK, NESTLEIND, CUB,
HEG) is a seam name, so no held position's entry, stop or NAV is touched by any of this.

## C-5 · The guard

`nq/data/adjustment_guard.py` now asserts the invariant on the refresh path, with a 13-entry
register carrying provenance. See `LIVE_REPAIR_DECISION.md` for the repair question, which remains
the owner's.
